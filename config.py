"""
Configuration management for the AI Workflow Capture System.
Loads all settings from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration class"""

    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

    # Flask Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'

    # Application Settings
    ENABLE_VALIDATION = os.getenv('ENABLE_VALIDATION', 'true').lower() == 'true'
    HEADLESS_BROWSER = os.getenv('HEADLESS_BROWSER', 'false').lower() == 'true'
    MAX_CONCURRENT_JOBS = int(os.getenv('MAX_CONCURRENT_JOBS', '3'))

    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
    SCREENSHOTS_DIR = os.path.join(BASE_DIR, 'static', 'screenshots')
    GUIDES_DIR = os.path.join(BASE_DIR, 'guides')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    DATABASE_PATH = os.path.join(BASE_DIR, 'workflows.db')

    # Browser Settings
    BROWSER_VIEWPORT_WIDTH = 1920
    BROWSER_VIEWPORT_HEIGHT = 1080
    BROWSER_TIMEOUT = 10000  # milliseconds
    USE_PERSISTENT_CONTEXT = os.getenv('USE_PERSISTENT_CONTEXT', 'false').lower() == 'true'
    # IMPORTANT: This should be the base "User Data" folder, NOT a specific profile
    # Playwright will automatically use the "Default" profile inside it
    # Examples:
    #   Chrome: C:\Users\USERNAME\AppData\Local\Google\Chrome\User Data
    #   Chromium: C:\Users\USERNAME\AppData\Local\Chromium\User Data
    #   Edge: C:\Users\USERNAME\AppData\Local\Microsoft\Edge\User Data
    BROWSER_USER_DATA_DIR = os.getenv('BROWSER_USER_DATA_DIR', r'C:\Users\prana\AppData\Local\Chromium\User Data')
    BROWSER_CHANNEL = os.getenv('BROWSER_CHANNEL', 'chromium')  # 'chrome', 'chromium', 'msedge', or None for default Chromium

    # Authentication Settings
    GOOGLE_ACCOUNT_EMAIL = os.getenv('GOOGLE_ACCOUNT_EMAIL', '')  # For OAuth detection
    AUTH_TIMEOUT = int(os.getenv('AUTH_TIMEOUT', '30000'))  # milliseconds - manual login timeout
    OAUTH_REDIRECT_TIMEOUT = int(os.getenv('OAUTH_REDIRECT_TIMEOUT', '15000'))  # milliseconds - OAuth redirect timeout

    # AI Model Settings
    GEMINI_MODEL = 'models/gemini-flash-lite-latest'
    CLAUDE_MODEL = 'claude-haiku-4-5-20251001'
    CLAUDE_VISION_MODEL = 'claude-haiku-4-5-20251001'  # For vision-guided execution (same as validator)
    GEMINI_TEMPERATURE = 0.3
    CLAUDE_MAX_TOKENS = 1024
    CLAUDE_VISION_MAX_TOKENS = 2048  # More tokens for vision decisions

    # Workflow Settings
    MAX_STEPS = 15
    SCREENSHOT_QUALITY = 80
    STEP_WAIT_TIME = 2000  # milliseconds between steps

    # Vision Loop Settings
    MAX_ACTIONS_PER_STEP = 10  # Prevent infinite loops within a step
    MAX_VISION_CALLS = 50  # Maximum total vision calls per workflow
    LOOP_DETECTION_THRESHOLD = 3  # Same action repeated this many times = loop
    SCREENSHOT_FULL_PAGE = False  # Just viewport by default (faster for vision)
    CAPTURE_ELEMENT_SCREENSHOTS = True  # Save both full + element screenshots

    # Ad Detection & Wait Times
    AD_WAIT_TIME = 5000  # milliseconds to wait when ad detected
    AD_KEYWORDS = ['advertisement', 'sponsored', 'ad', 'skip ad']  # Keywords for ad detection
    DYNAMIC_WAIT_TIME = 3000  # milliseconds to wait for dynamic content

    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        errors = []

        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is not set")

        if not cls.ANTHROPIC_API_KEY and cls.ENABLE_VALIDATION:
            errors.append("ANTHROPIC_API_KEY is required when ENABLE_VALIDATION is true")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

        return True

    @classmethod
    def ensure_directories(cls):
        """Create required directories if they don't exist"""
        os.makedirs(cls.SCREENSHOTS_DIR, exist_ok=True)
        os.makedirs(cls.GUIDES_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)

    @classmethod
    def get_next_run_dir(cls):
        """Get the next run directory (e.g., output/run1/, output/run2/, etc.)"""
        run_num = 1
        while os.path.exists(os.path.join(cls.OUTPUT_DIR, f'run{run_num}')):
            run_num += 1
        run_dir = os.path.join(cls.OUTPUT_DIR, f'run{run_num}')
        os.makedirs(run_dir, exist_ok=True)
        return run_dir, run_num
