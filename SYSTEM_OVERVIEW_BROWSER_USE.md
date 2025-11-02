# System Overview - FlowForge (Browser-Use Architecture)

## Architecture

**Gemini Research → Browser-Use Autonomous Execution → State Capture**

---

## Core Components

### 1. Configuration & Setup
- **config.py**: Environment variables (API keys, browser profile path, auth credentials)
- **utils/logger.py**: Logging system with console (INFO) and rotating file handlers (DEBUG)
- **.env**: Required environment variables

### 2. Research & Planning Phase

**[agent/planner.py](agent/planner.py) (GeminiPlanner)**

**Purpose**: Initial task research and authentication detection

**Responsibilities**:
- Web search grounding via Gemini to understand the task
- Determine if authentication is required
- Generate rough workflow outline (5-10 high-level steps)
- Provide context about the application

**Output Format**:
```json
{
  "task_analysis": {
    "requires_authentication": true,
    "auth_type": "oauth_google|email_password|manual",
    "estimated_steps": 8,
    "complexity": "medium"
  },
  "workflow_outline": [
    "Navigate to Supabase dashboard",
    "Authenticate (Google OAuth detected)",
    "Access database section",
    "Create new database",
    "Configure database name and region",
    "Set up initial schema",
    "Save configuration",
    "Verify database creation"
  ],
  "context": {
    "app_name": "Supabase",
    "app_url": "https://app.supabase.com",
    "common_patterns": "Uses modal dialogs for creation flows",
    "known_challenges": "May show onboarding tooltips on first login"
  }
}
```

**Gemini Prompt Structure**:
```
Research this task: {task_description}
Application: {app_url}

Provide:
1. Does this require login? If yes, what type? (oauth_google, oauth_github, email_password, custom)
2. High-level workflow steps (5-10 steps, not specific selectors)
3. Known UI patterns for this application
4. Potential challenges (modals, ads, onboarding)

Return as JSON.
```

---

### 3. Authentication Handler

**[agent/authenticator.py](agent/authenticator.py) (AuthenticationHandler)**

**Purpose**: Three-tier authentication strategy

**Tier 1: Persistent Profile Check**
- Browser launches with `user_data_dir` pointing to Chromium profile
- Checks if already logged in by detecting URL patterns
- Patterns: NOT ('login', 'signin', 'auth', 'signup')
- If logged in: Continue immediately
- If not logged in: Move to Tier 2

**Tier 2: Automatic Login (Email/Password)**
- Reads credentials from environment:
  ```
  DEFAULT_EMAIL=pranavgamedev.17@gmail.com
  DEFAULT_PASSWORD=your_password
  ```
- Creates Browser-Use agent with login task:
  ```python
  login_agent = Agent(
      task=f"Log in using email {email} and password {password}",
      llm=llm,
      browser=browser
  )
  ```
- Agent autonomously finds fields and logs in
- If OAuth detected (Google/GitHub button), clicks it automatically
- If login succeeds: Continue
- If login fails: Move to Tier 3

**Tier 3: Manual User Intervention**
- Display message:
  ```
  [AUTH] Automated login failed. Manual intervention required.
  Please log in to {app_name} in the browser window.
  
  Waiting for login... (timeout: 5 minutes)
  Press ENTER when logged in to continue, or wait for auto-resume.
  ```
- Implementation:
  ```python
  import threading
  
  def wait_with_timeout():
      timeout = 300  # 5 minutes
      user_input = threading.Event()
      
      def get_input():
          input()
          user_input.set()
      
      thread = threading.Thread(target=get_input)
      thread.daemon = True
      thread.start()
      
      # Wait for either user input or timeout
      user_input.wait(timeout)
      
      if not user_input.is_set():
          logging.warning("[AUTH] Timeout reached, checking login status...")
  ```
- After timeout or keypress: Verify login successful
- If still not logged in: Raise AuthenticationError

**Key Methods**:
```python
async def handle_authentication(browser, app_url, app_name, auth_type):
    """Main authentication flow"""
    
    # Tier 1: Check persistent profile
    if await is_logged_in(browser):
        logging.info("[AUTH] Already logged in via persistent profile")
        return True
    
    # Tier 2: Auto login
    if auth_type in ['email_password', 'oauth_google', 'oauth_github']:
        if await auto_login(browser, auth_type):
            logging.info("[AUTH] Automatic login successful")
            return True
    
    # Tier 3: Manual
    logging.warning("[AUTH] Falling back to manual login")
    await manual_login_prompt(browser, app_name)
    
    if not await is_logged_in(browser):
        raise AuthenticationError("Manual login failed or timed out")
    
    return True
```

---

### 4. Browser-Use Agent Executor

**[agent/browser_use_agent.py](agent/browser_use_agent.py) (BrowserUseAgent)**

**Purpose**: Execute workflow using Browser-Use autonomous agent

