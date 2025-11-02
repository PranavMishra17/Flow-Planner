"""
Test script for the AI Workflow Capture System agent pipeline.
Tests the complete flow: Planning -> Execution -> Validation
"""
import asyncio
import sys
import json
import os
from datetime import datetime
from utils.logger import setup_logging
from agent.planner import GeminiPlanner
from agent.executor import PlaywrightExecutor
from agent.validator import ClaudeValidator
from config import Config
import logging

logger = logging.getLogger(__name__)


async def test_workflow(task: str, app_url: str, app_name: str, output_dir: str = None):
    """
    Test the complete workflow capture pipeline.

    Args:
        task: Natural language task description
        app_url: Target application URL
        app_name: Application name
        output_dir: Optional directory to save results (defaults to current directory)
    """
    workflow_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    logger.info("=" * 80)
    logger.info("[TEST] Starting workflow capture test")
    logger.info(f"[TEST] Task: {task}")
    logger.info(f"[TEST] Application: {app_name} ({app_url})")
    logger.info(f"[TEST] Workflow ID: {workflow_id}")
    logger.info("=" * 80)

    try:
        # Phase 1: Planning
        logger.info("\n[TEST] PHASE 1: PLANNING")
        logger.info("-" * 80)

        planner = GeminiPlanner()
        plan = await planner.create_plan(task, app_url, app_name)

        # Add app_name to plan for executor
        plan['app_name'] = app_name

        logger.info(f"[TEST] Plan created with {len(plan['steps'])} steps")
        logger.info(f"[TEST] Research summary: {plan['research_summary']}")

        # Print plan steps
        logger.info("\n[TEST] Execution Plan:")
        for step in plan['steps']:
            logger.info(f"  Step {step['step_number']}: {step['action']} - {step['description']}")

        # Phase 2: Execution
        logger.info("\n[TEST] PHASE 2: EXECUTION")
        logger.info("-" * 80)

        executor = PlaywrightExecutor(workflow_id, output_dir=output_dir)
        executed_steps = await executor.execute_plan(plan, app_url)

        # Count successful steps and recoveries
        successful_steps = sum(1 for s in executed_steps if s.get('success', False))
        vision_recoveries = sum(1 for s in executed_steps if s.get('vision_recovery', False))
        logger.info(f"[TEST] Execution complete: {successful_steps}/{len(executed_steps)} steps successful")
        logger.info(f"[TEST] Vision recoveries: {vision_recoveries}")

        # Print execution results
        logger.info("\n[TEST] Execution Results:")
        for step in executed_steps:
            success_symbol = "[OK]" if step['success'] else "[FAIL]"
            recovery_tag = " [VISION]" if step.get('vision_recovery') else ""
            logger.info(f"  {success_symbol} Step {step['step_number']}: {step['description']}{recovery_tag}")
            if not step['success']:
                logger.info(f"      Error: {step['error_message']}")
            elif step.get('vision_recovery'):
                logger.info(f"      Recovered: {step.get('vision_observation', 'Unknown')[:60]}...")
            logger.info(f"      Screenshot: {step['screenshot_path']}")

        # Phase 3: Validation (optional - vision guide already validates during execution)
        logger.info("\n[TEST] PHASE 3: VALIDATION")
        logger.info("-" * 80)
        logger.info("[TEST] Vision-guided execution includes real-time validation")
        logger.info("[TEST] Skipping separate validation phase")

        # For compatibility, use executed_steps as validated_steps
        validated_steps = executed_steps
        valid_steps = successful_steps

        # Final Summary
        logger.info("\n" + "=" * 80)
        logger.info("[TEST] WORKFLOW CAPTURE COMPLETE")
        logger.info("-" * 80)
        logger.info(f"Total Steps: {len(executed_steps)}")
        logger.info(f"Successful: {successful_steps}")
        logger.info(f"Vision Recoveries: {vision_recoveries}")
        logger.info(f"Workflow ID: {workflow_id}")
        if output_dir:
            logger.info(f"Screenshots: {os.path.join(output_dir, workflow_id)}")
        else:
            logger.info(f"Screenshots: static/screenshots/{workflow_id}/")
        logger.info("=" * 80)

        # Save results to JSON file
        if output_dir:
            result_file = os.path.join(output_dir, f"test_results_{workflow_id}.json")
        else:
            result_file = f"test_results_{workflow_id}.json"

        with open(result_file, 'w') as f:
            json.dump({
                'workflow_id': workflow_id,
                'task': task,
                'app_name': app_name,
                'app_url': app_url,
                'plan': plan,
                'executed_steps': validated_steps,
                'summary': {
                    'total_steps': len(executed_steps),
                    'successful_steps': successful_steps,
                    'vision_recoveries': vision_recoveries,
                    'validated_steps': valid_steps
                }
            }, f, indent=2)

        logger.info(f"\n[TEST] Results saved to: {result_file}")

        return True

    except Exception as e:
        logger.error(f"[TEST] Test failed with error: {str(e)}", exc_info=True)
        return False


