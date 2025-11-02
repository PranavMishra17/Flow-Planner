# FlowForge Project Configuration
# This file provides context and rules for AI agents working on this project

## Project Overview
Project Name: FlowForge
Description: AI-powered workflow documentation system that automatically captures and visualizes step-by-step UI flows
Repository: flowforge
Tech Stack: Python, Flask, Playwright, Google Gemini, Anthropic Claude

## Project Purpose
An intelligent system that:
1. Accepts natural language task descriptions
2. Researches workflows using web search
3. Plans execution steps with AI
4. Autonomously navigates web applications
5. Captures screenshots at key UI states
6. Validates results with computer vision
7. Generates comprehensive step-by-step guides

## Core Architecture
- Frontend: HTML + Vanilla JS + Tailwind CSS
- Backend: Flask + Flask-SocketIO
- Agent Components: Gemini (planning) → Playwright (execution) → Claude (validation)
- Storage: SQLite database + filesystem for screenshots
- Real-time: WebSocket for live progress updates

## CRITICAL CODING RULES

### Rule 1: NO EMOJIS
NEVER use emojis in:
- Log messages
- Console output
- UI text
- Comments
- Error messages
- Any output whatsoever

CORRECT:
```python
logging.info("[PLANNING] Starting workflow plan generation")
logging.info("[SUCCESS] Screenshot captured for step 3")
logging.error("[ERROR] Failed to find selector: button.submit")
print("[INFO] Job queued successfully")
```

INCORRECT:
```python
logging.info("[EMOJI] Planning phase started")  # NEVER DO THIS - emojis forbidden
print("[EMOJI] Job complete")  # NEVER DO THIS - emojis forbidden
```

Use text-based indicators instead:
- [INFO], [DEBUG], [WARNING], [ERROR], [CRITICAL]
- [SUCCESS], [FAILED], [PENDING], [QUEUED]
- [PLANNING], [EXECUTING], [VALIDATING]
- [GEMINI], [PLAYWRIGHT], [CLAUDE], [API], [EXECUTOR]

### Rule 2: NO HARDCODING
NEVER hardcode:
- API keys (use environment variables)
- URLs (use configuration)
- File paths (use config or constants)
- Test data (use parameters)
- Timeouts (use config constants)
- Selectors (pass as parameters)

CORRECT:
```python
# config.py
class Config:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    SCREENSHOTS_DIR = os.getenv('SCREENSHOTS_DIR', 'static/screenshots')
    DEFAULT_TIMEOUT = int(os.getenv('DEFAULT_TIMEOUT', '10000'))

# usage
timeout = Config.DEFAULT_TIMEOUT
```

INCORRECT:
```python
api_key = "AIzaSy..."  # NEVER
screenshots_dir = "static/screenshots"  # Should be in config
timeout = 10000  # Should be configurable
```

If a value might need to change:
- Put it in config.py
- Make it an environment variable
- Define as a constant at the top of the file

### Rule 3: COMPREHENSIVE LOGGING
Log EVERYTHING important:
- All function entry/exit points
- All API calls (before and after)
- All state transitions
- All errors with full context
- All external interactions
- All user actions

Required logging pattern:
```python
def some_function(param):
    logging.info(f"[FUNCTION] Entering some_function with param={param}")
    
    try:
        logging.debug("[FUNCTION] Processing step 1")
        result = do_something()
        logging.info(f"[FUNCTION] Step 1 completed: {result}")
        
        return result
    except Exception as e:
        logging.error(f"[FUNCTION] Error in some_function: {str(e)}", exc_info=True)
        raise
    finally:
        logging.debug("[FUNCTION] Exiting some_function")
```

For external API calls:
```python
try:
    logging.info(f"[GEMINI] Calling API with prompt length: {len(prompt)}")
    response = model.generate_content(prompt)
    logging.info(f"[GEMINI] API call successful, response length: {len(response.text)}")
    return response
except Exception as e:
    logging.error(f"[GEMINI] API call failed: {str(e)}", exc_info=True)
    raise
```

### Rule 4: GRACEFUL ERROR HANDLING
ALL external calls MUST have try-except blocks:
- API calls (Gemini, Claude)
- Database operations
- File I/O
- Network requests
- Browser automation

