# AI Workflow Capture System - Development Prompt

## Context
You are building an AI-powered workflow capture system based on the provided DESIGN_DOCUMENT.md. This system captures step-by-step UI workflows with screenshots for any web application task.

## Critical Development Rules

### Code Quality Standards
1. **NO EMOJIS**: Never use emojis in logs, console output, or UI. Use text indicators only.
2. **NO HARDCODING**: 
   - Never hardcode values, URLs, or test data
   - Use environment variables for all configuration
   - Use constants defined at the top of files
   - If a function can't be fully implemented yet, leave a clear TODO comment and stub implementation
3. **NO MARKDOWN FILES**: Do not create documentation files unless explicitly requested
4. **COMPREHENSIVE LOGGING**: 
   - Use Python's logging module with appropriate levels (DEBUG, INFO, WARNING, ERROR)
   - Log all API calls with timestamps
   - Log all state transitions
   - Include context in error logs (what was being attempted)
5. **GRACEFUL ERROR HANDLING**:
   - Wrap all external API calls in try-except blocks
   - Provide meaningful error messages
   - Never let exceptions crash the application
   - Always clean up resources (close browsers, connections)
   - Return proper error responses from all endpoints

### Logging Standards
```python
# CORRECT - Text-based indicators
logging.info("[PLANNING] Starting workflow plan generation")
logging.info("[SUCCESS] Screenshot captured for step 3")
logging.error("[ERROR] Failed to find selector: button.submit")

# INCORRECT - No emojis
logging.info("🧠 Planning phase started")  # NEVER DO THIS
```

### Error Handling Pattern
```python
# ALWAYS use this pattern for external calls
try:
    result = external_api_call()
    logging.info(f"[SUCCESS] API call completed: {result.id}")
    return result
except SpecificException as e:
    logging.error(f"[ERROR] API call failed: {str(e)}", exc_info=True)
    # Handle gracefully, don't crash
    return None
except Exception as e:
    logging.error(f"[CRITICAL] Unexpected error: {str(e)}", exc_info=True)
    raise  # Only re-raise if truly unrecoverable
finally:
    # Always cleanup resources
    cleanup_resources()
```

## 5-Day Development Plan

### Day 1: Core Agent Components (No UI)
**Goal**: Build and test the three core agent components independently

**Deliverables**:
- `agent/planner.py` - Gemini planner with grounding
- `agent/executor.py` - Playwright executor  
- `agent/validator.py` - Claude vision validator
- `test_agent.py` - Simple test script to run pipeline
- `.env.example` - Template for environment variables
- `requirements.txt` - All dependencies

**Testing**: Run test script with 1-2 hardcoded test cases to verify each component works

**Validation Criteria**:
- Gemini generates valid execution plans
- Playwright captures screenshots
- Claude validates screenshots
- All components log comprehensively
- Errors are handled gracefully

---

### Day 2: Database & Storage Layer
**Goal**: Persistent storage for workflows and results

**Deliverables**:
- `models/database.py` - SQLite setup with connection pooling
- `models/workflow.py` - Workflow and Step data models
- `utils/storage.py` - File storage utilities for screenshots
- Migration script to initialize database
- Enhanced test script that saves results

**Testing**: Run workflow capture and verify data persists correctly

**Validation Criteria**:
- Database schema created correctly
- Workflows and steps saved properly
- Screenshots organized in correct directories
- All database operations have error handling
- Connection pooling works

---

### Day 3: Flask API & Job Queue
**Goal**: HTTP API with background job processing

**Deliverables**:
- `app.py` - Flask application setup
- `routes/api.py` - All REST API endpoints
- `jobs/queue.py` - Job queue management
- `jobs/worker.py` - Background worker with threading
- `config.py` - Application configuration
- `utils/helpers.py` - Utility functions

**API Endpoints**:
- POST `/api/capture` - Submit job
- GET `/api/status/<job_id>` - Get job status
- GET `/api/guides` - List all guides
- GET `/api/guide/<guide_id>` - Get specific guide
- GET `/static/screenshots/<workflow_id>/<file>` - Serve images

**Testing**: Use curl or Postman to test all endpoints

**Validation Criteria**:
- All endpoints return proper JSON responses
- Jobs run in background without blocking
- Error responses include helpful messages
- All endpoints have comprehensive logging
- Database updates reflect job progress

---

### Day 4: WebSocket Real-Time Updates
**Goal**: Live progress updates using WebSocket

**Deliverables**:
- Flask-SocketIO integration in `app.py`
- Event emitters throughout agent pipeline
- Connection management and error recovery
- Simple HTML test client (`test_websocket.html`)

