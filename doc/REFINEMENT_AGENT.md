# Vision Refinement Agent

## Overview

The Vision Refinement Agent is an optional post-processing step that uses multimodal AI to validate, crop, and enhance workflow guide screenshots for maximum clarity and accuracy.

## Purpose

After the initial workflow guide is generated, this agent:
1. Validates that each screenshot correctly represents its described step
2. Crops screenshots to focus on relevant UI elements (buttons, forms, etc.)
3. Refines step descriptions based on visual analysis
4. Generates an enhanced `REFINED_WORKFLOW_GUIDE.md`

## Architecture

### Components

```
agent/
├── refinement_agent.py      # Main orchestrator
├── vision_validator.py      # Multimodal AI validation (Gemini/Claude)
└── image_processor.py       # CV-based image cropping with 3x3 grid
```

### Flow Diagram

```
[Workflow Guide + Screenshots]
           ↓
[User Prompt: Refine? (y/n)]
           ↓
    [For each screenshot]
           ↓
[Vision Model Validation] ----→ [Invalid?] → [Try step i-1 screenshot]
           ↓                                            ↓
    [Valid + Grid Location]                      [Still invalid?]
           ↓                                            ↓
[Crop using 3x3 Grid]                            [Skip refinement]
           ↓
[Update Step Description]
           ↓
[Save Cropped Image]
           ↓
[Generate REFINED_WORKFLOW_GUIDE.md]
```

## Algorithm

### Phase 1: Preparation

```python
1. Load metadata.json and WORKFLOW_GUIDE.md
2. Extract all steps with screenshot references
3. Initialize vision model (Gemini Flash 2.0 Multimodal)
4. Set up fallback to Claude Sonnet 4.5 (multimodal)
```

### Phase 2: Sequential Screenshot Validation

For each step with `has_screenshot: true`:

```python
Step N processing:
  1. Load screenshot (step_XXX.png)
  2. Prepare context:
     - Task description
     - Step description
     - Current URL
     - Step action details

  3. Call vision model with prompt:
     """
     You are analyzing a workflow screenshot to validate and refine it.

     TASK: {task_description}
     STEP: {step_description}
     URL: {url}
     ACTION: {action_details}

     Analyze the screenshot and respond with:
     1. Is this screenshot showing the described action? (true/false)
     2. Where is the relevant UI element? (3x3 grid coordinates)
     3. Should the step description be improved?

     Use a 3x3 grid system:
     (1,1) (1,2) (1,3)  <- Top row
     (2,1) (2,2) (2,3)  <- Middle row
     (3,1) (3,2) (3,3)  <- Bottom row

     If the element spans multiple cells, list all cells.
     """

  4. Parse response:
     {
       "is_valid": boolean,
       "grid_locations": [(row, col), ...],
       "suggested_description": string,
       "reasoning": string
     }

  5. If is_valid == false:
     - Try previous screenshot (step_XXX-1.png)
     - If still invalid, skip refinement for this step

  6. If is_valid == true:
     - Crop image using grid_locations
     - Update step description if suggested
     - Save as step_XXX_refined.png
```

### Phase 3: Image Cropping (3x3 Grid System)

```python
Grid Mapping:
  Image dimensions: W x H

  Cell dimensions:
    cell_width = W / 3
    cell_height = H / 3

  For grid location (row, col):
    x_start = (col - 1) * cell_width
    y_start = (row - 1) * cell_height
    x_end = col * cell_width
    y_end = row * cell_height

  For multiple cells [(3,2), (3,3)]:
    - Find bounding box encompassing all cells
    - x_min = min(x_start for all cells)
    - x_max = max(x_end for all cells)
    - y_min = min(y_start for all cells)
    - y_max = max(y_end for all cells)
    - Crop to [x_min:x_max, y_min:y_max]

  Add padding:
    - 5% padding around cropped region
    - Ensure padding doesn't exceed image bounds
```

### Phase 4: Guide Generation

```python
1. Clone WORKFLOW_GUIDE.md structure
2. For each step:
   - If refined screenshot exists:
     - Replace reference: step_XXX.png → step_XXX_refined.png
     - Update description if improved
   - Else:
     - Keep original screenshot reference
3. Add refinement metadata footer:
   - Total steps refined
   - Vision model used
   - Timestamp
4. Save as REFINED_WORKFLOW_GUIDE.md
```

