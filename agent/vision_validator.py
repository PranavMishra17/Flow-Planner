"""
Vision-based validation of workflow screenshots using multimodal AI.
Uses Gemini Flash 2.0 (primary) with Claude Sonnet 4.5 (fallback) for screenshot analysis.
"""
import os
import logging
import json
import base64
from typing import Dict, List, Tuple, Optional
from PIL import Image
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

        # Load image
        image = Image.open(image_path)

        # Build prompt
        prompt = self._build_validation_prompt(step_context)

        # Call Gemini API
        model = genai.GenerativeModel(Config.GEMINI_MODEL)
        response = await model.generate_content_async([prompt, image])

        # Parse response
        result = self._parse_gemini_response(response.text, step_context)
        result['model_used'] = 'gemini'

        return result

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

        # Load and encode image
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        # Determine image type
        ext = os.path.splitext(image_path)[1].lower()
        media_type = "image/png" if ext == ".png" else "image/jpeg"

        # Build prompt
        prompt = self._build_validation_prompt(step_context)

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

    def _build_validation_prompt(self, step_context: Dict) -> str:
        """
        Build validation prompt for vision models.

        Args:
            step_context: Step context dictionary

        Returns:
            Formatted prompt string
        """
        task_desc = step_context.get('task_description', 'Unknown task')
        step_desc = step_context.get('step_description', 'Unknown step')
        step_num = step_context.get('step_number', '?')
        url = step_context.get('url', 'Unknown URL')
        action = step_context.get('action', {})

        prompt = f"""You are analyzing a workflow screenshot to validate and refine it for documentation purposes.

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
   - Use a 3x3 grid system to identify the region:
     ```
     (1,1) (1,2) (1,3)  <- Top row
     (2,1) (2,2) (2,3)  <- Middle row
     (3,1) (3,2) (3,3)  <- Bottom row
     ```
   - **CRITICAL**: Select 2-4 cells to include CONTEXT around the element
   - Include surrounding UI elements (nearby buttons, labels, navigation)
   - DON'T just select the single cell containing the element - too narrow!
   - DO select adjacent cells to show WHERE the element is in the interface

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
