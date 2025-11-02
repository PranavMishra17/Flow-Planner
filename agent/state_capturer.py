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

        # Prepare context for Gemini
        states = metadata.get('states', [])

        # Build prompt for Gemini
        prompt = f"""You are analyzing a captured UI workflow for the following task:

**Original Task**: {task_description}

**Workflow Metadata**:
- Total Steps: {metadata.get('execution', {}).get('total_steps', 0)}
- Successful Steps: {metadata.get('execution', {}).get('successful_steps', 0)}

**Steps Taken**:
{json.dumps(states, indent=2)}

Please generate a comprehensive, user-friendly step-by-step workflow guide in Markdown format that:

1. Includes a clear title and task description
2. Lists each step with:
   - Step number and clear action description
   - The URL if relevant
   - Key actions taken (clicks, inputs, navigations)
   - Reference to the screenshot file (format: `![Step X](step_XXX.png)`)
3. Provides helpful notes about what happens at each step
4. Includes tips or important observations
5. Has a summary at the end

Format the guide professionally with proper markdown headers, bullet points, and inline screenshots.

The screenshots are named: step_001.png, step_002.png, etc.

IMPORTANT: Include the screenshot references for EVERY step where a screenshot exists.
"""

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
