"""
Test Flask setup - verify all dependencies and files
Run this before starting the Flask app
"""
import os
import sys

def test_imports():
    """Test that all required imports are available"""
    print("Testing imports...")

    try:
        import flask
        print("  [OK] flask")
    except ImportError:
        print("  [FAIL] flask - Run: pip install flask")
        return False

    try:
        import flask_socketio
        print("  [OK] flask-socketio")
    except ImportError:
        print("  [FAIL] flask-socketio - Run: pip install flask-socketio")
        return False

    try:
        import flask_cors
        print("  [OK] flask-cors")
    except ImportError:
        print("  [FAIL] flask-cors - Run: pip install flask-cors")
        return False

    try:
        import engineio
        print("  [OK] python-engineio")
    except ImportError:
        print("  [FAIL] python-engineio - Run: pip install python-engineio")
        return False

    try:
        import socketio
        print("  [OK] python-socketio")
    except ImportError:
        print("  [FAIL] python-socketio - Run: pip install python-socketio")
        return False

    return True


def test_files():
    """Test that all required files exist"""
    print("\nTesting file structure...")

    required_files = [
        'app.py',
        'routes/workflows.py',
        'jobs/workflow_runner.py',
        'templates/index.html',
        'static/css/style.css',
        'static/js/app.js',
        'config.py'
    ]

    all_exist = True
    for filepath in required_files:
        if os.path.exists(filepath):
            print(f"  [OK] {filepath}")
        else:
            print(f"  [FAIL] {filepath} - MISSING!")
            all_exist = False

    return all_exist


def test_directories():
    """Test that required directories exist"""
    print("\nTesting directories...")

    required_dirs = [
        'templates',
        'static/css',
        'static/js',
        'static/images',
        'routes',
        'jobs'
    ]

    all_exist = True
    for dirpath in required_dirs:
        if os.path.isdir(dirpath):
            print(f"  [OK] {dirpath}/")
        else:
            print(f"  [FAIL] {dirpath}/ - MISSING!")
            all_exist = False

    return all_exist


def test_config():
    """Test configuration"""
    print("\nTesting configuration...")

    try:
        from config import Config

        if Config.GEMINI_API_KEY:
            print("  [OK] GEMINI_API_KEY is set")
        else:
            print("  [WARN] GEMINI_API_KEY not set")

        if Config.ANTHROPIC_API_KEY:
            print("  [OK] ANTHROPIC_API_KEY is set")
        else:
            print("  [WARN] ANTHROPIC_API_KEY not set")

        print(f"  [OK] SECRET_KEY: {Config.SECRET_KEY[:10]}...")
        print(f"  [OK] DEBUG: {Config.DEBUG}")

        return True

    except Exception as e:
        print(f"  [FAIL] Config error: {e}")
        return False


def test_portfolio_image():
    """Check if portfolio image exists"""
    print("\nChecking portfolio image...")

    if os.path.exists('static/images/me.png'):
        print("  [OK] static/images/me.png exists")
    else:
        print("  [WARN] static/images/me.png not found")
        print("    Add your portfolio image to: static/images/me.png")
        print("    (The app will still work, but the button will show a broken image)")


def main():
    """Run all tests"""
    print("="*60)
    print("FLOW PLANNER - FLASK SETUP TEST")
    print("="*60)
    print()

    results = {
        'imports': test_imports(),
        'files': test_files(),
        'directories': test_directories(),
        'config': test_config()
    }

    test_portfolio_image()

    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)

    all_passed = all(results.values())

    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{test_name.upper()}: {status}")

    print("="*60)

    if all_passed:
        print("\n[PASS] All tests passed! Ready to start Flask app.")
        print("\nRun: python app.py")
        print("Then open: http://localhost:5000")
    else:
        print("\n[FAIL] Some tests failed. Fix issues above before starting.")
        print("\nInstall missing packages:")
        print("  pip install -r requirements.txt")

    print()
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
