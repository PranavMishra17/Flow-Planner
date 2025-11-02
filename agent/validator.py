"""
Claude Vision-based screenshot validator.
Validates that workflow steps completed successfully by analyzing screenshots.
"""
import logging
import base64
import asyncio
from typing import Dict, List, Optional
from anthropic import Anthropic
from config import Config
import os

logger = logging.getLogger(__name__)


class ClaudeValidator:
    """
    AI-powered screenshot validator using Claude's vision capabilities.
    Analyzes screenshots to determine if workflow steps succeeded.
    """

    def __init__(self):
        """Initialize Claude validator with API configuration"""
        if not Config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        logger.info("[VALIDATOR] Claude validator initialized")

    async def validate_steps(self, steps: List[Dict], screenshot_base_dir: str = None) -> List[Dict]:
        """
        Validate all executed steps by analyzing their screenshots.

        Args:
            steps: List of executed steps with screenshot paths
            screenshot_base_dir: Base directory where screenshots are stored (defaults to Config.SCREENSHOTS_DIR)

        Returns:
            Updated list of steps with validation results

        Raises:
            Exception: If validation fails critically
        """
        if not Config.ENABLE_VALIDATION:
            logger.info("[VALIDATOR] Validation disabled, skipping")
            for step in steps:
                step['validated'] = False
                step['validation_reason'] = "Validation disabled"
            return steps

        # Set the base directory for finding screenshots
        self.screenshot_base_dir = screenshot_base_dir or Config.SCREENSHOTS_DIR

        logger.info(f"[VALIDATOR] Validating {len(steps)} steps")
        logger.info(f"[VALIDATOR] Looking for screenshots in: {self.screenshot_base_dir}")

        validated_steps = []
        for step in steps:
            try:
                # Skip validation for failed steps
                if not step.get('success', False):
                    step['validated'] = False
                    step['validation_reason'] = "Step execution failed"
                    validated_steps.append(step)
                    continue

                # Validate the step
                validation_result = await self._validate_single_step(step)

                # Add validation results to step
                step['validated'] = validation_result['is_valid']
                step['validation_reason'] = validation_result['reason']
                step['validation_confidence'] = validation_result.get('confidence', 'unknown')

                validated_steps.append(step)

                logger.info(
                    f"[VALIDATOR] Step {step['step_number']}: "
                    f"{'VALID' if step['validated'] else 'INVALID'} - "
                    f"{step['validation_reason']}"
                )

            except Exception as e:
                logger.error(f"[VALIDATOR] Failed to validate step {step['step_number']}: {str(e)}")
                step['validated'] = False
                step['validation_reason'] = f"Validation error: {str(e)}"
                validated_steps.append(step)

        valid_count = sum(1 for s in validated_steps if s.get('validated', False))
        logger.info(f"[VALIDATOR] Validation complete: {valid_count}/{len(steps)} steps valid")

        return validated_steps

    async def _validate_single_step(self, step: Dict) -> Dict:
        """
        Validate a single step by analyzing its screenshot.

        Args:
            step: Step dictionary with screenshot_path

        Returns:
            Dictionary with is_valid, reason, and confidence

        Raises:
            Exception: If validation fails
        """
        screenshot_path = step.get('screenshot_path')
        if not screenshot_path:
            raise ValueError("Step missing screenshot_path")

        # Build full path to screenshot
        full_path = os.path.join(self.screenshot_base_dir, screenshot_path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Screenshot not found: {full_path}")

        # Read and encode screenshot
        screenshot_base64 = self._encode_image(full_path)

        # Build validation prompt
        prompt = self._build_validation_prompt(step)

        # Call Claude API with retry
        result = await self._call_claude_with_retry(prompt, screenshot_base64)

        return result

    def _build_validation_prompt(self, step: Dict) -> str:
        """
        Build the prompt for Claude to validate a screenshot.

        Args:
            step: Step dictionary with description and expected outcome

        Returns:
            Formatted validation prompt
        """
        description = step.get('description', 'Unknown action')
        expected_outcome = step.get('expected_outcome', 'Action should complete successfully')
        action = step.get('action', 'unknown')

        prompt = f"""You are validating that a browser automation step completed successfully.

Step Description: {description}
Action Type: {action}
Expected Outcome: {expected_outcome}

Analyze the screenshot and determine if this step was successful.

Look for:
1. No error messages or alerts
2. The expected outcome is visible in the UI
3. The page is in a stable, loaded state (not showing loading spinners)
4. Any elements mentioned in the description are present

Return your answer in this EXACT JSON format:
{{
  "is_valid": true or false,
  "reason": "Brief 1-sentence explanation of why you determined this",
  "confidence": "high, medium, or low"
}}

Be strict but reasonable. If there are obvious errors or the expected outcome is clearly not met, mark as invalid.
If the page looks correct and no errors are visible, mark as valid.

Return ONLY the JSON object, no additional text."""

        return prompt

    def _encode_image(self, image_path: str) -> str:
        """
        Encode image file to base64, resizing if needed to stay under Claude's 8000px limit.

        Args:
            image_path: Path to image file

        Returns:
            Base64 encoded image string

        Raises:
            Exception: If encoding fails
        """
        try:
            from PIL import Image
            import io

            # Open image
            img = Image.open(image_path)
            width, height = img.size

            # Claude's limit is 8000px per dimension
            MAX_DIMENSION = 8000

            # Check if resizing is needed
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                logger.debug(f"[VALIDATOR] Resizing image from {width}x{height}")

                # Calculate new dimensions maintaining aspect ratio
                if width > height:
                    new_width = MAX_DIMENSION
                    new_height = int((MAX_DIMENSION / width) * height)
                else:
                    new_height = MAX_DIMENSION
                    new_width = int((MAX_DIMENSION / height) * width)

                # Resize image
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.debug(f"[VALIDATOR] Resized to {new_width}x{new_height}")

            # Convert to RGB if needed (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img

            # Save to bytes
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            # Encode to base64
            return base64.standard_b64encode(buffer.read()).decode('utf-8')

        except Exception as e:
            logger.error(f"[VALIDATOR] Failed to encode image: {str(e)}")
            raise

    async def _call_claude_with_retry(
        self,
        prompt: str,
        image_base64: str,
        max_retries: int = 3
    ) -> Dict:
        """
        Call Claude API with exponential backoff retry logic.

        Args:
            prompt: Validation prompt
            image_base64: Base64 encoded screenshot
            max_retries: Maximum number of retry attempts

        Returns:
            Parsed validation result

        Raises:
            Exception: If all retries fail
        """
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                logger.debug(f"[VALIDATOR] Calling Claude API (attempt {attempt + 1}/{max_retries})")

                # Use asyncio to run the synchronous API call
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.messages.create(
                        model=Config.CLAUDE_MODEL,
                        max_tokens=Config.CLAUDE_MAX_TOKENS,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": "image/png",
                                            "data": image_base64
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": prompt
                                    }
                                ]
                            }
                        ]
                    )
                )

                logger.debug("[VALIDATOR] Claude API call successful")

                # Parse response
                result = self._parse_validation_response(response)
                return result

            except Exception as e:
                logger.warning(f"[VALIDATOR] API call attempt {attempt + 1} failed: {str(e)}")

                if attempt < max_retries - 1:
                    logger.info(f"[VALIDATOR] Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("[VALIDATOR] All retry attempts exhausted")
                    raise

    def _parse_validation_response(self, response) -> Dict:
        """
        Parse Claude's response into validation result.

        Args:
            response: Claude API response

        Returns:
            Dictionary with is_valid, reason, and confidence

        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            import json

            # Extract text from response
            text = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]

            text = text.strip()

            # Parse JSON
            result = json.loads(text)

            # Validate structure
            if 'is_valid' not in result:
                raise ValueError("Response missing 'is_valid' field")

            if 'reason' not in result:
                result['reason'] = "No reason provided"

            if 'confidence' not in result:
                result['confidence'] = 'medium'

            return result

        except json.JSONDecodeError as e:
            logger.error(f"[VALIDATOR] Failed to parse JSON response: {str(e)}")
            logger.error(f"[VALIDATOR] Response text: {text[:500]}...")

            # Return a default invalid result
            return {
                'is_valid': False,
                'reason': f"Failed to parse validation response: {str(e)}",
                'confidence': 'low'
            }

        except Exception as e:
            logger.error(f"[VALIDATOR] Error parsing validation response: {str(e)}")
            raise
