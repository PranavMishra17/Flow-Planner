# Flow Planner - Flask Web Application

A retro-styled web interface for Flow Planner with real-time workflow capture and visualization.

## Features

### 🎮 Retro Game Aesthetic
- Pixelated fonts (Press Start 2P)
- CRT monitor screen effect
- Neon green terminal colors
- Color-coded step indicators

### 📊 Real-Time Logs
- Live streaming logs via SocketIO
- Color-coded steps:
  - **Planning** (Orange): Gemini planning phase
  - **Executing** (Blue): Browser-Use execution
  - **Saving** (Purple): State capture
  - **Generating** (Cyan): Guide generation
  - **Refining** (Pink): Vision AI refinement

### 📜 History Viewer
- Collapsible sidebar showing all workflow runs
- View workflow guides directly in browser
- Support for both original and refined guides
- Markdown rendering with image display

### 🎯 Algorithm Overview
- Visual representation of the 5-step process
- Always visible for reference

### 🔗 Status Bar
- Links to Browser-Use GitHub
- Links to Gemini and Claude AI
- Real-time job status
- Portfolio link button

## Quick Start

### 1. Install Dependencies

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Make sure your `.env` file has all required settings:

```env
# API Keys (Required)
GEMINI_API_KEY=your_gemini_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Flask (Optional)
FLASK_SECRET_KEY=your-random-secret-key
FLASK_ENV=development

# Auto-refinement (Optional)
REFINEMENT_AUTO=true  # Auto-run refinement without prompting
```

### 3. Add Portfolio Image

Place your profile image at `static/images/me.png`:

```bash
# Copy your image
cp /path/to/your/photo.png static/images/me.png
```

Image requirements:
- Square aspect ratio (48x48px or larger)
- PNG format
- Named exactly `me.png`

### 4. Start the Server

```bash
python app.py
```

The server will start at: **http://localhost:5000**

## Usage

### Running a Workflow

1. **Enter Task**: Type your task description in the input field
   - Example: "Create a new project in Linear"

2. **Optional Fields**:
   - **APP URL**: Specify the application URL (e.g., `https://linear.app`)
   - **APP NAME**: Specify the application name (e.g., `Linear`)
   - If omitted, the planner will infer these from your task

3. **Click "RUN WORKFLOW"**: The workflow will start immediately

4. **Watch Real-Time Logs**: The right panel shows live progress with color-coded steps

5. **View Results**: When complete, check the HISTORY panel to view the workflow guide

### Viewing History

1. Click **"HISTORY"** button in the left panel to expand
2. Browse previous workflow runs
3. Click on markdown files to view them in-browser
4. Images from workflows are displayed inline

### Keyboard Shortcuts

- **Ctrl + Enter**: Start workflow (when task input is focused)
- **Escape**: Close markdown viewer

## Architecture

### File Structure

```
Flow-Planner/
├── app.py                    # Flask application entry point
├── routes/
│   └── workflows.py          # API endpoints
├── jobs/
│   └── workflow_runner.py    # Background job execution
├── templates/
│   └── index.html            # Main UI template
├── static/
│   ├── css/
│   │   └── style.css         # Retro styling
│   ├── js/
│   │   └── app.js            # Frontend logic
│   └── images/
│       └── me.png            # Portfolio image (add your own)
└── [existing workflow code]  # Unchanged
```

### How It Works

1. **Frontend** (`templates/index.html`, `static/js/app.js`):
   - Sends task to `/api/workflow` endpoint
   - Connects to SocketIO for real-time updates
   - Displays logs with color coding
   - Loads history from `/api/history`
   - Renders markdown from `/api/markdown/<path>`

2. **Backend** (`app.py`, `routes/workflows.py`):
   - Handles API requests
   - Serves static files and output
   - Manages SocketIO connections

3. **Job Runner** (`jobs/workflow_runner.py`):
   - Wraps existing `run_workflow.py` logic
   - Runs workflow in background thread
   - Emits real-time updates via SocketIO
   - No changes to existing workflow code!

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application page |
| `/api/workflow` | POST | Start new workflow |
| `/api/workflow/<job_id>` | GET | Get job status |
| `/api/jobs` | GET | List all active jobs |
| `/api/history` | GET | Get workflow history |
| `/api/markdown/<path>` | GET | Get markdown content |
| `/output/<path>` | GET | Serve output files |

### SocketIO Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `connect` | Client → Server | Client connects |
| `disconnect` | Client → Server | Client disconnects |
| `join_job` | Client → Server | Join job room |
| `log` | Server → Client | Log message |
| `status` | Server → Client | Status update |

## Color Coding Reference

### Log Types
- **Info** (Gray): General information
- **Success** (Green): Successful operations
- **Error** (Red): Errors and failures
- **Warning** (Yellow): Warnings

### Step Types (Color-coded in logs)
- **Planning** (Orange `#ffaa00`): Gemini planning phase
- **Executing** (Blue `#00aaff`): Browser-Use execution
- **Saving** (Purple `#9d4edd`): State and screenshot capture
- **Generating** (Cyan `#06ffa5`): Workflow guide generation
- **Refining** (Pink `#ff006e`): Vision AI refinement

## Troubleshooting

### Port Already in Use

If port 5000 is already in use, change it in `app.py`:

```python
socketio.run(app, host='0.0.0.0', port=5001)  # Use different port
```

### Missing Images in Markdown

Make sure the output directory is accessible:
- Images are served from `/output/<run_dir>/<image>`
- Check that `Config.OUTPUT_DIR` exists and has proper permissions

### SocketIO Not Connecting

1. Check browser console for errors
2. Ensure `flask-socketio` is installed
3. Try disabling browser extensions
4. Check firewall settings

### Logs Not Appearing

1. Check browser console for JavaScript errors
2. Verify SocketIO connection (should see "Connected to server" in logs)
3. Check server logs for errors

## Development

### Running in Development Mode

```bash
# Enable debug mode
export FLASK_ENV=development
python app.py
```

Debug mode features:
- Auto-reload on code changes
- Detailed error pages
- Debug logging

### Customizing Styles

Edit `static/css/style.css` to customize:
- Colors (`:root` variables)
- Fonts
- Layout
- Animations

### Adding New Features

1. **New API Endpoint**: Add to `routes/workflows.py`
2. **New SocketIO Event**: Add to `app.py` and `static/js/app.js`
3. **New UI Section**: Edit `templates/index.html` and `static/css/style.css`

## CLI Still Works!

The original CLI workflow is completely unchanged:

```bash
# CLI mode still works
python run_workflow.py

# With predefined tests
python run_workflow.py --predefined
```

Both CLI and web app can coexist and use the same output directory.

## Production Deployment

For production deployment:

1. **Use Production WSGI Server**:
   ```bash
   pip install gunicorn eventlet
   gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
   ```

2. **Set Production Environment**:
   ```env
   FLASK_ENV=production
   FLASK_SECRET_KEY=generate-a-strong-random-key
   ```

3. **Use Reverse Proxy** (Nginx):
   ```nginx
   location / {
       proxy_pass http://localhost:5000;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
   }
   ```

4. **Enable HTTPS** for secure SocketIO connections

## Credits

- **Browser-Use**: https://github.com/browser-use/browser-use
- **Gemini API**: https://ai.google.dev/
- **Claude API**: https://www.anthropic.com/claude
- **Font**: Press Start 2P by CodeMan38

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review server logs in `logs/` directory
3. Check browser console for frontend errors
4. Verify all dependencies are installed

---

**Enjoy capturing workflows with the retro Flow Planner! 🎮✨**
