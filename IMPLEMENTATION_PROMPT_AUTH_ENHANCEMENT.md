# Implementation Task: Enhanced Authentication Flow with Manual Login Button

## Overview
Enhance the existing 3-tier authentication system to integrate with the webapp's socket.io communication, add a user confirmation button for manual login, and create authentication metadata for workflow tracking.

## Current State
- ✅ `AuthenticationHandler` exists in `/home/user/Flow-Planner/agent/authenticator.py` with 3-tier logic
- ✅ `execute_with_authentication()` method exists in `/home/user/Flow-Planner/agent/browser_use_agent.py` (line 506)
- ✅ Gemini planner detects `requires_authentication` and `auth_type` in plan output
- ❌ Webapp uses `execute_workflow()` instead of `execute_with_authentication()` (no auth handling)
- ❌ No socket.io events for authentication status
- ❌ No frontend button for manual login confirmation
- ❌ No login_metadata tracking

## Goal
Implement a seamless authentication flow:

1. **Tier 1**: Check if already logged in (persistent browser profile with cookies)
2. **Tier 2a**: Try OAuth (Google/GitHub "Continue with..." buttons)
3. **Tier 2b**: Try credential-based login (email + password fields)
4. **Tier 3**: If all fail → emit socket.io event with summary → show "CONTINUE" button → wait for user click
5. When user clicks CONTINUE → resume browser-use workflow
6. Track all authentication attempts in `login_metadata` object

---

## Implementation Details

### **Phase 1: Backend - Enhanced AuthenticationHandler**

#### File: `/home/user/Flow-Planner/agent/authenticator.py`

**Current signature (line 27):**
```python
def __init__(self):
    """Initialize authentication handler with configuration"""
```

**Change to:**
```python
def __init__(self, job_id: Optional[str] = None, socketio=None):
    """
    Initialize authentication handler with configuration

    Args:
        job_id: Workflow job ID for socket.io events (webapp only)
        socketio: SocketIO instance for emitting events (webapp only)
    """
    self.job_id = job_id
    self.socketio = socketio
    self.auth_attempts = []  # Track what was tried
```

**Modify `handle_authentication()` method (line 55):**

Current signature:
```python
async def handle_authentication(self, page: Page, app_name: str) -> bool:
```

Keep same signature but enhance to:
1. Track each tier's attempt in `self.auth_attempts`
2. Return authentication metadata along with success status

**Add new method:**
```python
async def handle_authentication_with_metadata(
    self,
    page: Page,
    app_name: str,
    app_url: str
) -> tuple[bool, Dict]:
    """
    Handle authentication and return detailed metadata.

    Returns:
        Tuple of (success: bool, metadata: dict)

    Metadata structure:
    {
        'authentication_required': bool,
        'authentication_method': 'persistent_profile|oauth_google|oauth_github|email_password|manual',
        'attempts': [
            {'tier': 1, 'method': 'persistent_profile', 'result': 'success|failed', 'timestamp': '...'},
            {'tier': 2, 'method': 'oauth_google', 'result': 'not_found|failed', 'timestamp': '...'},
            ...
        ],
        'manual_intervention_required': bool,
        'total_duration_seconds': float
    }
    """
```

**Modify `_manual_login_prompt()` (line 329):**

Current implementation only logs to server. Enhance it to:

