"""
Quick verification script to check Browser-Use setup.
Run this to verify all components are properly installed and configured.
"""
import sys

def check_imports():
    """Check if all required packages are installed"""
    print("Checking package imports...")
    errors = []

    try:
        import google.generativeai as genai
        print("  [OK] google-generativeai")
    except ImportError as e:
        errors.append(f"  [FAIL] google-generativeai: {str(e)}")

    try:
        from anthropic import Anthropic
        print("  [OK] anthropic")
    except ImportError as e:
        errors.append(f"  [FAIL] anthropic: {str(e)}")

    try:
        from browser_use import Agent, Browser
        print("  [OK] browser-use")
    except ImportError as e:
        errors.append(f"  [FAIL] browser-use: {str(e)}")

    try:
        from langchain_anthropic import ChatAnthropic
        print("  [OK] langchain-anthropic")
    except ImportError as e:
        errors.append(f"  [FAIL] langchain-anthropic: {str(e)}")

    try:
        from playwright.async_api import async_playwright
        print("  [OK] playwright")
    except ImportError as e:
        errors.append(f"  [FAIL] playwright: {str(e)}")

    try:
        from PIL import Image
        print("  [OK] Pillow")
    except ImportError as e:
        errors.append(f"  [FAIL] Pillow: {str(e)}")

    if errors:
        print("\nImport Errors:")
        for error in errors:
            print(error)
        return False
    else:
        print("\n[OK] All packages imported successfully!")
        return True


def check_config():
    """Check if configuration is valid"""
    print("\nChecking configuration...")

    try:
        from config import Config

        # Check API keys
        if not Config.GEMINI_API_KEY:
            print("  [FAIL] GEMINI_API_KEY not set")
            return False
        else:
            print(f"  [OK] GEMINI_API_KEY set (starts with: {Config.GEMINI_API_KEY[:10]}...)")

        if not Config.ANTHROPIC_API_KEY:
            print("  [FAIL] ANTHROPIC_API_KEY not set (REQUIRED for Browser-Use)")
            return False
        else:
            print(f"  [OK] ANTHROPIC_API_KEY set (starts with: {Config.ANTHROPIC_API_KEY[:10]}...)")

        # Check Browser-Use settings
        print(f"  [OK] BROWSER_USE_MAX_STEPS: {Config.BROWSER_USE_MAX_STEPS}")
        print(f"  [OK] BROWSER_USE_LLM_MODEL: {Config.BROWSER_USE_LLM_MODEL}")

        # Check authentication settings
        if Config.DEFAULT_EMAIL:
            print(f"  [OK] DEFAULT_EMAIL set: {Config.DEFAULT_EMAIL}")
        else:
            print("  [WARN] DEFAULT_EMAIL not set (Tier 2 auto-login disabled)")

        if Config.DEFAULT_PASSWORD:
            print(f"  [OK] DEFAULT_PASSWORD set (hidden)")
        else:
            print("  [WARN] DEFAULT_PASSWORD not set (Tier 2 auto-login disabled)")

        # Check browser settings
        print(f"  [OK] USE_PERSISTENT_CONTEXT: {Config.USE_PERSISTENT_CONTEXT}")
        print(f"  [OK] BROWSER_USER_DATA_DIR: {Config.BROWSER_USER_DATA_DIR}")
        print(f"  [OK] HEADLESS_BROWSER: {Config.HEADLESS_BROWSER}")

        # Validate config
        try:
            Config.validate()
            print("\n[OK] Configuration valid!")
            return True
        except Exception as e:
            print(f"\n[FAIL] Configuration validation failed: {str(e)}")
            return False

    except Exception as e:
        print(f"  [FAIL] Error loading config: {str(e)}")
        return False


def check_agent_files():
    """Check if all agent files exist"""
    print("\nChecking agent files...")

    import os

    files_to_check = [
        'agent/planner.py',
        'agent/browser_use_agent.py',
        'agent/state_capturer.py',
        'agent/authenticator.py',
        'config.py',
        'test_browser_use.py',
        'BROWSER_USE_IMPLEMENTATION.md'
    ]

    all_exist = True
    for file in files_to_check:
        if os.path.exists(file):
            print(f"  [OK] {file}")
        else:
            print(f"  [FAIL] {file} NOT FOUND")
            all_exist = False

    if all_exist:
        print("\n[OK] All files present!")
    else:
        print("\n[FAIL] Some files are missing")

    return all_exist


def check_directories():
    """Check if output directories exist"""
    print("\nChecking directories...")

    try:
        from config import Config
        Config.ensure_directories()

        import os
        dirs = [
            Config.OUTPUT_DIR,
            Config.SCREENSHOTS_DIR,
            Config.LOGS_DIR
        ]

        for dir_path in dirs:
            if os.path.exists(dir_path):
                print(f"  [OK] {dir_path}")
            else:
                print(f"  [WARN] {dir_path} (will be created)")

        print("\n[OK] Directories ready!")
        return True

    except Exception as e:
        print(f"  [FAIL] Error checking directories: {str(e)}")
        return False


def main():
    """Run all verification checks"""
    print("""
================================================================================
                    FlowForge Browser-Use Setup Verification
================================================================================
""")

    results = []

    # Run checks
    results.append(("Package Imports", check_imports()))
    results.append(("Configuration", check_config()))
    results.append(("Agent Files", check_agent_files()))
    results.append(("Directories", check_directories()))

    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)

    all_passed = True
    for check_name, passed in results:
        status = "[OK] PASSED" if passed else "[FAIL] FAILED"
        print(f"{check_name}: {status}")
        if not passed:
            all_passed = False

    print("="*80)

    if all_passed:
        print("\n[SUCCESS] Setup verification successful!")
        print("\nNext steps:")
        print("1. Run: python test_browser_use.py")
        print("2. Check BROWSER_USE_IMPLEMENTATION.md for usage guide")
        print("3. Start with Test 3 (Planner Only) for quick validation")
    else:
        print("\n[WARNING] Some checks failed. Please review the errors above.")
        print("\nCommon fixes:")
        print("1. Run: pip install -r requirements.txt")
        print("2. Check .env file has all required API keys")
        print("3. Ensure all agent files are present")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
