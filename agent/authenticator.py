"""
Three-tier authentication handler for FlowForge.
Handles authentication through persistent profiles, OAuth detection, and manual fallback.
"""
import logging
import asyncio
from typing import Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from config import Config

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails across all tiers"""
    pass


class AuthenticationHandler:
    """
    Handles authentication with three-tier fallback strategy:
    1. Persistent Browser Profile (automatic via cookies)
    2. OAuth Auto-Detection (semi-automatic button clicking)
    3. Manual User Intervention (user performs login)
    """

    def __init__(self):
        """Initialize authentication handler with configuration"""
        logger.info("[AUTH] Authentication handler initialized")
        self.oauth_providers = {
            'google': {
                'selectors': [
                    'button:has-text("Continue with Google")',
                    'button:has-text("Sign in with Google")',
                    'a:has-text("Continue with Google")',
                    'a:has-text("Sign in with Google")',
                    '[aria-label*="Google"]',
                    '[data-provider="google"]',
                ],
                'account_email': Config.GOOGLE_ACCOUNT_EMAIL
            },
            'github': {
                'selectors': [
                    'button:has-text("Continue with GitHub")',
                    'button:has-text("Sign in with GitHub")',
                    'a:has-text("Continue with GitHub")',
                    'a:has-text("Sign in with GitHub")',
                    '[aria-label*="GitHub"]',
                    '[data-provider="github"]',
                ],
                'account_email': None  # GitHub doesn't show email
            }
        }

    async def handle_authentication(self, page: Page, app_name: str) -> bool:
        """
        Main authentication handler with three-tier fallback strategy.

        Args:
            page: Playwright Page object
            app_name: Name of the application (for logging)

        Returns:
            True if authentication successful, False otherwise

        Raises:
            AuthenticationError: If authentication fails across all tiers
        """
        logger.info(f"[AUTH] ==================== AUTHENTICATION DEBUG ====================")
        logger.info(f"[AUTH] Starting authentication for {app_name}")
        logger.info(f"[AUTH] Current URL: {page.url}")

        # Log page title for debugging
        try:
            page_title = await page.title()
            logger.info(f"[AUTH] Page title: {page_title}")
            logger.warning(f"[WARNING-REMOVE FOR PROD] Page title: {page_title}")
        except:
            pass

        # Check if user profile/account elements are visible (logged in indicator)
        try:
            # Common selectors for logged-in state
            logged_in_selectors = [
                '[aria-label*="Account"]',
                '[aria-label*="Profile"]',
                'button[aria-label*="Google Account"]',
                '[data-testid="user-menu"]',
                'img[alt*="profile" i]',
                'img[alt*="avatar" i]'
            ]

            for selector in logged_in_selectors:
                element = await page.query_selector(selector)
                if element:
                    logger.info(f"[AUTH] Found logged-in indicator: {selector}")
                    logger.warning(f"[WARNING-REMOVE FOR PROD] Element visible: {selector}")
                    break
        except:
            pass

        # Tier 1: Check if already authenticated via persistent profile
        if not await self._is_on_login_page(page):
            logger.info(f"[AUTH] Tier 1 SUCCESS: Already authenticated via persistent profile")
            await self._log_authentication_state(page, app_name)
            logger.info(f"[AUTH] ==================== END AUTHENTICATION DEBUG ====================")
            return True

        logger.info(f"[AUTH] Tier 1 FAILED: On login page, attempting Tier 2")

        # Tier 2: Try OAuth auto-detection
        oauth_result = await self._try_oauth_login(page, app_name)
        if oauth_result:
            logger.info(f"[AUTH] Tier 2 SUCCESS: OAuth authentication completed")
            return True

        logger.info(f"[AUTH] Tier 2 FAILED: OAuth not available or failed, attempting Tier 3")

        # Tier 3: Manual user intervention
        manual_result = await self._manual_login_prompt(page, app_name)
        if manual_result:
            logger.info(f"[AUTH] Tier 3 SUCCESS: Manual authentication completed")
            return True

        # All tiers failed
        logger.error(f"[AUTH] All authentication tiers failed for {app_name}")
        raise AuthenticationError(
            f"Failed to authenticate to {app_name} after trying all methods. "
            f"Current URL: {page.url}"
        )

    async def _is_on_login_page(self, page: Page) -> bool:
        """
        Determine if the current page is a login page.

        Args:
            page: Playwright Page object

        Returns:
            True if on login page, False if already authenticated
        """
        url = page.url.lower()
        login_indicators = [
            'login',
            'signin',
            'sign-in',
            'auth',
            'signup',
            'sign-up',
            'authenticate',
            'register'
        ]

        # Check URL for login indicators
        is_login = any(indicator in url for indicator in login_indicators)

        if is_login:
            logger.debug(f"[AUTH] Login page detected: {page.url}")
        else:
            logger.debug(f"[AUTH] Not on login page: {page.url}")

        return is_login

    async def _try_oauth_login(self, page: Page, app_name: str) -> bool:
        """
        Attempt to authenticate using OAuth provider buttons (Google, GitHub).

        Args:
            page: Playwright Page object
            app_name: Name of the application

        Returns:
            True if OAuth login successful, False otherwise
        """
        logger.info(f"[AUTH] Attempting OAuth auto-detection for {app_name}")

        # Try each OAuth provider
        for provider_name, provider_config in self.oauth_providers.items():
            logger.debug(f"[AUTH] Trying {provider_name.upper()} OAuth")

            # Try to find and click OAuth button
            for selector in provider_config['selectors']:
                try:
                    logger.debug(f"[AUTH] Looking for selector: {selector}")

                    # Check if button exists
                    element = await page.query_selector(selector)
                    if not element:
                        continue

                    logger.info(f"[AUTH] Found {provider_name.upper()} OAuth button: {selector}")

                    # Click the OAuth button
                    await element.click()
                    logger.info(f"[AUTH] Clicked {provider_name.upper()} OAuth button")

                    # Wait for OAuth redirect or completion
                    try:
                        await asyncio.sleep(2)  # Brief wait for redirect

                        # Wait for navigation away from login page
                        await page.wait_for_url(
                            lambda url: not any(
                                indicator in url.lower()
                                for indicator in ['login', 'signin', 'sign-in', 'auth', 'signup']
                            ),
                            timeout=Config.OAUTH_REDIRECT_TIMEOUT
                        )

                        logger.info(f"[AUTH] {provider_name.upper()} OAuth redirect completed")
                        logger.info(f"[AUTH] New URL: {page.url}")

                        # Verify authentication succeeded
                        if not await self._is_on_login_page(page):
                            logger.info(f"[AUTH] {provider_name.upper()} OAuth authentication successful")
                            return True
                        else:
                            logger.warning(f"[AUTH] {provider_name.upper()} OAuth completed but still on login page")

                    except PlaywrightTimeoutError:
                        logger.warning(
                            f"[AUTH] {provider_name.upper()} OAuth redirect timeout "
                            f"after {Config.OAUTH_REDIRECT_TIMEOUT}ms"
                        )
                        continue

                except Exception as e:
                    logger.debug(f"[AUTH] Selector {selector} failed: {str(e)}")
                    continue

        # OAuth button detection failed, try auto-login with credentials
        if Config.DEFAULT_EMAIL and Config.DEFAULT_PASSWORD:
            logger.info("[AUTH] OAuth detection failed, attempting auto-login with credentials")
            return await self._try_auto_login(page, app_name)

        logger.info(f"[AUTH] No OAuth providers found or authentication failed")
        return False

    async def _try_auto_login(self, page: Page, app_name: str) -> bool:
        """
        Attempt to automatically log in using Browser-Use agent with credentials.

        Args:
            page: Playwright Page object
            app_name: Name of the application

        Returns:
            True if auto-login successful, False otherwise
        """
        logger.info("[AUTH] ==================== AUTO-LOGIN WITH BROWSER-USE ====================")
        logger.info(f"[AUTH] Attempting automatic login for {app_name}")
        logger.info(f"[AUTH] Using email: {Config.DEFAULT_EMAIL}")

        try:
            from browser_use import Agent, Browser
            from langchain_anthropic import ChatAnthropic

            # Create login task for Browser-Use agent
            login_task = f"""
