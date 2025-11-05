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
        Filter states to create a CLEAN SUCCESS PATH for the workflow guide.

        This creates an instruction manual showing only successful actions,
        NOT a history log of all attempts including failures.

        INCLUDE:
        - Initial navigation (first step to app URL)
        - Successful user interactions that moved the workflow forward
        - Final completion state

        EXCLUDE:
        - Failed actions and retries
        - Debugging/troubleshooting steps
        - Screenshot verification steps
        - Internal processing errors
        - Redundant/repeated actions on same element

        Args:
            states: All captured states from Browser-Use execution

        Returns:
            Clean list of successful workflow steps
        """
        # Step 1: Basic filtering (errors, screenshots, waits)
        initial_filtered = self._basic_filter(states)

        # Step 2: Remove failed actions and keep only successful final attempts
        success_path = self._extract_success_path(initial_filtered)

        logger.info(f"[CAPTURE] Filtered {len(states)} states → {len(initial_filtered)} meaningful → {len(success_path)} clean success path")
        return success_path

    def _basic_filter(self, states: List[Dict]) -> List[Dict]:
        """
        Basic filtering: remove obvious non-instructional steps.

        Args:
            states: All states

        Returns:
            States after basic filtering
        """
        filtered = []
        seen_navigation = False

        for state in states:
            action = state.get('action', {})
            action_list = action.get('action', [])
            description = state.get('description', '').lower()
            step_num = state.get('step_number', 0)

            # Exclude internal processing errors
            if 'invalid model output format' in description:
                logger.debug(f"[CAPTURE] Excluding step {step_num}: Internal error")
                continue

            # Exclude internal file operations (Browser-Use agent TODO tracking)
            if any(keyword in description for keyword in [
                'todo.md', 'local file', '.md file', 'update the local',
                'mark navigation complete', 'mark task complete'
            ]):
                logger.debug(f"[CAPTURE] Excluding step {step_num}: Internal file operation")
                continue

            # Exclude screenshot-only verification steps
            if 'requested screenshot' in description and len(action_list) == 1:
                if any('screenshot' in str(a) for a in action_list):
                    logger.debug(f"[CAPTURE] Excluding step {step_num}: Screenshot verification")
                    continue

            # Include initial navigation (once)
            if 'navigate to url' in description and not seen_navigation:
                seen_navigation = True
                filtered.append(state)
                logger.debug(f"[CAPTURE] Including step {step_num}: Initial navigation")
                continue

            # Exclude wait steps (not instructional)
            if 'waited for' in description:
                logger.debug(f"[CAPTURE] Excluding step {step_num}: Wait step")
                continue

            # Check for meaningful actions
            has_action = any(
                key in action_item
                for action_item in action_list
                for key in ['click', 'input', 'done']
            )

            if has_action:
                filtered.append(state)
                logger.debug(f"[CAPTURE] Including step {step_num}: Has action")

        return filtered

    def _extract_success_path(self, states: List[Dict]) -> List[Dict]:
        """
        Extract clean success path by removing failed attempts and retries.

        Strategy:
        1. Detect failed actions (errors in description)
        2. Detect repeated actions on same element/target
        3. Keep only the last successful occurrence of each unique action
        4. Remove debugging/correction steps

        Args:
            states: Basically filtered states

        Returns:
            Clean success path
        """
        success_path = []
        action_tracker = {}  # Track actions by target/type

        for state in states:
            description = state.get('description', '').lower()
            action = state.get('action', {})
            action_list = action.get('action', [])
            step_num = state.get('step_number')

            # Skip if this describes a failure or error
            if any(keyword in description for keyword in [
                'failed', 'error', 'could not', 'unable', 'not found',
                'incorrect', 'invalid', 're-input', 're-focusing',
                'troubleshoot', 'attempt to', 'trying again'
            ]):
                logger.debug(f"[CAPTURE] Excluding step {step_num}: Failure/retry indicator")
                continue

            # Skip done action (already implicit in success)
            if any('done' in str(a) for a in action_list):
                logger.debug(f"[CAPTURE] Excluding step {step_num}: Done action")
                continue

            # Extract action signature (to detect duplicates)
            action_signature = self._get_action_signature(action_list)

            if action_signature:
                # Check if we've seen this action before
                if action_signature in action_tracker:
                    # Replace previous occurrence with this one (likely the successful retry)
                    prev_index = action_tracker[action_signature]
                    logger.debug(f"[CAPTURE] Replacing previous occurrence of {action_signature} (step {success_path[prev_index].get('step_number')}) with step {step_num}")
                    success_path[prev_index] = state
                else:
                    # New unique action
                    action_tracker[action_signature] = len(success_path)
                    success_path.append(state)
                    logger.debug(f"[CAPTURE] Including step {step_num}: New action {action_signature}")
            else:
                # No clear action signature (keep it)
                success_path.append(state)

        return success_path

    def _get_action_signature(self, action_list: List[Dict]) -> Optional[str]:
        """
        Create a signature for an action to detect duplicates.

        Examples:
        - click on button X → "click:button_X"
        - input text into field Y → "input:field_Y"

        Args:
            action_list: List of action dictionaries

        Returns:
            Action signature string or None
        """
        if not action_list:
            return None

        signatures = []
        for action_item in action_list:
            if 'click' in action_item:
                # Click signature: type + index/element
                click_data = action_item.get('click', {})
                index = click_data.get('index', 'unknown')
                signatures.append(f"click:{index}")

            elif 'input' in action_item or 'input_text' in action_item:
                # Input signature: type + index
                input_key = 'input' if 'input' in action_item else 'input_text'
                input_data = action_item.get(input_key, {})
                index = input_data.get('index', 'unknown')
                # Don't include text content (might vary on retry)
                signatures.append(f"input:{index}")

        # Return combined signature
        return "|".join(signatures) if signatures else None

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
        prompt = f"""You are creating a DETAILED INSTRUCTION MANUAL for a future AI agent to execute this task.

