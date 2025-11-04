# Flow Planner Flask Web App - Setup Complete! 🎮

## What Was Created

### ✅ Core Flask Application
- **[app.py](app.py)**: Flask server with SocketIO for real-time updates
  - Main application routes
  - History API endpoint
  - Markdown viewer API
  - Static file serving
  - SocketIO event handlers

### ✅ API Routes
- **[routes/workflows.py](routes/workflows.py)**: Workflow management endpoints
  - `POST /api/workflow` - Start new workflow
  - `GET /api/workflow/<job_id>` - Get job status
  - `GET /api/jobs` - List active jobs

### ✅ Background Job Runner
- **[jobs/workflow_runner.py](jobs/workflow_runner.py)**: Async workflow execution
  - Wraps existing `run_workflow()` function
  - Emits real-time SocketIO updates
  - Color-coded log streaming
  - Status management
  - **NO CHANGES to existing workflow code!**

### ✅ Frontend (Retro Styled!)
- **[templates/index.html](templates/index.html)**: Main UI with:
  - Header with title and portfolio link
  - Left panel: History + Algorithm overview + Input form
  - Right panel: Real-time logs
  - Markdown viewer modal
  - Status bar with links

- **[static/css/style.css](static/css/style.css)**: Retro game aesthetic
  - Press Start 2P pixelated font
  - CRT screen effect
  - Neon green terminal colors
  - Color-coded step types
  - Responsive layout

- **[static/js/app.js](static/js/app.js)**: Frontend logic
  - SocketIO connection
  - Real-time log streaming
  - History panel with collapse/expand
  - Markdown viewer with image support
  - Input form management

### ✅ Documentation
- **[FLASK_APP.md](FLASK_APP.md)**: Complete usage guide
- **[FLASK_SETUP_SUMMARY.md](FLASK_SETUP_SUMMARY.md)**: This file

## Quick Start Guide

### 1. Add Your Portfolio Image

```bash
# Place your image (if you have one)
cp /path/to/your/photo.png static/images/me.png
```

If you don't have one, the link will still work but show a broken image icon.

### 2. Install Dependencies (if needed)

All required dependencies are already in `requirements.txt`:
- flask
- flask-socketio
- flask-cors
- python-socketio
- python-engineio

### 3. Start the Flask Server

```bash
python app.py
```

You should see:
```
================================================================================
                          FLOW PLANNER WEB APP
                         Retro Workflow Capture
================================================================================

Server starting at: http://localhost:5000
Press Ctrl+C to stop

================================================================================
```

### 4. Open Browser

Navigate to: **http://localhost:5000**

## Features Overview

