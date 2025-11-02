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
        app_url: Optional[str] = None,
        app_name: Optional[str] = None
    ) -> Dict:
        """
        Create a detailed execution plan for the given task.

        Args:
            task: Natural language task description (e.g., "Create a project in Linear")
            app_url: URL of the target application (optional - will be inferred if not provided)
            app_name: Name of the application (optional - will be inferred if not provided)

        Returns:
            Dictionary containing research_summary and list of steps

        Raises:
            Exception: If plan generation fails
        """
        logger.info(f"[PLANNER] Creating plan for task: {task}")

        # If app_url or app_name are missing, infer them from the task
        if not app_url or not app_name:
            logger.info("[PLANNER] Application details not provided, inferring from task...")
            inferred = await self._infer_application(task)
            app_url = app_url or inferred.get('url', 'https://example.com')
            app_name = app_name or inferred.get('name', 'Application')
            logger.info(f"[PLANNER] Inferred: {app_name} ({app_url})")

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
        Build the prompt for Gemini to research task and detect authentication needs.

        Args:
            task: Task description
            app_url: Target application URL
            app_name: Application name

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert at analyzing web applications and understanding authentication requirements.

Task: {task}
Application: {app_name}
URL: {app_url}

Your goal is to research this task and provide:
1. Authentication detection: Does this task require login? What type?
2. High-level workflow outline: 5-10 major steps (NO specific selectors!)
3. Application context: Known UI patterns and potential challenges

First, search the web for:
1. Official documentation for {app_name}
2. Tutorials showing how to {task}
3. Authentication methods used by {app_name}
4. Common UI patterns and challenges in {app_name}

Then, create a JSON response with this EXACT structure:

{{
  "task_analysis": {{
    "requires_authentication": true,
    "auth_type": "oauth_google|oauth_github|email_password|manual|none",
    "estimated_steps": 8,
    "complexity": "low|medium|high"
  }},
  "workflow_outline": [
    "Navigate to {app_name} dashboard",
    "Authenticate (if required)",
    "Access relevant section",
    "Perform main task action",
    "Configure settings if needed",
    "Save/submit changes",
    "Verify completion"
  ],
  "context": {{
    "app_name": "{app_name}",
    "app_url": "{app_url}",
    "common_patterns": "Brief description of UI patterns (modals, forms, navigation)",
    "known_challenges": "Potential issues like ads, onboarding, dynamic content"
  }}
}}

IMPORTANT RULES:
1. workflow_outline should be HIGH-LEVEL only (5-10 steps)
2. NO CSS selectors or specific element identifiers
3. Focus on WHAT to do, not HOW to do it (Browser-Use agent will figure out HOW)
4. Auth type detection is critical:
   - oauth_google: If app uses "Sign in with Google"
   - oauth_github: If app uses "Sign in with GitHub"
   - email_password: If app uses traditional email/password login
   - manual: If auth is complex or requires special handling
   - none: If no authentication needed
5. Complexity based on:
   - low: Simple tasks with <5 steps
   - medium: Standard workflows with 5-10 steps
   - high: Complex multi-stage tasks with >10 steps
6. Return ONLY the JSON object, no additional text

Generate the analysis now:"""

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
        Parse the Gemini response into a structured plan with auth detection and workflow outline.

        Args:
            response_text: Raw text response from Gemini

        Returns:
            Parsed plan dictionary with task_analysis, workflow_outline, and context

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

            # Validate structure - new format
            if 'task_analysis' not in plan:
                raise ValueError("Plan missing 'task_analysis' field")

            if 'workflow_outline' not in plan:
                raise ValueError("Plan missing 'workflow_outline' field")

            if not isinstance(plan['workflow_outline'], list):
                raise ValueError("'workflow_outline' must be a list")

            if len(plan['workflow_outline']) == 0:
                raise ValueError("'workflow_outline' cannot be empty")

            # Validate task_analysis structure
            task_analysis = plan['task_analysis']
            required_analysis_fields = ['requires_authentication', 'auth_type', 'estimated_steps', 'complexity']
            for field in required_analysis_fields:
                if field not in task_analysis:
                    logger.warning(f"[PLANNER] task_analysis missing field: {field}, using default")
                    if field == 'requires_authentication':
                        task_analysis[field] = False
                    elif field == 'auth_type':
                        task_analysis[field] = 'none'
                    elif field == 'estimated_steps':
                        task_analysis[field] = len(plan['workflow_outline'])
                    elif field == 'complexity':
                        task_analysis[field] = 'medium'

            # Ensure context exists
            if 'context' not in plan:
                plan['context'] = {
                    "app_name": "Unknown",
                    "app_url": "",
                    "common_patterns": "Standard web UI",
                    "known_challenges": "None identified"
                }

            logger.debug(f"[PLANNER] Parsed plan with {len(plan['workflow_outline'])} workflow steps")
            logger.info(f"[PLANNER] Auth required: {task_analysis['requires_authentication']}, Type: {task_analysis['auth_type']}")
            return plan

        except json.JSONDecodeError as e:
            logger.error(f"[PLANNER] Failed to parse JSON response: {str(e)}")
            logger.error(f"[PLANNER] Response text: {response_text[:500]}...")
            raise ValueError(f"Invalid JSON response from Gemini: {str(e)}")

        except Exception as e:
            logger.error(f"[PLANNER] Error parsing plan: {str(e)}")
            raise

    async def _infer_application(self, task: str) -> Dict:
        """
        Infer application name and URL from task description using Gemini.

        Args:
            task: Task description

        Returns:
            Dictionary with inferred 'name' and 'url'
        """
        prompt = f"""Analyze this task and identify the web application needed to complete it:

Task: {task}

Provide ONLY a JSON object with:
1. "name": The application name (e.g., "Asana", "Linear", "Notion")
2. "url": The main URL for the application (e.g., "https://app.asana.com", "https://linear.app")

If the application cannot be determined from the task, use generic values.

Return ONLY the JSON object, no additional text:"""

        try:
            logger.info("[PLANNER] Inferring application from task...")

            # Call Gemini
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(prompt)
            )

            # Parse response
            text = response.text.strip()

            # Remove markdown code blocks if present
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]

            text = text.strip()

            # Parse JSON
            inferred = json.loads(text)

            logger.info(f"[PLANNER] Inferred application: {inferred.get('name')} ({inferred.get('url')})")
            return inferred

        except Exception as e:
            logger.warning(f"[PLANNER] Failed to infer application: {str(e)}")
            # Return safe defaults
            return {
                'name': 'Web Application',
                'url': 'https://example.com'
            }

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

        if 'workflow_outline' not in plan or not plan['workflow_outline']:
            raise ValueError("Plan must contain workflow_outline with at least one step")

        if 'task_analysis' not in plan:
            raise ValueError("Plan must contain task_analysis")

        # Validate workflow outline is reasonable
        if len(plan['workflow_outline']) > 20:
            logger.warning(f"[PLANNER] Workflow outline has {len(plan['workflow_outline'])} steps, may be too detailed")

        return True
