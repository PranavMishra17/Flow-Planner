"""
Run workflow capture with predefined or custom tasks.
Quick test script for Browser-Use architecture.
"""
import asyncio
import logging
import sys
from agent.planner import GeminiPlanner
from agent.browser_use_agent import BrowserUseAgent
from agent.state_capturer import StateCapturer
from agent.refinement_agent import RefinementAgent
from utils.markdown_visualizer import MarkdownVisualizer
from config import Config
from utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

PREDEFINED_TASKS = [
    {
        "task": "Search for 'Machine Learning' on Wikipedia, return first article",
        "app_url": "https://www.wikipedia.org",
        "app_name": "Wikipedia"
    },
    {
        "task": "Create a note page on Notion",
        "app_url": "https://www.notion.so",
        "app_name": "Notion"
    },
    {
        "task": "Create a project on Linear",
        "app_url": "https://linear.app",
        "app_name": "Linear"
    }
]


async def run_workflow(task: str, app_url: str = None, app_name: str = None):
    """Execute a single workflow capture"""
    print("\n" + "="*80)
    print(f"TASK: {task}")
    if app_name and app_url:
        print(f"APP: {app_name} ({app_url})")
    elif app_name:
        print(f"APP: {app_name}")
    elif app_url:
        print(f"URL: {app_url}")
    else:
        print("APP: Will be inferred from task")
    print("="*80)

    try:
        # Step 1: Create plan (planner will infer app details if not provided)
        print("\n[1/4] Planning workflow with Gemini...")
        planner = GeminiPlanner()
        plan = await planner.create_plan(task, app_url, app_name)

        # Extract the actual app_url and app_name from the plan context
        inferred_url = plan.get('context', {}).get('app_url', app_url or 'https://example.com')
        inferred_name = plan.get('context', {}).get('app_name', app_name or 'Application')

        # Show if details were inferred
        if not app_url or not app_name:
            print(f"[INFO] Application inferred: {inferred_name} ({inferred_url})")

        app_url = inferred_url
        app_name = inferred_name

        print(f"[OK] Plan created:")
        print(f"  - Auth required: {plan['task_analysis']['requires_authentication']}")
        print(f"  - Steps: {len(plan['workflow_outline'])}")
        print(f"  - Complexity: {plan['task_analysis']['complexity']}")

        # Step 2: Execute workflow
        print(f"\n[2/4] Executing workflow with Browser-Use agent...")
        agent = BrowserUseAgent()
        states = await agent.execute_workflow(
            task=task,
            workflow_outline=plan['workflow_outline'],
            app_url=app_url,
            context=plan['context']
        )

        print(f"[OK] Workflow executed: {len(states)} states captured")

        # Step 3: Save results
        print(f"\n[3/4] Saving workflow data...")
        capturer = StateCapturer()
        task_name = app_name.lower().replace(" ", "_")
        summary = await capturer.capture_states(
            states=states,
            task_name=task_name,
            task_description=task
        )

        print(f"[OK] States saved: {summary['total_states']}")

        # Step 4: Generate AI-powered guide
        print(f"\n[4/4] Generating workflow guide with Gemini...")
        try:
            guide_path = await capturer.generate_guide(
                metadata_path=summary['metadata_path'],
                task_description=task
            )
            print(f"[OK] Workflow guide generated!")
        except Exception as e:
            print(f"[WARN] Guide generation failed: {str(e)}")
            guide_path = None

        print(f"\n[SUCCESS] Workflow captured successfully!")
        print(f"  - Output: {summary['output_directory']}")
        print(f"  - States: {summary['total_states']}")
        print(f"  - Metadata: {summary['metadata_path']}")
        if guide_path:
            print(f"  - Guide: {guide_path}")

        # Step 5: Optional refinement with Vision AI
        refined_guide_path = None
        if Config.ENABLE_REFINEMENT and guide_path:
            print(f"\n[OPTIONAL] Refine workflow with Vision AI? (y/n): ", end='')
            response = input().strip().lower()

            if response == 'y':
                print(f"\n[5/6] Refining workflow with Vision AI...")
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

                        print(f"[OK] Workflow refined!")
                        print(f"  - Refined steps: {refined_count}/{total_count}")
                        print(f"  - Enhanced guide: {refinement_result['refined_guide_path']}")
                        print(f"  - Refinement metadata: {refinement_result['refinement_metadata_path']}")

                        # Use refined guide for visualization
                        refined_guide_path = refinement_result['refined_guide_path']
                    else:
                        print(f"[WARN] Refinement failed: {refinement_result.get('message', 'Unknown error')}")

                except Exception as e:
                    print(f"[WARN] Refinement failed: {str(e)}")
                    logger.error("Refinement failed", exc_info=True)
            else:
                print("[INFO] Skipping refinement")

        # Step 6: Optional guide visualization and PDF export
        if Config.ENABLE_VISUALIZATION and guide_path:
            # Use refined guide if available, otherwise use original
            guide_to_visualize = refined_guide_path if refined_guide_path else guide_path

            print(f"\n[OPTIONAL] Visualize workflow guide in browser? (y/n): ", end='')
            viz_response = input().strip().lower()

            if viz_response == 'y':
                print(f"\n[6/6] Preparing guide visualization...")
                try:
                    visualizer = MarkdownVisualizer(
                        host=Config.VISUALIZATION_HOST,
                        port=Config.VISUALIZATION_PORT
                    )

                    # Generate HTML and open in browser
                    success = visualizer.preview_in_browser(guide_to_visualize, cleanup_html=False)

                    if not success:
                        print(f"[WARN] Visualization failed")

                except Exception as e:
                    print(f"[WARN] Visualization failed: {str(e)}")
                    logger.error("Visualization failed", exc_info=True)
            else:
                print("[INFO] Skipping visualization")

        return True

    except Exception as e:
        print(f"\n[FAIL] Workflow failed: {str(e)}")
        logger.error("Workflow execution failed", exc_info=True)
        return False