**WebSocket Events**:
- `connect` - Client connection
- `job_update` - Progress updates
- `phase_change` - Phase transitions
- `step_captured` - New screenshot
- `job_complete` - Completion
- `job_error` - Error occurred

**Testing**: Open test HTML file and verify real-time updates

**Validation Criteria**:
- Events emit at correct times
- Multiple clients can connect
- Disconnections handled gracefully
- All events logged
- No memory leaks from connections

---

### Day 5: Frontend UI
**Goal**: User-facing web interface

**Deliverables**:
- `templates/base.html` - Base template with Tailwind
- `templates/index.html` - Home page with submission form
- `templates/capture.html` - Live progress page
- `templates/guide.html` - Results viewer
- `static/js/capture.js` - WebSocket client
- `static/js/main.js` - General JavaScript
- `static/css/styles.css` - Custom styles
- `routes/pages.py` - Page routes

**Features**:
- Responsive design (mobile-friendly)
- Form validation
- Loading states
- Error displays
- Screenshot gallery
- Export options

**Testing**: Manually test entire user flow in browser

**Validation Criteria**:
- All pages render correctly
- Form submissions work
- Live updates display properly
- Screenshots display in gallery
- Works on mobile browsers
- No console errors

---

## Implementation Guidelines

### Starting Point (Day 1)
**YES - Start without UI**: This is the correct approach
- Build core functionality first
- Test with simple Python scripts
- Verify each component independently
- Add API layer once core is solid
- Add UI last

This approach allows:
- Faster debugging (no web layer complexity)
- Better testing of core logic
- Iterative validation
- Easier refactoring

### Development Workflow Per Day
1. **Plan**: Review day's objectives
2. **Scaffold**: Create file structure with function signatures
3. **Implement**: Write complete implementations (no hardcoding)
4. **Log**: Add comprehensive logging throughout
5. **Test**: Verify with test scripts or API calls
6. **Debug**: Fix issues before moving forward
7. **Commit**: Ready for next day

### Code Organization Principles
- One responsibility per file/function
- Clear function signatures with type hints
- Docstrings for all public functions
- Constants at top of file
- Imports organized (stdlib, third-party, local)

### Configuration Management
All configuration in `config.py` or `.env`:
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
    
    # Application
    ENABLE_VALIDATION = os.getenv('ENABLE_VALIDATION', 'true').lower() == 'true'
    HEADLESS_BROWSER = os.getenv('HEADLESS_BROWSER', 'false').lower() == 'true'
    MAX_CONCURRENT_JOBS = int(os.getenv('MAX_CONCURRENT_JOBS', '3'))
    
    # Paths
    SCREENSHOTS_DIR = 'static/screenshots'
    GUIDES_DIR = 'guides'
    DATABASE_PATH = 'workflows.db'
```

### Testing Strategy
**Day 1-2**: Direct Python script execution
```python
# test_agent.py
from agent.planner import GeminiPlanner
from agent.executor import PlaywrightExecutor
from agent.validator import ClaudeValidator
import asyncio

async def test_workflow():
    planner = GeminiPlanner()
    executor = PlaywrightExecutor()
    validator = ClaudeValidator()
    
    # Test with real task
    plan = await planner.create_plan(
        task="Create a new project",
        app_url="https://linear.app",
        app_name="Linear"
    )
    
    steps = await executor.execute_and_capture(plan, "https://linear.app")
    validated = await validator.validate_steps(steps)
    
    print(f"Captured {len(validated)} steps")

if __name__ == "__main__":
    asyncio.run(test_workflow())