```python
async def _manual_login_prompt(self, page: Page, app_name: str) -> bool:
    """
    Prompt user for manual login with socket.io notification and button.
    """
    logger.info(f"[AUTH] Initiating manual login for {app_name}")

    # Build summary of what was tried
    attempts_summary = self._build_attempts_summary()

    # Emit socket.io event if available
    if self.socketio and self.job_id:
        self.socketio.emit('auth_required', {
            'job_id': self.job_id,
            'app_name': app_name,
            'current_url': page.url,
            'attempts': self.auth_attempts,
            'summary': attempts_summary,
            'timeout_seconds': Config.AUTH_TIMEOUT // 1000
        }, room=self.job_id)

        logger.info(f"[AUTH] Socket.io event emitted: auth_required for job {self.job_id}")

    # Create asyncio event for user button click
    user_confirmation = asyncio.Event()

    # Store event in global dict for socket.io handler to access
    if self.job_id:
        from jobs.workflow_runner import auth_confirmation_events
        auth_confirmation_events[self.job_id] = user_confirmation

    # Wait for EITHER:
    # 1. URL changes away from login page (auto-detected)
    # 2. User clicks CONTINUE button (triggers event)
    try:
        # Create two tasks
        url_change_task = asyncio.create_task(
            page.wait_for_url(
                lambda url: not any(
                    indicator in url.lower()
                    for indicator in ['login', 'signin', 'sign-in', 'auth', 'signup', 'sign-up']
                ),
                timeout=Config.AUTH_TIMEOUT
            )
        )

        button_click_task = asyncio.create_task(
            user_confirmation.wait()
        )

        # Wait for first one to complete
        done, pending = await asyncio.wait(
            [url_change_task, button_click_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending task
        for task in pending:
            task.cancel()

        # Check which one completed
        if url_change_task in done:
            logger.info(f"[AUTH] Login detected via URL change: {page.url}")
        else:
            logger.info(f"[AUTH] User clicked CONTINUE button")

        # Verify authentication
        if not await self._is_on_login_page(page):
            logger.info(f"[AUTH] Manual authentication successful")

            # Emit success event
            if self.socketio and self.job_id:
                self.socketio.emit('auth_success', {
                    'job_id': self.job_id,
                    'message': 'Authentication successful! Resuming workflow...'
                }, room=self.job_id)

            return True
        else:
            logger.warning(f"[AUTH] Still on login page after confirmation")
            return False

    except asyncio.TimeoutError:
        logger.error(f"[AUTH] Manual login timeout after {Config.AUTH_TIMEOUT}ms")
        return False
    finally:
        # Cleanup
        if self.job_id:
            from jobs.workflow_runner import auth_confirmation_events
            auth_confirmation_events.pop(self.job_id, None)

def _build_attempts_summary(self) -> str:
    """Build human-readable summary of authentication attempts."""
    if not self.auth_attempts:
        return "No authentication attempts made yet."

    summary_lines = ["We tried the following authentication methods:"]

    for attempt in self.auth_attempts:
        tier = attempt['tier']
        method = attempt['method']
        result = attempt['result']

        if tier == 1:
            summary_lines.append(f"  • Tier 1 (Automatic): Checked persistent browser profile - {result}")
        elif tier == 2:
            if 'oauth' in method:
                provider = method.split('_')[1].title()  # oauth_google -> Google
                summary_lines.append(f"  • Tier 2a (OAuth): Tried '{provider}' sign-in button - {result}")
            elif method == 'email_password':
                summary_lines.append(f"  • Tier 2b (Auto-Login): Tried email/password login - {result}")

    summary_lines.append("\n⚠️ MANUAL LOGIN REQUIRED")
    summary_lines.append(f"Please log in or sign up in the Chromium browser window, then click CONTINUE below.")

    return "\n".join(summary_lines)
```

**Track attempts in each tier:**

In `_is_on_login_page()` (line 132):
```python
async def _is_on_login_page(self, page: Page) -> bool:
    url = page.url.lower()
    is_login = any(indicator in url for indicator in login_indicators)

    # Log the check result
    if not is_login:
        self.auth_attempts.append({
            'tier': 1,
            'method': 'persistent_profile',
            'result': 'success',
            'timestamp': datetime.now().isoformat(),
            'details': f'Already authenticated at {page.url}'
        })

    return is_login
```