async def run_predefined():
    """Run all predefined test cases"""
    print("""
================================================================================
                    FlowForge - Predefined Workflow Tests
================================================================================
""")

    results = []
    for i, test in enumerate(PREDEFINED_TASKS, 1):
        print(f"\n[Test {i}/{len(PREDEFINED_TASKS)}]")
        success = await run_workflow(
            task=test["task"],
            app_url=test["app_url"],
            app_name=test["app_name"]
        )
        results.append((test["app_name"], success))

        if i < len(PREDEFINED_TASKS):
            print("\nWaiting 5 seconds before next test...")
            await asyncio.sleep(5)

    # Summary
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    for app_name, success in results:
        status = "[OK] PASSED" if success else "[FAIL] FAILED"
        print(f"{app_name}: {status}")

    passed = sum(1 for _, s in results if s)
    print(f"\nTotal: {passed}/{len(results)} tests passed")


async def run_custom():
    """Run custom workflow from user input"""
    print("""
================================================================================
                    FlowForge - Custom Workflow Capture
================================================================================
""")

    task = input("\nEnter task description: ").strip()
    if not task:
        print("[FAIL] Task description is required")
        return

    app_url = input("Enter application URL (press Enter to skip): ").strip()
    app_name = input("Enter application name (press Enter to skip): ").strip()

    # If URL or name not provided, they will be inferred by the planner
    if not app_url:
        app_url = None
    if not app_name:
        app_name = None

    await run_workflow(task, app_url, app_name)


async def main():
    """Main entry point"""
    # Validate config
    try:
        Config.validate()
        Config.ensure_directories()
    except Exception as e:
        print(f"[FAIL] Configuration error: {str(e)}")
        return

    # Check arguments
    if "--predefined" in sys.argv or "-p" in sys.argv:
        await run_predefined()
    else:
        await run_custom()


if __name__ == "__main__":
    print("""
================================================================================
                         FlowForge Workflow Capture
                          Browser-Use Architecture
================================================================================

Usage:
  python run_workflow.py              Run custom workflow (interactive)
  python run_workflow.py --predefined Run predefined test cases
  python run_workflow.py -p           Run predefined test cases (short)

Interactive Mode:
  - Task description: REQUIRED
  - Application URL: Optional (will be inferred if not provided)
  - Application name: Optional (will be inferred if not provided)

Example: "add a new task in Asana, 'Buy groceries'"
  The system will automatically detect Asana and navigate to app.asana.com

================================================================================
""")

    asyncio.run(main())
