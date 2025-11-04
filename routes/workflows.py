"""
API routes for workflow management
"""
import logging
from flask import Blueprint, request, jsonify
from jobs.workflow_runner import start_workflow_job, get_job_status, active_jobs

logger = logging.getLogger(__name__)

workflows_bp = Blueprint('workflows', __name__)


@workflows_bp.route('/workflow', methods=['POST'])
def create_workflow():
    """
    Start a new workflow capture job

    Request body:
    {
        "task": "Task description",
        "app_url": "Optional app URL",
        "app_name": "Optional app name"
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

        # Start background job
        job_id = start_workflow_job(task, app_url, app_name)

        logger.info(f"[API] Started workflow job: {job_id}")

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