**Key Features**:
- Uses Browser-Use's perception-cognition-action loop
- LLM decides each action based on current UI state
- No pre-programmed selectors needed
- Handles dynamic UI, popups, ads automatically

**Setup**:
```python
from browser_use import Agent, Browser, ChatBrowserUse

class BrowserUseAgent:
    def __init__(self, config):
        self.config = config
        self.browser = Browser(
            user_data_dir=config.CHROMIUM_PROFILE_PATH,
            headless=False
        )
        self.llm = ChatBrowserUse()  # Or use Gemini/Claude
    
    async def execute_workflow(self, task, workflow_outline):
        """Execute task using Browser-Use agent"""
        
        # Create enhanced task description
        enhanced_task = f"""
        {task}
        
        Follow this general workflow:
        {'\n'.join(f'{i+1}. {step}' for i, step in enumerate(workflow_outline))}
        
        At each step, capture the current state before proceeding.
        """
        
        # Create agent
        agent = Agent(
            task=enhanced_task,
            llm=self.llm,
            browser=self.browser,
            max_steps=50
        )
        
        # Execute with state capture
        history = await agent.run()
        
        return history
```

**Browser-Use Integration**:
- Agent autonomously navigates UI
- Makes decisions based on screenshot + DOM
- Handles errors and retries automatically
- Captures state at each step (built-in)

---

### 5. State Capture System

**[agent/state_capturer.py](agent/state_capturer.py) (StateCapturer)**

**Purpose**: Extract and save UI states from Browser-Use history

**Responsibilities**:
- Extract screenshots from Browser-Use history
- Capture current URL at each step
- Save action descriptions
- Organize outputs into structured dataset

**Implementation**:
```python
class StateCapturer:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    async def capture_states(self, browser_use_history, task_name):
        """Extract and save all UI states from Browser-Use execution"""
        
        states = []
        
        for i, step in enumerate(browser_use_history):
            state = {
                "step_number": i + 1,
                "action": step.get("action", {}),
                "description": step.get("thought", ""),
                "url": step.get("url", ""),
                "timestamp": step.get("timestamp", ""),
                "screenshot_path": f"step_{i+1}.png"
            }
            
            # Save screenshot
            if "screenshot" in step:
                screenshot_path = os.path.join(
                    self.output_dir, 
                    f"step_{i+1}.png"
                )
                step["screenshot"].save(screenshot_path)
                state["screenshot_path"] = screenshot_path
            
            # Get current URL from browser
            current_url = await self.browser.get_current_url()
            state["url"] = current_url
            
            states.append(state)
        
        # Save metadata
        metadata = {
            "task": task_name,
            "total_steps": len(states),
            "states": states,
            "completed_at": datetime.now().isoformat()
        }
        
        metadata_path = os.path.join(self.output_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return states
```

**Screenshot Strategy**:
- Full viewport screenshots saved at each Browser-Use step
- Screenshots automatically captured by Browser-Use framework
- Additional element-specific captures available via:
  ```python
  element_screenshot = await browser.page.locator(selector).screenshot()
  ```

**Output Directory Structure**:
```
outputs/
└── {task_name}_{timestamp}/
    ├── metadata.json          # Task info + step descriptions
    ├── step_1.png            # Full viewport screenshots
    ├── step_2.png
    ├── step_3.png
    └── ...
```

---

## Data Flow

```
1. User Input
   ├─ Task: "Create a database on Supabase"
   ├─ App URL: https://app.supabase.com
   └─ App Name: Supabase

2. Gemini Research (Planner)
   ├─ Web search grounding
   ├─ Determine auth requirement
   ├─ Generate workflow outline
   └─ Output: JSON with auth_type + outline

3. Authentication Handler
   ├─ Tier 1: Check persistent profile
   ├─ Tier 2: Auto-login (if needed)
   └─ Tier 3: Manual fallback (if needed)

4. Browser-Use Agent Execution
   ├─ Receive task + outline
   ├─ Autonomous execution loop:
   │   ├─ Perception: Screenshot + DOM
   │   ├─ Cognition: LLM decides next action
   │   ├─ Action: Execute via Playwright
   │   └─ Repeat until complete
   └─ Return: Full history with states

5. State Capture
   ├─ Extract screenshots from history
   ├─ Save URLs at each step
   ├─ Organize into dataset
   └─ Generate metadata.json

6. Final Output
   └─ Complete workflow guide with screenshots + steps
```

---

## Key Files & Structure

```
flowforge/
├── .env                           # API keys + config
├── config.py                      # Configuration management
├── main.py                        # Entry point
│
├── agent/
│   ├── planner.py                # Gemini research + outline
│   ├── authenticator.py          # 3-tier auth handler
│   ├── browser_use_agent.py      # Browser-Use wrapper
│   └── state_capturer.py         # Screenshot + URL capture
│
├── models/
│   ├── database.py               # SQLite operations
│   └── workflow.py               # Data models
│
├── routes/
│   ├── api.py                    # REST API endpoints
│   └── pages.py                  # HTML page routes
│
├── utils/
│   ├── logger.py                 # Logging setup
│   └── helpers.py                # Utility functions
│
├── outputs/                       # Generated datasets
│   └── {task_name}_{timestamp}/
│       ├── metadata.json
│       ├── step_1.png
│       └── ...
│
└── workflows.db                   # Workflow metadata storage
```