## Vision Model Integration

### Primary: Gemini Flash 2.0 (Multimodal)

```python
Model: gemini-2.0-flash-exp
Capabilities:
  - Image understanding
  - Text + image input
  - Fast response time
  - Cost-effective

Prompt Strategy:
  - Provide step context
  - Show screenshot
  - Request structured JSON response
  - Use 3x3 grid coordinate system
```

### Fallback: Claude Sonnet 4.5 (Multimodal)

```python
Model: claude-sonnet-4-5-20250929
Capabilities:
  - Advanced vision analysis
  - Precise UI element detection
  - Detailed reasoning

Triggered when:
  - Gemini API fails
  - Gemini returns invalid response
  - User specifies Claude preference
```

## Validation Logic

### Image Validity Criteria

```python
Valid screenshot if:
  1. Shows the URL mentioned in step
  2. Contains the UI element described (button/form/modal)
  3. Matches the action context (before/after state)
  4. Has clear visual indicators of the step

Invalid screenshot if:
  1. Wrong URL/page
  2. UI element not visible
  3. Wrong application state
  4. Corrupted/blank image
```

### Fallback Strategy

```python
Current step N has invalid screenshot:
  Step 1: Try step N-1 screenshot
    - Sometimes agent captures screenshot after action
    - Previous screenshot may show pre-action state

  Step 2: If N-1 also invalid:
    - Log warning
    - Skip refinement for this step
    - Keep original screenshot in guide
```

## Output Structure

```
output/task_timestamp/
├── step_001.png                    # Original (navigation - no refinement)
├── step_002.png                    # Original (wait - no refinement)
├── step_003.png                    # Original
├── step_003_refined.png            # Cropped to button location
├── step_004.png                    # Original
├── step_004_refined.png            # Cropped to modal
├── step_005.png                    # Original
├── step_005_refined.png            # Cropped to input field
├── WORKFLOW_GUIDE.md               # Original guide
├── REFINED_WORKFLOW_GUIDE.md       # Enhanced guide
├── metadata.json                   # Original metadata
└── refinement_metadata.json        # Refinement details
```

## Integration with Main Workflow

### User Interaction

```bash
[4/4] Generating workflow guide with Gemini...
[OK] Workflow guide generated!

[SUCCESS] Workflow captured successfully!
  - Output: E:\Flow-Planner\output\asana_20251103_212330
  - States: 6
  - Metadata: E:\Flow-Planner\output\asana_20251103_212330\metadata.json
  - Guide: E:\Flow-Planner\output\asana_20251103_212330\WORKFLOW_GUIDE.md

[OPTIONAL] Refine workflow with Vision AI? (y/n): █
```

If user chooses 'y':

```bash
[5/5] Refining workflow with Vision AI...
  [1/4] Validating step 3 screenshot... OK (cropped to grid [3,1])
  [2/4] Validating step 4 screenshot... OK (cropped to grid [2,2])
  [3/4] Validating step 5 screenshot... INVALID, trying previous... OK
  [4/4] Validating step 6 screenshot... OK (cropped to grid [3,2], [3,3])

[OK] Workflow refined!
  - Refined steps: 4/4
  - Cropped screenshots: 4
  - Enhanced guide: REFINED_WORKFLOW_GUIDE.md
```

## Configuration

### Environment Variables

```env
# Refinement Settings
ENABLE_REFINEMENT=true
REFINEMENT_MODEL=gemini           # gemini or claude
REFINEMENT_FALLBACK=claude
REFINEMENT_GRID_SIZE=3            # 3x3 grid
REFINEMENT_PADDING=0.05           # 5% padding
REFINEMENT_AUTO=false             # Auto-refine without prompt
```

### Config.py Updates

```python
# Refinement configuration
ENABLE_REFINEMENT = os.getenv('ENABLE_REFINEMENT', 'true').lower() == 'true'
REFINEMENT_MODEL = os.getenv('REFINEMENT_MODEL', 'gemini')
REFINEMENT_FALLBACK = os.getenv('REFINEMENT_FALLBACK', 'claude')
REFINEMENT_GRID_SIZE = int(os.getenv('REFINEMENT_GRID_SIZE', '3'))
REFINEMENT_PADDING = float(os.getenv('REFINEMENT_PADDING', '0.05'))
REFINEMENT_AUTO = os.getenv('REFINEMENT_AUTO', 'false').lower() == 'true'
```

