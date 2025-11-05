"""
Background workflow job runner
Wraps existing workflow code and emits real-time updates via SocketIO
"""
import asyncio
import threading
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, Dict

# Import workflow modules at startup to prevent Flask auto-reload
from agent.planner import GeminiPlanner
from agent.browser_use_agent import BrowserUseAgent
from agent.state_capturer import StateCapturer
from agent.refinement_agent import RefinementAgent
from config import Config

logger = logging.getLogger(__name__)

# Store active jobs
active_jobs: Dict[str, Dict] = {}

# Will be set by app.py
socketio = None


def init_socketio(sio):
    """Initialize SocketIO instance"""
    global socketio
    socketio = sio


def emit_log(job_id: str, message: str, log_type: str = 'info', step_type: Optional[str] = None):
    """
    Emit log message to connected clients

    Args:
        job_id: Job identifier
        message: Log message
        log_type: Type of log (info, success, error, warning)
        step_type: Optional step type for color coding (planning, executing, refining, etc.)
    """
    logger.info(f"[EMIT_LOG {job_id}] {log_type}: {message}")
    if socketio:
        try:
            socketio.emit('log', {
                'job_id': job_id,
                'message': message,
                'type': log_type,
                'step_type': step_type,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"[EMIT_LOG] Failed to emit: {str(e)}", exc_info=True)


def emit_status(job_id: str, status: str, data: Optional[Dict] = None):
    """Emit status update to connected clients"""
    logger.info(f"[EMIT_STATUS {job_id}] Status: {status}")
    if socketio:
        try:
            event_data = {
                'job_id': job_id,
                'status': status,
                'timestamp': datetime.now().isoformat()
            }
            if data:
                event_data.update(data)

            socketio.emit('status', event_data)
        except Exception as e:
            logger.error(f"[EMIT_STATUS] Failed to emit: {str(e)}", exc_info=True)


def start_workflow_job(task: str, app_url: Optional[str], app_name: Optional[str], user_settings: Optional[Dict] = None) -> str:
    """
    Start a new workflow capture job in background thread

    Args:
        task: Task description
        app_url: Optional application URL
        app_name: Optional application name
        user_settings: Optional dict with user's API keys and model preferences

    Returns:
        Job ID
    """
    job_id = str(uuid.uuid4())[:8]

    # Store job info
    active_jobs[job_id] = {
        'job_id': job_id,
        'task': task,
        'app_url': app_url,
        'app_name': app_name,
        'status': 'starting',
        'started_at': datetime.now().isoformat(),
        'user_settings': user_settings
    }

    # Emit initial log immediately
    emit_log(job_id, f"Job {job_id} created, starting workflow...", 'info')
    if user_settings:
        emit_log(job_id, "Using user-provided API keys and model preferences", 'info')

    # Start background thread
    thread = threading.Thread(
        target=run_workflow_thread,
        args=(job_id, task, app_url, app_name, user_settings),
        daemon=True
    )
    thread.start()

    logger.info(f"[JOB] Started job {job_id}: {task} (user settings: {bool(user_settings)})")

    return job_id


def run_workflow_thread(job_id: str, task: str, app_url: Optional[str], app_name: Optional[str], user_settings: Optional[Dict] = None):
    """Run workflow in background thread"""
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run async workflow
        loop.run_until_complete(run_workflow_async(job_id, task, app_url, app_name, user_settings))

    except Exception as e:
        logger.error(f"[JOB] Job {job_id} failed: {str(e)}", exc_info=True)
        active_jobs[job_id]['status'] = 'failed'
        active_jobs[job_id]['error'] = str(e)
        emit_log(job_id, f"ERROR: {str(e)}", 'error')
        emit_status(job_id, 'failed', {'error': str(e)})

    finally:
        loop.close()


async def run_workflow_async(job_id: str, task: str, app_url: Optional[str], app_name: Optional[str], user_settings: Optional[Dict] = None):
    """
    Execute workflow with real-time updates
    Wraps existing run_workflow.py logic
    """
    # Emit immediate test log to verify connection
    emit_log(job_id, "Workflow runner starting...", 'info')
    logger.info(f"[JOB {job_id}] Async workflow starting")

    emit_log(job_id, "="*80, 'info')
    emit_log(job_id, f"TASK: {task}", 'info')
    if app_name:
        emit_log(job_id, f"APP: {app_name} ({app_url or 'auto'})", 'info')
    emit_log(job_id, "="*80, 'info')

    # Store original config values and override with user settings if provided
    original_config = {}
    if user_settings:
        if user_settings.get('gemini_api_key'):
            original_config['GEMINI_API_KEY'] = Config.GEMINI_API_KEY
            Config.GEMINI_API_KEY = user_settings['gemini_api_key']
            emit_log(job_id, "Using user-provided Gemini API key", 'info')

        if user_settings.get('anthropic_api_key'):
            original_config['ANTHROPIC_API_KEY'] = Config.ANTHROPIC_API_KEY
            Config.ANTHROPIC_API_KEY = user_settings['anthropic_api_key']
            emit_log(job_id, "Using user-provided Anthropic API key", 'info')

        if user_settings.get('gemini_model'):
            original_config['GEMINI_MODEL'] = Config.GEMINI_MODEL
            Config.GEMINI_MODEL = user_settings['gemini_model']
            emit_log(job_id, f"Using Gemini model: {user_settings['gemini_model']}", 'info')

        if user_settings.get('claude_model'):
            original_config['BROWSER_USE_LLM_MODEL'] = Config.BROWSER_USE_LLM_MODEL
            Config.BROWSER_USE_LLM_MODEL = user_settings['claude_model']
            emit_log(job_id, f"Using Claude model: {user_settings['claude_model']}", 'info')

    try:
        # Update job status
        active_jobs[job_id]['status'] = 'planning'
        emit_status(job_id, 'planning')

        # Step 1: Planning
        emit_log(job_id, "\n" + "="*80, 'info')
        emit_log(job_id, "[1/4] Planning workflow with Gemini...", 'info', 'planning')
        emit_log(job_id, "="*80, 'info')
        logger.info(f"[JOB {job_id}] Creating planner")

        try:
            planner = GeminiPlanner()
            emit_log(job_id, "Planner initialized, creating plan...", 'info')
            logger.info(f"[JOB {job_id}] Calling create_plan")

            plan = await planner.create_plan(task, app_url, app_name)
            logger.info(f"[JOB {job_id}] Plan created successfully")

        except Exception as plan_error:
            logger.error(f"[JOB {job_id}] Planning failed: {str(plan_error)}", exc_info=True)
            emit_log(job_id, f"ERROR: Planning failed: {str(plan_error)}", 'error')
            raise

        # Extract app details
        inferred_url = plan.get('context', {}).get('app_url', app_url or 'https://example.com')
        inferred_name = plan.get('context', {}).get('app_name', app_name or 'Application')

        if not app_url or not app_name:
            emit_log(job_id, f"[INFO] Application inferred: {inferred_name} ({inferred_url})", 'info')

        app_url = inferred_url
        app_name = inferred_name

        emit_log(job_id, f"[OK] Plan created:", 'success')
        emit_log(job_id, f"  - Auth required: {plan['task_analysis']['requires_authentication']}", 'info')
        emit_log(job_id, f"  - Steps: {len(plan['workflow_outline'])}", 'info')
        emit_log(job_id, f"  - Complexity: {plan['task_analysis']['complexity']}", 'info')

        # Step 2: Execution
        active_jobs[job_id]['status'] = 'executing'
        emit_status(job_id, 'executing')
        emit_log(job_id, "\n" + "="*80, 'info')
        emit_log(job_id, f"[2/4] Executing workflow with Browser-Use agent...", 'info', 'executing')
        emit_log(job_id, "="*80, 'info')

        # Create agent with log callback for intermediate steps
        def log_callback(message, log_type='info', step_type=None):
            emit_log(job_id, message, log_type, step_type)

        agent = BrowserUseAgent(log_callback=log_callback)
        states = await agent.execute_workflow(
            task=task,
            workflow_outline=plan['workflow_outline'],
            app_url=app_url,
            context=plan['context']
        )

        emit_log(job_id, f"[OK] Workflow executed: {len(states)} states captured", 'success', 'executing')

        # Step 3: Save results
        active_jobs[job_id]['status'] = 'saving'
        emit_status(job_id, 'saving')
        emit_log(job_id, "\n" + "="*80, 'info')
        emit_log(job_id, f"[3/4] Saving workflow data...", 'info', 'saving')
        emit_log(job_id, "="*80, 'info')

        capturer = StateCapturer()
        task_name = app_name.lower().replace(" ", "_")
        summary = await capturer.capture_states(
            states=states,
            task_name=task_name,
            task_description=task
        )

        emit_log(job_id, f"[OK] States saved: {summary['total_states']}", 'success', 'saving')

        # Step 4: Generate guide
        emit_log(job_id, "\n" + "="*80, 'info')
        emit_log(job_id, f"[4/4] Generating workflow guide with Gemini...", 'info', 'generating')
        emit_log(job_id, "="*80, 'info')

        try:
            guide_path = await capturer.generate_guide(
                metadata_path=summary['metadata_path'],
                task_description=task
            )
            emit_log(job_id, f"[OK] Workflow guide generated!", 'success', 'generating')
        except Exception as e:
            emit_log(job_id, f"[WARN] Guide generation failed: {str(e)}", 'warning', 'generating')
            guide_path = None

        emit_log(job_id, f"\n[SUCCESS] Workflow captured successfully!", 'success')
        emit_log(job_id, f"  - Output: {summary['output_directory']}", 'info')
        emit_log(job_id, f"  - States: {summary['total_states']}", 'info')
        emit_log(job_id, f"  - Metadata: {summary['metadata_path']}", 'info')
        if guide_path:
            emit_log(job_id, f"  - Guide: {guide_path}", 'info')

        # Step 5: Optional refinement (auto-run if enabled)
        refined_guide_path = None
        if Config.ENABLE_REFINEMENT and guide_path and Config.REFINEMENT_AUTO:
            active_jobs[job_id]['status'] = 'refining'
            emit_status(job_id, 'refining')
            emit_log(job_id, "\n" + "="*80, 'info')
            emit_log(job_id, f"[5/5] Refining workflow with Vision AI...", 'info', 'refining')
            emit_log(job_id, "="*80, 'info')

            try:
                refiner = RefinementAgent(
                    primary_model=Config.REFINEMENT_MODEL,
                    fallback_model=Config.REFINEMENT_FALLBACK,
                    grid_size=Config.REFINEMENT_GRID_SIZE,
                    padding_percent=Config.REFINEMENT_PADDING
                )

                refinement_result = await refiner.refine_workflow(
                    metadata_path=summary['metadata_path'],
                    workflow_guide_path=guide_path,
                    task_description=task
                )

                if refinement_result['success']:
                    refined_count = refinement_result['refined_count']
                    total_count = refinement_result['total_count']

                    emit_log(job_id, f"[OK] Workflow refined!", 'success')
                    emit_log(job_id, f"  - Refined steps: {refined_count}/{total_count}", 'info')
                    emit_log(job_id, f"  - Enhanced guide: {refinement_result['refined_guide_path']}", 'info')

                    refined_guide_path = refinement_result['refined_guide_path']
                else:
                    emit_log(job_id, f"[WARN] Refinement failed: {refinement_result.get('message', 'Unknown error')}", 'warning')

            except Exception as e:
                emit_log(job_id, f"[WARN] Refinement failed: {str(e)}", 'warning')

        # Complete job
        active_jobs[job_id]['status'] = 'completed'
        active_jobs[job_id]['output_dir'] = summary['output_directory']
        active_jobs[job_id]['guide_path'] = guide_path
        active_jobs[job_id]['refined_guide_path'] = refined_guide_path

        emit_status(job_id, 'completed', {
            'output_dir': summary['output_directory'],  # Send full absolute path for refinement
            'guide_path': os.path.basename(guide_path) if guide_path else None,
            'refined_guide_path': os.path.basename(refined_guide_path) if refined_guide_path else None
        })

    except Exception as e:
        logger.error(f"[JOB] Workflow failed: {str(e)}", exc_info=True)
        active_jobs[job_id]['status'] = 'failed'
        active_jobs[job_id]['error'] = str(e)
        emit_log(job_id, f"\n[FAIL] Workflow failed: {str(e)}", 'error')
        emit_status(job_id, 'failed', {'error': str(e)})

    finally:
        # Restore original config values if we modified them
        if original_config:
            for key, value in original_config.items():
                setattr(Config, key, value)
            logger.info(f"[JOB {job_id}] Restored original config values")


def get_job_status(job_id: str) -> Optional[Dict]:
    """Get status of a specific job"""
    return active_jobs.get(job_id)


# Import os for path operations
import os
