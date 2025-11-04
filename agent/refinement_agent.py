"""
Workflow refinement agent using vision AI to validate and enhance screenshot documentation.
Orchestrates validation, cropping, and guide generation for optimal workflow documentation.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from agent.vision_validator import VisionValidator
from agent.image_processor import ImageProcessor
from config import Config

logger = logging.getLogger(__name__)


class RefinementAgent:
    """
    Orchestrates workflow refinement using vision AI and image processing.
    Validates screenshots, crops to relevant regions, and generates enhanced guides.
    """

    def __init__(
        self,
        primary_model: str = "gemini",
        fallback_model: str = "claude",
        grid_size: int = 3,
        padding_percent: float = 0.05
    ):
        """
        Initialize refinement agent.

        Args:
            primary_model: Primary vision model ("gemini" or "claude")
            fallback_model: Fallback vision model
            grid_size: Size of grid for cropping (default 3x3)
            padding_percent: Padding around cropped regions (default 5%)
        """
        self.validator = VisionValidator(primary_model, fallback_model)
        self.processor = ImageProcessor(grid_size, padding_percent)

        logger.info(f"[REFINEMENT] Agent initialized with {primary_model} (fallback: {fallback_model})")

    async def refine_workflow(
        self,
        metadata_path: str,
        workflow_guide_path: str,
        task_description: str
    ) -> Dict:
        """
        Refine workflow by validating and cropping screenshots.

        Args:
            metadata_path: Path to metadata.json
            workflow_guide_path: Path to WORKFLOW_GUIDE.md
            task_description: Original task description

        Returns:
            Dictionary with refinement results and paths
        """
        logger.info("[REFINEMENT] ==================== WORKFLOW REFINEMENT ====================")
        logger.info(f"[REFINEMENT] Metadata: {metadata_path}")
        logger.info(f"[REFINEMENT] Guide: {workflow_guide_path}")

        try:
            # Load metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Get workflow directory
            workflow_dir = os.path.dirname(metadata_path)

            # Extract steps with screenshots
            states = metadata.get('states', [])
            steps_to_refine = self._extract_screenshot_steps(states)

            logger.info(f"[REFINEMENT] Found {len(steps_to_refine)} steps with screenshots to refine")

            if not steps_to_refine:
                logger.warning("[REFINEMENT] No screenshots to refine")
                return {
                    'success': False,
                    'message': 'No screenshots found for refinement',
                    'refined_count': 0
                }

            # Process each screenshot
            refinement_results = []
            for step in steps_to_refine:
                result = await self._refine_step(
                    step,
                    workflow_dir,
                    task_description
                )
                refinement_results.append(result)

            # Generate refined guide
            refined_guide_path = os.path.join(workflow_dir, "REFINED_WORKFLOW_GUIDE.md")
            self._generate_refined_guide(
                workflow_guide_path,
                refined_guide_path,
                refinement_results
            )

            # Save refinement metadata
            refinement_metadata_path = os.path.join(workflow_dir, "refinement_metadata.json")
            self._save_refinement_metadata(
                refinement_metadata_path,
                refinement_results,
                task_description
            )

            # Calculate statistics
            refined_count = sum(1 for r in refinement_results if r['refined'])
            total_count = len(refinement_results)

            logger.info(f"[REFINEMENT] Refined {refined_count}/{total_count} screenshots")
            logger.info("[REFINEMENT] ==================== END REFINEMENT ====================")

            return {
                'success': True,
                'refined_guide_path': refined_guide_path,
                'refinement_metadata_path': refinement_metadata_path,
                'refined_count': refined_count,
                'total_count': total_count,
                'results': refinement_results
            }

        except Exception as e:
            logger.error(f"[REFINEMENT] Refinement failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f"Refinement failed: {str(e)}",
                'refined_count': 0
            }

    def _extract_screenshot_steps(self, states: List[Dict]) -> List[Dict]:
        """
        Extract steps that have screenshots and should be refined.

        Args:
            states: List of workflow states

        Returns:
            List of steps with screenshot information
        """
        screenshot_steps = []

        for state in states:
            step_num = state.get('step_number')

            # Only process steps with screenshots
            if not state.get('screenshot_path'):
                logger.debug(f"[REFINEMENT] Skipping step {step_num}: No screenshot")
                continue

            # Check action list to determine if this is a refineable step
            action = state.get('action', {})
            action_list = action.get('action', [])

            # Skip if this is a done action (actual done action, not 'is_done' field in description)
            if any('done' in str(action_item) and isinstance(action_item, dict) and 'done' in action_item for action_item in action_list):
                logger.debug(f"[REFINEMENT] Skipping step {step_num}: Done action")
                continue

            # Skip navigation actions
            if any('navigate' in str(action_item) for action_item in action_list):
                logger.debug(f"[REFINEMENT] Skipping step {step_num}: Navigation")
                continue

            # Check for actual UI actions (clicks and inputs)
            has_ui_action = any(
                key in action_item
                for action_item in action_list
                for key in ['click', 'input', 'input_text']
            )

            if has_ui_action:
                screenshot_steps.append(state)
                logger.info(f"[REFINEMENT] Including step {step_num} for refinement (has UI action)")
            else:
                logger.debug(f"[REFINEMENT] Skipping step {step_num}: No UI action")

        return screenshot_steps

    async def _refine_step(
        self,
        step: Dict,
        workflow_dir: str,
        task_description: str
    ) -> Dict:
        """
        Refine a single step's screenshot.

        Args:
            step: Step dictionary
            workflow_dir: Workflow output directory
            task_description: Original task description

        Returns:
            Dictionary with refinement result for this step
        """
        step_num = step.get('step_number')
        screenshot_path = step.get('screenshot_path', '')
        full_screenshot_path = os.path.join(workflow_dir, screenshot_path)

        logger.info(f"[REFINEMENT] Processing step {step_num}: {screenshot_path}")

        result = {
            'step_number': step_num,
            'original_screenshot': screenshot_path,
            'refined_screenshot': None,
            'refined': False,
            'valid': False,
            'grid_locations': [],
            'suggested_description': step.get('description', ''),
            'reasoning': '',
            'model_used': 'none'
        }

        try:
            # Build step context
            step_context = {
                'task_description': task_description,
                'step_description': step.get('description', ''),
                'step_number': step_num,
                'url': step.get('url', ''),
                'action': step.get('action', {})
            }

            # Validate screenshot
            validation = await self.validator.validate_screenshot(
                full_screenshot_path,
                step_context
            )

            result['valid'] = validation['is_valid']
            result['grid_locations'] = validation['grid_locations']
            result['suggested_description'] = validation['suggested_description']
            result['reasoning'] = validation['reasoning']
            result['model_used'] = validation['model_used']

            # If invalid, try previous screenshot
            if not validation['is_valid']:
                logger.warning(f"[REFINEMENT] Step {step_num} screenshot invalid, trying previous")
                prev_screenshot = self._get_previous_screenshot(step_num, screenshot_path)

                if prev_screenshot:
                    prev_full_path = os.path.join(workflow_dir, prev_screenshot)
                    if os.path.exists(prev_full_path):
                        logger.info(f"[REFINEMENT] Trying previous screenshot: {prev_screenshot}")

                        validation = await self.validator.validate_screenshot(
                            prev_full_path,
                            step_context
                        )

                        if validation['is_valid']:
                            logger.info(f"[REFINEMENT] Previous screenshot is valid")
                            full_screenshot_path = prev_full_path
                            screenshot_path = prev_screenshot
                            result['valid'] = True
                            result['grid_locations'] = validation['grid_locations']
                            result['suggested_description'] = validation['suggested_description']
                            result['reasoning'] = validation['reasoning'] + " (using previous screenshot)"
                        else:
                            logger.warning(f"[REFINEMENT] Previous screenshot also invalid, skipping")
                            return result
                else:
                    logger.warning(f"[REFINEMENT] No previous screenshot available, skipping")
                    return result

            # Crop screenshot
            if result['valid'] and result['grid_locations']:
                refined_filename = screenshot_path.replace('.png', '_refined.png')
                refined_path = os.path.join(workflow_dir, refined_filename)

                success = self.processor.crop_to_grid(
                    full_screenshot_path,
                    result['grid_locations'],
                    refined_path
                )

                if success:
                    result['refined_screenshot'] = refined_filename
                    result['refined'] = True
                    logger.info(f"[REFINEMENT] Step {step_num} refined successfully")
                else:
                    logger.warning(f"[REFINEMENT] Step {step_num} crop failed, keeping original")

        except Exception as e:
            logger.error(f"[REFINEMENT] Step {step_num} refinement failed: {str(e)}", exc_info=True)
            result['reasoning'] = f"Refinement error: {str(e)}"

        return result

    def _get_previous_screenshot(self, current_step: int, current_path: str) -> Optional[str]:
        """
        Get filename of previous screenshot.

        Args:
            current_step: Current step number
            current_path: Current screenshot path (e.g., "step_005.png")

        Returns:
            Previous screenshot filename or None
        """
        if current_step <= 1:
            return None

        # Extract format from current path (step_XXX.png)
        prefix = current_path.rsplit('_', 1)[0]  # "step"
        suffix = current_path.split('.')[-1]  # "png"

        # Build previous filename
        prev_step = current_step - 1
        prev_filename = f"{prefix}_{prev_step:03d}.{suffix}"

        return prev_filename

    def _generate_refined_guide(
        self,
        original_guide_path: str,
        refined_guide_path: str,
        refinement_results: List[Dict]
    ):
        """
        Generate refined workflow guide with cropped screenshots.

        Args:
            original_guide_path: Path to original WORKFLOW_GUIDE.md
            refined_guide_path: Path to save REFINED_WORKFLOW_GUIDE.md
            refinement_results: List of refinement results
        """
        logger.info(f"[REFINEMENT] Generating refined guide: {refined_guide_path}")

        try:
            # Load original guide
            with open(original_guide_path, 'r', encoding='utf-8') as f:
                guide_content = f.read()

            # Build replacement map
            replacements = {}
            for result in refinement_results:
                if result['refined'] and result['refined_screenshot']:
                    original = result['original_screenshot']
                    refined = result['refined_screenshot']
                    replacements[original] = refined

            # Replace screenshot references
            for original, refined in replacements.items():
                guide_content = guide_content.replace(f"]({original})", f"]({refined})")
                logger.debug(f"[REFINEMENT] Replaced {original} → {refined}")

            # Update descriptions if suggested
            for result in refinement_results:
                if result.get('suggested_description'):
                    # This is a simple replacement - in practice, might need more sophisticated parsing
                    pass  # TODO: Implement description updates if needed

            # Add refinement footer
            refined_count = sum(1 for r in refinement_results if r['refined'])
            refinement_footer = f"""

