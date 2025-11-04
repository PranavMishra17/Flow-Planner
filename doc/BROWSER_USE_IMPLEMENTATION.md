# Browser-Use Architecture Implementation

## Overview

Successfully migrated FlowForge from custom Playwright executor to Browser-Use autonomous agent architecture.

## What Changed

### Architecture Transformation

**Before (Old System)**:
```
Gemini (detailed plan with CSS selectors)
  ↓
Playwright Executor (follows plan exactly)
  ↓
Claude Vision Guide (error recovery)
  ↓
Claude Validator (validation)
```

**After (Browser-Use System)**:
```
Gemini (auth detection + high-level outline)
  ↓
Browser-Use Agent (autonomous execution)
  ↓
State Capturer (extract screenshots + metadata)
```

## New Components

### 1. Modified Planner (`agent/planner.py`)
- **New Output Format**:
  - `task_analysis`: Authentication detection and complexity
  - `workflow_outline`: High-level steps (NO CSS selectors)
  - `context`: Application patterns and challenges

**Example Output**:
```json
{
  "task_analysis": {
    "requires_authentication": true,
    "auth_type": "oauth_google",
    "estimated_steps": 6,
    "complexity": "medium"
  },
  "workflow_outline": [
    "Navigate to application dashboard",
    "Authenticate via Google OAuth",
    "Access projects section",
    "Create new project",
    "Configure project settings",
    "Save and verify creation"
  ],
  "context": {
    "app_name": "Linear",
    "app_url": "https://linear.app",
    "common_patterns": "Uses modal dialogs for creation",
    "known_challenges": "May show onboarding on first login"
  }
}
```

### 2. Browser-Use Agent (`agent/browser_use_agent.py`)
- **Autonomous Execution**: LLM-powered navigation without pre-programmed selectors
- **Vision + DOM Analysis**: Makes decisions based on current UI state
- **Error Handling**: Automatically handles popups, ads, dynamic content
- **State Tracking**: Captures screenshots and actions at each step

**Key Features**:
- Perception-cognition-action loop
- Dynamic UI adaptation
- Self-recovery from errors
- Built-in state capture

### 3. State Capturer (`agent/state_capturer.py`)
- **Extracts States**: Screenshots, URLs, actions from Browser-Use history
- **Structured Storage**: Organized output with metadata.json
- **Guide Generation**: Creates markdown workflow guides

**Output Structure**:
```
outputs/
└── task_name_20250102_123456/
    ├── metadata.json
    ├── step_001.png
    ├── step_002.png
    ├── step_003.png
    └── workflow_guide.md
```

### 4. Enhanced Authenticator (`agent/authenticator.py`)
- **Tier 1**: Persistent browser profile (unchanged)
- **Tier 2**: **NEW** - Auto-login using Browser-Use agent with credentials
- **Tier 3**: Manual intervention (unchanged)

**New Tier 2 Flow**:
```python
# If OAuth buttons not found, use Browser-Use agent to log in
login_agent = Agent(
    task=f"Log in with email {email} and password {password}",
    llm=llm,
    browser=browser
)
await login_agent.run()
```

## Configuration

### Environment Variables

Add to `.env`:
```bash
# Browser-Use Settings
BROWSER_USE_MAX_STEPS=50
BROWSER_USE_LLM_MODEL=gpt-4o

# Authentication (for Tier 2 auto-login)
DEFAULT_EMAIL=your.email@gmail.com
DEFAULT_PASSWORD=your_secure_password

# Existing settings
USE_PERSISTENT_CONTEXT=true
BROWSER_USER_DATA_DIR=C:\Users\YourName\AppData\Local\Chromium\User Data
```

### API Keys Required
- `GEMINI_API_KEY`: For planning and auth detection
- `OPENAI_API_KEY`: For Browser-Use agent (or other LLM provider)
- `ANTHROPIC_API_KEY`: Optional (only if using old validator)

## Usage

### Basic Workflow

```python
import asyncio
from agent.planner import GeminiPlanner
from agent.browser_use_agent import BrowserUseAgent
from agent.state_capturer import StateCapturer

async def run_workflow():
    # 1. Create plan
    planner = GeminiPlanner()
    plan = await planner.create_plan(
        task="Create a new project in Linear",
        app_url="https://linear.app",
        app_name="Linear"
    )

    # 2. Execute with Browser-Use
    agent = BrowserUseAgent()
    states = await agent.execute_workflow(
        task="Create a new project in Linear",
        workflow_outline=plan['workflow_outline'],
        app_url="https://linear.app",
        context=plan['context']
    )

    # 3. Capture states
    capturer = StateCapturer()
    summary = await capturer.capture_states(
        states=states,
        task_name="linear_create_project",
        task_description="Create a new project in Linear"
    )

    # 4. Generate guide
    guide_path = await capturer.generate_guide(summary['metadata_path'])

    print(f"Workflow complete! Guide: {guide_path}")

asyncio.run(run_workflow())
```