### 🎮 Retro Design
- Pixelated "Press Start 2P" font
- CRT monitor scanline effect
- Neon green terminal colors (#00ff41)
- Retro button animations

### 📊 Real-Time Logs (THE CRUX!)
Logs are color-coded by step type:

| Step | Color | Hex Code |
|------|-------|----------|
| **Planning** | 🟠 Orange | `#ffaa00` |
| **Executing** | 🔵 Blue | `#00aaff` |
| **Saving** | 🟣 Purple | `#9d4edd` |
| **Generating** | 🟢 Cyan | `#06ffa5` |
| **Refining** | 🔴 Pink | `#ff006e` |

Regular logs (info/success/error) remain black/gray/red/yellow.

### 📜 History Viewer
- Collapsible sidebar (click "HISTORY" to toggle)
- Shows all workflow runs from `output/` directory
- Displays run name (task description)
- Lists markdown files (original + refined if available)
- Click markdown button to view in-browser
- Images displayed inline

### 📝 Markdown Viewer
- Modal popup overlay
- GitHub-flavored markdown rendering (via marked.js)
- Screenshots displayed inline
- Proper path resolution for images
- Close with X button or Escape key

### 🏗️ Algorithm Overview
Always-visible 5-step process:
1. PLAN with Gemini
2. EXECUTE with Browser-Use
3. CAPTURE states & screenshots
4. GENERATE workflow guide
5. REFINE with Vision AI

### 📍 Status Bar
- Live status indicator (READY/RUNNING/ERROR)
- Current job ID
- Links to:
  - Browser-Use GitHub
  - Gemini API docs
  - Claude API docs
- Portfolio link button (top right)

## How It Works

### Workflow Execution Flow

```
User enters task → Click "RUN WORKFLOW"
        ↓
    Inputs disabled (non-interactive)
        ↓
    POST to /api/workflow
        ↓
    Background thread starts
        ↓
    Calls existing run_workflow() function
        ↓
    Emits SocketIO events for each step
        ↓
    Frontend receives logs in real-time
        ↓
    Color-codes logs by step type
        ↓
    Workflow completes
        ↓
    Inputs re-enabled
        ↓
    History panel refreshed
        ↓
    User can view guide in history
```

### Code Wrapping (No Changes to Existing Code!)

The Flask app **wraps** your existing workflow code:

```python
# jobs/workflow_runner.py

async def run_workflow_async(job_id, task, app_url, app_name):
    # Import existing code
    from agent.planner import GeminiPlanner
    from agent.browser_use_agent import BrowserUseAgent
    # ... etc

    # Planning step
    emit_log(job_id, "[1/4] Planning...", 'info', 'planning')
    planner = GeminiPlanner()
    plan = await planner.create_plan(task, app_url, app_name)  # EXISTING CODE
    emit_log(job_id, "[OK] Plan created", 'success', 'planning')

    # Execution step
    emit_log(job_id, "[2/4] Executing...", 'info', 'executing')
    agent = BrowserUseAgent()
    states = await agent.execute_workflow(...)  # EXISTING CODE
    emit_log(job_id, "[OK] Executed", 'success', 'executing')

    # ... and so on
```

All existing business logic remains **100% unchanged**!

## Testing

### Test 1: Start Server
```bash
python app.py
# Should start without errors at http://localhost:5000
```

### Test 2: Open Browser
Navigate to http://localhost:5000
- Should see retro-styled interface
- Title: "FLOW PLANNER"
- Portfolio button (top right)
- Left panel with algorithm overview
- Right panel with logs
- Footer status bar

### Test 3: Run Workflow
1. Enter task: "Search for Python on Wikipedia"
2. Click "RUN WORKFLOW"
3. Inputs should become disabled
4. Logs should stream in real-time with colors
5. Status bar should show "RUNNING"
6. On completion, inputs re-enable
7. History panel should update

### Test 4: View History
1. Click "HISTORY" to expand
2. Should see previous runs
3. Click markdown file button
4. Modal should open with rendered guide
5. Screenshots should display inline
6. Close with X or Escape

## File Structure

```
Flow-Planner/
├── app.py                           # ✨ NEW - Flask server
├── routes/
│   ├── __init__.py                  # ✅ Exists
│   └── workflows.py                 # ✨ NEW - API routes
├── jobs/
│   ├── __init__.py                  # ✅ Exists
│   └── workflow_runner.py           # ✨ NEW - Background jobs
├── templates/
│   └── index.html                   # ✨ NEW - Main UI
├── static/
│   ├── css/
│   │   └── style.css                # ✨ NEW - Retro styles
│   ├── js/
│   │   └── app.js                   # ✨ NEW - Frontend logic
│   └── images/
│       ├── README.md                # ✨ NEW - Instructions
│       └── me.png                   # ⚠️ ADD YOUR IMAGE HERE
├── agent/                           # ✅ UNCHANGED
├── utils/                           # ✅ UNCHANGED
├── config.py                        # ✅ UNCHANGED
├── run_workflow.py                  # ✅ UNCHANGED (CLI still works!)
├── FLASK_APP.md                     # ✨ NEW - Documentation
└── FLASK_SETUP_SUMMARY.md           # ✨ NEW - This file
```

## Configuration

No new configuration required! Uses existing `.env` settings:

```env
# Existing config works
GEMINI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
FLASK_SECRET_KEY=your_secret  # Optional, has default

# Optional: Auto-run refinement
REFINEMENT_AUTO=true
```

## Keyboard Shortcuts

- **Ctrl + Enter**: Start workflow (when task input focused)
- **Escape**: Close markdown viewer

## CLI Still Works!

The original CLI is completely unchanged:

```bash
# Run CLI workflow (still works!)
python run_workflow.py

# Or with predefined tests
python run_workflow.py --predefined
```

Both CLI and web app use the same:
- Configuration (config.py)
- Workflow code (agent/, utils/)
- Output directory (output/)

## Next Steps

1. **Add your portfolio image**: `static/images/me.png`
2. **Start the server**: `python app.py`
3. **Test a workflow**: Enter a task and run
4. **View the guide**: Check history panel after completion

## Troubleshooting

### "Address already in use" error
Port 5000 is taken. Change in app.py:
```python
socketio.run(app, host='0.0.0.0', port=5001)  # Different port
```

### No logs appearing
1. Check browser console (F12)
2. Verify SocketIO connection (should see green "Connected" message)
3. Check server terminal for errors

### Images not loading in markdown
1. Ensure output directory exists and is readable
2. Check browser Network tab for 404 errors
3. Verify image paths in markdown are relative

### Missing dependencies
```bash
pip install flask flask-socketio flask-cors python-socketio python-engineio
```

## Color Reference

### CSS Variables (in style.css)
```css
--color-planning: #ffaa00;    /* Orange */
--color-executing: #00aaff;   /* Blue */
--color-saving: #9d4edd;      /* Purple */
--color-generating: #06ffa5;  /* Cyan */
--color-refining: #ff006e;    /* Pink */
```

Logs with these step types automatically get colored!

## Success Criteria ✅

All requested features implemented:

- ✅ Flask web app wrapping existing code
- ✅ Retro pixelated font design
- ✅ Input fields on left (task, app_url, app_name)
- ✅ Inputs become disabled during execution
- ✅ Real-time log window on right (THE CRUX!)
- ✅ Color-coded step logs (planning, executing, etc.)
- ✅ Regular logs remain black/gray
- ✅ Title "FLOW PLANNER" at top
- ✅ Portfolio button (me.png) linking to your portfolio
- ✅ Collapsible history panel on left
- ✅ View markdown files from history
- ✅ Support for 1-2 markdown files per run
- ✅ Markdown viewer opens on website
- ✅ Status bar with details
- ✅ Links to Browser-Use GitHub
- ✅ Links to Gemini/Google AI Studio
- ✅ Algorithm overview on left
- ✅ No PDF export (ditched as requested)
- ✅ NO changes to existing workflow code

## Ready to Launch! 🚀

Everything is set up and ready to go. Just add your portfolio image and start the server!

```bash
python app.py
```

Then open http://localhost:5000 and enjoy the retro workflow capture experience! 🎮✨
