"""
Playwright-based workflow executor with vision-guided execution.
Uses Claude Vision to dynamically decide actions based on screenshots.
"""
import logging
import asyncio
import os
from typing import Dict, List, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
from config import Config
from agent.authenticator import AuthenticationHandler, AuthenticationError
from agent.vision_guide import VisionGuide

logger = logging.getLogger(__name__)


class PlaywrightExecutor:
    """
    Browser automation executor using Playwright.
    Executes workflow steps and captures screenshots.
    """

    def __init__(self, workflow_id: str, output_dir: str = None):
        """
        Initialize Playwright executor.

        Args:
            workflow_id: Unique identifier for this workflow execution
            output_dir: Optional output directory for screenshots (defaults to static/screenshots)
        """
        self.workflow_id = workflow_id
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None

        # Create screenshots directory for this workflow
        if output_dir:
            # Use output directory for test runs
            self.screenshot_dir = os.path.join(output_dir, workflow_id)
        else:
            # Use default static directory for API runs
            self.screenshot_dir = os.path.join(Config.SCREENSHOTS_DIR, workflow_id)

        os.makedirs(self.screenshot_dir, exist_ok=True)

        logger.info(f"[EXECUTOR] Initialized for workflow {workflow_id}")
        logger.info(f"[EXECUTOR] Screenshots will be saved to: {self.screenshot_dir}")

    async def execute_plan(
        self,
        plan: Dict,
        start_url: str
    ) -> List[Dict]:
        """
        Execute workflow plan with vision-based error recovery.

        Args:
            plan: Plan from GeminiPlanner with steps
            start_url: Starting URL for the workflow

        Returns:
            List of executed steps with screenshots and metadata

        Raises:
            Exception: If execution fails critically
        """
        steps = plan['steps']
        app_name = plan.get('app_name', 'Application')

        logger.info(f"[EXECUTOR] Starting execution of {len(steps)} steps from Gemini")
        logger.info(f"[EXECUTOR] Will use vision for error recovery if needed")

        # Initialize vision guide (for error recovery)
        vision_guide = VisionGuide()

        # Initialize execution state
        executed_steps = []
        vision_recovery_count = 0

        try:
            # Launch browser
            await self._launch_browser()

            # Navigate to start URL
            logger.info(f"[EXECUTOR] Navigating to {start_url}")
            await self.page.goto(start_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)  # Wait for page to settle

            # Handle authentication
            auth_attempted = await self._handle_authentication(app_name)

            # Execute each step from Gemini
            for step in steps:
                step_number = step['step_number']
                logger.info(f"[EXECUTOR] Executing step {step_number}/{len(steps)}: {step['description']}")

                try:
                    # Skip first goto if we already navigated
                    if step['action'] == 'goto' and step_number == 1:
                        logger.info(f"[EXECUTOR] Skipping step {step_number} (already navigated)")
                        screenshot_path = await self._capture_screenshot(step_number)

                        executed_step = {
                            'step_number': step_number,
                            'description': step['description'],
                            'action': step['action'],
                            'screenshot_path': screenshot_path,
                            'url': self.page.url,
                            'success': True,
                            'error_message': None,
                            'vision_recovery': False,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        executed_steps.append(executed_step)
                        continue

                    # Try to execute the step with fallback selectors
                    await self._execute_step_with_fallback(step)

                    # Wait for UI to settle
                    await asyncio.sleep(Config.STEP_WAIT_TIME / 1000)

                    # Capture screenshot
                    screenshot_path = await self._capture_screenshot(step_number)

                    # Record successful step
                    executed_step = {
                        'step_number': step_number,
                        'description': step['description'],
                        'action': step['action'],
                        'screenshot_path': screenshot_path,
                        'url': self.page.url,
                        'success': True,
                        'error_message': None,
                        'vision_recovery': False,
                        'timestamp': datetime.utcnow().isoformat()
                    }

                    executed_steps.append(executed_step)
                    logger.info(f"[EXECUTOR] Step {step_number} completed successfully")

                except Exception as e:
                    logger.error(f"[EXECUTOR] Step {step_number} failed: {str(e)}")

                    # Capture error screenshot
                    try:
                        screenshot_path = await self._capture_screenshot(step_number, error=True)
                        full_screenshot_path = os.path.join(self.screenshot_dir, f"step_{step_number}_error.png")
                    except:
                        screenshot_path = None
                        full_screenshot_path = None

                    # Try vision recovery
                    logger.warning(f"[EXECUTOR] Attempting vision recovery for step {step_number}")
                    vision_recovery_count += 1

                    try:
                        if full_screenshot_path and os.path.exists(full_screenshot_path):
                            # Create a mini high-level plan for vision context
                            remaining_steps = [s['description'] for s in steps[step_number-1:]]

                            vision_result = await vision_guide.get_next_actions(
                                screenshot_path=full_screenshot_path,
                                high_level_plan=remaining_steps,
                                current_step=step['description'],
                                current_step_index=0,
                                executed_steps=[]
                            )

                            # Check if vision detected authentication blocker
                            logger.info(f"[EXECUTOR] Vision suggests: {vision_result['observation'][:80]}...")

                            if vision_result.get('status') == 'blocked' and vision_result.get('blocker') == 'authentication':
                                logger.warning(f"[EXECUTOR] Vision detected authentication needed, triggering auth handler")
                                auth_success = await self._handle_authentication_with_user_prompt(app_name)
                                if not auth_success:
                                    logger.error(f"[EXECUTOR] Authentication failed or timed out")
                                    # Continue anyway, might already be logged in
                                await asyncio.sleep(2)  # Wait for auth to settle
                            else:
                                # Execute vision's suggested actions
                                for action in vision_result['next_actions']:
                                    try:
                                        await self._execute_action(action)
                                        await asyncio.sleep(Config.DYNAMIC_WAIT_TIME / 1000)
                                    except Exception as recovery_error:
                                        logger.error(f"[EXECUTOR] Vision recovery action failed: {str(recovery_error)}")

                            # Capture screenshot after recovery
                            screenshot_path = await self._capture_screenshot(step_number, error=False)

                            # Record recovered step
                            executed_step = {
                                'step_number': step_number,
                                'description': step['description'],
                                'action': step['action'],
                                'screenshot_path': screenshot_path,
                                'url': self.page.url,
                                'success': True,
                                'error_message': f"Recovered with vision: {str(e)}",
                                'vision_recovery': True,
                                'vision_observation': vision_result['observation'],
                                'timestamp': datetime.utcnow().isoformat()
                            }

                            executed_steps.append(executed_step)
                            logger.info(f"[EXECUTOR] Step {step_number} recovered with vision")

                        else:
                            raise Exception("No screenshot for vision recovery")

                    except Exception as recovery_error:
                        logger.error(f"[EXECUTOR] Vision recovery failed: {str(recovery_error)}")

                        # Record failed step
                        executed_step = {
                            'step_number': step_number,
                            'description': step['description'],
                            'action': step['action'],
                            'screenshot_path': screenshot_path,
                            'url': self.page.url if self.page else start_url,
                            'success': False,
                            'error_message': str(e),
                            'vision_recovery': False,
                            'timestamp': datetime.utcnow().isoformat()
                        }

                        executed_steps.append(executed_step)
                        logger.warning(f"[EXECUTOR] Continuing to next step after failure")

            logger.info(f"[EXECUTOR] Execution completed: {len(executed_steps)} steps executed")
            logger.info(f"[EXECUTOR] Vision recoveries: {vision_recovery_count}")

            return executed_steps

        except Exception as e:
            logger.error(f"[EXECUTOR] Critical execution error: {str(e)}", exc_info=True)
            raise

        finally:
            # Always cleanup browser resources
            await self._cleanup()

    async def _launch_browser(self):
        """Launch Playwright browser instance"""
        try:
            logger.info("[EXECUTOR] Launching browser...")
            logger.info("[EXECUTOR] ==================== BROWSER LAUNCH DEBUG ====================")
            self.playwright = await async_playwright().start()

            if Config.USE_PERSISTENT_CONTEXT:
                # Use persistent context with existing profile (preserves logins)
                logger.info(f"[EXECUTOR] Using persistent context: {Config.BROWSER_USER_DATA_DIR}")
                logger.warning("[EXECUTOR] Make sure browser is CLOSED before running!")

                # Check if user data directory exists
                import os
                logger.info(f"[EXECUTOR] User Data Dir exists: {os.path.exists(Config.BROWSER_USER_DATA_DIR)}")

                # Check for cookies/session data in Default profile
                default_profile_path = os.path.join(Config.BROWSER_USER_DATA_DIR, 'Default')
                cookies_path = os.path.join(default_profile_path, 'Cookies')
                login_data_path = os.path.join(default_profile_path, 'Login Data')
                logger.info(f"[EXECUTOR] Default profile exists: {os.path.exists(default_profile_path)}")
                logger.info(f"[EXECUTOR] Cookies file exists: {os.path.exists(cookies_path)}")
                logger.info(f"[EXECUTOR] Login Data exists: {os.path.exists(login_data_path)}")

                # Launch with persistent context
                # IMPORTANT: user_data_dir should be the base "User Data" folder, NOT a specific profile
                # Playwright will use the Default profile inside it automatically
                logger.info("[EXECUTOR] Launching Chromium with persistent context...")
                self.browser = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=Config.BROWSER_USER_DATA_DIR,  # Base User Data dir, not profile path!
                    headless=False,  # Must be non-headless for persistent context
                    channel=Config.BROWSER_CHANNEL if Config.BROWSER_CHANNEL != 'chromium' else None,  # Use None for Chromium
                    viewport={
                        'width': Config.BROWSER_VIEWPORT_WIDTH,
                        'height': Config.BROWSER_VIEWPORT_HEIGHT
                    },
                    args=['--disable-blink-features=AutomationControlled']
                )

                logger.info("[EXECUTOR] Browser context launched successfully")

                # Get the first page (persistent context creates a page automatically)
                pages = self.browser.pages
                logger.info(f"[EXECUTOR] Number of pages in context: {len(pages)}")

                if pages:
                    self.page = pages[0]
                    logger.info(f"[EXECUTOR] Using existing page, URL: {self.page.url}")
                else:
                    self.page = await self.browser.new_page()
                    logger.info("[EXECUTOR] Created new page")

                # Log all cookies in the context
                try:
                    cookies = await self.browser.cookies()
                    logger.info(f"[EXECUTOR] Total cookies loaded: {len(cookies)}")

                    # Group cookies by domain
                    cookie_domains = {}
                    for cookie in cookies:
                        domain = cookie.get('domain', 'unknown')
                        if domain not in cookie_domains:
                            cookie_domains[domain] = []
                        cookie_domains[domain].append(cookie.get('name', 'unknown'))

                    logger.info("[EXECUTOR] Cookies by domain:")
                    for domain, cookie_names in cookie_domains.items():
                        logger.info(f"[EXECUTOR]   {domain}: {len(cookie_names)} cookies")
                        logger.warning(f"[WARNING-REMOVE FOR PROD]     Cookie names: {', '.join(cookie_names[:5])}{'...' if len(cookie_names) > 5 else ''}")

                    # Check for Google cookies specifically
                    google_cookies = [c for c in cookies if 'google' in c.get('domain', '').lower()]
                    if google_cookies:
                        logger.info(f"[EXECUTOR] Google cookies found: {len(google_cookies)}")
                        for gc in google_cookies[:3]:  # Show first 3
                            logger.warning(f"[WARNING-REMOVE FOR PROD]   Google cookie: {gc.get('name')} = {gc.get('value', '')[:20]}...")
                    else:
                        logger.warning("[EXECUTOR] NO Google cookies found in persistent context!")

                    # Check for YouTube cookies
                    youtube_cookies = [c for c in cookies if 'youtube' in c.get('domain', '').lower()]
                    if youtube_cookies:
                        logger.info(f"[EXECUTOR] YouTube cookies found: {len(youtube_cookies)}")
                    else:
                        logger.warning("[EXECUTOR] NO YouTube cookies found")

                except Exception as e:
                    logger.error(f"[EXECUTOR] Error checking cookies: {str(e)}")

                logger.info("[EXECUTOR] ==================== END BROWSER LAUNCH DEBUG ====================")

            else:
                # Standard browser launch (no saved logins)
                logger.info("[EXECUTOR] Using standard browser context")

                self.browser = await self.playwright.chromium.launch(
                    headless=Config.HEADLESS_BROWSER,
                    args=['--disable-blink-features=AutomationControlled']
                )

                self.page = await self.browser.new_page(
                    viewport={
                        'width': Config.BROWSER_VIEWPORT_WIDTH,
                        'height': Config.BROWSER_VIEWPORT_HEIGHT
                    }
                )

            # Set reasonable timeout
            self.page.set_default_timeout(Config.BROWSER_TIMEOUT)

            logger.info("[EXECUTOR] Browser launched successfully")

        except Exception as e:
            logger.error(f"[EXECUTOR] Failed to launch browser: {str(e)}")
            raise

    async def _execute_step_with_fallback(self, step: Dict):
        """
        Execute a step with fallback to alternative selectors.

        Args:
            step: Step dictionary from Gemini planner

        Raises:
            Exception: If all selectors fail
        """
        action = step['action']
        selector = step.get('selector', '')
        value = step.get('value', '')
        alternative_selectors = step.get('alternative_selectors', [])

        if action == 'goto':
            url = selector if selector.startswith('http') else value
            logger.debug(f"[EXECUTOR] Navigating to: {url}")
            await self.page.goto(url, wait_until='networkidle', timeout=30000)

        elif action == 'click':
            await self._click_with_fallback(selector, alternative_selectors)

        elif action == 'fill':
            await self._fill_with_fallback(selector, value, alternative_selectors)

        elif action == 'select':
            await self._select_with_fallback(selector, value, alternative_selectors)

        elif action == 'wait':
            timeout = int(value) if value and str(value).isdigit() else 3000
            if selector:
                logger.debug(f"[EXECUTOR] Waiting for selector: {selector}")
                await self.page.wait_for_selector(selector, timeout=timeout)
            else:
                logger.debug(f"[EXECUTOR] Waiting {timeout}ms")
                await asyncio.sleep(timeout / 1000)

        elif action == 'scroll':
            logger.debug(f"[EXECUTOR] Scrolling to: {selector}")
            element = self.page.locator(selector).first
            await element.scroll_into_view_if_needed(timeout=10000)
            await asyncio.sleep(1)

        elif action == 'press_key':
            logger.debug(f"[EXECUTOR] Pressing key: {value}")
            await self.page.keyboard.press(value)

        else:
            logger.warning(f"[EXECUTOR] Unknown action: {action}")

    async def _execute_action(self, action: Dict):
        """
        Execute a single action (from Gemini or Vision).

        Args:
            action: Action dictionary with action type and parameters

        Raises:
            Exception: If action execution fails
        """
        action_type = action.get('action')
        selector = action.get('selector', '')
        value = action.get('value', '')
        description = action.get('description', '')

        try:
            if action_type == 'goto':
                url = action.get('url', selector)
                logger.debug(f"[EXECUTOR] Navigating to: {url}")
                await self.page.goto(url, wait_until='networkidle', timeout=30000)

            elif action_type == 'click':
                logger.debug(f"[EXECUTOR] Clicking: {selector}")
                # Playwright auto-scrolls before clicking
                element = self.page.locator(selector).first
                await element.scroll_into_view_if_needed(timeout=5000)
                await element.click(timeout=10000)

            elif action_type == 'fill':
                logger.debug(f"[EXECUTOR] Filling {selector} with: {value[:50]}...")
                element = self.page.locator(selector).first
                await element.scroll_into_view_if_needed(timeout=5000)
                await element.fill(value, timeout=10000)

            elif action_type == 'select':
                logger.debug(f"[EXECUTOR] Selecting {value} in: {selector}")
                await self.page.select_option(selector, value, timeout=10000)

            elif action_type == 'wait':
                duration = action.get('duration', 2000)
                if selector:
                    logger.debug(f"[EXECUTOR] Waiting for selector: {selector}")
                    await self.page.wait_for_selector(selector, timeout=duration)
                else:
                    logger.debug(f"[EXECUTOR] Waiting {duration}ms")
                    await asyncio.sleep(duration / 1000)

            elif action_type == 'scroll':
                logger.debug(f"[EXECUTOR] Scrolling to: {selector}")
                element = self.page.locator(selector).first
                await element.scroll_into_view_if_needed(timeout=10000)
                # Wait a bit after scrolling for UI to settle
                await asyncio.sleep(1)

            elif action_type == 'press_key':
                key = action.get('key', value)
                logger.debug(f"[EXECUTOR] Pressing key: {key}")
                await self.page.keyboard.press(key)

            else:
                logger.warning(f"[EXECUTOR] Unknown action: {action_type}")

        except Exception as e:
            logger.error(f"[EXECUTOR] Action execution failed ({action_type}): {str(e)}")
            raise

    async def _handle_authentication(self, app_name: str) -> bool:
        """
        Handle authentication using three-tier strategy.

        Args:
            app_name: Name of the application

        Returns:
            True if auth succeeded, False otherwise
        """
        try:
            logger.info(f"[EXECUTOR] Initiating authentication for {app_name}")
            auth_handler = AuthenticationHandler()
            auth_success = await auth_handler.handle_authentication(self.page, app_name)

            if auth_success:
                logger.info(f"[EXECUTOR] Authentication successful for {app_name}")
                return True
            else:
                logger.warning(f"[EXECUTOR] Authentication uncertain for {app_name}")
                return False

        except AuthenticationError as e:
            logger.error(f"[EXECUTOR] Authentication failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[EXECUTOR] Unexpected auth error: {str(e)}")
            return False

    async def _handle_authentication_with_user_prompt(self, app_name: str) -> bool:
        """
        Handle authentication with user prompt when vision detects login needed.

        Args:
            app_name: Name of the application

        Returns:
            True if auth succeeded, False otherwise
        """
        logger.warning(f"[EXECUTOR] Vision detected authentication required for {app_name}")
        logger.warning(f"[EXECUTOR] Please log in manually in the browser window")
        logger.warning(f"[EXECUTOR] Waiting {Config.AUTH_TIMEOUT / 1000} seconds for manual login...")

        # Wait for user to login
        await asyncio.sleep(Config.AUTH_TIMEOUT / 1000)

        # Check if we're still on a login page
        current_url = self.page.url.lower()
        login_patterns = ['login', 'signin', 'sign-in', 'auth', 'authenticate']

        if any(pattern in current_url for pattern in login_patterns):
            logger.error("[EXECUTOR] Still on login page after timeout. Authentication failed.")
            return False

        logger.info("[EXECUTOR] Login page no longer detected. Assuming authentication successful.")
        return True

    def _detect_loop(self, executed_steps: List[Dict], current_step_index: int) -> bool:
        """
        Detect if we're stuck in a loop (same actions repeated).

        Args:
            executed_steps: List of executed steps
            current_step_index: Current step index

        Returns:
            True if loop detected, False otherwise
        """
        # Get recent steps for current high-level step
        recent_steps = [
            step for step in executed_steps[-Config.LOOP_DETECTION_THRESHOLD * 2:]
            if step.get('step_index') == current_step_index
        ]

        if len(recent_steps) < Config.LOOP_DETECTION_THRESHOLD:
            return False

        # Check if last N actions are identical
        last_n_steps = recent_steps[-Config.LOOP_DETECTION_THRESHOLD:]

        # Compare action signatures
        action_signatures = []
        for step in last_n_steps:
            actions = step.get('actions', [])
            signature = tuple(
                (action.get('action'), action.get('selector', ''))
                for action in actions
            )
            action_signatures.append(signature)

        # If all signatures are the same, we have a loop
        if len(set(action_signatures)) == 1:
            logger.warning(f"[EXECUTOR] Loop detected: Same actions repeated {Config.LOOP_DETECTION_THRESHOLD} times")
            return True

        return False

    async def _click_with_fallback(self, selector: str, alternatives: List[str]):
        """
        Try to click element with fallback to alternative selectors.

        Args:
            selector: Primary CSS selector
            alternatives: List of alternative selectors

        Raises:
            Exception: If all selectors fail
        """
        # Try primary selector first
        try:
            logger.debug(f"[EXECUTOR] Trying primary selector: {selector}")
            await self.page.wait_for_selector(selector, timeout=5000)
            await self.page.click(selector)
            logger.debug(f"[EXECUTOR] Primary selector succeeded")
            return
        except Exception as e:
            logger.debug(f"[EXECUTOR] Primary selector failed: {str(e)}")

        # Try alternative selectors
        for alt in alternatives:
            try:
                logger.debug(f"[EXECUTOR] Trying alternative selector: {alt}")
                await self.page.wait_for_selector(alt, timeout=3000)
                await self.page.click(alt)
                logger.debug(f"[EXECUTOR] Alternative selector succeeded")
                return
            except Exception as e:
                logger.debug(f"[EXECUTOR] Alternative selector failed: {str(e)}")
                continue

        # All selectors failed
        raise Exception(f"Could not find clickable element with any selector")

    async def _fill_with_fallback(self, selector: str, value: str, alternatives: List[str]):
        """
        Try to fill input field with fallback to alternative selectors.

        Args:
            selector: Primary CSS selector
            value: Text to fill
            alternatives: List of alternative selectors

        Raises:
            Exception: If all selectors fail
        """
        # Try primary selector first
        try:
            logger.debug(f"[EXECUTOR] Filling primary selector: {selector}")
            await self.page.wait_for_selector(selector, timeout=5000)
            await self.page.fill(selector, value)
            logger.debug(f"[EXECUTOR] Fill succeeded")
            return
        except Exception as e:
            logger.debug(f"[EXECUTOR] Primary selector failed: {str(e)}")

        # Try alternative selectors
        for alt in alternatives:
            try:
                logger.debug(f"[EXECUTOR] Filling alternative selector: {alt}")
                await self.page.wait_for_selector(alt, timeout=3000)
                await self.page.fill(alt, value)
                logger.debug(f"[EXECUTOR] Alternative fill succeeded")
                return
            except Exception as e:
                logger.debug(f"[EXECUTOR] Alternative selector failed: {str(e)}")
                continue

        # All selectors failed
        raise Exception(f"Could not find fillable element with any selector")

    async def _select_with_fallback(self, selector: str, value: str, alternatives: List[str]):
        """
        Try to select dropdown option with fallback to alternative selectors.

        Args:
            selector: Primary CSS selector
            value: Option value or text to select
            alternatives: List of alternative selectors

        Raises:
            Exception: If all selectors fail
        """
        # Try primary selector first
        try:
            logger.debug(f"[EXECUTOR] Selecting from primary selector: {selector}")
            await self.page.wait_for_selector(selector, timeout=5000)
            await self.page.select_option(selector, value)
            logger.debug(f"[EXECUTOR] Select succeeded")
            return
        except Exception as e:
            logger.debug(f"[EXECUTOR] Primary selector failed: {str(e)}")

        # Try alternative selectors
        for alt in alternatives:
            try:
                logger.debug(f"[EXECUTOR] Selecting from alternative: {alt}")
                await self.page.wait_for_selector(alt, timeout=3000)
                await self.page.select_option(alt, value)
                logger.debug(f"[EXECUTOR] Alternative select succeeded")
                return
            except Exception as e:
                logger.debug(f"[EXECUTOR] Alternative selector failed: {str(e)}")
                continue

        # All selectors failed
        raise Exception(f"Could not find selectable element with any selector")

    async def _capture_screenshot(self, step_number: int, error: bool = False) -> str:
        """
        Capture screenshot of current page state.

        Args:
            step_number: Current step number
            error: Whether this is an error state screenshot

        Returns:
            Relative path to saved screenshot

        Raises:
            Exception: If screenshot capture fails
        """
        try:
            suffix = '_error' if error else ''
            filename = f"step_{step_number}{suffix}.png"
            filepath = os.path.join(self.screenshot_dir, filename)

            logger.debug(f"[EXECUTOR] Capturing screenshot: {filename}")

            await self.page.screenshot(
                path=filepath,
                full_page=True
            )

            # Return relative path for database/API
            relative_path = os.path.join(self.workflow_id, filename)
            logger.debug(f"[EXECUTOR] Screenshot saved: {relative_path}")

            return relative_path

        except Exception as e:
            logger.error(f"[EXECUTOR] Failed to capture screenshot: {str(e)}")
            raise

    async def _cleanup(self):
        """Cleanup browser resources"""
        try:
            logger.info("[EXECUTOR] Cleaning up browser resources...")

            if self.page:
                await self.page.close()

            if self.browser:
                await self.browser.close()

            if self.playwright:
                await self.playwright.stop()

            logger.info("[EXECUTOR] Cleanup completed")

        except Exception as e:
            logger.error(f"[EXECUTOR] Error during cleanup: {str(e)}")
