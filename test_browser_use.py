"""
Test script for Browser-Use architecture end-to-end workflow.
Tests the complete pipeline: Planner → Browser-Use Agent → State Capture
"""
import asyncio
import logging
import sys
from agent.planner import GeminiPlanner
from agent.browser_use_agent import BrowserUseAgent
from agent.state_capturer import StateCapturer
from agent.authenticator import AuthenticationHandler
from config import Config
from utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


async def test_simple_navigation():
    """
    Test 1: Simple navigation without authentication.
    Navigate to a public page and capture states.
    """
    print("\n" + "="*80)
    print("TEST 1: Simple Navigation (No Auth)")
    print("="*80 + "\n")

    try:
        # Test case
        task = "Navigate to Wikipedia homepage and search for 'Python programming'"
        app_url = "https://www.wikipedia.org"
        app_name = "Wikipedia"

        # Step 1: Create plan with Gemini
        print("[1/4] Creating plan with Gemini...")
        planner = GeminiPlanner()
        plan = await planner.create_plan(task, app_url, app_name)

        print(f"\n[OK] Plan created:")
        print(f"  - Auth required: {plan['task_analysis']['requires_authentication']}")
        print(f"  - Auth type: {plan['task_analysis']['auth_type']}")
        print(f"  - Workflow steps: {len(plan['workflow_outline'])}")
        print(f"  - Complexity: {plan['task_analysis']['complexity']}")

        for i, step in enumerate(plan['workflow_outline'], 1):
            print(f"    {i}. {step}")

        # Step 2: Execute with Browser-Use agent
        print(f"\n[2/4] Executing workflow with Browser-Use agent...")
        browser_agent = BrowserUseAgent()
        states = await browser_agent.execute_workflow(
            task=task,
            workflow_outline=plan['workflow_outline'],
            app_url=app_url,
            context=plan['context']
        )

        print(f"\n[OK] Workflow executed: {len(states)} states captured")

        # Step 3: Capture and save states
        print(f"\n[3/4] Saving states to disk...")
        capturer = StateCapturer()
        summary = await capturer.capture_states(
            states=states,
            task_name="wikipedia_search_test",
            task_description=task
        )

        print(f"\n[OK] States saved:")
        print(f"  - Output directory: {summary['output_directory']}")
        print(f"  - Total states: {summary['total_states']}")
        print(f"  - Metadata: {summary['metadata_path']}")

        # Step 4: Generate guide
        print(f"\n[4/4] Generating workflow guide...")
        guide_path = await capturer.generate_guide(summary['metadata_path'])

        print(f"\n[OK] Guide generated: {guide_path}")

        print("\n" + "="*80)
        print("[OK] TEST 1 PASSED")
        print("="*80 + "\n")

        return True

    except Exception as e:
        print(f"\n[FAIL] TEST 1 FAILED: {str(e)}")
        logger.error("Test 1 failed", exc_info=True)
        return False


async def test_with_authentication():
    """
    Test 2: Workflow requiring authentication.
    Tests the 3-tier authentication strategy.
    """
    print("\n" + "="*80)
    print("TEST 2: Workflow with Authentication")
    print("="*80 + "\n")

    try:
        # Test case - adjust based on your credentials
        task = "Create a new repository on GitHub"
        app_url = "https://github.com"
        app_name = "GitHub"

        # Step 1: Create plan
        print("[1/4] Creating plan with Gemini...")
        planner = GeminiPlanner()
        plan = await planner.create_plan(task, app_url, app_name)

        print(f"\n[OK] Plan created:")
        print(f"  - Auth required: {plan['task_analysis']['requires_authentication']}")
        print(f"  - Auth type: {plan['task_analysis']['auth_type']}")
        print(f"  - Workflow steps: {len(plan['workflow_outline'])}")

        # Step 2: Execute with authentication
        print(f"\n[2/4] Executing workflow with authentication...")
        browser_agent = BrowserUseAgent()
        auth_handler = AuthenticationHandler()

        states = await browser_agent.execute_with_authentication(
            task=task,
            workflow_outline=plan['workflow_outline'],
            app_url=app_url,
            context=plan['context'],
            auth_handler=auth_handler,
            requires_auth=plan['task_analysis']['requires_authentication'],
            auth_type=plan['task_analysis']['auth_type']
        )

        print(f"\n[OK] Workflow executed: {len(states)} states captured")

        # Step 3: Save states
        print(f"\n[3/4] Saving states...")
        capturer = StateCapturer()
        summary = await capturer.capture_states(
            states=states,
            task_name="github_create_repo_test",
            task_description=task
        )

        print(f"\n[OK] States saved: {summary['output_directory']}")

        # Step 4: Generate guide
        print(f"\n[4/4] Generating guide...")
        guide_path = await capturer.generate_guide(summary['metadata_path'])

        print(f"\n[OK] Guide generated: {guide_path}")

        print("\n" + "="*80)
        print("[OK] TEST 2 PASSED")
        print("="*80 + "\n")

        return True

    except Exception as e:
        print(f"\n[FAIL] TEST 2 FAILED: {str(e)}")
        logger.error("Test 2 failed", exc_info=True)
        return False