Log in to {app_name} using the following credentials:
Email: {Config.DEFAULT_EMAIL}
Password: {Config.DEFAULT_PASSWORD}

Steps:
1. Find the email/username input field and enter: {Config.DEFAULT_EMAIL}
2. Find the password input field and enter the password
3. Find and click the login/sign-in button
4. Wait for login to complete

If you see OAuth buttons (Google, GitHub, etc.), you can try clicking them.
If login fails, try alternative login methods or report the issue.
"""

            logger.info("[AUTH] Creating Browser-Use agent for login...")

            # Create LLM using Claude
            llm = ChatAnthropic(
                model=Config.BROWSER_USE_LLM_MODEL,
                temperature=0.3,
                api_key=Config.ANTHROPIC_API_KEY
            )

            # Get browser instance from current page's context
            # Note: This assumes we can reuse the browser - may need adjustment
            browser_config = {
                'headless': Config.HEADLESS_BROWSER,
            }

            if Config.USE_PERSISTENT_CONTEXT:
                browser_config['user_data_dir'] = Config.BROWSER_USER_DATA_DIR

            browser = Browser(config=browser_config)

            # Create login agent
            login_agent = Agent(
                task=login_task,
                llm=llm,
                browser=browser,
                max_actions=15  # Limit actions for login
            )

            logger.info("[AUTH] Executing auto-login with Browser-Use agent...")

            # Execute login
            history = await login_agent.run()

            logger.info(f"[AUTH] Auto-login agent completed with {len(history.action_results())} actions")

            # Wait a moment for login to settle
            await asyncio.sleep(3)

            # Verify login succeeded
            if not await self._is_on_login_page(page):
                logger.info("[AUTH] Auto-login successful! User is authenticated.")
                logger.info("[AUTH] ==================== END AUTO-LOGIN ====================")
                await browser.close()
                return True
            else:
                logger.warning("[AUTH] Auto-login completed but still on login page")
                logger.info("[AUTH] ==================== END AUTO-LOGIN ====================")
                await browser.close()
                return False

        except Exception as e:
            logger.error(f"[AUTH] Auto-login failed with error: {str(e)}", exc_info=True)
            logger.info("[AUTH] ==================== END AUTO-LOGIN ====================")
            return False

    async def _manual_login_prompt(self, page: Page, app_name: str) -> bool:
        """
        Prompt user to manually perform login and wait for completion.

        Args:
            page: Playwright Page object
            app_name: Name of the application

        Returns:
            True if manual login successful, False otherwise
        """
        logger.info(f"[AUTH] Initiating manual login for {app_name}")
        logger.warning(
            f"[AUTH] MANUAL INTERVENTION REQUIRED: Please log into {app_name} in the browser window"
        )
        logger.warning(f"[AUTH] Current URL: {page.url}")
        logger.warning(f"[AUTH] Waiting up to {Config.AUTH_TIMEOUT}ms for manual login")

        try:
            # Wait for user to complete login
            # Detect when URL changes away from login page
            await page.wait_for_url(
                lambda url: not any(
                    indicator in url.lower()
                    for indicator in ['login', 'signin', 'sign-in', 'auth', 'signup', 'sign-up']
                ),
                timeout=Config.AUTH_TIMEOUT
            )

            logger.info(f"[AUTH] Manual login completed, new URL: {page.url}")

            # Verify authentication
            if not await self._is_on_login_page(page):
                logger.info(f"[AUTH] Manual authentication verified successful")
                return True
            else:
                logger.warning(f"[AUTH] URL changed but still appears to be on login page")
                return False

        except PlaywrightTimeoutError:
            logger.error(
                f"[AUTH] Manual login timeout after {Config.AUTH_TIMEOUT}ms. "
                f"User did not complete login."
            )
            return False

        except Exception as e:
            logger.error(f"[AUTH] Error during manual login: {str(e)}")
            return False

    async def verify_authentication(self, page: Page, app_name: str) -> bool:
        """
        Verify that the page is authenticated (not on login page).

        Args:
            page: Playwright Page object
            app_name: Name of the application

        Returns:
            True if authenticated, False if on login page
        """
        is_login = await self._is_on_login_page(page)
        if is_login:
            logger.warning(f"[AUTH] Verification failed: Still on login page for {app_name}")
            return False
        else:
            logger.info(f"[AUTH] Verification passed: Authenticated to {app_name}")
            return True

    async def _log_authentication_state(self, page: Page, app_name: str):
        """
        Log detailed authentication state for debugging.

        Args:
            page: Playwright Page object
            app_name: Name of the application
        """
        try:
            logger.info(f"[AUTH] Logging authentication state for {app_name}")

            # Try to extract user email or profile info from common locations
            # YouTube/Google account button
            try:
                google_account = await page.query_selector('button[aria-label*="Google Account"]')
                if google_account:
                    aria_label = await google_account.get_attribute('aria-label')
                    logger.info(f"[AUTH] Google Account button found")
                    logger.warning(f"[WARNING-REMOVE FOR PROD] Google Account aria-label: {aria_label}")
            except:
                pass

            # Check for profile image with alt text containing email
            try:
                profile_imgs = await page.query_selector_all('img[alt*="@"]')
                if profile_imgs:
                    for img in profile_imgs[:1]:  # Just check first one
                        alt_text = await img.get_attribute('alt')
                        logger.info(f"[AUTH] Profile image found with email in alt text")
                        logger.warning(f"[WARNING-REMOVE FOR PROD] Profile alt text: {alt_text}")
            except:
                pass

            # Check for any text elements containing email pattern
            try:
                # Look for elements with email-like content
                page_content = await page.content()
                if '@gmail.com' in page_content or '@' in page_content:
                    logger.info(f"[AUTH] Email pattern detected in page content")
                    # Don't log full content, just confirmation
            except:
                pass

            # Check localStorage for user data (if accessible)
            try:
                local_storage = await page.evaluate('() => JSON.stringify(localStorage)')
                if local_storage and len(local_storage) > 10:
                    logger.info(f"[AUTH] LocalStorage has data (length: {len(local_storage)})")
                    logger.warning(f"[WARNING-REMOVE FOR PROD] LocalStorage keys: {local_storage[:200]}...")
            except:
                pass

        except Exception as e:
            logger.debug(f"[AUTH] Error logging authentication state: {str(e)}")