In `_try_oauth_login()` (line 164):
```python
# Add at start
import datetime

# Track each OAuth provider attempt
for provider_name, provider_config in self.oauth_providers.items():
    attempt_record = {
        'tier': 2,
        'method': f'oauth_{provider_name}',
        'result': 'not_found',
        'timestamp': datetime.now().isoformat()
    }

    # ... existing code ...

    if element:  # Found button
        attempt_record['result'] = 'clicked'
        attempt_record['details'] = f'Found and clicked {provider_name} OAuth button'
        self.auth_attempts.append(attempt_record)

        # ... wait for redirect ...

        if not await self._is_on_login_page(page):
            attempt_record['result'] = 'success'
            return True
        else:
            attempt_record['result'] = 'failed'

    self.auth_attempts.append(attempt_record)
```

In `_try_auto_login()` (line 239):
```python
# Track credential-based login attempt
attempt_record = {
    'tier': 2,
    'method': 'email_password',
    'result': 'attempting',
    'timestamp': datetime.now().isoformat(),
    'details': f'Using email: {Config.DEFAULT_EMAIL}'
}
self.auth_attempts.append(attempt_record)

try:
    # ... existing browser-use login code ...

    if not await self._is_on_login_page(page):
        attempt_record['result'] = 'success'
        return True
    else:
        attempt_record['result'] = 'failed'
        return False
except Exception as e:
    attempt_record['result'] = 'error'
    attempt_record['error'] = str(e)
    return False
```

---

### **Phase 2: Backend - Workflow Runner Integration**

#### File: `/home/user/Flow-Planner/jobs/workflow_runner.py`

**Add global dict for auth events (top of file, after imports):**
```python
# Global dictionary to store auth confirmation events per job
auth_confirmation_events: Dict[str, asyncio.Event] = {}
```

**Add socket.io event handler (after emit_log and emit_status functions, around line 75):**
```python
@socketio.on('auth_confirmed')
def handle_auth_confirmation(data):
    """Handle user clicking CONTINUE button after manual login."""
    job_id = data.get('job_id')

    if not job_id:
        logger.warning("[SOCKET] auth_confirmed received without job_id")
        return

    logger.info(f"[SOCKET] User confirmed manual login for job {job_id}")

    # Set the event to unblock _manual_login_prompt()
    if job_id in auth_confirmation_events:
        auth_confirmation_events[job_id].set()
        logger.info(f"[AUTH] Resuming workflow for job {job_id}")

        # Emit acknowledgment
        emit_log(job_id, "✅ Login confirmed! Resuming workflow execution...", 'success')
    else:
        logger.warning(f"[AUTH] No pending auth event for job {job_id}")
```

**Modify workflow execution (around line 220):**

Current code:
```python
# Step 2: Execution
active_jobs[job_id]['status'] = 'executing'
emit_status(job_id, 'executing')
emit_log(job_id, "\n" + "="*80, 'info')
emit_log(job_id, f"[2/4] Executing workflow with Browser-Use agent...", 'info', 'executing')
emit_log(job_id, "="*80, 'info')

agent = BrowserUseAgent(log_callback=log_callback)
states = await agent.execute_workflow(
    task=task,
    workflow_outline=plan['workflow_outline'],
    app_url=app_url,
    context=plan['context']
)
```