async def test_planner_only():
    """
    Test 3: Test planner in isolation.
    Verify auth detection and workflow outline generation.
    """
    print("\n" + "="*80)
    print("TEST 3: Planner Only (Auth Detection)")
    print("="*80 + "\n")

    test_cases = [
        {
            'task': 'View trending videos on YouTube',
            'app_url': 'https://www.youtube.com',
            'app_name': 'YouTube',
            'expected_auth': False
        },
        {
            'task': 'Create a new project in Linear',
            'app_url': 'https://linear.app',
            'app_name': 'Linear',
            'expected_auth': True
        },
        {
            'task': 'Search for Python documentation',
            'app_url': 'https://www.google.com',
            'app_name': 'Google',
            'expected_auth': False
        }
    ]

    planner = GeminiPlanner()
    passed = 0
    failed = 0

    for i, test_case in enumerate(test_cases, 1):
        try:
            print(f"\n[Test {i}/{len(test_cases)}] {test_case['task']}")

            plan = await planner.create_plan(
                task=test_case['task'],
                app_url=test_case['app_url'],
                app_name=test_case['app_name']
            )

            requires_auth = plan['task_analysis']['requires_authentication']
            auth_type = plan['task_analysis']['auth_type']

            print(f"  [OK] Auth required: {requires_auth} (expected: {test_case['expected_auth']})")
            print(f"  [OK] Auth type: {auth_type}")
            print(f"  [OK] Workflow steps: {len(plan['workflow_outline'])}")
            print(f"  [OK] Complexity: {plan['task_analysis']['complexity']}")

            passed += 1

        except Exception as e:
            print(f"  [FAIL] Failed: {str(e)}")
            failed += 1

    print("\n" + "="*80)
    print(f"TEST 3 RESULTS: {passed} passed, {failed} failed")
    print("="*80 + "\n")

    return failed == 0


async def run_all_tests():
    """Run all tests sequentially"""
    print("\n" + "="*80)
    print("BROWSER-USE ARCHITECTURE TEST SUITE")
    print("="*80)

    # Validate configuration
    print("\nValidating configuration...")
    try:
        Config.validate()
        Config.ensure_directories()
        print("[OK] Configuration valid")
    except Exception as e:
        print(f"[FAIL] Configuration error: {str(e)}")
        return

    # Run tests
    results = []

    # Test 1: Simple navigation (no auth)
    result1 = await test_simple_navigation()
    results.append(("Simple Navigation", result1))

    # Test 2: Planner only (multiple cases)
    result2 = await test_planner_only()
    results.append(("Planner Auth Detection", result2))

    # Test 3: With authentication (commented out by default - requires credentials)
    # Uncomment when ready to test with real credentials
    # result3 = await test_with_authentication()
    # results.append(("Authentication Flow", result3))

    # Summary
    print("\n" + "="*80)
    print("TEST SUITE SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "[OK] PASSED" if passed else "[FAIL] FAILED"
        print(f"{test_name}: {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed")

    print("="*80 + "\n")


if __name__ == "__main__":
    print("""
================================================================================
                    FlowForge Browser-Use Architecture
                              Test Suite v1.0
================================================================================
""")

    # Run tests
    asyncio.run(run_all_tests())
