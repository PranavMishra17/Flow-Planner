"""
Browser-Use agent wrapper for autonomous workflow execution.
Replaces the custom Playwright executor with Browser-Use's perception-cognition-action loop.
"""
import logging
import asyncio
from typing import Dict, List, Optional
from browser_use import Agent, Browser, Controller
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from config import Config

logger = logging.getLogger(__name__)


class ChatAnthropicAdapter:
    """
    Adapter to make ChatAnthropic compatible with Browser-Use's BaseChatModel interface.
    Adds required attributes: provider, model_name, name
    """
    def __init__(self, model: str, api_key: str, temperature: float = 0.3):
        self._chat_model = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=temperature
        )
        # Required by Browser-Use BaseChatModel
        self.provider = 'anthropic'
        self.model_name = model
        self.name = f'ChatAnthropic-{model}'

    def _convert_messages(self, messages):
        """Convert Browser-Use messages to LangChain messages, handling multimodal content"""
        converted = []
        for msg in messages:
            # Check if it's already a LangChain message
            if isinstance(msg, (HumanMessage, SystemMessage, AIMessage)):
                converted.append(msg)
            # Convert Browser-Use messages to LangChain messages
            elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                role = msg.role.lower() if hasattr(msg.role, 'lower') else str(msg.role).lower()
                content = msg.content

                # Handle multimodal content (list of ContentPartTextParam and ContentPartImageParam)
                if isinstance(content, list):
                    # Convert Browser-Use content parts to LangChain format
                    langchain_content = []
                    for part in content:
                        if hasattr(part, 'text'):
                            # Text content
                            langchain_content.append({"type": "text", "text": part.text})
                        elif hasattr(part, 'image'):
                            # Image content - convert to LangChain image_url format
                            image_data = part.image
                            if hasattr(image_data, 'source'):
                                # Anthropic format: {source: {data: "base64", media_type: "image/jpeg"}}
                                source = image_data.source
                                if hasattr(source, 'data') and hasattr(source, 'media_type'):
                                    # Create data URL
                                    data_url = f"data:{source.media_type};base64,{source.data}"
                                    langchain_content.append({
                                        "type": "image_url",
                                        "image_url": {"url": data_url}
                                    })
                            elif isinstance(image_data, dict):
                                # Dict format
                                source = image_data.get('source', {})
                                if 'data' in source and 'media_type' in source:
                                    data_url = f"data:{source['media_type']};base64,{source['data']}"
                                    langchain_content.append({
                                        "type": "image_url",
                                        "image_url": {"url": data_url}
                                    })
                        elif isinstance(part, dict):
                            # Already in dict format
                            if part.get('type') == 'text':
                                langchain_content.append({"type": "text", "text": part.get('text', '')})
                            elif part.get('type') == 'image':
                                # Handle dict image format
                                source = part.get('source', {})
                                if 'data' in source and 'media_type' in source:
                                    data_url = f"data:{source['media_type']};base64,{source['data']}"
                                    langchain_content.append({
                                        "type": "image_url",
                                        "image_url": {"url": data_url}
                                    })

                    content = langchain_content if langchain_content else content

                if role == 'system':
                    converted.append(SystemMessage(content=content))
                elif role == 'user' or role == 'human':
                    converted.append(HumanMessage(content=content))
                elif role == 'assistant' or role == 'ai':
                    converted.append(AIMessage(content=content))
                else:
                    # Default to HumanMessage for unknown roles
                    converted.append(HumanMessage(content=content))
            else:
                # If it's a dict-like object
                if isinstance(msg, dict):
                    role = msg.get('role', 'user').lower()
                    content = msg.get('content', '')
                    if role == 'system':
                        converted.append(SystemMessage(content=content))
                    elif role == 'user' or role == 'human':
                        converted.append(HumanMessage(content=content))
                    elif role == 'assistant' or role == 'ai':
                        converted.append(AIMessage(content=content))
                    else:
                        converted.append(HumanMessage(content=content))
                else:
                    # Last resort: treat as content string
                    converted.append(HumanMessage(content=str(msg)))

        return converted

    async def ainvoke(self, messages, output_format=None, **kwargs):
        """Delegate ainvoke to wrapped model, converting Pydantic config to dict"""
        # Convert Browser-Use messages to LangChain messages
        converted_messages = self._convert_messages(messages)

        # Browser-Use may pass Pydantic config objects, but LangChain expects dicts
        if 'config' in kwargs:
            config = kwargs['config']
            # Convert Pydantic model to dict if needed
            if hasattr(config, 'model_dump'):
                kwargs['config'] = config.model_dump()
            elif hasattr(config, 'dict'):
                kwargs['config'] = config.dict()

        # If output_format is provided, use LangChain's structured output
        if output_format is not None:
            # Use with_structured_output to get parsed output
            structured_llm = self._chat_model.with_structured_output(output_format)
            result = await structured_llm.ainvoke(converted_messages, **kwargs)

            # Browser-Use expects AIMessage with a 'completion' attribute
            # The structured output is returned directly, so wrap it in an AIMessage-like object
            if not isinstance(result, (HumanMessage, SystemMessage, AIMessage)):
                # Create a wrapper that has both the parsed output and acts like AIMessage
                from langchain_core.messages import AIMessage as LangChainAIMessage
                ai_message = LangChainAIMessage(content=str(result))
                ai_message.completion = result  # Add completion attribute for Browser-Use
                result = ai_message
            else:
                # If it's already a message, add completion attribute
                result.completion = result
        else:
            result = await self._chat_model.ainvoke(converted_messages, **kwargs)

        # Browser-Use's token tracker expects result.usage attribute with specific field names
        # LangChain stores this in response_metadata or usage_metadata
        if not hasattr(result, 'usage'):
            # Get usage from response_metadata or usage_metadata
            usage_data = {}
            if hasattr(result, 'usage_metadata'):
                usage_data = result.usage_metadata
            elif hasattr(result, 'response_metadata') and 'usage' in result.response_metadata:
                usage_data = result.response_metadata['usage']

            # Convert Anthropic usage format to Browser-Use expected format
            # Anthropic uses: input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens
            # Browser-Use expects: prompt_tokens, completion_tokens, total_tokens, prompt_cached_tokens, etc.
            if isinstance(usage_data, dict):
                prompt_tokens = usage_data.get('input_tokens', 0)
                completion_tokens = usage_data.get('output_tokens', 0)
                result.usage = {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': prompt_tokens + completion_tokens,
                    'prompt_cached_tokens': usage_data.get('cache_read_input_tokens', 0),
                    'prompt_cache_creation_tokens': usage_data.get('cache_creation_input_tokens', 0),
                    'prompt_image_tokens': 0  # Anthropic doesn't separate image tokens
                }
            else:
                # Fallback if usage_data is not a dict
                result.usage = {
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0,
                    'prompt_cached_tokens': 0,
                    'prompt_cache_creation_tokens': 0,
                    'prompt_image_tokens': 0
                }

        return result

    def __getattr__(self, name):
        """Delegate all other attribute access to wrapped model"""
        return getattr(self._chat_model, name)


