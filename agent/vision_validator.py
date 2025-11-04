"""
Vision-based validation of workflow screenshots using multimodal AI.
Uses Gemini Flash 2.0 (primary) with Claude Sonnet 4.5 (fallback) for screenshot analysis.
"""
import os
import logging
import json
import base64
import tempfile
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageDraw
import google.generativeai as genai
from anthropic import Anthropic
from config import Config

logger = logging.getLogger(__name__)


class VisionValidator:
    """
    Validates workflow screenshots using multimodal AI models.
    Determines screenshot validity, relevant UI regions, and provides step refinements.
    """

    def __init__(self, primary_model: str = "gemini", fallback_model: str = "claude"):
        """
        Initialize vision validator.

        Args:
            primary_model: Primary model to use ("gemini" or "claude")
            fallback_model: Fallback model if primary fails
        """
        self.primary_model = primary_model
        self.fallback_model = fallback_model

        # Configure models
        if "gemini" in [primary_model, fallback_model]:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            logger.info(f"[VISION_VALIDATOR] Gemini configured")

        if "claude" in [primary_model, fallback_model]:
            self.claude_client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            logger.info(f"[VISION_VALIDATOR] Claude configured")

        logger.info(f"[VISION_VALIDATOR] Initialized with primary={primary_model}, fallback={fallback_model}")

    def _create_grid_overlay(self, image_path: str, grid_size: int = 3) -> str:
        """
        Create a copy of the image with a 3x3 grid overlay for vision model analysis.

        Args:
            image_path: Path to original image
            grid_size: Grid size (default 3 for 3x3)

        Returns:
            Path to temporary image with grid overlay
        """
        try:
            # Load image
            image = Image.open(image_path)
            # Create a copy to draw on
            image_with_grid = image.copy()
            draw = ImageDraw.Draw(image_with_grid)

            width, height = image.size

            # Calculate cell dimensions
            cell_width = width / grid_size
            cell_height = height / grid_size

            # Draw vertical grid lines (white, thick enough to see)
            line_thickness = max(3, int(width * 0.002))  # At least 3px, scales with image size
            for i in range(1, grid_size):
                x = int(i * cell_width)
                draw.line([(x, 0), (x, height)], fill='white', width=line_thickness)

            # Draw horizontal grid lines
            for i in range(1, grid_size):
                y = int(i * cell_height)
                draw.line([(0, y), (width, y)], fill='white', width=line_thickness)

            # Add grid cell labels (row, col) at center of each cell
            from PIL import ImageFont
            try:
                # Try to use a small font
                font_size = max(12, int(min(cell_width, cell_height) * 0.15))
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                # Fallback to default font
                font = ImageDraw.getfont()

            for row in range(1, grid_size + 1):
                for col in range(1, grid_size + 1):
                    # Calculate center of cell
                    center_x = int((col - 0.5) * cell_width)
                    center_y = int((row - 0.5) * cell_height)

                    # Draw label with background for visibility
                    label = f"({row},{col})"

                    # Get text bounding box for background
                    bbox = draw.textbbox((center_x, center_y), label, font=font, anchor="mm")

                    # Draw semi-transparent background
                    padding = 4
                    draw.rectangle([
                        bbox[0] - padding,
                        bbox[1] - padding,
                        bbox[2] + padding,
                        bbox[3] + padding
                    ], fill='black', outline='white', width=2)

                    # Draw text
                    draw.text((center_x, center_y), label, fill='white', font=font, anchor="mm")

            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            image_with_grid.save(temp_file.name, 'PNG')
            temp_file.close()

            logger.debug(f"[VISION_VALIDATOR] Created grid overlay: {temp_file.name}")
            return temp_file.name

        except Exception as e:
            logger.error(f"[VISION_VALIDATOR] Failed to create grid overlay: {str(e)}", exc_info=True)
            # Return original image path if overlay fails
            return image_path

    async def validate_screenshot(
        self,
        image_path: str,
        step_context: Dict
    ) -> Dict:
        """
        Validate screenshot and get grid location of relevant UI elements.

        Args:
            image_path: Path to screenshot
            step_context: Dictionary containing:
                - task_description: Overall task
                - step_description: Specific step description
                - step_number: Step number
                - url: Current URL
                - action: Action details

        Returns:
            Dictionary with validation results:
            {
                "is_valid": bool,
                "grid_locations": [(row, col), ...],
                "suggested_description": str,
                "reasoning": str,
                "model_used": str
            }
        """
        logger.info(f"[VISION_VALIDATOR] Validating step {step_context.get('step_number')}")
        logger.debug(f"[VISION_VALIDATOR] Context: {json.dumps(step_context, indent=2)}")

        try:
            # Try primary model
            if self.primary_model == "gemini":
                result = await self._validate_with_gemini(image_path, step_context)
            else:
                result = await self._validate_with_claude(image_path, step_context)

            logger.info(f"[VISION_VALIDATOR] Validation successful with {self.primary_model}")
            return result

        except Exception as e:
            logger.warning(f"[VISION_VALIDATOR] Primary model ({self.primary_model}) failed: {str(e)}")

            try:
                # Try fallback model
                logger.info(f"[VISION_VALIDATOR] Trying fallback model: {self.fallback_model}")

                if self.fallback_model == "gemini":
                    result = await self._validate_with_gemini(image_path, step_context)
                else:
                    result = await self._validate_with_claude(image_path, step_context)

                logger.info(f"[VISION_VALIDATOR] Validation successful with fallback ({self.fallback_model})")
                return result

            except Exception as fallback_error:
                logger.error(f"[VISION_VALIDATOR] Both models failed: {str(fallback_error)}", exc_info=True)
                # Return default invalid response
                return {
                    "is_valid": False,
                    "grid_locations": [],
                    "suggested_description": step_context.get('step_description', ''),
                    "reasoning": f"Validation failed: {str(fallback_error)}",
                    "model_used": "none"
                }

    async def _validate_with_gemini(
        self,
        image_path: str,
        step_context: Dict
    ) -> Dict:
        """
        Validate screenshot using Gemini Flash 2.0.

        Args:
            image_path: Path to screenshot
            step_context: Step context dictionary

        Returns:
            Validation result dictionary
        """
        logger.info(f"[VISION_VALIDATOR] Using Gemini for validation")

        # Create grid overlay for vision model
        grid_image_path = self._create_grid_overlay(image_path, grid_size=3)

        try:
            # Load image with grid overlay
            image = Image.open(grid_image_path)

            # Build prompt (updated to mention grid overlay)
            prompt = self._build_validation_prompt(step_context, has_grid_overlay=True)

            # Call Gemini API
            model = genai.GenerativeModel(Config.GEMINI_MODEL)
            response = await model.generate_content_async([prompt, image])

            # Parse response
            result = self._parse_gemini_response(response.text, step_context)
            result['model_used'] = 'gemini'

            return result

        finally:
            # Clean up temporary grid overlay file
            try:
                if grid_image_path != image_path and os.path.exists(grid_image_path):
                    os.remove(grid_image_path)
                    logger.debug(f"[VISION_VALIDATOR] Cleaned up grid overlay: {grid_image_path}")
            except Exception as cleanup_error:
                logger.warning(f"[VISION_VALIDATOR] Could not remove grid overlay: {str(cleanup_error)}")

    async def _validate_with_claude(
        self,
        image_path: str,
        step_context: Dict
    ) -> Dict:
        """
        Validate screenshot using Claude Sonnet 4.5.

        Args:
            image_path: Path to screenshot
            step_context: Step context dictionary

        Returns:
            Validation result dictionary
        """
        logger.info(f"[VISION_VALIDATOR] Using Claude for validation")

        # Create grid overlay for vision model
        grid_image_path = self._create_grid_overlay(image_path, grid_size=3)

        try:
            # Load and encode image with grid overlay
            with open(grid_image_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            # Determine image type
            ext = os.path.splitext(grid_image_path)[1].lower()
            media_type = "image/png" if ext == ".png" else "image/jpeg"

            # Build prompt (updated to mention grid overlay)
            prompt = self._build_validation_prompt(step_context, has_grid_overlay=True)

            # Call Claude API
            message = self.claude_client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }],
            )

            # Parse response
            response_text = message.content[0].text
            result = self._parse_claude_response(response_text, step_context)
            result['model_used'] = 'claude'

            return result

        finally:
            # Clean up temporary grid overlay file
            try:
                if grid_image_path != image_path and os.path.exists(grid_image_path):
                    os.remove(grid_image_path)
                    logger.debug(f"[VISION_VALIDATOR] Cleaned up grid overlay: {grid_image_path}")
            except Exception as cleanup_error:
                logger.warning(f"[VISION_VALIDATOR] Could not remove grid overlay: {str(cleanup_error)}")

    def _build_validation_prompt(self, step_context: Dict, has_grid_overlay: bool = False) -> str:
        """
        Build validation prompt for vision models.

        Args:
            step_context: Step context dictionary
            has_grid_overlay: If True, mentions the visual grid overlay in the prompt

        Returns:
            Formatted prompt string
        """
        task_desc = step_context.get('task_description', 'Unknown task')
        step_desc = step_context.get('step_description', 'Unknown step')
        step_num = step_context.get('step_number', '?')
        url = step_context.get('url', 'Unknown URL')
        action = step_context.get('action', {})

        grid_notice = ""
        if has_grid_overlay:
            grid_notice = """
**IMPORTANT**: The screenshot has a 3x3 grid OVERLAY with white lines and labeled cells.
- Grid cells are labeled (1,1) to (3,3) directly on the image
- These grid lines and labels are ONLY for your reference
- Use them to accurately identify which cells the UI element occupies
- The grid coordinates match the response format you'll provide
"""

        prompt = f"""You are analyzing a workflow screenshot to validate and refine it for documentation purposes.
{grid_notice}

**Workflow Context**:
- Overall Task: {task_desc}
- Current Step: Step {step_num}
- Step Description: {step_desc}
- URL: {url}
- Action: {json.dumps(action, indent=2)}

**Your Task**:
Analyze the screenshot and provide a structured response answering these questions:

1. **Is this screenshot valid for the described step?**
   - Does it show the correct URL/page?
   - Is the described UI element visible (button, form, modal, etc.)?
   - Does it match the action context?
   - Answer: true or false

2. **Where is the relevant UI element located? (Include surrounding context)**
   - The screenshot has a visible 3x3 grid overlay with labeled cells
   - Each cell is labeled directly on the image: (1,1) to (3,3)
   - Look at the grid lines and labels to identify which cells the element occupies
     ```
     (1,1) (1,2) (1,3)  <- Top row
     (2,1) (2,2) (2,3)  <- Middle row
     (3,1) (3,2) (3,3)  <- Bottom row
     ```
   - **CRITICAL**: Select 2-4 cells to include CONTEXT around the element
   - Include surrounding UI elements (nearby buttons, labels, navigation)
   - DON'T just select the single cell containing the element - too narrow!
   - DO select adjacent cells to show WHERE the element is in the interface

   **How to identify cells:**
   - Look at the white grid lines overlaid on the screenshot
   - Check the (row,col) labels at the center of each grid cell
   - Select all cells that contain or surround the target element

   **Examples:**
   - Search bar at top center: [(1,1), (1,2), (1,3)] - full top row for context
   - Button in middle area: [(2,2), (2,3)] - button + surrounding context
   - Form in center: [(2,1), (2,2), (2,3), (3,2)] - form + navigation context
   - Modal dialog: [(2,2), (2,3), (3,2), (3,3)] - entire modal area

   **Why multiple cells?**
   The cropped image needs to show not just the element, but WHERE it is in the UI.
   A future agent needs to see surrounding elements to locate the target element.

3. **Should the step description be improved?**
   - If yes, provide a refined description that:
     - Is clear and specific
     - Mentions WHERE the element is located
     - Explains WHAT to look for
   - If no, return the original description

**Response Format** (JSON):
```json
{{
  "is_valid": true/false,
  "grid_locations": [(row, col), ...],
  "suggested_description": "Improved step description",
  "reasoning": "Brief explanation of your analysis"
}}
```

**Important**:
- Select 2-4 grid cells (not just 1!) to include context
- Be precise about grid locations
- Only mark as valid if the screenshot clearly shows the described element
- Provide helpful reasoning for your decisions
- If invalid, explain what's wrong or missing
- Remember: The goal is to crop to a useful region, not just the exact element

Analyze the screenshot now and respond with ONLY the JSON object."""

        return prompt

    def _parse_gemini_response(self, response_text: str, step_context: Dict) -> Dict:
        """
        Parse Gemini response into structured format.

        Args:
            response_text: Raw response from Gemini
            step_context: Original step context

        Returns:
            Parsed validation result
        """
        logger.debug(f"[VISION_VALIDATOR] Parsing Gemini response: {response_text[:200]}...")

        try:
            # Extract JSON from response (may have markdown code blocks)
            response_text = response_text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                # Remove first line (```json) and last line (```)
                response_text = "\n".join(lines[1:-1])

            # Parse JSON
            result = json.loads(response_text)

            # Validate required fields
            if 'is_valid' not in result:
                logger.warning("[VISION_VALIDATOR] Missing 'is_valid' field, defaulting to False")
                result['is_valid'] = False

            if 'grid_locations' not in result or not isinstance(result['grid_locations'], list):
                logger.warning("[VISION_VALIDATOR] Invalid grid_locations, defaulting to center region")
                result['grid_locations'] = [(2, 1), (2, 2), (2, 3)]  # Middle row for context

            # Convert grid_locations to list of tuples
            result['grid_locations'] = [tuple(loc) for loc in result['grid_locations']]

            if 'suggested_description' not in result:
                result['suggested_description'] = step_context.get('step_description', '')

            if 'reasoning' not in result:
                result['reasoning'] = "No reasoning provided"

            logger.info(f"[VISION_VALIDATOR] Parsed result: valid={result['is_valid']}, grids={result['grid_locations']}")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"[VISION_VALIDATOR] JSON parse error: {str(e)}")
            logger.error(f"[VISION_VALIDATOR] Raw response: {response_text}")

            # Return fallback result
            return {
                "is_valid": False,
                "grid_locations": [(2, 1), (2, 2), (2, 3)],  # Middle row for context
                "suggested_description": step_context.get('step_description', ''),
                "reasoning": f"Failed to parse response: {str(e)}"
            }

        except Exception as e:
            logger.error(f"[VISION_VALIDATOR] Parse error: {str(e)}", exc_info=True)

            return {
                "is_valid": False,
                "grid_locations": [(2, 1), (2, 2), (2, 3)],  # Middle row for context
                "suggested_description": step_context.get('step_description', ''),
                "reasoning": f"Parse error: {str(e)}"
            }

    def _parse_claude_response(self, response_text: str, step_context: Dict) -> Dict:
        """
        Parse Claude response into structured format.

        Args:
            response_text: Raw response from Claude
            step_context: Original step context

        Returns:
            Parsed validation result
        """
        logger.debug(f"[VISION_VALIDATOR] Parsing Claude response: {response_text[:200]}...")

        # Claude responses are parsed the same way as Gemini
        return self._parse_gemini_response(response_text, step_context)
