"""
Gemini-based workflow planner with Google Search grounding.
Uses Gemini 1.5 Flash to research tasks and generate execution plans.
"""
import logging
import json
import asyncio
from typing import Dict, List, Optional
import google.generativeai as genai
from config import Config

logger = logging.getLogger(__name__)


class GeminiPlanner:
    """
    AI-powered workflow planner using Google Gemini with grounding.
    Researches tasks via web search and generates structured execution plans.
    """

    def __init__(self):
        """Initialize Gemini planner with API configuration"""
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")

        genai.configure(api_key=Config.GEMINI_API_KEY)

        # Configure model with grounding for web search
        self.model = genai.GenerativeModel(
            model_name=Config.GEMINI_MODEL,
            generation_config={
                'temperature': Config.GEMINI_TEMPERATURE,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 8192,
            }
        )

        logger.info("[PLANNER] Gemini planner initialized")

    async def create_plan(
        self,
        task: str,
        app_url: str,
        app_name: str
    ) -> Dict:
        """
        Create a detailed execution plan for the given task.

        Args:
            task: Natural language task description (e.g., "Create a project in Linear")
            app_url: URL of the target application
            app_name: Name of the application

        Returns:
            Dictionary containing research_summary and list of steps

        Raises:
            Exception: If plan generation fails
        """
        logger.info(f"[PLANNER] Creating plan for task: {task}")
        logger.info(f"[PLANNER] Target app: {app_name} ({app_url})")

        prompt = self._build_planning_prompt(task, app_url, app_name)

        try:
            # Call Gemini API with retry logic
            response = await self._call_gemini_with_retry(prompt)

            # Parse the response
            plan = self._parse_plan_response(response.text)

            logger.info(f"[PLANNER] Plan created successfully with {len(plan.get('steps', []))} steps")
            return plan

        except Exception as e:
            logger.error(f"[PLANNER] Failed to create plan: {str(e)}", exc_info=True)
            raise

    def _build_planning_prompt(self, task: str, app_url: str, app_name: str) -> str:
        """
        Build the prompt for Gemini to generate high-level outline and first actions.

        Args:
            task: Task description
            app_url: Target application URL
            app_name: Application name

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert at analyzing web applications and creating step-by-step automation plans.

Task: {task}
Application: {app_name}
URL: {app_url}

Your goal is to create a detailed, actionable plan for automating this task using browser automation (Playwright).

First, search the web for:
1. Official documentation for {app_name}
2. Tutorials showing how to {task}
3. Common UI patterns in {app_name}
4. Specific button names, selectors, and interaction patterns

Then, create a JSON plan with this EXACT structure:

{{
  "research_summary": "Brief 2-3 sentence summary of what you learned from web research about how to complete this task",
  "steps": [
    {{
      "step_number": 1,
      "action": "goto|click|fill|select|wait|press_key|scroll",
      "description": "Clear human-readable description of what this step does",
      "selector": "CSS selector or text content to find the element",
      "alternative_selectors": ["backup selector 1", "backup selector 2"],
      "value": "Value to type or select (only for fill/select actions)",
      "expected_outcome": "What should happen after this step completes"
    }}
  ]
}}

IMPORTANT RULES:
1. Start with "goto" action to navigate to {app_url}
2. Include realistic selectors based on common web UI patterns you find in search
3. For buttons/links, try multiple selector strategies: button text, aria-label, data-testid, class names
4. Always provide 2-3 alternative selectors for robustness
5. Add "wait" steps after actions that trigger page loads or animations
6. Be thorough - complete the ENTIRE task, not just the first action
7. For modal dialogs (share, create, etc.), include steps to interact with elements INSIDE the modal
8. The "value" field should only be present for "fill" and "select" actions
9. Return ONLY the JSON object, no additional text
10. Use scroll action if elements might be below the fold
11. For YouTube share: Must include steps to (1) navigate to video, (2) click share button, (3) click copy link button in modal
12. For tasks asking "How to..." - create a complete guide with ALL necessary steps to finish the task

Available actions:
- goto: Navigate to a URL
- click: Click on an element (button, link, etc.)
- fill: Type text into an input field
- select: Choose an option from a dropdown
- wait: Wait for an element to appear or for a timeout
- press_key: Press a keyboard key (Enter, Escape, etc.)
- scroll: Scroll to make an element visible

Generate the plan now:"""

        return prompt

    async def _call_gemini_with_retry(self, prompt: str, max_retries: int = 3) -> any:
        """
        Call Gemini API with exponential backoff retry logic.

        Args:
            prompt: The prompt to send
            max_retries: Maximum number of retry attempts

        Returns:
            Gemini API response

        Raises:
            Exception: If all retries fail
        """
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                logger.info(f"[PLANNER] Calling Gemini API (attempt {attempt + 1}/{max_retries})")

                # Use asyncio to run the synchronous API call
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content(prompt)
                )

                logger.info("[PLANNER] Gemini API call successful")
                return response

            except Exception as e:
                logger.warning(f"[PLANNER] API call attempt {attempt + 1} failed: {str(e)}")

                if attempt < max_retries - 1:
                    logger.info(f"[PLANNER] Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("[PLANNER] All retry attempts exhausted")
                    raise

    def _parse_plan_response(self, response_text: str) -> Dict:
        """
        Parse the Gemini response into a structured plan with high-level outline.

        Args:
            response_text: Raw text response from Gemini

        Returns:
            Parsed plan dictionary with high_level_plan and first_actions

        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            # Try to find JSON in the response
            # Sometimes the model wraps it in markdown code blocks
            text = response_text.strip()

            # Remove markdown code blocks if present
            if text.startswith('```json'):
                text = text[7:]  # Remove ```json
            if text.startswith('```'):
                text = text[3:]  # Remove ```
            if text.endswith('```'):
                text = text[:-3]  # Remove trailing ```

            text = text.strip()

            # Parse JSON
            plan = json.loads(text)

            # Validate structure
            if 'steps' not in plan:
                raise ValueError("Plan missing 'steps' field")

            if not isinstance(plan['steps'], list):
                raise ValueError("'steps' must be a list")

            if len(plan['steps']) == 0:
                raise ValueError("'steps' cannot be empty")

            # Ensure research_summary exists
            if 'research_summary' not in plan:
                plan['research_summary'] = "Plan generated successfully"

            # Validate each step has required fields
            required_step_fields = ['step_number', 'action', 'description', 'selector']
            for i, step in enumerate(plan['steps']):
                for field in required_step_fields:
                    if field not in step:
                        raise ValueError(f"Step {i+1} missing required field: {field}")

                # Ensure alternative_selectors exists
                if 'alternative_selectors' not in step:
                    step['alternative_selectors'] = []

                # Ensure expected_outcome exists
                if 'expected_outcome' not in step:
                    step['expected_outcome'] = f"Step {i+1} completes successfully"

            logger.debug(f"[PLANNER] Parsed plan with {len(plan['steps'])} steps")
            return plan

        except json.JSONDecodeError as e:
            logger.error(f"[PLANNER] Failed to parse JSON response: {str(e)}")
            logger.error(f"[PLANNER] Response text: {response_text[:500]}...")
            raise ValueError(f"Invalid JSON response from Gemini: {str(e)}")

        except Exception as e:
            logger.error(f"[PLANNER] Error parsing plan: {str(e)}")
            raise

    def validate_plan(self, plan: Dict) -> bool:
        """
        Validate that a plan is well-formed and executable.

        Args:
            plan: Plan dictionary to validate

        Returns:
            True if valid

        Raises:
            ValueError: If plan is invalid
        """
        if not plan or not isinstance(plan, dict):
            raise ValueError("Plan must be a non-empty dictionary")

        if 'steps' not in plan or not plan['steps']:
            raise ValueError("Plan must contain at least one step")

        if len(plan['steps']) > Config.MAX_STEPS:
            raise ValueError(f"Plan exceeds maximum steps ({Config.MAX_STEPS})")

        # Validate first step is 'goto'
        if plan['steps'][0]['action'] != 'goto':
            logger.warning("[PLANNER] First step is not 'goto', plan may fail")

        return True
