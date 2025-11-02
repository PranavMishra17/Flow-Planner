# System Overview - AI Workflow Capture System

## Architecture

**Autonomous Execution**: Gemini Planning → Browser-Use Agent → State Capture

## Core Files

### Configuration & Setup
- **[config.py](config.py)**: Configuration management (API keys, browser settings)
- **utils/logger.py**: Logging with console and rotating file handlers
- **.env**: Environment variables including persistent browser profile path

### Agent Pipeline

**1. [agent/planner.py](agent/planner.py) (GeminiPlanner)**
- Uses Google Gemini to analyze tasks and detect authentication requirements
- Outputs high-level workflow outline (no CSS selectors)
- Returns: task_analysis (auth type, complexity) + workflow_outline steps

**2. [agent/browser_use_agent.py](agent/browser_use_agent.py) (BrowserUseAgent)**
- Wrapper for Browser-Use autonomous agent framework
- Uses Claude Sonnet 4.5 for vision + DOM-based navigation
- Autonomous perception-cognition-action loop
- Handles dynamic content, popups, and navigation automatically
- No pre-programmed selectors required

**3. [agent/state_capturer.py](agent/state_capturer.py) (StateCapturer)**
- Extracts screenshots and metadata from Browser-Use execution history
- Organizes output into structured directories
- Generates workflow guides from captured states

**4. [agent/authenticator.py](agent/authenticator.py) (AuthenticationHandler)**
- **Tier 1**: Persistent profile (automatic via saved cookies)
- **Tier 2**: Browser-Use agent auto-login with credentials from .env
- **Tier 3**: Manual user login with timeout prompt

## Data Flow

```
User Task → Planner (Gemini) → Auth detection + workflow outline
           ↓
Browser-Use Agent → Autonomous execution
   - Perception: Screenshot + DOM analysis
   - Cognition: Claude Sonnet 4.5 reasoning
   - Action: Dynamic navigation decisions
   - Loop until workflow complete
           ↓
State Capturer → Extract screenshots + metadata
           ↓
Save to output/{task_name}_{timestamp}/
```

## Key Features

- **Autonomous Navigation**: Agent decides actions based on live UI state
- **No Pre-Programmed Selectors**: Adapts to dynamic content automatically
- **Vision + DOM**: Combined approach for robust navigation
- **Persistent Authentication**: Saved browser profiles for seamless login
- **Cost Effective**: Single Claude model, fewer API calls

## Test Scripts
- **[test_browser_use.py](test_browser_use.py)**: Comprehensive test suite (navigation, auth detection)
- **[run_workflow.py](run_workflow.py)**: Quick workflow capture with predefined tasks