**Replace with:**
```python
# Step 2: Authentication (if required)
requires_auth = plan['task_analysis'].get('requires_authentication', False)
auth_type = plan['task_analysis'].get('auth_type', 'none')
login_metadata = None

if requires_auth and auth_type != 'none':
    active_jobs[job_id]['status'] = 'authenticating'
    emit_status(job_id, 'authenticating')
    emit_log(job_id, "\n" + "="*80, 'info')
    emit_log(job_id, f"[2/5] Authenticating to {app_name}...", 'info', 'authenticating')
    emit_log(job_id, f"      Authentication type: {auth_type}", 'info')
    emit_log(job_id, "="*80, 'info')

    # Import authenticator
    from agent.authenticator import AuthenticationHandler

    # Create auth handler with socket.io integration
    auth_handler = AuthenticationHandler(
        job_id=job_id,
        socketio=socketio
    )

    # Use authenticated execution method
    agent = BrowserUseAgent(log_callback=log_callback)

    try:
        # This method handles auth then executes workflow
        states, login_metadata = await agent.execute_with_authentication_and_metadata(
            task=task,
            workflow_outline=plan['workflow_outline'],
            app_url=app_url,
            app_name=app_name,
            context=plan['context'],
            auth_handler=auth_handler,
            requires_auth=True,
            auth_type=auth_type
        )

        emit_log(job_id, f"[OK] Authentication successful: {login_metadata['authentication_method']}", 'success')

    except Exception as auth_error:
        emit_log(job_id, f"[ERROR] Authentication failed: {str(auth_error)}", 'error')
        raise

else:
    # No authentication required
    emit_log(job_id, f"[INFO] No authentication required for this task", 'info')

    # Step 2: Execution (original flow)
    active_jobs[job_id]['status'] = 'executing'
    emit_status(job_id, 'executing')
    emit_log(job_id, "\n" + "="*80, 'info')
    emit_log(job_id, f"[2/4] Executing workflow with Browser-Use agent...", 'info', 'executing')
    emit_log(job_id, "="*80, 'info')

    agent = BrowserUseAgent(log_callback=log_callback)
    states = await agent.execute_workflow(
        task=task,
        workflow_outline=plan['workflow_outline'],
        app_url=app_url,
        context=plan['context']
    )
```

**Add login_metadata to final output (around line 318):**

Find where completed event is emitted:
```python
emit_status(job_id, 'completed', {
    'output_dir': summary['output_directory'],
    'guide_path': guide_path or summary['metadata_path'],
    'refined_guide_path': refined_guide_path
})
```

**Add login_metadata:**
```python
emit_status(job_id, 'completed', {
    'output_dir': summary['output_directory'],
    'guide_path': guide_path or summary['metadata_path'],
    'refined_guide_path': refined_guide_path,
    'login_metadata': login_metadata  # NEW
})
```

---

### **Phase 3: Backend - BrowserUseAgent Enhancement**

#### File: `/home/user/Flow-Planner/agent/browser_use_agent.py`

**Add new method (after `execute_with_authentication()` around line 586):**

