"""
Flask Web Application for Flow Planner
Real-time workflow capture with SocketIO streaming
"""
import os
import sys
import logging
from flask import Flask, render_template, jsonify, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
from config import Config
from utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
CORS(app)

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Import routes
from routes.workflows import workflows_bp
app.register_blueprint(workflows_bp, url_prefix='/api')

# Store reference to socketio for background jobs
app.socketio = socketio


@app.route('/')
def index():
    """Main application page"""
    return render_template('index.html')


@app.route('/output/<path:filename>')
def serve_output(filename):
    """Serve files from output directory (screenshots, markdown, etc.)"""
    return send_from_directory(Config.OUTPUT_DIR, filename)


@app.route('/api/history')
def get_history():
    """Get list of all workflow runs from output directory"""
    try:
        if not os.path.exists(Config.OUTPUT_DIR):
            return jsonify({'runs': []})

        runs = []
        for run_dir in sorted(os.listdir(Config.OUTPUT_DIR), reverse=True):
            run_path = os.path.join(Config.OUTPUT_DIR, run_dir)

            if not os.path.isdir(run_path):
                continue

            # Look for markdown files
            md_files = []
            for file in os.listdir(run_path):
                if file.endswith('.md'):
                    md_files.append(file)

            # Get metadata if available
            metadata_path = os.path.join(run_path, 'metadata.json')
            task_name = run_dir
            if os.path.exists(metadata_path):
                import json
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        task_name = metadata.get('task_description', run_dir)
                except:
                    pass

            runs.append({
                'id': run_dir,
                'name': task_name,
                'markdown_files': md_files,
                'path': run_dir
            })

        return jsonify({'runs': runs})

    except Exception as e:
        logger.error(f"Failed to get history: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/markdown/<path:filepath>')
def get_markdown(filepath):
    """Get markdown file content"""
    try:
        full_path = os.path.join(Config.OUTPUT_DIR, filepath)
        if not os.path.exists(full_path):
            return jsonify({'error': 'File not found'}), 404

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return jsonify({'content': content, 'path': filepath})

    except Exception as e:
        logger.error(f"Failed to read markdown: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("[SOCKETIO] Client connected")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("[SOCKETIO] Client disconnected")


@socketio.on('join_job')
def handle_join_job(data):
    """Join a specific job room for updates"""
    job_id = data.get('job_id')
    logger.info(f"[SOCKETIO] Client joined job: {job_id}")


if __name__ == '__main__':
    # Validate configuration
    try:
        Config.validate()
        Config.ensure_directories()

        print("""
================================================================================
                          FLOW PLANNER WEB APP
                         Retro Workflow Capture
================================================================================

Server starting at: http://localhost:5000
Press Ctrl+C to stop

================================================================================
""")

        # Run Flask app with SocketIO
        socketio.run(
            app,
            debug=Config.DEBUG,
            host='0.0.0.0',
            port=5000,
            allow_unsafe_werkzeug=True  # For development
        )

    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        sys.exit(1)
