"""
Deployment verification test suite
Tests imports, configuration, API connectivity, and core functionality
Follows pytest industry standards
"""
import os
import sys
import pytest
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestImports:
    """Test that all required packages are installed"""

    def test_flask_imports(self):
        """Test Flask and extensions"""
        import flask
        import flask_socketio
        import flask_cors
        assert flask.__version__ is not None

    def test_socket_io_imports(self):
        """Test SocketIO dependencies"""
        import socketio
        import engineio
        # socketio module doesn't have __version__ in all versions
        assert socketio is not None
        assert engineio is not None

    def test_ai_imports(self):
        """Test AI/ML libraries"""
        import anthropic
        import google.generativeai
        assert anthropic.__version__ is not None

    def test_browser_automation_imports(self):
        """Test browser automation libraries"""
        import playwright
        from browser_use import Agent
        # Playwright module exists but may not have __version__ at top level
        assert playwright is not None
        assert Agent is not None

    def test_utility_imports(self):
        """Test utility libraries"""
        import aiofiles
        from dotenv import load_dotenv
        # aiofiles may not have __version__ in all versions
        assert aiofiles is not None
        assert load_dotenv is not None


class TestConfiguration:
    """Test configuration and environment variables"""

    def test_config_loads(self):
        """Test that config module loads"""
        from config import Config
        assert Config is not None

    def test_required_env_vars(self):
        """Test required environment variables are set"""
        from config import Config

        # Check API keys are set (not None or empty)
        assert Config.GEMINI_API_KEY, "GEMINI_API_KEY not set"
        assert Config.ANTHROPIC_API_KEY, "ANTHROPIC_API_KEY not set"
        assert Config.SECRET_KEY, "SECRET_KEY not set"

        # Verify keys are not placeholder values
        assert Config.GEMINI_API_KEY != "your_gemini_api_key_here"
        assert Config.ANTHROPIC_API_KEY != "your_anthropic_api_key_here"

    def test_directories_exist(self):
        """Test required directories exist or can be created"""
        required_dirs = [
            'templates',
            'static/css',
            'static/js',
            'static/images',
            'routes',
            'jobs',
            'agent',
            'utils'
        ]

        for dir_path in required_dirs:
            assert os.path.isdir(dir_path), f"Directory missing: {dir_path}"

    def test_required_files_exist(self):
        """Test critical files exist"""
        required_files = [
            'app.py',
            'config.py',
            'requirements.txt',
            'templates/index.html',
            'static/js/app.js',
            'static/css/style.css',
            'routes/workflows.py',
            'jobs/workflow_runner.py'
        ]

        for file_path in required_files:
            assert os.path.isfile(file_path), f"File missing: {file_path}"


class TestAPIConnectivity:
    """Test API connectivity and authentication"""

    @pytest.mark.asyncio
    async def test_gemini_api_connection(self):
        """Test Google Gemini API connectivity"""
        from config import Config
        import google.generativeai as genai

        try:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')

            # Send a simple test prompt
            response = await asyncio.to_thread(
                model.generate_content,
                "Say 'API test successful' and nothing else."
            )

            assert response.text is not None, "No response from Gemini API"
            assert len(response.text) > 0, "Empty response from Gemini API"

        except Exception as e:
            pytest.fail(f"Gemini API connection failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_anthropic_api_connection(self):
        """Test Anthropic Claude API connectivity"""
        from config import Config
        import anthropic

        try:
            client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

            # Send a simple test message
            message = await asyncio.to_thread(
                client.messages.create,
                model="claude-sonnet-4-20250514",
                max_tokens=50,
                messages=[
                    {"role": "user", "content": "Say 'API test successful' and nothing else."}
                ]
            )

            assert message.content is not None, "No response from Claude API"
            assert len(message.content) > 0, "Empty response from Claude API"

        except Exception as e:
            pytest.fail(f"Claude API connection failed: {str(e)}")

    def test_playwright_browser_available(self):
        """Test that Playwright browsers are installed"""
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                # Try to get chromium browser
                browser_type = p.chromium
                assert browser_type is not None, "Chromium browser not available"

        except Exception as e:
            pytest.fail(f"Playwright browser check failed: {str(e)}")


class TestFlaskApplication:
    """Test Flask application setup"""

    def test_flask_app_imports(self):
        """Test that Flask app can be imported"""
        try:
            from app import app, socketio
            assert app is not None
            assert socketio is not None
        except Exception as e:
            pytest.fail(f"Flask app import failed: {str(e)}")

    def test_flask_routes_registered(self):
        """Test that routes are registered"""
        from app import app

        # Check that routes exist
        routes = [rule.rule for rule in app.url_map.iter_rules()]

        assert '/' in routes, "Index route not registered"
        assert '/api/workflow' in routes, "Workflow route not registered"
        # Note: App may have different route names, just verify core routes exist
        assert len(routes) > 0, "No routes registered"

    def test_flask_config(self):
        """Test Flask app configuration"""
        from app import app

        assert app.config['SECRET_KEY'] is not None
        assert len(app.config['SECRET_KEY']) >= 32, "SECRET_KEY too short"


class TestAgentModules:
    """Test agent modules can be imported and initialized"""

    def test_planner_import(self):
        """Test Gemini planner can be imported"""
        from agent.planner import GeminiPlanner
        assert GeminiPlanner is not None

    def test_browser_agent_import(self):
        """Test Browser-Use agent can be imported"""
        from agent.browser_use_agent import BrowserUseAgent
        assert BrowserUseAgent is not None

    def test_state_capturer_import(self):
        """Test state capturer can be imported"""
        from agent.state_capturer import StateCapturer
        assert StateCapturer is not None

    def test_refinement_agent_import(self):
        """Test refinement agent can be imported"""
        from agent.refinement_agent import RefinementAgent
        assert RefinementAgent is not None


class TestHealthChecks:
    """Test application health endpoints"""

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        from app import app

        with app.test_client() as client:
            response = client.get('/api/health')

            assert response.status_code == 200, "Health check failed"

            data = response.get_json()
            assert data is not None, "No JSON response"
            assert data.get('status') == 'online', "Status not online"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Run tests if executed directly
if __name__ == "__main__":
    print("\n" + "="*80)
    print("FLOW PLANNER - DEPLOYMENT VERIFICATION TEST SUITE")
    print("="*80 + "\n")

    # Run pytest with verbose output
    exit_code = pytest.main([
        __file__,
        "-v",  # Verbose
        "--tb=short",  # Short traceback
        "--color=yes",  # Colored output
        "-s"  # Show print statements
    ])

    sys.exit(exit_code)