```python
async def execute_with_authentication_and_metadata(
    self,
    task: str,
    workflow_outline: List[str],
    app_url: str,
    app_name: str,
    context: Dict,
    auth_handler,
    requires_auth: bool,
    auth_type: str
) -> tuple[List[Dict], Dict]:
    """
    Execute workflow with authentication handling and return login metadata.

    Args:
        task: Natural language task description
        workflow_outline: High-level steps from Gemini planner
        app_url: Target application URL
        app_name: Application name
        context: Additional context about the application
        auth_handler: AuthenticationHandler instance (with socketio integration)
        requires_auth: Whether authentication is required
        auth_type: Type of authentication needed

    Returns:
        Tuple of (states: List[Dict], login_metadata: Dict)

    Raises:
        Exception: If authentication or workflow execution fails
    """
    logger.info("[BROWSER-USE] Starting workflow with authentication handling and metadata tracking")

    import time
    start_time = time.time()
    login_metadata = {
        'authentication_required': requires_auth,
        'authentication_method': 'none',
        'attempts': [],
        'manual_intervention_required': False,
        'total_duration_seconds': 0
    }

    try:
        # Create browser instance
        browser = Browser(
            headless=self.headless,
            user_data_dir=self.user_data_dir,
            disable_security=True,
            wait_between_actions=1.0
        )

        # Get current page
        # Note: Browser-Use v0.9.5+ uses get_current_page()
        context_manager = await browser.new_context()
        page = await context_manager.new_page()

        # Navigate to app URL first
        await page.goto(app_url)
        logger.info(f"[BROWSER-USE] Navigated to {app_url}")

        # Handle authentication if required
        if requires_auth:
            logger.info(f"[BROWSER-USE] Authentication required: {auth_type}")

            # Use the existing authentication handler with metadata
            auth_success, auth_meta = await auth_handler.handle_authentication_with_metadata(
                page=page,
                app_name=app_name,
                app_url=app_url
            )

            if not auth_success:
                raise Exception("Authentication failed across all tiers")

            # Store metadata
            login_metadata = auth_meta
            login_metadata['total_duration_seconds'] = time.time() - start_time

            logger.info(f"[BROWSER-USE] Authentication successful via {auth_meta['authentication_method']}")
        else:
            logger.info("[BROWSER-USE] No authentication required")

        # Now execute the main workflow using regular execute_workflow logic
        # We're already authenticated, so just run the agent

        enhanced_task = self._build_enhanced_task(
            task,
            workflow_outline,
            app_url,
            context
        )

        # Storage for screenshots
        step_screenshots = []

        # Screenshot callback (same as execute_workflow)
        async def capture_screenshot_callback(state, model_output, steps):
            if self.log_callback:
                try:
                    action_desc = "Processing step..."
                    if model_output and hasattr(model_output, 'current_state'):
                        if hasattr(model_output.current_state, 'evaluation_previous_goal'):
                            action_desc = str(model_output.current_state.evaluation_previous_goal)
                    self.log_callback(f"  Step {steps}: {action_desc}", 'info')
                except Exception as log_error:
                    logger.debug(f"[BROWSER-USE] Failed to emit step log: {str(log_error)}")

            try:
                if hasattr(state, 'screenshot') and state.screenshot:
                    import base64
                    screenshot_b64 = state.screenshot
                    if isinstance(screenshot_b64, str):
                        if screenshot_b64.startswith('data:image'):
                            screenshot_b64 = screenshot_b64.split(',', 1)[1]
                        screenshot_bytes = base64.b64decode(screenshot_b64)
                        step_screenshots.append(screenshot_bytes)
                        return

                step_screenshots.append(None)
            except Exception as e:
                logger.warning(f"[BROWSER-USE] Screenshot capture failed: {str(e)}")
                step_screenshots.append(None)

        # Create agent with existing browser/page
        agent = Agent(
            task=enhanced_task,
            llm=self.llm,
            browser=browser,
            save_conversation_path=None,
            save_trace_path=None,
            use_vision=True,
            max_actions_per_step=10,
            register_new_step_callback=capture_screenshot_callback
        )

        # Execute workflow
        logger.info("[BROWSER-USE] Executing main workflow...")
        history = await agent.run(max_steps=Config.BROWSER_USE_MAX_STEPS)

        logger.info(f"[BROWSER-USE] Execution complete. Captured {len(step_screenshots)} screenshots")

        # Convert history to states
        states = await self._convert_history_to_states(history, step_screenshots)

        # Close browser
        await browser.close()

        return states, login_metadata

    except Exception as e:
        logger.error(f"[BROWSER-USE] Workflow execution failed: {str(e)}", exc_info=True)
        raise
```

---

### **Phase 4: Frontend - Socket.io Handlers & UI**

#### File: `/home/user/Flow-Planner/static/js/app.js`

**Add new socket handlers (after existing handlers around line 132):**

```javascript
// Add after socket.on('status', ...)

socket.on('auth_required', (data) => {
    handleAuthRequired(data);
});

socket.on('auth_success', (data) => {
    handleAuthSuccess(data);
});
```

**Add handler functions (add to bottom of file or after handleStatusUpdate):**