```

**Day 3-4**: API testing with curl/Postman
```bash
# Test job submission
curl -X POST http://localhost:5000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"task": "Create a project", "app_url": "https://linear.app", "app_name": "Linear"}'
```

**Day 5**: Browser-based testing

### Error Handling Requirements

#### API Endpoints
```python
@app.route('/api/capture', methods=['POST'])
def capture_workflow():
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'task' not in data:
            logging.warning("[API] Invalid request: missing task")
            return jsonify({'error': 'Task is required'}), 400
        
        # Process
        job_id = create_job(data)
        logging.info(f"[API] Job created: {job_id}")
        
        return jsonify({'job_id': job_id, 'status': 'queued'}), 201
        
    except ValueError as e:
        logging.error(f"[API] Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"[API] Server error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
```

#### External API Calls
```python
async def call_gemini_api(self, prompt: str):
    """Call Gemini API with retry logic"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logging.info(f"[GEMINI] API call attempt {attempt + 1}")
            response = self.model.generate_content(prompt)
            logging.info("[GEMINI] API call successful")
            return response
            
        except Exception as e:
            logging.warning(f"[GEMINI] Attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logging.error("[GEMINI] All retry attempts exhausted")
                raise
```

#### Browser Automation
```python
async def execute_action(self, page, step):
    """Execute single action with comprehensive error handling"""
    action = step['action']
    
    try:
        logging.info(f"[EXECUTOR] Executing {action}: {step.get('description')}")
        
        if action == 'click':
            selector = step['selector']
            
            # Try primary selector
            try:
                await page.wait_for_selector(selector, timeout=5000)
                await page.click(selector)
                logging.info(f"[EXECUTOR] Click successful: {selector}")
                return
            except Exception as e:
                logging.warning(f"[EXECUTOR] Primary selector failed: {selector}")
                
                # Try alternative selectors
                for alt_selector in step.get('alternative_selectors', []):
                    try:
                        await page.wait_for_selector(alt_selector, timeout=3000)
                        await page.click(alt_selector)
                        logging.info(f"[EXECUTOR] Alternative selector worked: {alt_selector}")
                        return
                    except:
                        continue
                
                # All selectors failed
                raise Exception(f"Could not find element with any selector")
        
        # Handle other actions...
        
    except Exception as e:
        logging.error(f"[EXECUTOR] Action failed: {action} - {str(e)}")
        # Don't crash - capture error state and continue
        raise
```

### Logging Configuration
```python
# Setup in app.py or main script
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    """Configure application-wide logging"""
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    logging.info("[SYSTEM] Logging configured successfully")
```

## Key Technical Decisions

### Why Start Without UI?
1. **Faster Validation**: Test core logic without web complexity
2. **Better Debugging**: Python scripts easier to debug than web requests
3. **Clearer Architecture**: Forces proper separation of concerns
4. **Flexible Testing**: Can test edge cases more easily
5. **Iterative Development**: Add layers progressively

### When to Add Each Layer?
- **Day 1-2**: Pure Python components (agent, database)
- **Day 3**: Add HTTP API layer (Flask routes)
- **Day 4**: Add real-time layer (WebSocket)
- **Day 5**: Add presentation layer (HTML/JS)

### File Organization Strategy
```
workflow-capture/
├── agent/           # Core AI components (no web dependencies)
├── models/          # Data layer (no web dependencies)
├── jobs/            # Background processing (no web dependencies)
├── routes/          # Web layer (depends on above)
├── templates/       # Presentation layer
├── static/          # Static assets
├── utils/           # Shared utilities
└── tests/           # Test scripts
```

This structure ensures lower layers never depend on higher layers.

## Success Criteria

### Day 1 Success
- [ ] Can run Python script that captures workflow
- [ ] Gemini generates valid plans with web search
- [ ] Playwright captures clear screenshots
- [ ] Claude validates screenshots
- [ ] All components log comprehensively
- [ ] Errors handled gracefully

### Day 2 Success
- [ ] Workflows persist to database
- [ ] Screenshots saved to filesystem
- [ ] Can query past workflows
- [ ] Database handles concurrent access
- [ ] All storage operations have error handling

### Day 3 Success
- [ ] API endpoints respond correctly
- [ ] Jobs run in background
- [ ] Can submit via curl/Postman
- [ ] Job status updates correctly
- [ ] All endpoints return proper error responses

### Day 4 Success
- [ ] WebSocket connections work
- [ ] Real-time updates emit correctly
- [ ] Multiple clients can connect
- [ ] Disconnections handled gracefully
- [ ] Test HTML client works

### Day 5 Success
- [ ] Complete UI works end-to-end
- [ ] Can submit workflows via form
- [ ] Live progress displays
- [ ] Results page shows guide
- [ ] Mobile responsive
- [ ] No console errors

## Final Checklist

Before considering the project complete:
- [ ] All functions have comprehensive logging
- [ ] All external calls have error handling
- [ ] No emojis anywhere in codebase
- [ ] No hardcoded values (all in config)
- [ ] All API endpoints tested
- [ ] WebSocket events tested
- [ ] UI tested in multiple browsers
- [ ] 3-5 complete workflows captured successfully
- [ ] README has setup instructions
- [ ] `.env.example` provided
- [ ] Can run without errors on fresh setup

## Development Commands Reference

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Day 1-2: Direct testing
python test_agent.py

# Day 3+: Run Flask app
python app.py

# Test API endpoints
curl http://localhost:5000/api/guides

# View logs
tail -f logs/app.log
```

## Remember
- Build incrementally - each day should produce working code
- Test thoroughly before moving to next day
- Log everything - debugging will be easier
- Handle all errors gracefully
- No emojis, no hardcoding, no skipped implementations
- Start simple (Python scripts), add complexity progressively (API, WebSocket, UI)

Begin with Day 1 and proceed systematically. Good luck!