## Error Handling

### Vision Model Failures

```python
try:
    result = gemini_validate(screenshot, context)
except GeminiAPIError as e:
    logger.warning(f"[REFINEMENT] Gemini failed: {str(e)}, trying Claude")
    try:
        result = claude_validate(screenshot, context)
    except ClaudeAPIError as e:
        logger.error(f"[REFINEMENT] Both models failed: {str(e)}")
        # Skip refinement for this step
        continue
```

### Image Processing Failures

```python
try:
    cropped_image = crop_to_grid(image, grid_locations)
except ImageProcessingError as e:
    logger.error(f"[REFINEMENT] Crop failed: {str(e)}")
    # Use original image
    cropped_image = image
```

### Invalid Grid Coordinates

```python
if not validate_grid_coords(grid_locations):
    logger.warning(f"[REFINEMENT] Invalid grid coords: {grid_locations}")
    # Use center region as fallback
    grid_locations = [(2, 2)]
```

## Performance Considerations

### Cost Optimization

```python
- Use Gemini Flash 2.0 (cheaper) as primary
- Claude Sonnet 4.5 only as fallback
- Process only screenshots with has_screenshot=true
- Skip navigation/wait/done steps (no refinement needed)

Estimated cost per workflow:
  - Average 4 screenshots to refine
  - Gemini: ~$0.02 per workflow
  - Claude fallback: ~$0.10 per workflow (if needed)
```

### Speed Optimization

```python
- Sequential processing (no parallel - rate limits)
- Skip steps without screenshots
- Cache model responses
- Reuse image buffers

Estimated time:
  - 2-3 seconds per screenshot validation
  - 0.5 seconds per crop operation
  - Total: ~10-15 seconds for typical workflow
```

## File Associations

### Core Files

| File | Purpose | Dependencies |
|------|---------|--------------|
| `agent/refinement_agent.py` | Main orchestrator | vision_validator, image_processor |
| `agent/vision_validator.py` | AI validation calls | google.generativeai, anthropic |
| `agent/image_processor.py` | Image cropping | PIL, cv2, numpy |
| `run_workflow.py` | Updated main flow | refinement_agent |

### Generated Files

| File | When Created | Content |
|------|-------------|---------|
| `REFINED_WORKFLOW_GUIDE.md` | After refinement | Enhanced guide with cropped screenshots |
| `refinement_metadata.json` | After refinement | Validation results and crop details |
| `step_XXX_refined.png` | Per valid screenshot | Cropped/focused version |

## Testing Strategy

### Unit Tests

```python
test_image_processor.py:
  - test_grid_coordinate_calculation()
  - test_single_cell_crop()
  - test_multiple_cell_crop()
  - test_boundary_handling()
  - test_padding_application()

test_vision_validator.py:
  - test_gemini_validation()
  - test_claude_fallback()
  - test_invalid_response_handling()
  - test_grid_parsing()

test_refinement_agent.py:
  - test_sequential_processing()
  - test_fallback_to_previous_screenshot()
  - test_guide_generation()
  - test_error_recovery()
```

### Integration Tests

```python
test_refinement_workflow.py:
  - test_end_to_end_refinement()
  - test_partial_refinement_success()
  - test_all_validations_fail()
  - test_user_cancellation()
```

## Future Enhancements

1. **Adaptive Grid**: Use variable grid sizes (4x4, 5x5) for complex UIs
2. **Smart Cropping**: ML-based element detection instead of grid
3. **Batch Processing**: Parallel validation with rate limiting
4. **Interactive Mode**: Let user approve/reject each refinement
5. **Style Transfer**: Consistent screenshot styling (borders, highlights)

## Success Metrics

```python
Refinement Quality:
  - Screenshot validation accuracy: >90%
  - Crop relevance score: >85%
  - Step description improvement: >70%

Performance:
  - Processing time: <20 seconds per workflow
  - API call success rate: >95%
  - User satisfaction: >80% find refinement valuable
```

---

**Version**: 1.0
**Last Updated**: 2025-11-03
**Maintainer**: FlowForge Team