```javascript
// =============================================================================
// AUTHENTICATION HANDLERS
// =============================================================================

function handleAuthRequired(data) {
    console.log('[AUTH] Manual login required:', data);

    const { app_name, summary, timeout_seconds, job_id } = data;

    // Log the summary
    addLog('\n' + '='.repeat(80), 'warning');
    addLog('⚠️ AUTHENTICATION REQUIRED', 'warning');
    addLog('='.repeat(80), 'warning');

    // Show what was tried
    const attemptLines = summary.split('\n');
    attemptLines.forEach(line => {
        if (line.trim()) {
            addLog(line, 'warning');
        }
    });

    // Show browser instruction
    addLog('\n📱 A Chromium browser window should be open.', 'info');
    addLog('Please log in or sign up, then click the button below.', 'info');

    // Create and show CONTINUE button
    showAuthContinueButton(job_id, timeout_seconds);
}

function showAuthContinueButton(job_id, timeoutSeconds) {
    const actionButtons = document.getElementById('action-buttons');
    if (!actionButtons) {
        console.error('[AUTH] action-buttons container not found');
        return;
    }

    // Clear existing buttons
    actionButtons.innerHTML = '';

    // Create container
    const container = document.createElement('div');
    container.className = 'auth-prompt-container';
    container.style.cssText = `
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 24px;
        margin: 16px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    `;

    // Title
    const title = document.createElement('h3');
    title.textContent = '🔐 Manual Login Required';
    title.style.cssText = 'color: white; margin: 0 0 12px 0; font-size: 20px;';
    container.appendChild(title);

    // Countdown timer
    const timer = document.createElement('div');
    timer.id = 'auth-timer';
    timer.style.cssText = 'color: rgba(255,255,255,0.9); margin: 8px 0; font-size: 14px;';
    timer.textContent = `Time remaining: ${timeoutSeconds}s`;
    container.appendChild(timer);

    // Continue button
    const continueBtn = document.createElement('button');
    continueBtn.id = 'auth-continue-btn';
    continueBtn.textContent = '✅ I\'ve Logged In - CONTINUE';
    continueBtn.style.cssText = `
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        border: none;
        padding: 16px 32px;
        font-size: 16px;
        font-weight: bold;
        border-radius: 8px;
        cursor: pointer;
        margin-top: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s, box-shadow 0.2s;
    `;

    continueBtn.onmouseover = () => {
        continueBtn.style.transform = 'translateY(-2px)';
        continueBtn.style.boxShadow = '0 6px 12px rgba(0, 0, 0, 0.3)';
    };

    continueBtn.onmouseout = () => {
        continueBtn.style.transform = 'translateY(0)';
        continueBtn.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.2)';
    };

    continueBtn.onclick = () => {
        // Emit confirmation
        socket.emit('auth_confirmed', { job_id: job_id });

        // Update button state
        continueBtn.disabled = true;
        continueBtn.textContent = '⏳ Resuming workflow...';
        continueBtn.style.background = '#6c757d';
        continueBtn.style.cursor = 'not-allowed';

        // Stop countdown
        if (window.authCountdownInterval) {
            clearInterval(window.authCountdownInterval);
        }

        addLog('\n✅ Login confirmed by user', 'success');
    };

    container.appendChild(continueBtn);
    actionButtons.appendChild(container);
    actionButtons.style.display = 'block';

    // Start countdown
    let remaining = timeoutSeconds;
    window.authCountdownInterval = setInterval(() => {
        remaining--;
        if (remaining <= 0) {
            clearInterval(window.authCountdownInterval);
            timer.textContent = '⏰ Timeout reached';
            timer.style.color = '#ff6b6b';
        } else {
            timer.textContent = `Time remaining: ${remaining}s`;
        }
    }, 1000);
}

function handleAuthSuccess(data) {
    console.log('[AUTH] Authentication successful:', data);

    addLog('\n✅ ' + data.message, 'success');

    // Hide auth button
    const actionButtons = document.getElementById('action-buttons');
    if (actionButtons) {
        actionButtons.innerHTML = '';
        actionButtons.style.display = 'none';
    }

    // Clear countdown
    if (window.authCountdownInterval) {
        clearInterval(window.authCountdownInterval);
    }
}
```