**CRITICAL PRINCIPLES:**
1. This is NOT a history log of what happened - it's a RECIPE for how to do it
2. Write in IMPERATIVE language: "Click the button" NOT "The agent clicked"
3. Be CONCISE - only essential information per step
4. Create GRANULAR, INCREMENTAL steps - break down EVERY action into its own step
5. Ensure ALL steps needed to COMPLETE the task are documented

**STRICT EXCLUSIONS - DO NOT INCLUDE IN THE GUIDE:**
- NO references to local files (todo.md, metadata.json, .md files, etc.)
- NO file system operations (updating files, marking tasks complete in files, etc.)
- NO implementation details about how the agent works internally
- NO references to screenshots, metadata, or data files in the workflow steps
- NO debugging or internal processing steps
- ONLY include user-facing UI actions that happen in the web application

**REMEMBER:** The future agent reading this guide will execute actions in a WEB BROWSER, not on the local file system.
Every step must be a UI action: navigate, click, type, select, scroll, submit, verify.

**GRANULAR STEP REQUIREMENT:**
- Navigation to website = separate step
- Login check/action = separate step
- Each button click = separate step
- Each text input = separate step
- Each form submission/Enter key = separate step
- Final verification/success state = separate step (if applicable)

**Task to Complete**: {task_description}

**Workflow Data** (successful execution path):
{json.dumps(states_with_validated_screenshots, indent=2)}

---

## Guide Structure

### 1. Essential Context Section

Start with:

```markdown
## Essential Context

### Initial Setup
- **Application**: [Name of the application/website]
- **Starting URL**: `https://example.com`
- **Authentication**: [REQUIRED - Choose one of the following]
  * Already logged in (persistent session detected)
  * Logged in with provided credentials
  * Manual login required before starting
  * No login required (public access)