---

## Refinement Information

This guide has been enhanced using Vision AI to validate and crop screenshots for clarity.

- **Refined Screenshots**: {refined_count}/{len(refinement_results)}
- **Refinement Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Models Used**: {', '.join(set(r['model_used'] for r in refinement_results if r['model_used'] != 'none'))}

### Refinement Details

| Step | Original | Refined | Valid | Grid Location |
|------|----------|---------|-------|---------------|
"""

            for result in refinement_results:
                step_num = result['step_number']
                original = result['original_screenshot']
                refined = result.get('refined_screenshot', 'Not refined')
                valid = 'Yes' if result['valid'] else 'No'
                grid = str(result.get('grid_locations', []))

                refinement_footer += f"| {step_num} | {original} | {refined} | {valid} | {grid} |\n"

            # Append footer
            guide_content += refinement_footer

            # Save refined guide
            with open(refined_guide_path, 'w', encoding='utf-8') as f:
                f.write(guide_content)

            logger.info(f"[REFINEMENT] Refined guide saved: {refined_guide_path}")

        except Exception as e:
            logger.error(f"[REFINEMENT] Guide generation failed: {str(e)}", exc_info=True)
            raise

    def _save_refinement_metadata(
        self,
        metadata_path: str,
        refinement_results: List[Dict],
        task_description: str
    ):
        """
        Save refinement metadata to JSON file.

        Args:
            metadata_path: Path to save metadata
            refinement_results: List of refinement results
            task_description: Original task description
        """
        logger.info(f"[REFINEMENT] Saving refinement metadata: {metadata_path}")

        try:
            metadata = {
                'task': task_description,
                'refined_at': datetime.now().isoformat(),
                'total_steps': len(refinement_results),
                'refined_steps': sum(1 for r in refinement_results if r['refined']),
                'results': refinement_results
            }

            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"[REFINEMENT] Metadata saved successfully")

        except Exception as e:
            logger.error(f"[REFINEMENT] Metadata save failed: {str(e)}", exc_info=True)