**Update status handler to recognize 'authenticating' status (around line 293):**

```javascript
function handleStatusUpdate(data) {
    const status = data.status;

    console.log('[STATUS]', status, data);

    // Add new case for authenticating
    if (status === 'authenticating') {
        updateStatusIndicator('running');
        addLog('🔐 Authenticating...', 'info');
        return;
    }

    // ... rest of existing cases
```

---

### **Phase 5: Frontend - HTML & CSS**

#### File: `/home/user/Flow-Planner/templates/index.html`

**Verify action-buttons container exists (should already be there):**

Find or add (usually around line 100-120):
```html
<div id="action-buttons" class="action-buttons" style="display: none;">
    <!-- Auth prompt and continue button will be inserted here dynamically -->
</div>
```

**Add CSS for auth prompt (in `<style>` section):**

```css
.auth-prompt-container {
    animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

#auth-timer {
    font-family: 'Courier New', monospace;
    font-weight: bold;
}
```

---

### **Phase 6: Save login_metadata to Workflow Output**

#### File: `/home/user/Flow-Planner/agent/state_capturer.py`

**Modify `capture_states()` method to accept and save login_metadata:**

Find the method signature (around line 50-60):
```python
async def capture_states(
    self,
    states: List[Dict],
    task_name: str,
    task_description: str
) -> Dict:
```

**Add parameter:**
```python
async def capture_states(
    self,
    states: List[Dict],
    task_name: str,
    task_description: str,
    login_metadata: Optional[Dict] = None  # NEW
) -> Dict:
```

**In metadata creation (find where metadata dict is built):**

```python
metadata = {
    "task_name": task_name,
    "task_description": task_description,
    "total_states": len(states),
    "timestamp": datetime.now().isoformat(),
    "screenshots_dir": screenshots_dir_name,
    "login_metadata": login_metadata or {  # NEW
        "authentication_required": False,
        "authentication_method": "none"
    }
}
```

**Update workflow_runner.py call to capture_states (around line 249):**

```python
summary = await capturer.capture_states(
    states=states,
    task_name=task_name,
    task_description=task,
    login_metadata=login_metadata  # NEW
)
```

---

## Testing Checklist

After implementation, test these scenarios:

### ✅ Test 1: Persistent Profile (Tier 1 Success)
- **Setup**: Log into Gmail manually once in Chromium with persistent profile
- **Task**: "Go to Gmail and check inbox"
- **Expected**: Tier 1 succeeds, no manual intervention needed
- **Verify**: `login_metadata.authentication_method = 'persistent_profile'`

### ✅ Test 2: OAuth Google (Tier 2a Success)
- **Setup**: Use app with "Continue with Google" button (e.g., Notion)
- **Task**: "Go to Notion and create a page"
- **Expected**: Tier 2a finds OAuth button, clicks it, auto-logs in
- **Verify**: `login_metadata.authentication_method = 'oauth_google'`

### ✅ Test 3: Email/Password (Tier 2b Success)
- **Setup**: Configure `DEFAULT_EMAIL` and `DEFAULT_PASSWORD` in .env
- **Task**: "Log into GitHub" (using credentials, not OAuth)
- **Expected**: Tier 2b fills form and logs in
- **Verify**: `login_metadata.authentication_method = 'email_password'`

### ✅ Test 4: Manual Intervention (Tier 3)
- **Setup**: Fresh browser profile, no saved login, app without OAuth
- **Task**: "Go to Discord and send a message"
- **Expected**:
  1. Webapp shows "Manual login required" message
  2. Button appears: "I've Logged In - CONTINUE"
  3. User logs in manually
  4. User clicks button
  5. Workflow resumes