---

## Environment Variables

```bash
# API Keys
GEMINI_API_KEY=AIzaSy...
BROWSER_USE_API_KEY=optional-for-cloud

# Browser Configuration
CHROMIUM_PROFILE_PATH=C:\Users\YourName\AppData\Local\Chromium\User Data\Default
HEADLESS_BROWSER=false

# Authentication
DEFAULT_EMAIL=pranavgamedev.17@gmail.com
DEFAULT_PASSWORD=your_secure_password
AUTH_TIMEOUT=300

# Browser-Use Settings
MAX_STEPS=50
SCREENSHOT_QUALITY=80
```

---

## Execution Flow Example

### Task: "Create a database on Supabase"

**Step 1: Research (Gemini)**
```json
{
  "requires_authentication": true,
  "auth_type": "oauth_google",
  "workflow_outline": [
    "Navigate to Supabase dashboard",
    "Authenticate via Google",
    "Access Projects section",
    "Click Create Database",
    "Configure database settings",
    "Submit creation"
  ]
}
```

**Step 2: Authentication**
```
[AUTH] Launching browser with persistent profile
[AUTH] Checking login status...
[AUTH] Already logged in via saved cookies
[AUTH] Authentication complete
```

**Step 3: Browser-Use Execution**
```
[BROWSER-USE] Starting autonomous execution
[BROWSER-USE] Step 1: Screenshot taken, analyzing...
[BROWSER-USE] Thought: "I see the Supabase dashboard. Need to click 'New Project'"
[BROWSER-USE] Action: click(selector="button:has-text('New Project')")
[BROWSER-USE] Step 2: Screenshot taken, analyzing...
[BROWSER-USE] Thought: "Modal opened. Need to enter database name"
[BROWSER-USE] Action: fill(selector="input[name='name']", value="my_database")
...
[BROWSER-USE] Task complete. Total steps: 8
```

**Step 4: State Capture**
```
[CAPTURE] Extracting 8 states from history
[CAPTURE] Saving screenshots to outputs/supabase_create_database_20250102/
[CAPTURE] Metadata saved
[CAPTURE] Workflow guide complete
```

---

## Integration with Existing System

### What Changes
- **Remove**: Custom Playwright executor, vision recovery loop, validation
- **Replace with**: Browser-Use agent (autonomous)
- **Keep**: Gemini research, authentication handler (adapted), state capture
- **Add**: Browser-Use integration layer

### Migration Path
1. Install Browser-Use: `pip install browser-use`
2. Update planner output format (auth detection + outline)
3. Implement Browser-Use wrapper
4. Adapt authenticator for Browser-Use browser object
5. Update state capturer to work with Browser-Use history
6. Test with existing workflows (Linear, Notion, Supabase)

---

## Advantages of Browser-Use Architecture

1. **Dynamic Adaptation**: No pre-programmed selectors, adapts to any UI
2. **Error Recovery**: LLM naturally handles popups, ads, modals
3. **Simplified Code**: No custom vision loop or validation needed
4. **Community Support**: 71k+ stars, active development
5. **Proven Patterns**: Login, auth, state capture all documented
6. **Cost Effective**: ChatBrowserUse LLM optimized for web tasks

---

## Testing Strategy

**Phase 1: Single App**
- Task: Create Supabase database
- Verify: Auth works, screenshots captured, guide generated

**Phase 2: Multiple Apps**
- Linear: Create project
- Notion: Create database
- Asana: Create task

**Phase 3: Complex Workflows**
- Multi-step tasks with forms
- Tasks requiring multiple authentications
- Tasks with dynamic UI elements

---

## Logging Standards

All logs use component prefixes:

```
[PLANNER] Researching task via Gemini...
[PLANNER] Auth required: oauth_google
[PLANNER] Generated 6-step outline

[AUTH] Checking persistent profile...
[AUTH] Already logged in
[AUTH] Authentication complete

[BROWSER-USE] Starting autonomous execution
[BROWSER-USE] Step 1: Analyzing dashboard...
[BROWSER-USE] Action: Click 'New Project' button
[BROWSER-USE] Step 2: Modal detected...
[BROWSER-USE] Task complete in 8 steps

[CAPTURE] Extracting states from history
[CAPTURE] Saved 8 screenshots
[CAPTURE] Metadata written to outputs/
```

---

## Success Metrics

- Completes workflows without pre-programmed selectors
- Handles authentication automatically (Tier 1) or with minimal intervention (Tier 2-3)
- Captures all UI states with screenshots and URLs
- Generates structured dataset for documentation
- Works across different web applications without code changes
- Adapts to UI changes, popups, and dynamic content
