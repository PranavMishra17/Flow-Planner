# Claude Code Agent Implementation Prompt

## Task: Implement Enhanced 3-Tier Authentication with Manual Login Button

You are implementing an enhanced authentication system for a Flow-Planner webapp that uses Browser-Use agent for web automation.

---

## Context

**Current State:**
- ✅ 3-tier `AuthenticationHandler` exists in `agent/authenticator.py` but only logs to server
- ✅ Gemini planner detects `requires_authentication` in plan output
- ❌ Webapp doesn't use authentication (uses wrong method)
- ❌ No UI notification when manual login needed
- ❌ No login metadata tracking

**Goal:** When manual login is required, show a "CONTINUE" button in the webapp UI, track all authentication attempts, and save login metadata to workflow output.

---

## Implementation Requirements

### **Tier 1**: Check if already logged in (persistent browser profile)
- If URL doesn't contain "login/signin/auth" → return success
- Track attempt in metadata

### **Tier 2a**: Try OAuth (Google/GitHub)
- Search for "Continue with Google" or "Continue with GitHub" buttons
- Click and wait for redirect
- Track attempt in metadata

### **Tier 2b**: Try email/password auto-login
- Use Browser-Use agent to fill email/password fields
- Use `DEFAULT_EMAIL` and `DEFAULT_PASSWORD` from config
- Track attempt in metadata

### **Tier 3**: Manual login with button
- Emit socket.io event: `'auth_required'` with summary of what was tried
- Frontend shows: "⚠️ We tried OAuth and credentials - Manual login required"
- Show **CONTINUE** button with countdown timer
- Wait for EITHER:
  - User clicks CONTINUE button (emit `'auth_confirmed'`)
  - URL changes away from login page (auto-detect)
- Resume workflow when button clicked

### **Login Metadata Structure:**
```json
{
  "authentication_required": true,
  "authentication_method": "manual",
  "attempts": [
    {"tier": 1, "method": "persistent_profile", "result": "failed", "timestamp": "..."},
    {"tier": 2, "method": "oauth_google", "result": "not_found", "timestamp": "..."},
    {"tier": 2, "method": "email_password", "result": "failed", "timestamp": "..."},
    {"tier": 3, "method": "manual", "result": "success", "timestamp": "..."}
  ],
  "manual_intervention_required": true,
  "total_duration_seconds": 45.2
}
```

This metadata should be saved in the workflow output (metadata.json) alongside other workflow data.

---

## Files to Modify

### 1. **`agent/authenticator.py`**
- Add `job_id` and `socketio` params to `__init__`
- Track all attempts in `self.auth_attempts` list
- In `_manual_login_prompt()`:
  - Emit `socketio.emit('auth_required', {job_id, app_name, summary, attempts})`
  - Wait for EITHER URL change OR user button click using `asyncio.wait()` with `FIRST_COMPLETED`
  - Use global dict `auth_confirmation_events[job_id] = asyncio.Event()`
- Add method: `handle_authentication_with_metadata()` returning `(success, metadata_dict)`
- Add method: `_build_attempts_summary()` for human-readable summary

### 2. **`jobs/workflow_runner.py`**
- Add global: `auth_confirmation_events: Dict[str, asyncio.Event] = {}`
- Add socket handler:
  ```python
  @socketio.on('auth_confirmed')
  def handle_auth_confirmation(data):
      job_id = data.get('job_id')
      if job_id in auth_confirmation_events:
          auth_confirmation_events[job_id].set()
  ```
- Check `plan['task_analysis']['requires_authentication']`
- If true:
  - Emit status: `'authenticating'`
  - Call `agent.execute_with_authentication_and_metadata()`
  - Store returned `login_metadata`
- Pass `login_metadata` to `capturer.capture_states()`
- Include in final completed event

### 3. **`agent/browser_use_agent.py`**
- Add new method: `execute_with_authentication_and_metadata()`
- Call `auth_handler.handle_authentication_with_metadata()`
- Return tuple: `(states, login_metadata)`
- Ensure browser session persists from auth to main workflow

### 4. **`agent/state_capturer.py`**
- Add `login_metadata` parameter to `capture_states()`
- Include in metadata.json:
  ```python
  metadata = {
      ...,
      "login_metadata": login_metadata or {"authentication_required": False}
  }
  ```