- **Verify**:
  - `login_metadata.authentication_method = 'manual'`
  - `login_metadata.manual_intervention_required = true`
  - `login_metadata.attempts` shows all 3 tiers tried

### ✅ Test 5: No Auth Required
- **Setup**: Public website
- **Task**: "Go to Wikipedia and search for Python programming"
- **Expected**: No authentication flow triggered
- **Verify**: `login_metadata.authentication_required = false`

---

## File Summary

Files to modify:
1. ✅ `/home/user/Flow-Planner/agent/authenticator.py` (~150 lines changed)
2. ✅ `/home/user/Flow-Planner/agent/browser_use_agent.py` (~120 lines added)
3. ✅ `/home/user/Flow-Planner/jobs/workflow_runner.py` (~80 lines changed)
4. ✅ `/home/user/Flow-Planner/agent/state_capturer.py` (~10 lines changed)
5. ✅ `/home/user/Flow-Planner/static/js/app.js` (~150 lines added)
6. ✅ `/home/user/Flow-Planner/templates/index.html` (~20 lines CSS)

Total estimated changes: ~530 lines of code

---

## Configuration Required

Update `.env` file:
```bash
# Authentication Settings
USE_PERSISTENT_CONTEXT=true
BROWSER_USER_DATA_DIR=C:\Users\YourName\AppData\Local\Google\Chrome\User Data
BROWSER_CHANNEL=chrome

# OAuth Detection
GOOGLE_ACCOUNT_EMAIL=your.email@gmail.com

# Tier 2b Auto-Login Credentials
DEFAULT_EMAIL=your.email@example.com
DEFAULT_PASSWORD=your_password

# Manual Login Timeout (5 minutes for user confirmation)
AUTH_TIMEOUT=300000

# OAuth Redirect Timeout
OAUTH_REDIRECT_TIMEOUT=15000
```

---

## Success Criteria

Implementation is complete when:

1. ✅ Webapp uses `execute_with_authentication()` instead of `execute_workflow()`
2. ✅ All 3 tiers attempt authentication in order
3. ✅ Socket.io event 'auth_required' emitted when Tier 3 triggered
4. ✅ Frontend shows "CONTINUE" button with countdown timer
5. ✅ User can click button to resume workflow after manual login
6. ✅ `login_metadata` object saved in workflow output with:
   - `authentication_required`: bool
   - `authentication_method`: string (persistent_profile|oauth_google|oauth_github|email_password|manual)
   - `attempts`: array of attempt records
   - `manual_intervention_required`: bool
   - `total_duration_seconds`: float
7. ✅ All test scenarios pass

---

## Additional Notes

- **Error Handling**: If user doesn't click CONTINUE within timeout, workflow should fail gracefully with clear error message
- **Browser Window**: Ensure `HEADLESS_BROWSER=false` in .env so user can see login screen
- **Session Persistence**: Browser profile must be shared between authentication and main workflow execution
- **Logging**: All authentication attempts should be logged to both server logs and socket.io for debugging
- **Security**: Never log passwords or credentials in plain text

---

## Questions for Clarification

Before starting implementation:

1. Should the CONTINUE button have a "Skip Authentication" option for debugging?
2. Should login_metadata be included in the final Gemini-generated guide?
3. What should happen if user closes browser window during manual login?
4. Should we track authentication time separately from workflow execution time?

---

## Implementation Order

Recommended order:

1. **Backend Auth Handler** (authenticator.py) - Core logic
2. **Backend Workflow Runner** (workflow_runner.py) - Integration
3. **Backend Browser-Use Agent** (browser_use_agent.py) - New method
4. **Backend State Capturer** (state_capturer.py) - Metadata saving
5. **Frontend Socket Handlers** (app.js) - Event handling
6. **Frontend UI** (app.js + index.html) - Button and styling
7. **Testing** - All 5 test scenarios

Total estimated time: **4-6 hours**

---

Good luck with the implementation! 🚀