```

### 2. Complete Workflow Path

Provide a numbered list showing ALL incremental steps:
```markdown
### Complete Workflow Path
1. Navigate to [application URL]
2. [If authentication needed] Login or verify logged-in status
3. [Action 1, e.g., "Click the Create button"]
4. [Action 2, e.g., "Type task name in input field"]
5. [Action 3, e.g., "Press Enter to submit"]
6. [Continue with EVERY action until task is COMPLETED]
7. [Final step] Verify task completion / Success state
```

**CRITICAL REQUIREMENTS:**
- EVERY meaningful action must be a separate numbered step
- Do NOT combine multiple actions into one step
- Include navigation, authentication checks, each click, each input, submissions
- Verify the last step COMPLETES the task from the original task description
- If task says "create task in Asana", ensure you show: navigate→login→click create→input name→submit→verify
- DO NOT create high-level summaries - be GRANULAR and INCREMENTAL

### 3. Detailed Workflow Steps

For each step, use this format:

```markdown
### Step N: [Action in Imperative Form]

- **Action**: [Concise imperative instruction, e.g., "Click the 'New Project' button"]
- **URL**: `https://current-url.com`
- **Screenshot**: ![Step N](screenshot_path_value)  [ONLY if has_screenshot=true]
```

**Step Description Rules:**
- Use imperative verbs: "Click", "Type", "Select", "Navigate"
- Be specific: "Click the blue 'Submit' button in bottom-right corner"
- Keep it ONE sentence when possible
- NO verbose explanations or "What's Happening" sections

**Screenshot Rules - STRICT ENFORCEMENT:**
- ONLY add `![Step X](path)` if state has `"has_screenshot": true`
- ONLY use EXACT value from `"screenshot_path"` field
- Navigation steps: NO screenshot
- Wait/loading steps: NO screenshot
- Done actions: NO screenshot
- If `"has_screenshot": false` or missing: NO screenshot line at all

**Examples:**

GOOD (action-focused, UI only):
```markdown
### Step 3: Click the Search Button

- **Action**: Click the search button (magnifying glass icon) in the top navigation bar
- **URL**: `https://youtube.com`
- **Screenshot**: ![Step 3](step_003.png)
```

BAD (verbose, history-like):
```markdown
### Step 3: Search Button Interaction

The agent then proceeded to click on the search button. What's happening: The page is showing the YouTube homepage with various UI elements. The search button is located in the navigation bar and clicking it will activate the search functionality.
```

BAD (contains local file references - NEVER DO THIS):
```markdown
### Step 4: Complete Workflow Path

- **Action**: Update the local file todo.md to mark navigation complete
- **URL**: `https://linear.app`
```

BAD (contains metadata/implementation details - NEVER DO THIS):
```markdown
### Step 5: Save Metadata

- **Action**: Save workflow metadata to metadata.json
- Update screenshot references in local files
```

---

## Output Format

Generate the complete guide following this exact structure:

```markdown
## Essential Context

### Initial Setup
[Fill this section]

### Complete Workflow Path
[Numbered list of high-level steps]

---

## Detailed Workflow Steps

### Step 1: [Action]
[Details]

### Step 2: [Action]
[Details]

[Continue for all steps...]

---

## Workflow Summary

[Brief 2-3 sentence summary of what was accomplished]

- **Total Steps**: [number]
- **Key Actions**: [List main actions taken]
```

**Final Verification Before Outputting:**
- Does the last documented step COMPLETE the original task?
- Are all steps written in imperative language?
- Are screenshot references only where has_screenshot=true?
- Is the authentication status clearly documented?
- CRITICAL: Have you removed ALL references to local files (todo.md, metadata.json, etc.)?
- CRITICAL: Have you removed ALL file system operations?
- CRITICAL: Are ALL steps UI actions in the web browser ONLY?

**REMEMBER:** This guide is for a future agent who will ONLY interact with the web UI, NOT with local files.

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