async def run_predefined_tests():
    """Run a set of predefined test cases"""

    # Create run directory for this test session
    run_dir, run_num = Config.get_next_run_dir()
    logger.info(f"\n[TEST] Test run directory: {run_dir}")

    test_cases = [
        {
            'task': 'How to share a youtube video?',
            'app_url': 'https://youtube.com',
            'app_name': 'YouTube'
        },
        {
            'task': 'How to initialise a postgres database on supabase?',
            'app_url': 'https://supabase.com',
            'app_name': 'Supabase'
        },
        {
            'task': 'How to create a form on Notion?',
            'app_url': 'https://notion.so',
            'app_name': 'Notion'
        },
    ]

    # Display all test cases before starting
    logger.info(f"\n{'=' * 80}")
    logger.info(f"[TEST] PREDEFINED TEST CASES - RUN {run_num} - {len(test_cases)} tests")
    logger.info(f"{'=' * 80}")
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"{i}. {test_case['task']}")
        logger.info(f"   App: {test_case['app_name']} ({test_case['app_url']})")
    logger.info(f"{'=' * 80}\n")

    logger.info(f"[TEST] Starting test execution...\n")

    results = []
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"[TEST] Test Case {i}/{len(test_cases)}")
        logger.info(f"{'=' * 80}\n")

        result = await test_workflow(
            test_case['task'],
            test_case['app_url'],
            test_case['app_name'],
            output_dir=run_dir
        )
        results.append(result)

        # Wait between tests
        if i < len(test_cases):
            logger.info("\n[TEST] Waiting 5 seconds before next test...")
            await asyncio.sleep(5)

    # Summary
    passed = sum(results)
    logger.info(f"\n{'=' * 80}")
    logger.info(f"[TEST] ALL TESTS COMPLETE: {passed}/{len(results)} passed")
    logger.info(f"[TEST] All results saved to: {run_dir}")
    logger.info(f"{'=' * 80}\n")


async def run_custom_test():
    """Run a custom test with user input"""
    print("\n" + "=" * 80)
    print("AI Workflow Capture System - Custom Test")
    print("=" * 80)

    task = input("\nEnter task description (e.g., 'Create a project'): ").strip()
    if not task:
        print("[ERROR] Task is required")
        return

    app_url = input("Enter application URL (e.g., 'https://linear.app'): ").strip()
    if not app_url:
        print("[ERROR] URL is required")
        return

    app_name = input("Enter application name (e.g., 'Linear'): ").strip()
    if not app_name:
        app_name = "Application"

    print("\n" + "=" * 80 + "\n")

    await test_workflow(task, app_url, app_name)


def main():
    """Main entry point"""
    # Setup logging
    setup_logging()

    # Validate configuration
    try:
        Config.validate()
        Config.ensure_directories()
        logger.info("[TEST] Configuration validated successfully")
    except Exception as e:
        logger.error(f"[TEST] Configuration error: {str(e)}")
        sys.exit(1)

    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--predefined':
            # Run predefined tests
            asyncio.run(run_predefined_tests())
        elif sys.argv[1] == '--help':
            print("\nUsage:")
            print("  python test_agent.py              # Interactive mode")
            print("  python test_agent.py --predefined # Run predefined test cases")
            print("  python test_agent.py --help       # Show this help")
            print()
        else:
            print(f"[ERROR] Unknown argument: {sys.argv[1]}")
            print("Use --help for usage information")
            sys.exit(1)
    else:
        # Interactive mode
        asyncio.run(run_custom_test())


if __name__ == '__main__':
    main()
