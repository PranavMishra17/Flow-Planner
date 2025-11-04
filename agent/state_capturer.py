"""
State capture system for Browser-Use workflow execution.
Extracts and saves UI states (screenshots, URLs, actions) from Browser-Use history.
"""
import os
import json
import logging
import base64
from datetime import datetime
from typing import Dict, List, Optional
from PIL import Image
import io
import google.generativeai as genai
from config import Config

logger = logging.getLogger(__name__)


class StateCapturer:
    """
    Captures and saves UI states from Browser-Use workflow execution.
    Organizes outputs into structured dataset with screenshots and metadata.
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize state capturer.

        Args:
            output_dir: Custom output directory (defaults to config-based)
        """
        self.output_dir = output_dir or Config.OUTPUT_DIR
        logger.info(f"[CAPTURE] State capturer initialized with output dir: {self.output_dir}")

    async def capture_states(
        self,
        states: List[Dict],
        task_name: str,
        task_description: str
    ) -> Dict:
        """
        Capture and save all UI states from workflow execution.

        Args:
            states: List of state dictionaries from Browser-Use agent
            task_name: Name/identifier for this task
            task_description: Full task description

        Returns:
            Dictionary with capture results and paths

        Raises:
            Exception: If capture fails
        """
        logger.info("[CAPTURE] ==================== STATE CAPTURE ====================")
        logger.info(f"[CAPTURE] Task: {task_name}")
        logger.info(f"[CAPTURE] Total states to capture: {len(states)}")

        try:
            # Create task-specific output directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_dir = os.path.join(
                self.output_dir,
                f"{self._sanitize_filename(task_name)}_{timestamp}"
            )
            os.makedirs(task_dir, exist_ok=True)

            logger.info(f"[CAPTURE] Created output directory: {task_dir}")

            # Process and save each state
            processed_states = []
            for i, state in enumerate(states):
                try:
                    processed_state = await self._process_state(
                        state,
                        i + 1,
                        task_dir
                    )
                    processed_states.append(processed_state)
                except Exception as e:
                    logger.error(f"[CAPTURE] Failed to process state {i+1}: {str(e)}")
                    # Continue with remaining states

            logger.info(f"[CAPTURE] Successfully processed {len(processed_states)} states")

            # Create metadata file
            metadata = self._create_metadata(
                task_name,
                task_description,
                processed_states
            )

            metadata_path = os.path.join(task_dir, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"[CAPTURE] Metadata saved to: {metadata_path}")

            # Create summary
            summary = {
                'task_name': task_name,
                'output_directory': task_dir,
                'metadata_path': metadata_path,
                'total_states': len(processed_states),
                'timestamp': timestamp
            }

            logger.info("[CAPTURE] ==================== END CAPTURE ====================")

            return summary

        except Exception as e:
            logger.error(f"[CAPTURE] State capture failed: {str(e)}", exc_info=True)
            raise

    async def _process_state(
        self,
        state: Dict,
        step_number: int,
        task_dir: str
    ) -> Dict:
        """
        Process a single state: save screenshot and extract metadata.

        Args:
            state: State dictionary from Browser-Use
            step_number: Sequential step number
            task_dir: Task output directory

        Returns:
            Processed state dictionary
        """
        processed = {
            'step_number': step_number,
            'description': state.get('description', f'Step {step_number}'),
            'url': state.get('url', ''),
            'timestamp': state.get('timestamp', ''),
            'action': state.get('action', {}),
            'success': state.get('success', True)
        }

        # Save screenshot if available
        screenshot = state.get('screenshot')
        if screenshot:
            screenshot_filename = f"step_{step_number:03d}.png"
            screenshot_path = os.path.join(task_dir, screenshot_filename)

            try:
                # Handle different screenshot formats
                if isinstance(screenshot, Image.Image):
                    # PIL Image object
                    screenshot.save(screenshot_path, quality=Config.SCREENSHOT_QUALITY)
                elif isinstance(screenshot, bytes):
                    # Raw bytes
                    with open(screenshot_path, 'wb') as f:
                        f.write(screenshot)
                elif isinstance(screenshot, str):
                    # Could be base64 or file path
                    if os.path.exists(screenshot):
                        # File path
                        import shutil
                        shutil.copy(screenshot, screenshot_path)
                    else:
                        # Try to decode as base64
                        try:
                            # Remove data URL prefix if present
                            if screenshot.startswith('data:image'):
                                screenshot = screenshot.split(',', 1)[1]

                            # Decode base64
                            image_data = base64.b64decode(screenshot)
                            with open(screenshot_path, 'wb') as f:
                                f.write(image_data)
                        except Exception as e:
                            logger.warning(f"[CAPTURE] Failed to decode base64 screenshot: {str(e)}")
                            screenshot_path = None
                else:
                    logger.warning(f"[CAPTURE] Unknown screenshot format for step {step_number}: {type(screenshot)}")
                    screenshot_path = None

                if screenshot_path and os.path.exists(screenshot_path):
                    processed['screenshot_path'] = screenshot_filename
                    processed['screenshot_full_path'] = screenshot_path
                    logger.info(f"[CAPTURE] Saved screenshot: {screenshot_filename}")
                else:
                    logger.warning(f"[CAPTURE] Screenshot not saved for step {step_number}")

            except Exception as e:
                logger.error(f"[CAPTURE] Failed to save screenshot for step {step_number}: {str(e)}")
        else:
            logger.debug(f"[CAPTURE] No screenshot available for step {step_number}")

        return processed

    def _create_metadata(
        self,
        task_name: str,
        task_description: str,
        states: List[Dict]
    ) -> Dict:
        """
        Create metadata JSON with all workflow information.

        Args:
            task_name: Task name
            task_description: Full task description
            states: Processed states

        Returns:
            Metadata dictionary
        """
        metadata = {
            'task': {
                'name': task_name,
                'description': task_description,
                'completed_at': datetime.now().isoformat()
            },
            'execution': {
                'total_steps': len(states),
                'successful_steps': sum(1 for s in states if s.get('success', True)),
                'failed_steps': sum(1 for s in states if not s.get('success', True))
            },
            'states': states,
            'version': '1.0',
            'architecture': 'browser-use'
        }

        return metadata

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to remove invalid characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Limit length
        max_length = 50
        if len(filename) > max_length:
            filename = filename[:max_length]

        return filename.strip()

    async def generate_guide(
        self,
        metadata_path: str,
        task_description: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate a human-readable workflow guide using Gemini to analyze metadata and screenshots.

        Args:
            metadata_path: Path to metadata.json
            task_description: Original task description
            output_path: Optional custom output path for guide

        Returns:
            Path to generated guide file
        """
        logger.info("[CAPTURE] Generating AI-powered workflow guide with Gemini...")

        try:
            # Load metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Determine output path
            if not output_path:
                metadata_dir = os.path.dirname(metadata_path)
                output_path = os.path.join(metadata_dir, "WORKFLOW_GUIDE.md")

            # Generate guide using Gemini
            guide_content = await self._generate_guide_with_gemini(
                metadata,
                task_description,
                metadata_dir
            )

            # Save guide
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(guide_content)

            logger.info(f"[CAPTURE] AI-powered workflow guide generated: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"[CAPTURE] Failed to generate guide: {str(e)}", exc_info=True)
            # Fallback to simple guide
            logger.info("[CAPTURE] Falling back to simple markdown guide")
            try:
                guide_content = self._build_simple_markdown_guide(metadata)
                if not output_path:
                    metadata_dir = os.path.dirname(metadata_path)
                    output_path = os.path.join(metadata_dir, "WORKFLOW_GUIDE.md")
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(guide_content)
                return output_path
            except Exception as fallback_error:
                logger.error(f"[CAPTURE] Fallback guide generation also failed: {str(fallback_error)}")
                raise

    def _filter_meaningful_states(self, states: List[Dict]) -> List[Dict]:
        """
        Filter states to only exclude truly unnecessary steps.

        INCLUDE:
        - Initial navigation (first step to app URL)
        - Authentication steps and checks
        - All user interactions (clicks, inputs)
        - Completion states

        EXCLUDE ONLY:
        - Mid-workflow screenshot verification steps
        - Internal processing errors
        - Redundant wait actions (unless they're the first wait after navigation)

        Args:
            states: All captured states

        Returns:
            Filtered list of meaningful states
        """
        meaningful_states = []
        seen_navigation = False
        seen_wait = False

        for state in states:
            action = state.get('action', {})
            action_list = action.get('action', [])
            description = state.get('description', '').lower()
            step_num = state.get('step_number', 0)

            # Always exclude internal processing errors
            if 'invalid model output format' in description:
                logger.debug(f"[CAPTURE] Excluding step {step_num}: Internal processing error")
                continue

            # Exclude screenshot-only verification steps (no other actions)
            if 'requested screenshot' in description and len(action_list) == 1:
                is_screenshot_only = False
                for action_item in action_list:
                    if 'screenshot' in action_item and len(action_item) == 1:
                        is_screenshot_only = True
                        break
                if is_screenshot_only:
                    logger.debug(f"[CAPTURE] Excluding step {step_num}: Screenshot-only verification")
                    continue

            # Include initial navigation (first navigate action)
            if 'navigate to url' in description and not seen_navigation:
                seen_navigation = True
                meaningful_states.append(state)
                logger.debug(f"[CAPTURE] Including step {step_num}: Initial navigation")
                continue

            # Include first wait (usually for page load)
            if 'waited for' in description and not seen_wait:
                seen_wait = True
                meaningful_states.append(state)
                logger.debug(f"[CAPTURE] Including step {step_num}: Initial page load wait")
                continue

            # Exclude subsequent waits (unless they have other actions)
            if 'waited for' in description and seen_wait:
                if len(action_list) <= 1:
                    logger.debug(f"[CAPTURE] Excluding step {step_num}: Redundant wait")
                    continue

            # Include all other meaningful interactions
            has_action = False
            for action_item in action_list:
                if any(key in action_item for key in ['click', 'input', 'done', 'navigate']):
                    has_action = True
                    break

            if has_action:
                meaningful_states.append(state)
                logger.debug(f"[CAPTURE] Including step {step_num}: Has user action")
            else:
                logger.debug(f"[CAPTURE] Excluding step {step_num}: No meaningful action")

        logger.info(f"[CAPTURE] Filtered {len(states)} states to {len(meaningful_states)} contextual steps")
        return meaningful_states

    def _validate_screenshots(
        self,
        states: List[Dict],
        screenshots_dir: str
    ) -> List[Dict]:
        """
        Validate screenshot existence and categorize steps by screenshot necessity.

        Args:
            states: Filtered meaningful states
            screenshots_dir: Directory containing screenshots

        Returns:
            States with validated screenshot information
        """
        validated_states = []

        for state in states:
            state_copy = state.copy()
            screenshot_path = state.get('screenshot_path', '')
            description = state.get('description', '').lower()
            action = state.get('action', {})
            action_list = action.get('action', [])

            step_num = state.get('step_number')
            logger.debug(f"[CAPTURE] Step {step_num}: Validating screenshot")
            logger.debug(f"[CAPTURE] Step {step_num}: Description: {description[:100]}...")
            logger.debug(f"[CAPTURE] Step {step_num}: Action list: {action_list}")
            logger.debug(f"[CAPTURE] Step {step_num}: Screenshot path: {screenshot_path}")

            # Determine if this step SHOULD have a screenshot
            needs_screenshot = False

            # Check for UI interactions that warrant screenshots
            for action_item in action_list:
                logger.debug(f"[CAPTURE] Step {step_num}: Checking action_item: {action_item}")
                if any(key in action_item for key in ['click', 'input_text', 'input']):
                    needs_screenshot = True
                    logger.debug(f"[CAPTURE] Step {step_num}: Found UI interaction - needs screenshot")
                    break

            logger.debug(f"[CAPTURE] Step {step_num}: After UI check, needs_screenshot = {needs_screenshot}")

            # EXCLUDE screenshots for navigation and wait steps
            if 'navigate to url' in description or 'waited for' in description:
                needs_screenshot = False
                logger.debug(f"[CAPTURE] Step {step_num}: Navigation/wait - no screenshot needed")

            # EXCLUDE screenshots for done actions - check for actual done action, not 'is_done'
            if any('done' in action_item for action_item in action_list):
                needs_screenshot = False
                logger.debug(f"[CAPTURE] Step {step_num}: Done action - no screenshot needed")

            logger.debug(f"[CAPTURE] Step {step_num}: Final needs_screenshot = {needs_screenshot}")

            # Validate file existence if screenshot is claimed
            if screenshot_path:
                full_path = os.path.join(screenshots_dir, screenshot_path)
                if os.path.exists(full_path):
                    if needs_screenshot:
                        state_copy['has_screenshot'] = True
                        state_copy['screenshot_path'] = screenshot_path
                        logger.info(f"[CAPTURE] Step {state.get('step_number')}: Screenshot validated and needed")
                    else:
                        # Screenshot exists but not needed for this type of step
                        state_copy['has_screenshot'] = False
                        state_copy.pop('screenshot_path', None)
                        logger.info(f"[CAPTURE] Step {state.get('step_number')}: Screenshot exists but not needed for this step type")
                else:
                    # Screenshot claimed but doesn't exist - hallucination
                    state_copy['has_screenshot'] = False
                    state_copy.pop('screenshot_path', None)
                    logger.warning(f"[CAPTURE] Step {state.get('step_number')}: Screenshot {screenshot_path} does not exist - removing reference")
            else:
                state_copy['has_screenshot'] = False
                logger.debug(f"[CAPTURE] Step {state.get('step_number')}: No screenshot available")

            validated_states.append(state_copy)

        return validated_states

    async def _generate_guide_with_gemini(
        self,
        metadata: Dict,
        task_description: str,
        screenshots_dir: str
    ) -> str:
        """
        Generate comprehensive workflow guide using Gemini vision model.

        Args:
            metadata: Workflow metadata
            task_description: Original task description
            screenshots_dir: Directory containing screenshots

        Returns:
            Markdown formatted guide
        """
        # Configure Gemini
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel(Config.GEMINI_MODEL)

        # Prepare context for Gemini - filter to only meaningful states
        all_states = metadata.get('states', [])
        states = self._filter_meaningful_states(all_states)

        # CRITICAL: Validate and categorize screenshots
        states_with_validated_screenshots = self._validate_screenshots(
            states,
            screenshots_dir
        )
        logger.info(f"[CAPTURE] Validated screenshots for {len(states_with_validated_screenshots)} states")

        # Build prompt for Gemini with explicit screenshot rules
        prompt = f"""You are creating a comprehensive workflow guide that will help a NEW user or agent understand how to complete this task from scratch.

**Original Task**: {task_description}

**Workflow Context**:
- Total Steps Executed: {metadata.get('execution', {}).get('total_steps', 0)}
- Key Steps to Document: {len(states_with_validated_screenshots)}

**Captured Workflow Steps**:
{json.dumps(states_with_validated_screenshots, indent=2)}

Generate a detailed, user-friendly step-by-step workflow guide in Markdown format that includes:

**Essential Context (MUST INCLUDE):**
1. **Initial Setup**: Start with navigation to the application
   - Format: "Navigate to [App Name] at `https://url.com`"
   - Include the URL explicitly
   - Note if user is already authenticated or needs to log in

2. **Complete Workflow Path**: Document the full journey
   - Include initial navigation and any authentication steps
   - Show the path through the UI (e.g., "Click Projects in sidebar" → "Click Add Project button")
   - This helps a new agent understand the complete flow

**For Each Step Include:**
- **Step Number** and **Clear Action Description**
- **URL** (always include if available, especially if it changed)
- **Screenshot Reference**: CRITICAL RULES FOR SCREENSHOTS
  - ONLY add screenshot if the state has "has_screenshot": true
  - ONLY use the EXACT value from "screenshot_path" field (e.g., step_005.png)
  - If "has_screenshot" is false or missing, DO NOT add any screenshot reference
  - If "screenshot_path" is missing, DO NOT add any screenshot reference
  - Format: `![Step X](screenshot_path_value)` - use the exact screenshot_path value
  - NEVER create screenshot references for steps without "screenshot_path" field
  - NEVER guess or infer screenshot filenames
- **What's Happening**: Brief explanation of what's happening in this step
  - For steps WITH screenshots: WHERE the button/link is located, WHAT the form/modal looks like
  - For steps WITHOUT screenshots: Just describe the action (navigation, waiting, etc.)

**CRITICAL SCREENSHOT RULES:**
- Navigation steps (e.g., "Navigate to URL"): NO screenshot reference
- Wait/loading steps (e.g., "Waited for X seconds"): NO screenshot reference
- Done/completion actions: NO screenshot reference
- Button clicks: Include screenshot ONLY if has_screenshot=true
- Form inputs: Include screenshot ONLY if has_screenshot=true
- Modal appearances: Include screenshot ONLY if has_screenshot=true

**Screenshot Validation:**
Each state in the workflow data has been pre-validated. Trust the "has_screenshot" field:
- If "has_screenshot": true → Use the "screenshot_path" value
- If "has_screenshot": false → DO NOT add any screenshot reference
- If no "screenshot_path" field → DO NOT add any screenshot reference

**Format:**
- Use clear markdown headers (##, ###)
- Use bullet points for actions
- Use code blocks for URLs: `https://example.com`
- Include a workflow summary at the end

**Goal**: A new agent reading this guide should understand:
- Where to start (URL)
- How to navigate through the application
- What each button/form looks like (when screenshots are available)
- The complete workflow from start to finish

Generate the guide now:"""

        try:
            # Generate content
            response = await model.generate_content_async(prompt)
            guide_content = response.text

            # Add header and footer
            guide_with_metadata = f"""# Workflow Guide

> Auto-generated using Gemini Flash 2.0 AI Analysis
>
> **Task**: {task_description}
>
> **Captured**: {metadata.get('task', {}).get('completed_at', 'Unknown')}

---

{guide_content}

---

## Technical Details

- **Architecture**: Browser-Use autonomous agent v0.9.5
- **AI Models**: Claude Sonnet 4.5 (execution) + Gemini Flash 2.0 (guide generation)
- **Metadata**: See `metadata.json` for technical details
- **Workflow Version**: {metadata.get('version', '1.0')}

Generated by [Flow Planner](https://github.com/your-repo/flow-planner)
"""

            return guide_with_metadata

        except Exception as e:
            logger.error(f"[CAPTURE] Gemini guide generation failed: {str(e)}")
            raise

    def _build_simple_markdown_guide(self, metadata: Dict) -> str:
        """
        Build simple markdown-formatted workflow guide (fallback).

        Args:
            metadata: Metadata dictionary

        Returns:
            Markdown string
        """
        task = metadata.get('task', {})
        execution = metadata.get('execution', {})
        states = metadata.get('states', [])

        guide = f"""# Workflow Guide: {task.get('name', 'Unknown Task')}

## Task Description
{task.get('description', 'No description provided')}

## Execution Summary
- **Total Steps**: {execution.get('total_steps', 0)}
- **Successful**: {execution.get('successful_steps', 0)}
- **Failed**: {execution.get('failed_steps', 0)}
- **Completed At**: {task.get('completed_at', 'Unknown')}

## Workflow Steps

"""

        # Add each step
        for state in states:
            step_num = state.get('step_number', '?')
            description = state.get('description', 'No description')
            url = state.get('url', 'No URL')
            screenshot = state.get('screenshot_path', '')
            action = state.get('action', {})

            guide += f"### Step {step_num}: {description}\n\n"

            if url:
                guide += f"**URL**: `{url}`\n\n"

            if action:
                action_type = action.get('type', 'unknown')
                guide += f"**Action**: {action_type}\n\n"

            if screenshot:
                guide += f"![Step {step_num}]({screenshot})\n\n"

            guide += "---\n\n"

        guide += f"""
## Notes

This workflow guide was automatically generated using the FlowForge Browser-Use architecture.

- **Architecture**: Browser-Use autonomous agent
- **Metadata Version**: {metadata.get('version', 'Unknown')}
"""

        return guide