class BrowserUseAgent:
    """
    Wrapper for Browser-Use autonomous agent.
    Handles workflow execution using vision + DOM-based navigation.
    """

    def __init__(self):
        """Initialize Browser-Use agent with configuration"""
        logger.info("[BROWSER-USE] Initializing Browser-Use agent")

        # Store config for later browser creation
        self.headless = Config.HEADLESS_BROWSER
        self.user_data_dir = Config.BROWSER_USER_DATA_DIR if Config.USE_PERSISTENT_CONTEXT else None

        if self.user_data_dir:
            logger.info(f"[BROWSER-USE] Using persistent profile: {self.user_data_dir}")

        # Initialize LLM for Browser-Use with adapter for BaseChatModel compatibility
        self.llm = ChatAnthropicAdapter(
            model=Config.BROWSER_USE_LLM_MODEL,
            api_key=Config.ANTHROPIC_API_KEY,
            temperature=0.3
        )

        logger.info(f"[BROWSER-USE] Using LLM model: {Config.BROWSER_USE_LLM_MODEL}")
        logger.info("[BROWSER-USE] Browser-Use agent initialized successfully")

    async def execute_workflow(
        self,
        task: str,
        workflow_outline: List[str],
        app_url: str,
        context: Dict
    ) -> List[Dict]:
        """
        Execute workflow using Browser-Use autonomous agent.

        Args:
            task: Natural language task description
            workflow_outline: High-level steps from Gemini planner
            app_url: Target application URL
            context: Additional context about the application

        Returns:
            List of state dictionaries with screenshots, URLs, and actions

        Raises:
            Exception: If workflow execution fails
        """
        logger.info("[BROWSER-USE] ==================== WORKFLOW EXECUTION ====================")
        logger.info(f"[BROWSER-USE] Task: {task}")
        logger.info(f"[BROWSER-USE] Target URL: {app_url}")
        logger.info(f"[BROWSER-USE] Workflow steps: {len(workflow_outline)}")

        try:
            # Create enhanced task description for the agent
            enhanced_task = self._build_enhanced_task(
                task,
                workflow_outline,
                app_url,
                context
            )

            logger.info("[BROWSER-USE] Starting autonomous execution...")

            # Create browser instance (v0.9.5+ API) with configuration
            browser = Browser(
                headless=self.headless,
                user_data_dir=self.user_data_dir,
                disable_security=True,  # Helps with automated browsing detection
                wait_between_actions=1.0  # Wait 1 second between actions
            )

            # Storage for screenshots captured during execution
            step_screenshots = []

            # Define callback to capture screenshots at each step
            # Browser-Use v0.9.5 signature: (state, model_output, steps)
            async def capture_screenshot_callback(state, model_output, steps):
                """Called after each step - captures screenshot directly from page."""
                try:
                    # Try to get screenshot from state first
                    if hasattr(state, 'screenshot') and state.screenshot:
                        import base64
                        screenshot_b64 = state.screenshot
                        if isinstance(screenshot_b64, str):
                            if screenshot_b64.startswith('data:image'):
                                screenshot_b64 = screenshot_b64.split(',', 1)[1]
                            screenshot_bytes = base64.b64decode(screenshot_b64)
                            step_screenshots.append(screenshot_bytes)
                            logger.info(f"[BROWSER-USE] Screenshot from state for step {steps} ({len(screenshot_bytes)} bytes)")
                            return

                    # Fallback: capture screenshot manually from current page
                    # Access browser session through the agent's browser attribute
                    if hasattr(agent, 'browser_session'):
                        page = await agent.browser_session.get_current_page()
                        if page:
                            # Playwright screenshot() - no parameters (defaults to PNG, viewport only)
                            screenshot_bytes = await page.screenshot()
                            step_screenshots.append(screenshot_bytes)
                            logger.info(f"[BROWSER-USE] Screenshot captured from page for step {steps} ({len(screenshot_bytes)} bytes)")
                            return

                    # No screenshot available
                    step_screenshots.append(None)
                    logger.debug(f"[BROWSER-USE] No screenshot available for step {steps}")

                except Exception as e:
                    logger.warning(f"[BROWSER-USE] Failed to capture screenshot for step {steps}: {str(e)}")
                    step_screenshots.append(None)

            # Create Browser-Use agent with screenshot callback registered
            logger.info("[BROWSER-USE] Creating agent with screenshot capture callback...")
            agent = Agent(
                task=enhanced_task,
                llm=self.llm,
                browser=browser,
                save_conversation_path=None,
                save_trace_path=None,
                use_vision=True,
                max_actions_per_step=10,
                register_new_step_callback=capture_screenshot_callback  # Register callback at initialization
            )

            # Execute workflow
            logger.info("[BROWSER-USE] Executing workflow...")
            history = await agent.run(max_steps=Config.BROWSER_USE_MAX_STEPS)

            logger.info(f"[BROWSER-USE] Execution complete. Captured {len(step_screenshots)} screenshots")
            logger.info("[BROWSER-USE] ==================== END EXECUTION ====================")

            # Convert history to our state format with captured screenshots
            states = await self._convert_history_to_states(history, step_screenshots)

            return states

        except Exception as e:
            logger.error(f"[BROWSER-USE] Workflow execution failed: {str(e)}", exc_info=True)
            raise
        finally:
            # Cleanup
            try:
                await browser.close()
                logger.info("[BROWSER-USE] Browser closed")
            except:
                pass

    def _build_enhanced_task(
        self,
        task: str,
        workflow_outline: List[str],
        app_url: str,
        context: Dict
    ) -> str:
        """
        Build enhanced task description with context for Browser-Use agent.

        Args:
            task: Original task description
            workflow_outline: High-level workflow steps
            app_url: Target URL
            context: Application context

        Returns:
            Enhanced task description string
        """
        # Format workflow outline
        workflow_steps = '\n'.join(
            f"{i+1}. {step}"
            for i, step in enumerate(workflow_outline)
        )

        # Build enhanced task with context
        enhanced_task = f"""
{task}

Application: {context.get('app_name', 'Unknown')}
Target URL: {app_url}

Follow this general workflow:
{workflow_steps}

Context:
- Common UI patterns: {context.get('common_patterns', 'Standard web UI')}
- Known challenges: {context.get('known_challenges', 'None')}

Important instructions:
1. Navigate step-by-step through the workflow
2. Capture the state at each major step
3. Handle popups, modals, and dynamic content automatically
4. If you encounter ads or onboarding, dismiss them and continue
5. Take your time to ensure each action succeeds before moving to the next
6. Complete ALL steps in the workflow

Begin by navigating to: {app_url}
"""

        return enhanced_task.strip()

    async def _convert_history_to_states(self, history, step_screenshots: List[bytes] = None) -> List[Dict]:
        """
        Convert Browser-Use history to our state format with captured screenshots.

        Args:
            history: Browser-Use agent history object
            step_screenshots: List of screenshot bytes captured during execution

        Returns:
            List of state dictionaries with screenshots
        """
        states = []

        try:
            # Browser-Use v0.9.5+ returns history object differently
            # Try to extract states from the history
            if hasattr(history, 'history'):
                history_list = history.history
            elif isinstance(history, list):
                history_list = history
            else:
                logger.warning(f"[BROWSER-USE] Unknown history type: {type(history)}")
                history_list = []

            logger.info(f"[BROWSER-USE] Processing {len(history_list)} history items with {len(step_screenshots) if step_screenshots else 0} screenshots")

            for i, step in enumerate(history_list):
                # Handle Pydantic models - use model_dump() or direct attribute access
                if hasattr(step, 'model_dump'):
                    step_dict = step.model_dump()
                    state_data = step_dict.get('state', {})

                    # Get screenshot from our captured list (prioritize this)
                    screenshot = None
                    if step_screenshots and i < len(step_screenshots):
                        screenshot = step_screenshots[i]
                        if screenshot:
                            logger.debug(f"[BROWSER-USE] Using captured screenshot for step {i+1} ({len(screenshot)} bytes)")

                    # Fallback: try to extract from Browser-Use state if we don't have it
                    if not screenshot:
                        if 'screenshot' in state_data:
                            screenshot = state_data['screenshot']
                        elif 'interacted_element' in step_dict:
                            elem = step_dict.get('interacted_element', {})
                            if isinstance(elem, dict) and 'screenshot' in elem:
                                screenshot = elem['screenshot']

                    state = {
                        'step_number': i + 1,
                        'description': str(step_dict.get('result', f"Step {i+1}")),
                        'action': step_dict.get('model_output', {}),
                        'url': str(state_data.get('url', '')),
                        'timestamp': str(step_dict.get('metadata', {}).get('timestamp', '')),
                        'screenshot': screenshot,
                        'success': True
                    }
                else:
                    # Fallback for dict-like objects
                    screenshot = None
                    if step_screenshots and i < len(step_screenshots):
                        screenshot = step_screenshots[i]

                    state = {
                        'step_number': i + 1,
                        'description': str(getattr(step, 'result', f"Step {i+1}")),
                        'action': {},
                        'url': getattr(step, 'url', '') if hasattr(step, 'url') else '',
                        'timestamp': '',
                        'screenshot': screenshot,
                        'success': True
                    }

                states.append(state)

            logger.info(f"[BROWSER-USE] Converted {len(states)} steps to states with screenshots")

        except Exception as e:
            logger.error(f"[BROWSER-USE] Error converting history to states: {str(e)}", exc_info=True)
            logger.debug(f"[BROWSER-USE] History type: {type(history)}")
            # Return at least one state with available info
            states = [{
                'step_number': 1,
                'description': 'Workflow executed',
                'action': {'type': 'complete'},
                'url': '',
                'timestamp': '',
                'screenshot': None,
                'success': True
            }]

        return states

    async def execute_with_authentication(
        self,
        task: str,
        workflow_outline: List[str],
        app_url: str,
        context: Dict,
        auth_handler,
        requires_auth: bool,
        auth_type: str
    ) -> List[Dict]:
        """
        Execute workflow with authentication handling.

        Args:
            task: Natural language task description
            workflow_outline: High-level steps from Gemini planner
            app_url: Target application URL
            context: Additional context about the application
            auth_handler: AuthenticationHandler instance
            requires_auth: Whether authentication is required
            auth_type: Type of authentication needed

        Returns:
            List of state dictionaries

        Raises:
            Exception: If authentication or workflow execution fails
        """
        logger.info("[BROWSER-USE] Starting workflow with authentication handling")

        try:
            # Create browser instance
            browser = Browser(config=self.browser_config)

            # Get page from browser
            # Note: Browser-Use API may differ, adjust as needed
            page = await browser.get_current_page()

            # Navigate to app URL first
            await page.goto(app_url)
            logger.info(f"[BROWSER-USE] Navigated to {app_url}")

            # Handle authentication if required
            if requires_auth:
                logger.info(f"[BROWSER-USE] Authentication required: {auth_type}")

                # Use the existing authentication handler
                auth_success = await auth_handler.handle_authentication(
                    page,
                    context.get('app_name', 'Unknown')
                )

                if not auth_success:
                    raise Exception("Authentication failed")

                logger.info("[BROWSER-USE] Authentication successful")
            else:
                logger.info("[BROWSER-USE] No authentication required")

            # Now execute the main workflow
            enhanced_task = self._build_enhanced_task(
                task,
                workflow_outline,
                app_url,
                context
            )

            # Create agent
            agent = Agent(
                task=enhanced_task,
                llm=self.llm,
                browser=browser,
                max_actions=Config.BROWSER_USE_MAX_STEPS
            )

            # Execute
            history = await agent.run()

            logger.info(f"[BROWSER-USE] Workflow complete. Total actions: {len(history.action_results())}")

            # Convert to states
            states = await self._convert_history_to_states(history)

            return states

        except Exception as e:
            logger.error(f"[BROWSER-USE] Workflow with auth failed: {str(e)}", exc_info=True)
            raise
        finally:
            try:
                await browser.close()
            except:
                pass
