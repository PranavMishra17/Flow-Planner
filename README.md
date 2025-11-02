# Flow Planner

An AI-powered multi-agent system that automatically captures, documents, and visualizes step-by-step UI workflows for any web application. Powered by Gemini planning, Playwright automation, and Claude vision validation.

## Features

- **AI Planning**: Uses Google Gemini with web search grounding to research tasks and create execution plans
- **Browser Automation**: Playwright-based execution with fallback selectors for robustness
- **Visual Validation**: Claude Vision validates each step by analyzing screenshots
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Error Recovery**: Graceful error handling with alternative selectors and retry logic

## Day 1 Status: COMPLETE

Core agent components implemented and ready for testing:
- [config.py](config.py) - Configuration management
- [utils/logger.py](utils/logger.py) - Logging setup
- [agent/planner.py](agent/planner.py) - Gemini-based workflow planner
- [agent/executor.py](agent/executor.py) - Playwright automation executor
- [agent/validator.py](agent/validator.py) - Claude Vision validator
- [test_agent.py](test_agent.py) - Test script for complete pipeline

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### 2. Configure Environment

Copy the `.env-template` file to `.env` and add your API keys:

```bash
# API Keys
GEMINI_API_KEY=your-gemini-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here

# Flask Configuration
FLASK_SECRET_KEY=generate-random-secret-key-here
FLASK_ENV=development

# Application Settings
ENABLE_VALIDATION=true
HEADLESS_BROWSER=false
MAX_CONCURRENT_JOBS=3
```

**Get API Keys:**
- **Gemini**: https://aistudio.google.com/app/apikey (Free)
- **Anthropic**: https://console.anthropic.com/ ($5 free credit)

### 3. Test Your Setup

First, verify your API keys work:

```bash
python test_keys.py
```

You should see:
```
[SUCCESS] Gemini: Gemini works
[SUCCESS] Claude: Claude works
```

## Testing Day 1 Components

### Interactive Mode

Run the test script and enter your own test case:

```bash
python test_agent.py
```

You'll be prompted to enter:
- Task description (e.g., "Navigate to the homepage")
- Application URL (e.g., "https://example.com")
- Application name (e.g., "Example Website")

### Predefined Tests

Run the included test cases:

```bash
python test_agent.py --predefined
```

### What Happens During a Test

1. **Planning Phase**: Gemini researches the task and creates an execution plan
2. **Execution Phase**: Playwright executes each step and captures screenshots
3. **Validation Phase**: Claude analyzes screenshots to verify success
4. **Results**: A JSON file is saved with complete workflow data

### Expected Output

```
[PLANNER] Creating plan for task: Navigate to the homepage
[PLANNER] Plan created successfully with 2 steps
[EXECUTOR] Starting execution of 2 steps
[EXECUTOR] Step 1 completed successfully
[EXECUTOR] Step 2 completed successfully
[VALIDATOR] Validating 2 steps
[VALIDATOR] Validation complete: 2/2 steps valid

Screenshots saved to: static/screenshots/test_YYYYMMDD_HHMMSS/
Results saved to: test_results_test_YYYYMMDD_HHMMSS.json
```

## Project Structure

```
Flow-Planner/
├── agent/
│   ├── planner.py       # Gemini workflow planner
│   ├── executor.py      # Playwright automation
│   └── validator.py     # Claude Vision validator
├── utils/
│   └── logger.py        # Logging configuration
├── static/
│   └── screenshots/     # Captured screenshots
├── logs/                # Application logs
├── config.py            # Configuration management
├── test_agent.py        # Test script
└── requirements.txt     # Python dependencies
```

## Validation Criteria - Day 1

- [x] Gemini generates valid execution plans
- [x] Playwright captures screenshots
- [x] Claude validates screenshots
- [x] All components log comprehensively
- [x] Errors are handled gracefully
- [x] Can run Python script that captures workflow

## Troubleshooting

### "Configuration error: GEMINI_API_KEY is not set"
- Make sure you copied `.env-template` to `.env`
- Add your API keys to the `.env` file

### "Failed to launch browser"
- Run `playwright install chromium`
- Check that you have sufficient disk space

### "API call failed"
- Verify your API keys are correct
- Check your internet connection
- Review rate limits (Gemini: 60 req/min free tier)

### Browser opens but nothing happens
- Check the logs in `logs/app.log` for detailed error messages
- Try setting `HEADLESS_BROWSER=false` to see what's happening

## Next Steps

- **Day 2**: Database & Storage Layer (SQLite + file storage)
- **Day 3**: Flask API & Job Queue (REST endpoints + background workers)
- **Day 4**: WebSocket Real-Time Updates (Live progress)
- **Day 5**: Frontend UI (Web interface)

## Cost Estimate Per Workflow

- Gemini Flash: $0.00 (Free tier)
- Playwright: $0.00 (Open source)
- Claude Vision (~6 steps): ~$0.018
- **Total**: ~$0.02 per workflow

## License

See [LICENSE](LICENSE) file for details.
