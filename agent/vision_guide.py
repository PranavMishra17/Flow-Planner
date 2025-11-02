"""
Claude Vision-based execution guide.
Analyzes screenshots in real-time to decide next actions dynamically.
"""
import logging
import base64
import asyncio
import json
from typing import Dict, List, Optional
from anthropic import Anthropic
from config import Config
import os
from PIL import Image
import io

logger = logging.getLogger(__name__)


class VisionGuide:
    """
    AI-powered vision guide using Claude's vision capabilities.
    Analyzes screenshots to decide next actions dynamically during execution.
    """

    def __init__(self):
        """Initialize Vision Guide with API configuration"""
        if not Config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        logger.info("[VISION] Vision Guide initialized")

    async def get_next_actions(
        self,
        screenshot_path: str,
        high_level_plan: List[str],
        current_step: str,
        current_step_index: int,
        executed_steps: List[Dict]
    ) -> Dict:
        """
        Analyze screenshot and decide next actions.

        Args:
            screenshot_path: Path to current screenshot
            high_level_plan: List of high-level workflow steps
            current_step: Current high-level step being attempted
            current_step_index: Index of current step in high_level_plan
            executed_steps: List of previously executed steps with their results

        Returns:
            Dictionary with:
            - observation: What the AI sees in the screenshot
            - status: "step_complete" | "in_progress" | "blocked"
            - blocker: (if blocked) Type of blocker
            - next_actions: List of 1-2 Playwright actions to execute
            - relevant_region: Region description for cropping final guide

        Raises:
            Exception: If vision analysis fails
        """
        logger.info(f"[VISION] Analyzing screenshot for step {current_step_index + 1}/{len(high_level_plan)}: {current_step}")

        # Read and encode screenshot
        screenshot_base64 = self._encode_image(screenshot_path)

        # Build context for Claude
        context = self._build_context(
            high_level_plan,
            current_step,
            current_step_index,
            executed_steps
        )

        # Build prompt with few-shot examples
        prompt = self._build_vision_prompt(context)

        # Call Claude Vision API
        result = await self._call_claude_vision(prompt, screenshot_base64)

        logger.info(f"[VISION] Observation: {result['observation']}")
        logger.info(f"[VISION] Status: {result['status']}")
        logger.info(f"[VISION] Next actions: {len(result['next_actions'])}")

        return result

    def _build_context(
        self,
        high_level_plan: List[str],
        current_step: str,
        current_step_index: int,
        executed_steps: List[Dict]
    ) -> Dict:
        """
        Build context dictionary for Claude.

        Args:
            high_level_plan: List of high-level steps
            current_step: Current step description
            current_step_index: Index of current step
            executed_steps: Previous executed steps

        Returns:
            Context dictionary
        """
        return {
            'high_level_plan': high_level_plan,
            'current_step': current_step,
            'current_step_index': current_step_index,
            'total_steps': len(high_level_plan),
            'executed_steps': executed_steps
        }

    def _build_vision_prompt(self, context: Dict) -> str:
        """
        Build the vision prompt with few-shot examples.

        Args:
            context: Context dictionary with plan and execution history

        Returns:
            Formatted prompt string
        """
        high_level_plan = context['high_level_plan']
        current_step = context['current_step']
        current_step_index = context['current_step_index']
        executed_steps = context['executed_steps']

        # Format executed steps for display
        executed_summary = []
        for step in executed_steps[-3:]:  # Show last 3 steps
            actions_summary = f"{len(step.get('actions', []))} actions"
            executed_summary.append(f"- {step.get('observation', 'Unknown')[:80]} ({actions_summary})")

        executed_text = "\n".join(executed_summary) if executed_summary else "None (just started)"

        prompt = f"""You are a web automation expert analyzing screenshots to guide Playwright browser actions.

CONTEXT:
High-level workflow plan: {json.dumps(high_level_plan, indent=2)}
Current step: {current_step_index + 1}/{len(high_level_plan)} - "{current_step}"

Recent executed steps:
{executed_text}

TASK:
Analyze the screenshot and determine:
1. What you see in the current UI state
2. Whether the current high-level step is complete, in progress, or blocked
3. The next 1-2 specific Playwright actions to execute
4. Which UI region is most relevant (for cropping screenshots later)

AVAILABLE PLAYWRIGHT ACTIONS:
- click: Click an element
  {{
    "action": "click",
    "selector": "button#submit" or "button:has-text('Submit')",
    "description": "Click the submit button"
  }}

- fill: Fill an input field
  {{
    "action": "fill",
    "selector": "input[name='email']",
    "value": "user@example.com",
    "description": "Enter email address"
  }}

- select: Select dropdown option
  {{
    "action": "select",
    "selector": "select#country",
    "value": "USA",
    "description": "Select country"
  }}

- wait: Wait for element or duration
  {{
    "action": "wait",
    "selector": "div.modal" (optional),
    "duration": 2000 (milliseconds),
    "description": "Wait for modal to appear"
  }}

- scroll: Scroll to element (use when element might be below viewport)
  {{
    "action": "scroll",
    "selector": "button#share",
    "description": "Scroll to share button"
  }}

- press_key: Press keyboard key
  {{
    "action": "press_key",
    "key": "Enter",
    "description": "Press Enter key"
  }}

SELECTOR TIPS:
- Prefer text-based selectors: button:has-text('Click me')
- Use common attributes: [aria-label="Close"], [data-testid="submit-btn"]
- Be specific but not overly brittle: Use 'button.primary' not 'div > div > button:nth-child(3)'
- For dynamic content, use partial matches: [class*="submit-button"]

IMPORTANT RULES:
1. If you see a login page, set status to "blocked" with blocker "authentication"
2. If you see ads or "Skip Ad" buttons, add a wait action (ads don't mean failure)
3. If an element is not visible in the viewport, add a scroll action first
4. Only mark status as "step_complete" when the current high-level step is truly done
5. Keep next_actions to 1-2 actions maximum - vision will be called again after execution
6. Be adaptive: if previous action failed, try a different selector approach

FEW-SHOT EXAMPLES:

Example 1: Login Required
USER: High-level plan: ["Navigate to dashboard", "Create project"]
Current step: 1/2 - "Navigate to dashboard"
Screenshot: [shows login page with "Continue with Google" button]

ASSISTANT:
{{
  "observation": "Login page detected. See 'Continue with Google' button and email/password form.",
  "status": "blocked",
  "blocker": "authentication",
  "next_actions": [
    {{
      "action": "wait",
      "duration": 1000,
      "description": "Pause for authentication handler"
    }}
  ],
  "relevant_region": {{
    "description": "Login form area, center of page",
    "crop_suggestion": "center_third"
  }}
}}

Example 2: Form Filling in Progress
USER: High-level plan: ["Login", "Create database", "Configure settings"]
Current step: 2/3 - "Create database"
Screenshot: [shows database creation modal with name input and Create button]

ASSISTANT:
{{
  "observation": "Database creation modal is open. See 'Database Name' input field empty and 'Create' button ready.",
  "status": "in_progress",
  "next_actions": [
    {{
      "action": "fill",
      "selector": "input[name='name'], input[placeholder*='database name' i]",
      "value": "my_new_database",
      "description": "Enter database name"
    }},
    {{
      "action": "click",
      "selector": "button:has-text('Create'), button[type='submit']",
      "description": "Click Create button"
    }}
  ],
  "relevant_region": {{
    "description": "Modal dialog in center",
    "crop_suggestion": "modal_content"
  }}
}}

Example 3: Step Complete with Success Message
USER: High-level plan: ["Login", "Create database", "Configure settings"]
Current step: 2/3 - "Create database"
Screenshot: [shows success toast "Database created successfully"]

ASSISTANT:
{{
  "observation": "Success notification visible: 'Database created successfully'. Database appears in the list.",
  "status": "step_complete",
  "next_actions": [
    {{
      "action": "wait",
      "duration": 2000,
      "description": "Wait for page to stabilize before next step"
    }}
  ],
  "relevant_region": {{
    "description": "Success notification, top-right",
    "crop_suggestion": "top_right_quadrant"
  }}
}}

Example 4: Ad Detection
USER: High-level plan: ["Navigate to video", "Share video"]
Current step: 2/2 - "Share video"
Screenshot: [shows YouTube video with "Skip Ad" button overlay]

ASSISTANT:
{{
  "observation": "Video page loaded but showing advertisement overlay with 'Skip Ad' button (will auto-skip). Share functionality below.",
  "status": "in_progress",
  "next_actions": [
    {{
      "action": "wait",
      "duration": 5000,
      "description": "Wait for ad to finish or auto-skip"
    }}
  ],
  "relevant_region": {{
    "description": "Video player with ad overlay",
    "crop_suggestion": "center_half"
  }}
}}

Example 5: Element Not Visible (Need Scroll)
USER: High-level plan: ["Navigate to page", "Click share button"]
Current step: 2/2 - "Click share button"
Screenshot: [shows page top, share button not visible]

ASSISTANT:
{{
  "observation": "Page loaded successfully but share button not visible in current viewport. Likely below the fold.",
  "status": "in_progress",
  "next_actions": [
    {{
      "action": "scroll",
      "selector": "button[aria-label='Share'], button:has-text('Share')",
      "description": "Scroll to share button"
    }},
    {{
      "action": "click",
      "selector": "button[aria-label='Share'], button:has-text('Share')",
      "description": "Click share button"
    }}
  ],
  "relevant_region": {{
    "description": "Share button area",
    "crop_suggestion": "bottom_third"
  }}
}}

Now analyze the provided screenshot and respond in the EXACT JSON format shown above.
Return ONLY the JSON object, no additional text."""

        return prompt

    def _encode_image(self, image_path: str) -> str:
        """
        Encode image file to base64, resizing if needed to stay under Claude's limits.

        Args:
            image_path: Path to image file

        Returns:
            Base64 encoded image string

        Raises:
            Exception: If encoding fails
        """
        try:
            # Open image
            img = Image.open(image_path)
            width, height = img.size

            # Claude's limit is 8000px per dimension
            MAX_DIMENSION = 8000

            # Check if resizing is needed
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                logger.debug(f"[VISION] Resizing image from {width}x{height}")

                # Calculate new dimensions maintaining aspect ratio
                if width > height:
                    new_width = MAX_DIMENSION
                    new_height = int((MAX_DIMENSION / width) * height)
                else:
                    new_height = MAX_DIMENSION
                    new_width = int((MAX_DIMENSION / height) * width)

                # Resize image
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.debug(f"[VISION] Resized to {new_width}x{new_height}")

            # Convert to RGB if needed (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img

            # Save to bytes with compression
            buffer = io.BytesIO()
            img.save(buffer, format='PNG', optimize=True, quality=Config.SCREENSHOT_QUALITY)
            buffer.seek(0)

            # Encode to base64
            return base64.standard_b64encode(buffer.read()).decode('utf-8')

        except Exception as e:
            logger.error(f"[VISION] Failed to encode image: {str(e)}")
            raise

    async def _call_claude_vision(
        self,
        prompt: str,
        image_base64: str,
        max_retries: int = 3
    ) -> Dict:
        """
        Call Claude Vision API with exponential backoff retry logic.

        Args:
            prompt: Vision analysis prompt
            image_base64: Base64 encoded screenshot
            max_retries: Maximum number of retry attempts

        Returns:
            Parsed vision response

        Raises:
            Exception: If all retries fail
        """
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                logger.debug(f"[VISION] Calling Claude Vision API (attempt {attempt + 1}/{max_retries})")

                # Use asyncio to run the synchronous API call
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.messages.create(
                        model=Config.CLAUDE_VISION_MODEL,
                        max_tokens=Config.CLAUDE_VISION_MAX_TOKENS,
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

                logger.debug("[VISION] Claude Vision API call successful")

                # Parse response
                result = self._parse_vision_response(response)
                return result

            except Exception as e:
                logger.warning(f"[VISION] API call attempt {attempt + 1} failed: {str(e)}")

                if attempt < max_retries - 1:
                    logger.info(f"[VISION] Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("[VISION] All retry attempts exhausted")
                    raise

    def _parse_vision_response(self, response) -> Dict:
        """
        Parse Claude's vision response into structured result.

        Args:
            response: Claude API response

        Returns:
            Dictionary with observation, status, next_actions, relevant_region

        Raises:
            ValueError: If response cannot be parsed
        """
        try:
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
            required_fields = ['observation', 'status', 'next_actions', 'relevant_region']
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Response missing required field: {field}")

            # Validate status
            valid_statuses = ['step_complete', 'in_progress', 'blocked']
            if result['status'] not in valid_statuses:
                raise ValueError(f"Invalid status: {result['status']}")

            # If blocked, ensure blocker is present
            if result['status'] == 'blocked' and 'blocker' not in result:
                result['blocker'] = 'unknown'

            # Validate next_actions is a list
            if not isinstance(result['next_actions'], list):
                raise ValueError("next_actions must be a list")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"[VISION] Failed to parse JSON response: {str(e)}")
            logger.error(f"[VISION] Response text: {text[:500]}...")

            # Return a safe default
            return {
                'observation': f"Failed to parse vision response: {str(e)}",
                'status': 'blocked',
                'blocker': 'vision_error',
                'next_actions': [
                    {
                        'action': 'wait',
                        'duration': 1000,
                        'description': 'Wait due to vision error'
                    }
                ],
                'relevant_region': {
                    'description': 'Unknown',
                    'crop_suggestion': 'full'
                }
            }

        except Exception as e:
            logger.error(f"[VISION] Error parsing vision response: {str(e)}")
            raise
