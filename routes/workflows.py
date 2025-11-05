"""
API routes for workflow management
"""
import logging
import asyncio
from flask import Blueprint, request, jsonify
from jobs.workflow_runner import start_workflow_job, get_job_status, active_jobs
import google.generativeai as genai
import anthropic

logger = logging.getLogger(__name__)

workflows_bp = Blueprint('workflows', __name__)


@workflows_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring and deployment verification
    """
    return jsonify({
        'status': 'online',
        'service': 'Flow Planner API',
        'version': '1.0.0'
    }), 200


@workflows_bp.route('/workflow', methods=['POST'])
def create_workflow():
    """
    Start a new workflow capture job

    Request body:
    {
        "task": "Task description",
        "app_url": "Optional app URL",
        "app_name": "Optional app name",
        "gemini_api_key": "Optional user's Gemini API key",
        "anthropic_api_key": "Optional user's Anthropic API key",
        "gemini_model": "Optional Gemini model",
        "claude_model": "Optional Claude model"
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'Request body required'}), 400

        task = (data.get('task') or '').strip()
        if not task:
            return jsonify({'error': 'Task description is required'}), 400

        # Handle None values properly
        app_url = (data.get('app_url') or '').strip() or None
        app_name = (data.get('app_name') or '').strip() or None

        # User settings (API keys and models)
        user_settings = {}
        if data.get('gemini_api_key'):
            user_settings['gemini_api_key'] = data.get('gemini_api_key').strip()
        if data.get('anthropic_api_key'):
            user_settings['anthropic_api_key'] = data.get('anthropic_api_key').strip()
        if data.get('gemini_model'):
            user_settings['gemini_model'] = data.get('gemini_model').strip()
        if data.get('claude_model'):
            user_settings['claude_model'] = data.get('claude_model').strip()

        # Start background job with user settings
        job_id = start_workflow_job(task, app_url, app_name, user_settings if user_settings else None)

        logger.info(f"[API] Started workflow job: {job_id} (with user settings: {bool(user_settings)})")

        return jsonify({
            'job_id': job_id,
            'status': 'started',
            'message': 'Workflow capture started'
        })

    except Exception as e:
        logger.error(f"[API] Failed to start workflow: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@workflows_bp.route('/workflow/<job_id>', methods=['GET'])
def get_workflow_status_route(job_id):
    """Get status of a specific workflow job"""
    try:
        status = get_job_status(job_id)

        if not status:
            return jsonify({'error': 'Job not found'}), 404

        return jsonify(status)

    except Exception as e:
        logger.error(f"[API] Failed to get job status: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@workflows_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all active jobs"""
    try:
        jobs = [
            {
                'job_id': job_id,
                'task': job_info['task'],
                'status': job_info['status']
            }
            for job_id, job_info in active_jobs.items()
        ]

        return jsonify({'jobs': jobs})

    except Exception as e:
        logger.error(f"[API] Failed to list jobs: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@workflows_bp.route('/refine', methods=['POST'])
def refine_workflow():
    """
    Start refinement for a completed workflow

    Request body:
    {
        "job_id": "Job ID",
        "output_dir": "Output directory path"
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'Request body required'}), 400

        job_id = data.get('job_id')
        output_dir = data.get('output_dir')

        if not job_id or not output_dir:
            return jsonify({'error': 'job_id and output_dir are required'}), 400

        # Check if job exists and is completed
        job_info = active_jobs.get(job_id)
        if not job_info:
            return jsonify({'error': f'Job {job_id} not found'}), 404

        if job_info['status'] != 'completed':
            return jsonify({'error': f'Job {job_id} is not completed (status: {job_info["status"]})'}), 400

        # Import refinement modules
        import os
        from agent.refinement_agent import RefinementAgent
        from config import Config
        import asyncio
        import threading

        # Get metadata path and guide path
        metadata_path = os.path.join(output_dir, 'metadata.json')
        guide_path = job_info.get('guide_path')

        if not guide_path:
            guide_path = os.path.join(output_dir, 'WORKFLOW_GUIDE.md')

        if not os.path.exists(metadata_path):
            return jsonify({'error': f'Metadata file not found at {metadata_path}'}), 404

        if not os.path.exists(guide_path):
            return jsonify({'error': f'Guide file not found at {guide_path}'}), 404

        # Start refinement in background thread
        def run_refinement():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def refine():
                    from jobs.workflow_runner import emit_log, emit_status

                    emit_log(job_id, "\n" + "="*80, 'info')
                    emit_log(job_id, "[REFINEMENT] Starting workflow refinement with Vision AI...", 'info', 'refining')
                    emit_log(job_id, "="*80, 'info')

                    try:
                        refiner = RefinementAgent(
                            primary_model=Config.REFINEMENT_MODEL,
                            fallback_model=Config.REFINEMENT_FALLBACK,
                            grid_size=Config.REFINEMENT_GRID_SIZE,
                            padding_percent=Config.REFINEMENT_PADDING
                        )

                        # Get task description from job info
                        task_description = job_info.get('task', '')

                        refinement_result = await refiner.refine_workflow(
                            metadata_path=metadata_path,
                            workflow_guide_path=guide_path,
                            task_description=task_description
                        )

                        if refinement_result['success']:
                            refined_count = refinement_result['refined_count']
                            total_count = refinement_result['total_count']
                            refined_guide_path = refinement_result['refined_guide_path']
                            refinement_metadata_path = refinement_result.get('refinement_metadata_path')

                            emit_log(job_id, f"[OK] Workflow refined!", 'success', 'refining')
                            emit_log(job_id, f"  - Refined steps: {refined_count}/{total_count}", 'info')
                            emit_log(job_id, f"  - Enhanced guide: {os.path.basename(refined_guide_path)}", 'info')
                            if refinement_metadata_path:
                                emit_log(job_id, f"  - Refinement metadata: {os.path.basename(refinement_metadata_path)}", 'info')

                            # Update job info
                            active_jobs[job_id]['refined_guide_path'] = refined_guide_path
                            if refinement_metadata_path:
                                active_jobs[job_id]['refinement_metadata_path'] = refinement_metadata_path

                            emit_status(job_id, 'refined', {
                                'refined_guide_path': os.path.basename(refined_guide_path),
                                'refinement_metadata_path': os.path.basename(refinement_metadata_path) if refinement_metadata_path else None
                            })

                        else:
                            emit_log(job_id, f"[WARN] Refinement failed: {refinement_result.get('message', 'Unknown error')}", 'warning', 'refining')
                            emit_status(job_id, 'refinement_failed', {
                                'error': refinement_result.get('message', 'Unknown error')
                            })

                    except Exception as e:
                        logger.error(f"[REFINE] Refinement failed: {str(e)}", exc_info=True)
                        emit_log(job_id, f"[ERROR] Refinement failed: {str(e)}", 'error', 'refining')
                        emit_status(job_id, 'refinement_failed', {'error': str(e)})

                loop.run_until_complete(refine())

            except Exception as e:
                logger.error(f"[REFINE] Background refinement failed: {str(e)}", exc_info=True)

            finally:
                loop.close()

        thread = threading.Thread(target=run_refinement, daemon=True)
        thread.start()

        logger.info(f"[API] Started refinement for job {job_id}")

        return jsonify({
            'job_id': job_id,
            'status': 'refining',
            'message': 'Refinement started'
        })

    except Exception as e:
        logger.error(f"[API] Failed to start refinement: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@workflows_bp.route('/verify-keys', methods=['POST'])
def verify_keys():
    """
    Verify API keys by pinging Gemini and Claude APIs

    Request body:
    {
        "gemini_key": "Optional Gemini API key",
        "anthropic_key": "Optional Anthropic API key"
    }
    """
    try:
        data = request.json or {}
        gemini_key = (data.get('gemini_key') or '').strip()
        anthropic_key = (data.get('anthropic_key') or '').strip()

        results = {
            'gemini': {'valid': False, 'error': None},
            'anthropic': {'valid': False, 'error': None}
        }

        # Test Gemini API
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('models/gemini-flash-lite-latest')
                response = model.generate_content('Say "OK" and nothing else.')

                if response and response.text:
                    results['gemini']['valid'] = True
                    logger.info("[API] Gemini API key verified successfully")
                else:
                    results['gemini']['error'] = 'No response from API'

            except Exception as e:
                results['gemini']['error'] = str(e)
                logger.warning(f"[API] Gemini API key verification failed: {str(e)}")

        # Test Anthropic API
        if anthropic_key:
            try:
                client = anthropic.Anthropic(api_key=anthropic_key)
                message = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=50,
                    messages=[{"role": "user", "content": "Say 'OK' and nothing else."}]
                )

                if message and message.content:
                    results['anthropic']['valid'] = True
                    logger.info("[API] Anthropic API key verified successfully")
                else:
                    results['anthropic']['error'] = 'No response from API'

            except Exception as e:
                results['anthropic']['error'] = str(e)
                logger.warning(f"[API] Anthropic API key verification failed: {str(e)}")

        return jsonify(results)

    except Exception as e:
        logger.error(f"[API] Failed to verify keys: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@workflows_bp.route('/models/gemini', methods=['GET'])
def get_gemini_models():
    """
    Get list of available Gemini models

    Query params:
    - api_key: Optional Gemini API key (uses server key if not provided)
    """
    try:
        api_key = request.args.get('api_key', '').strip()

        # Use provided key or fall back to server config
        if api_key:
            genai.configure(api_key=api_key)
        else:
            from config import Config
            if not Config.GEMINI_API_KEY:
                return jsonify({'error': 'No API key provided and server key not configured'}), 400
            genai.configure(api_key=Config.GEMINI_API_KEY)

        # Fetch available models
        models = []
        for model in genai.list_models():
            # Filter for multimodal vision models
            if 'generateContent' in model.supported_generation_methods:
                models.append({
                    'id': model.name,
                    'name': model.display_name or model.name,
                    'description': model.description or ''
                })

        logger.info(f"[API] Fetched {len(models)} Gemini models")
        return jsonify({'models': models})

    except Exception as e:
        logger.error(f"[API] Failed to fetch Gemini models: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@workflows_bp.route('/models/claude', methods=['GET'])
def get_claude_models():
    """
    Get list of available Claude models

    Query params:
    - api_key: Optional Anthropic API key (uses server key if not provided)
    """
    try:
        api_key = request.args.get('api_key', '').strip()

        # Use provided key or fall back to server config
        if not api_key:
            from config import Config
            api_key = Config.ANTHROPIC_API_KEY

        if not api_key:
            return jsonify({'error': 'No API key provided and server key not configured'}), 400

        client = anthropic.Anthropic(api_key=api_key)

        # Fetch available models from API
        response = client.models.list()

        # Filter for multimodal models (Claude 3+ with vision)
        models = []
        for model in response.data:
            # All Claude 3+ models support vision
            if 'claude-3' in model.id or 'claude-sonnet' in model.id or 'claude-haiku' in model.id or 'claude-opus' in model.id:
                models.append({
                    'id': model.id,
                    'name': model.display_name or model.id,
                    'created': model.created_at
                })

        # If API doesn't return models or filtering removed all, provide defaults
        if not models:
            models = [
                {
                    'id': 'claude-sonnet-4-5-20250929',
                    'name': 'Claude Sonnet 4.5',
                    'created': '2025-09-29'
                },
                {
                    'id': 'claude-haiku-4-5-20251001',
                    'name': 'Claude Haiku 4.5',
                    'created': '2025-10-01'
                },
                {
                    'id': 'claude-opus-4-20250514',
                    'name': 'Claude Opus 4',
                    'created': '2025-05-14'
                }
            ]

        logger.info(f"[API] Fetched {len(models)} Claude models")
        return jsonify({'models': models})

    except Exception as e:
        logger.error(f"[API] Failed to fetch Claude models: {str(e)}", exc_info=True)
        # Return default models on error
        models = [
            {
                'id': 'claude-sonnet-4-5-20250929',
                'name': 'Claude Sonnet 4.5',
                'created': '2025-09-29'
            },
            {
                'id': 'claude-haiku-4-5-20251001',
                'name': 'Claude Haiku 4.5',
                'created': '2025-10-01'
            },
            {
                'id': 'claude-opus-4-20250514',
                'name': 'Claude Opus 4',
                'created': '2025-05-14'
            }
        ]
        return jsonify({'models': models})