Error handling pattern:
```python
try:
    # Risky operation
    result = external_call()
    
except SpecificException as e:
    # Handle specific error
    logging.error(f"[MODULE] Specific error: {str(e)}", exc_info=True)
    # Graceful degradation or retry
    return fallback_value
    
except Exception as e:
    # Handle unexpected errors
    logging.error(f"[MODULE] Unexpected error: {str(e)}", exc_info=True)
    # Don't crash the entire app
    return None
    
finally:
    # ALWAYS cleanup resources
    cleanup_resources()
```

For Flask endpoints:
```python
@app.route('/api/endpoint', methods=['POST'])
def endpoint():
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'required_field' not in data:
            logging.warning("[API] Invalid request: missing required_field")
            return jsonify({'error': 'Required field missing'}), 400
        
        # Process
        result = process_data(data)
        logging.info(f"[API] Request processed successfully: {result.id}")
        
        return jsonify({'success': True, 'data': result}), 200
        
    except ValueError as e:
        logging.error(f"[API] Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        logging.error(f"[API] Server error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
```

### Rule 5: NO PARTIAL IMPLEMENTATIONS
NEVER leave placeholder code like:
```python
def some_function():
    # TODO: implement this
    pass
```

Instead, either:
1. Fully implement the function
2. Or leave a clear TODO with explanation:
```python
def some_function():
    """
    TODO: This function will handle retry logic
    
    Implementation pending:
    - Exponential backoff strategy
    - Max retry attempts configuration
    - Error type classification
    
    For now, just raises the original exception.
    """
    raise NotImplementedError("Retry logic not yet implemented")
```