### 5. **`static/js/app.js`**
- Add socket handlers:
  ```javascript
  socket.on('auth_required', (data) => { showAuthButton(data); });
  socket.on('auth_success', (data) => { hideAuthButton(); });
  ```
- Create function `showAuthButton(data)`:
  - Display summary of what was tried
  - Show styled "✅ I've Logged In - CONTINUE" button
  - Start countdown timer
  - On click: `socket.emit('auth_confirmed', {job_id})`
- Update `handleStatusUpdate()` to recognize `'authenticating'` status

### 6. **`templates/index.html`**
- Add CSS for auth prompt (gradient background, animated button)
- Ensure `#action-buttons` container exists

---

## Key Implementation Details

### **Backend: Dual-Wait Logic**
```python
# In authenticator.py _manual_login_prompt()

user_confirmation = asyncio.Event()
auth_confirmation_events[job_id] = user_confirmation

url_change_task = asyncio.create_task(page.wait_for_url(...))
button_click_task = asyncio.create_task(user_confirmation.wait())

done, pending = await asyncio.wait(
    [url_change_task, button_click_task],
    return_when=asyncio.FIRST_COMPLETED
)

for task in pending:
    task.cancel()
```

### **Frontend: Button Styling**
```javascript
const continueBtn = document.createElement('button');
continueBtn.textContent = '✅ I\'ve Logged In - CONTINUE';
continueBtn.style.cssText = `
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: white;
    padding: 16px 32px;
    font-size: 16px;
    font-weight: bold;
    border-radius: 8px;
    cursor: pointer;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
`;
continueBtn.onclick = () => {
    socket.emit('auth_confirmed', { job_id });
    continueBtn.disabled = true;
    continueBtn.textContent = '⏳ Resuming workflow...';
};
```

---

## Test Scenarios

After implementation, verify these work:

1. **Tier 1 Success**: Already logged in → no manual intervention
2. **Tier 2a Success**: "Continue with Google" button found and clicked
3. **Tier 2b Success**: Email/password auto-filled and submitted
4. **Tier 3 Success**: Manual login required → button appears → user logs in → clicks CONTINUE → workflow resumes
5. **No Auth**: Public site → no authentication flow triggered

Each should save appropriate `login_metadata` in workflow output.

---

## Environment Variables Needed

```bash
USE_PERSISTENT_CONTEXT=true
BROWSER_USER_DATA_DIR=/path/to/chrome/profile
GOOGLE_ACCOUNT_EMAIL=your@gmail.com
DEFAULT_EMAIL=your@email.com
DEFAULT_PASSWORD=your_password
AUTH_TIMEOUT=300000  # 5 minutes
HEADLESS_BROWSER=false  # So user can see login screen
```

---

## Socket.io Events

### **Emit from Backend:**
- `'auth_required'`: {job_id, app_name, summary, attempts, timeout_seconds}
- `'auth_success'`: {job_id, message}

### **Receive in Backend:**
- `'auth_confirmed'`: {job_id} → triggers event to resume workflow

---

## Success Criteria

✅ Webapp detects when auth is required (via Gemini planner)
✅ All 3 tiers execute in order
✅ Frontend shows button when manual login needed
✅ Button click resumes workflow
✅ login_metadata saved to metadata.json
✅ User sees clear status: "Authenticating..." → "Waiting for login..." → "Executing..."

---

## Detailed Implementation Guide

For full implementation details including exact code locations and line numbers, see: `IMPLEMENTATION_PROMPT_AUTH_ENHANCEMENT.md`

---

## Start Here

1. Read full implementation guide
2. Start with `agent/authenticator.py` (core logic)
3. Then `jobs/workflow_runner.py` (integration)
4. Then `agent/browser_use_agent.py` (new method)
5. Then frontend (`app.js` + `index.html`)
6. Then `agent/state_capturer.py` (metadata)
7. Test all 5 scenarios

**Estimated time:** 4-6 hours

---

## Questions Before Starting?

- Should button have "Skip Auth" option for debugging?
- Include login_metadata in Gemini-generated guide?
- What if user closes browser during login?
- Track auth time separately from workflow time?

---

**Full detailed spec:** `/home/user/Flow-Planner/IMPLEMENTATION_PROMPT_AUTH_ENHANCEMENT.md`
