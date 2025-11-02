"""Quick test to verify Browser-Use integration"""
import asyncio
import logging
from agent.planner import GeminiPlanner
from agent.browser_use_agent import BrowserUseAgent
from agent.state_capturer import StateCapturer
from config import Config
from utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

async def main():
    """Run a single quick test"""
    Config.validate()
    Config.ensure_directories()

    task = "Search for 'Machine Learning' on Wikipedia"
    app_url = "https://www.wikipedia.org"
    app_name = "Wikipedia"

    print(f"\n[TEST] Task: {task}")
    print(f"[TEST] URL: {app_url}\n")

    # Step 1: Plan
    print("[1/3] Planning...")
    planner = GeminiPlanner()
    plan = await planner.create_plan(task, app_url, app_name)
    print(f"[OK] Plan created with {len(plan['workflow_outline'])} steps")

    # Step 2: Execute
    print("\n[2/3] Executing with Browser-Use...")
    agent = BrowserUseAgent()
    states = await agent.execute_workflow(
        task=task,
        workflow_outline=plan['workflow_outline'],
        app_url=app_url,
        context=plan['context']
    )
    print(f"[OK] Execution complete: {len(states)} states")

    # Step 3: Capture
    print("\n[3/3] Capturing states...")
    capturer = StateCapturer()
    summary = await capturer.capture_states(
        states=states,
        task_name="quick_test",
        task_description=task
    )

    print(f"\n[SUCCESS] Test complete!")
    print(f"  Output: {summary['output_directory']}")
    print(f"  States: {summary['total_states']}")

if __name__ == "__main__":
    asyncio.run(main())
