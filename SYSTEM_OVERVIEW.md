# System Overview - AI Workflow Capture System

## Architecture

**Hybrid Execution**: Gemini Planning → Execution with Vision Recovery

## Core Files

### Configuration & Setup
- **[config.py](config.py)**: Centralized environment variable configuration (API keys, browser settings, vision recovery settings)
- **utils/logger.py**: Logging system with console (INFO) and rotating file handlers (DEBUG)
- **.env**: Environment variables including persistent browser profile path

### Agent Pipeline

**1. [agent/planner.py](agent/planner.py) (GeminiPlanner)**
- Uses Google Gemini with web search grounding to research workflows
- Generates COMPLETE execution plans with specific CSS selectors and fallbacks
- Researches actual UI patterns and selector strategies
- Output: List of detailed steps with actions (goto, click, fill, wait, scroll)

**2. [agent/executor.py](agent/executor.py) (PlaywrightExecutor)**
- Launches Chromium with persistent context (loads saved cookies/logins)
- Logs all cookies by domain on startup for debugging
- Calls authenticator before executing workflow
- **Executes Gemini's plan first** with fallback selectors
- **Vision Recovery**: Only calls Claude Vision when a step fails
- Captures screenshots after each step (and on errors)
- Uses scroll_into_view_if_needed for all interactions (auto-scroll)

**3. [agent/vision_guide.py](agent/vision_guide.py) (VisionGuide)**
- Uses Claude Haiku Vision for error recovery only
- Analyzes error screenshots and suggests corrective actions
- Provides few-shot prompting for common scenarios (login, ads, scrolling, form filling)
- Detects authentication blockers and triggers auth handler automatically
- Handles dynamic UI elements and unexpected states

**4. [agent/authenticator.py](agent/authenticator.py) (AuthenticationHandler)**
- **Tier 1**: Checks if already logged in via persistent profile (detects login page URL patterns)
- **Tier 2**: Auto-detects OAuth buttons (Google/GitHub) and clicks them
- **Tier 3**: Prompts user for manual login with configurable timeout
- Logs authentication state: cookies, profile elements, localStorage

**5. [agent/validator.py](agent/validator.py) (ClaudeValidator)**
- Optional post-execution validation using Claude Vision
- Resizes images to fit 8000px limit automatically
- Returns validation with confidence level and reason

## Data Flow

```
User Task → Planner (Gemini grounded search) → Full Execution Plan with selectors
           ↓
Executor launches browser → Authenticator checks login
           ↓
Execute each step from Gemini plan:
   - Try primary selector
   - Try fallback selectors
   - If all fail → Vision Recovery (Claude analyzes screenshot)
       - If authentication blocker detected → Trigger auth handler
       - Otherwise execute vision's suggested actions
           ↓
Capture screenshots → Save to output/runN/
           ↓
Optional: Validator (Claude) analyzes final results
```

## Key Features

- **Gemini-First Execution**: Fast, reliable execution using researched selectors
- **Vision Recovery**: Claude Vision only called on errors (cost-effective)
- **Auto-Scroll**: Built into all interactions via Playwright
- **Fallback Selectors**: Multiple selector strategies from Gemini research
- **Ad Detection**: System understands ads don't mean failure

## Test Script
- **[test_agent.py](test_agent.py)**: Runs complete pipeline with predefined test cases (YouTube, Supabase, Notion)