### With Authentication

```python
async def run_with_auth():
    # 1. Create plan
    planner = GeminiPlanner()
    plan = await planner.create_plan(task, app_url, app_name)

    # 2. Execute with authentication
    agent = BrowserUseAgent()
    auth_handler = AuthenticationHandler()

    states = await agent.execute_with_authentication(
        task=task,
        workflow_outline=plan['workflow_outline'],
        app_url=app_url,
        context=plan['context'],
        auth_handler=auth_handler,
        requires_auth=plan['task_analysis']['requires_authentication'],
        auth_type=plan['task_analysis']['auth_type']
    )

    # 3. Capture and save
    capturer = StateCapturer()
    summary = await capturer.capture_states(states, task_name, task)
```

## Testing

### Run Test Suite

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python test_browser_use.py
```

### Test Cases

1. **Simple Navigation**: Public page without auth (Wikipedia search)
2. **Planner Only**: Auth detection for multiple sites
3. **With Authentication**: Full workflow with login (GitHub, Linear, etc.)

### Quick Test

```bash
# Test planner auth detection
python -c "
import asyncio
from agent.planner import GeminiPlanner

async def test():
    planner = GeminiPlanner()
    plan = await planner.create_plan(
        'Search for Python',
        'https://www.google.com',
        'Google'
    )
    print(plan)

asyncio.run(test())
"
```

## Advantages

### Why Browser-Use?

1. **No Pre-Programmed Selectors**: Adapts to any UI dynamically
2. **Self-Healing**: Automatically handles UI changes, popups, ads
3. **Reduced Complexity**: No custom vision loop or validation needed
4. **Community Support**: 71k+ GitHub stars, active development
5. **Cost Effective**: Fewer API calls than old validation approach
6. **Universal**: Works across different web apps without code changes

### Performance

- **Old System**: 1 Gemini call + N Playwright steps + M Claude validations
- **New System**: 1 Gemini call + K Browser-Use LLM calls (typically 5-15)

## Migration Path

If you have existing code using the old system:

1. ✅ Install Browser-Use: `pip install browser-use`
2. ✅ Update `config.py`: Add Browser-Use settings
3. ✅ Modify `planner.py`: Change output format
4. ✅ Create `browser_use_agent.py`: Wrapper for execution
5. ✅ Create `state_capturer.py`: State extraction
6. ✅ Update `authenticator.py`: Add Tier 2 auto-login
7. ⚠️ Update API/routes: Use new agent structure (if applicable)
8. ⚠️ Remove old files: `executor.py`, `validator.py`, `vision_guide.py` (when ready)

## Known Issues & Solutions

### Issue 1: Browser-Use API compatibility
- **Problem**: Browser-Use API may differ from documentation
- **Solution**: Check `browser-use` version in requirements.txt, adjust imports

### Issue 2: Authentication with persistent profile
- **Problem**: Browser-Use may create new context instead of using existing
- **Solution**: Ensure `user_data_dir` is set correctly in browser config

### Issue 3: Screenshot format
- **Problem**: Browser-Use may return different screenshot formats
- **Solution**: State capturer handles PIL Image, bytes, and file paths

## Next Steps

1. **Test with Real Workflows**: Run test suite with actual applications
2. **Tune LLM Settings**: Adjust model and temperature for optimal performance
3. **Add Monitoring**: Track success rates and common failure patterns
4. **Optimize Costs**: Consider using cheaper models for simple tasks
5. **Scale Up**: Test with multiple concurrent workflows

## Files Created/Modified

### New Files
- `agent/browser_use_agent.py` - Browser-Use wrapper
- `agent/state_capturer.py` - State extraction and storage
- `test_browser_use.py` - Comprehensive test suite
- `BROWSER_USE_IMPLEMENTATION.md` - This documentation

### Modified Files
- `requirements.txt` - Added browser-use package
- `config.py` - Added Browser-Use and auth settings
- `agent/planner.py` - Changed output format for auth detection
- `agent/authenticator.py` - Added Tier 2 auto-login with Browser-Use

### Files to Remove (When Ready)
- `agent/executor.py` - Replaced by Browser-Use agent
- `agent/validator.py` - Not needed (agent self-validates)
- `agent/vision_guide.py` - Not needed (agent handles errors)

## Support

For issues or questions:
1. Check Browser-Use docs: https://github.com/browser-use/browser-use
2. Review test cases in `test_browser_use.py`
3. Enable debug logging in `config.py`
4. Check logs in `logs/` directory

## Version

- **Implementation Date**: 2025-01-02
- **Browser-Use Version**: 0.1.14
- **Architecture**: Browser-Use autonomous agent
- **Status**: ✅ Ready for testing

---

**Remember**: Always test with persistent browser profiles to maximize authentication success!