### Rule 6: NO DOCUMENTATION FILES
Do NOT create:
- README.md (unless explicitly requested)
- CHANGELOG.md
- CONTRIBUTING.md
- docs/*.md files

Exception: Technical documentation that is REQUIRED for the system to function:
- .env.example (needed for setup)
- requirements.txt (needed for dependencies)
- This .claude file (project context)

### Rule 7: PROPER LOGGING SETUP
Always configure logging at application start:
```python
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    """Configure application-wide logging"""
    os.makedirs('logs', exist_ok=True)
    
    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console.setFormatter(console_fmt)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_fmt)
    
    # Configure root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(console)
    root.addHandler(file_handler)
    
    logging.info("[SYSTEM] Logging configured successfully")
```

## File Structure
```
flowforge/
├── .env                      # Environment variables (NOT in git)
├── .gitignore               # Git ignore rules
├── .claude                  # This file (project context)
├── requirements.txt         # Python dependencies
├── config.py               # Application configuration
├── app.py                  # Flask application entry
│
├── agent/                  # Core AI agent components
│   ├── __init__.py
│   ├── planner.py         # Gemini planner with grounding
│   ├── executor.py        # Playwright browser automation
│   └── validator.py       # Claude vision validation
│
├── models/                 # Data layer
│   ├── __init__.py
│   ├── database.py        # SQLite operations
│   └── workflow.py        # Data models
│
├── routes/                 # Web layer
│   ├── __init__.py
│   ├── api.py            # REST API endpoints
│   └── pages.py          # HTML page routes
│
├── jobs/                   # Background processing
│   ├── __init__.py
│   ├── queue.py          # Job queue management
│   └── worker.py         # Background worker
│
├── utils/                  # Shared utilities
│   ├── __init__.py
│   ├── storage.py        # File storage utilities
│   └── helpers.py        # Helper functions
│
├── templates/              # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── capture.html
│   └── guide.html
│
├── static/                 # Static assets
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── capture.js    # WebSocket client
│   │   └── main.js
│   └── screenshots/       # Generated screenshots
│
├── guides/                 # Generated JSON guides
├── logs/                   # Application logs
└── workflows.db           # SQLite database
```

## Environment Variables Required
```
# API Keys
GEMINI_API_KEY=           # Google Gemini API key
ANTHROPIC_API_KEY=        # Anthropic Claude API key

# Flask Configuration
FLASK_SECRET_KEY=         # Random secret key for sessions
FLASK_ENV=development     # development or production

# Application Settings
ENABLE_VALIDATION=true    # Enable Claude vision validation
HEADLESS_BROWSER=false    # Run browser in headless mode
MAX_CONCURRENT_JOBS=3     # Maximum concurrent capture jobs
DEFAULT_TIMEOUT=10000     # Default timeout in milliseconds
```

## Development Phases

### Phase 1: Core Agent Components (No UI)
Files to create:
- agent/planner.py
- agent/executor.py
- agent/validator.py
- config.py
- test_agent.py (for testing)

### Phase 2: Database & Storage
Files to create:
- models/database.py
- models/workflow.py
- utils/storage.py

### Phase 3: Flask API & Job Queue
Files to create:
- app.py
- routes/api.py
- jobs/queue.py
- jobs/worker.py
- utils/helpers.py

### Phase 4: WebSocket Real-Time
Files to modify:
- app.py (add Flask-SocketIO)
- jobs/worker.py (add event emitters)
Files to create:
- test_websocket.html (for testing)

### Phase 5: Frontend UI
Files to create:
- templates/*.html
- static/js/*.js
- static/css/*.css
- routes/pages.py

## Testing Strategy
- Phase 1-2: Direct Python script execution (`python test_agent.py`)
- Phase 3: API testing with curl/Postman
- Phase 4: WebSocket testing with test HTML client
- Phase 5: Full browser-based testing

## Common Patterns

### Configuration Loading
```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    
    # Paths
    SCREENSHOTS_DIR = 'static/screenshots'
    GUIDES_DIR = 'guides'
    DATABASE_PATH = 'workflows.db'
    
    # Timeouts
    DEFAULT_TIMEOUT = int(os.getenv('DEFAULT_TIMEOUT', '10000'))
    NETWORK_IDLE_TIMEOUT = int(os.getenv('NETWORK_IDLE_TIMEOUT', '5000'))
    
    # Limits
    MAX_CONCURRENT_JOBS = int(os.getenv('MAX_CONCURRENT_JOBS', '3'))
    MAX_STEPS = int(os.getenv('MAX_STEPS', '15'))
```

### Database Operations
```python
try:
    logging.debug(f"[DATABASE] Inserting workflow: {workflow_id}")
    cursor.execute(sql, params)
    conn.commit()
    logging.info(f"[DATABASE] Workflow inserted successfully: {workflow_id}")
except sqlite3.Error as e:
    logging.error(f"[DATABASE] Insert failed: {str(e)}", exc_info=True)
    conn.rollback()
    raise
```

### API Responses
```python
# Success
return jsonify({
    'success': True,
    'data': result,
    'message': 'Operation completed successfully'
}), 200

# Client error
return jsonify({
    'success': False,
    'error': 'Validation failed',
    'details': 'Task field is required'
}), 400

# Server error
return jsonify({
    'success': False,
    'error': 'Internal server error',
    'message': 'An unexpected error occurred'
}), 500
```

## Code Style Guidelines
- Use type hints where possible
- Use descriptive variable names
- Keep functions focused (single responsibility)
- Add docstrings to public functions
- Use constants for magic numbers
- Organize imports (stdlib, third-party, local)

## Testing Checklist
Before considering any phase complete:
- [ ] All functions have comprehensive logging
- [ ] All external calls have error handling
- [ ] No emojis anywhere in codebase
- [ ] No hardcoded values (all in config)
- [ ] No placeholder/incomplete implementations
- [ ] Code has been tested and works
- [ ] Logs are clear and traceable

## Common Mistakes to Avoid
1. Using emojis in any output
2. Hardcoding API keys or configuration
3. Missing error handling on external calls
4. Insufficient logging
5. Creating unnecessary documentation files
6. Leaving TODO stubs without implementation
7. Not cleaning up resources in finally blocks
8. Missing input validation on API endpoints

## When Working on This Project
1. Read this file first to understand context
2. Follow all CRITICAL CODING RULES
3. Log everything important
4. Handle all errors gracefully
5. Never use emojis
6. Never hardcode values
7. Test your changes
8. Ensure logs are comprehensive

## Success Criteria
- Code runs without crashes
- All errors are caught and logged
- Logs provide clear trace of execution
- No emojis anywhere
- All configuration is in config.py or .env
- All functions are fully implemented (no stubs)

## Questions to Ask Before Writing Code
1. Am I using emojis? (Answer must be NO)
2. Am I hardcoding any values? (Answer must be NO)
3. Is this external call wrapped in try-except? (Answer must be YES)
4. Am I logging this operation? (Answer must be YES)
5. Will this error crash the app? (Answer must be NO)
6. Is this function fully implemented? (Answer must be YES)

Remember: This is a production-quality system. Write code as if it will be deployed to users immediately.
