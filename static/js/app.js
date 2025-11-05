// =============================================================================
// FLOW PLANNER - CLIENT-SIDE JAVASCRIPT
// SocketIO real-time updates, history viewer, markdown renderer
// =============================================================================

// Global state
let socket = null;
let currentJobId = null;
let isRunning = false;
let currentGuidePath = null;
let currentRefinedGuidePath = null;
let currentOutputDir = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeSocketIO();
    loadHistory();
    setupEventListeners();
    populateSettingsForm();  // Load saved API keys and model preferences
});

// =============================================================================
// SOCKETIO CONNECTION
// =============================================================================

function initializeSocketIO() {
    socket = io();

    socket.on('connect', () => {
        console.log('[SOCKET] Connected to server');
        addLog('Connected to Flow Planner server', 'success');
    });

    socket.on('disconnect', () => {
        console.log('[SOCKET] Disconnected from server');
        addLog('Disconnected from server', 'error');
    });

    socket.on('log', (data) => {
        handleLogMessage(data);
    });

    socket.on('status', (data) => {
        handleStatusUpdate(data);
    });
}

// =============================================================================
// WORKFLOW EXECUTION
// =============================================================================

async function startWorkflow() {
    const taskInput = document.getElementById('task-input');
    const appUrlInput = document.getElementById('app-url-input');
    const appNameInput = document.getElementById('app-name-input');
    const runBtn = document.getElementById('run-btn');

    const task = taskInput.value.trim();
    if (!task) {
        addLog('ERROR: Task description is required', 'error');
        return;
    }

    // Disable inputs
    isRunning = true;
    taskInput.disabled = true;
    appUrlInput.disabled = true;
    appNameInput.disabled = true;
    runBtn.disabled = true;
    runBtn.textContent = '⏳ RUNNING...';

    // Update status indicator
    updateStatusIndicator('running');

    // Clear logs and hide action buttons
    clearLogs();
    hideActionButtons();
    addLog('Starting workflow capture...', 'info');

    try {
        // Get user settings (API keys and model preferences)
        const settings = getCurrentSettings();

        const requestBody = {
            task: task,
            app_url: appUrlInput.value.trim() || null,
            app_name: appNameInput.value.trim() || null
        };

        // Include user settings if provided
        if (settings) {
            if (settings.gemini_key) {
                requestBody.gemini_api_key = settings.gemini_key;
            }
            if (settings.anthropic_key) {
                requestBody.anthropic_api_key = settings.anthropic_key;
            }
            if (settings.gemini_model) {
                requestBody.gemini_model = settings.gemini_model;
            }
            if (settings.claude_model) {
                requestBody.claude_model = settings.claude_model;
            }
        }

        const response = await fetch('/api/workflow', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to start workflow');
        }

        currentJobId = data.job_id;
        addLog(`Job started: ${currentJobId}`, 'success');

        // Join job room for updates
        socket.emit('join_job', { job_id: currentJobId });

        // Update footer
        document.getElementById('job-info').textContent = `Job: ${currentJobId}`;

    } catch (error) {
        addLog(`ERROR: ${error.message}`, 'error');
        resetUI();
    }
}

function resetUI(preserveJobId = false) {
    const taskInput = document.getElementById('task-input');
    const appUrlInput = document.getElementById('app-url-input');
    const appNameInput = document.getElementById('app-name-input');
    const runBtn = document.getElementById('run-btn');

    isRunning = false;
    taskInput.disabled = false;
    appUrlInput.disabled = false;
    appNameInput.disabled = false;
    runBtn.disabled = false;
    runBtn.textContent = '▶ RUN WORKFLOW';

    updateStatusIndicator('ready');

    // Only reset job ID if not preserving it (for refinement)
    if (!preserveJobId) {
        document.getElementById('job-info').textContent = 'No active job';
        currentJobId = null;
        // Hide action buttons
        hideActionButtons();
    }
}

// =============================================================================
// LOG HANDLING
// =============================================================================

function handleLogMessage(data) {
    const message = data.message;
    const logType = data.type || 'info';
    const stepType = data.step_type;

    addLog(message, logType, stepType);
}

function addLog(message, type = 'info', stepType = null) {
    const logsContainer = document.getElementById('logs-container');
    const logLine = document.createElement('div');

    // Base class
    logLine.className = 'log-line';

    // Add type class
    logLine.classList.add(type);

    // Add step-specific class for color coding
    if (stepType) {
        logLine.classList.add(`step-${stepType}`);
    }

    logLine.textContent = message;

    logsContainer.appendChild(logLine);

    // Auto-scroll to bottom - use double requestAnimationFrame for reliability
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            logsContainer.scrollTop = logsContainer.scrollHeight;
        });
    });
}

function clearLogs() {
    const logsContainer = document.getElementById('logs-container');
    logsContainer.innerHTML = '';
}

// =============================================================================
// STATUS UPDATES
// =============================================================================

function handleStatusUpdate(data) {
    const status = data.status;

    console.log('[STATUS]', status, data);

    if (status === 'completed') {
        addLog('\n' + '='.repeat(80), 'success');
        addLog('WORKFLOW COMPLETED SUCCESSFULLY!', 'success');
        addLog('='.repeat(80), 'success');

        if (data.output_dir) {
            // Extract folder name for display (cleaner UI)
            const folderName = data.output_dir.split(/[/\\]/).pop();
            addLog(`Output directory: ${folderName}`, 'info');
            currentOutputDir = data.output_dir;  // Store full path for refinement backend call
        }

        // Reset UI but preserve job ID for refinement
        resetUI(true);

        if (data.guide_path) {
            addLog(`Guide: ${data.guide_path}`, 'info');
            console.log('[STATUS] Guide path:', data.guide_path);

            // Store guide path
            currentGuidePath = `${data.output_dir}/${data.guide_path}`;
            console.log('[STATUS] Current guide path set to:', currentGuidePath);

            // Check if we also have a refined guide
            if (data.refined_guide_path) {
                currentRefinedGuidePath = `${data.output_dir}/${data.refined_guide_path}`;
                addLog(`Refined guide: ${data.refined_guide_path}`, 'info');
                console.log('[STATUS] Showing buttons with refined guide');
                showActionButtons(true, true); // Show all buttons including refined
            } else {
                console.log('[STATUS] Showing buttons without refined guide');
                showActionButtons(true, false); // Show guide and refine buttons only
            }
        } else {
            console.log('[STATUS] No guide_path in data');
        }

        loadHistory(); // Refresh history

    } else if (status === 'failed') {
        addLog('\n' + '='.repeat(80), 'error');
        addLog(`WORKFLOW FAILED: ${data.error}`, 'error');
        addLog('='.repeat(80), 'error');

        resetUI();

    } else if (status === 'refining') {
        // Hide refine button when refinement starts
        document.getElementById('refine-btn').classList.add('hidden');

    } else {
        // Status change (planning, executing, etc.)
        updateStatusIndicator('running', status);
    }
}

function updateStatusIndicator(state, detail = null) {
    const indicator = document.getElementById('status-indicator');

    if (state === 'ready') {
        indicator.textContent = 'READY';
        indicator.className = 'status-ready';
    } else if (state === 'running') {
        indicator.textContent = detail ? detail.toUpperCase() : 'RUNNING';
        indicator.className = 'status-running';
    } else if (state === 'error') {
        indicator.textContent = 'ERROR';
        indicator.className = 'status-error';
    }
}

// =============================================================================
// HISTORY PANEL
// =============================================================================

function toggleHistory() {
    const content = document.getElementById('history-content');
    const icon = document.getElementById('history-icon');

    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        icon.classList.add('expanded');
        loadHistory(); // Refresh when opening
    } else {
        content.classList.add('collapsed');
        icon.classList.remove('expanded');
    }
}

function toggleAlgorithm() {
    const content = document.getElementById('algorithm-content');
    const icon = document.getElementById('algorithm-icon');

    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        icon.textContent = '▼';
    } else {
        content.classList.add('collapsed');
        icon.textContent = '▶';
    }
}

async function loadHistory() {
    const historyList = document.getElementById('history-list');

    try {
        const response = await fetch('/api/history');
        const data = await response.json();

        if (!data.runs || data.runs.length === 0) {
            historyList.innerHTML = '<div style="color: #888;">No workflow runs yet</div>';
            return;
        }

        // Build history list
        historyList.innerHTML = '';

        data.runs.forEach(run => {
            const item = document.createElement('div');
            item.className = 'history-item';

            const name = document.createElement('div');
            name.className = 'history-item-name';
            name.textContent = run.name;

            const files = document.createElement('div');
            files.className = 'history-item-files';

            run.markdown_files.forEach(file => {
                const btn = document.createElement('button');
                btn.className = 'history-file-btn';
                btn.textContent = `📄 ${file}`;
                btn.onclick = () => viewMarkdown(`${run.path}/${file}`);
                files.appendChild(btn);
            });

            item.appendChild(name);
            item.appendChild(files);
            historyList.appendChild(item);
        });

    } catch (error) {
        console.error('[HISTORY] Failed to load:', error);
        historyList.innerHTML = '<div style="color: #ff0055;">Failed to load history</div>';
    }
}

// =============================================================================
// MARKDOWN VIEWER
// =============================================================================

async function viewMarkdown(filepath) {
    const modal = document.getElementById('markdown-modal');
    const viewer = document.getElementById('markdown-viewer');
    const title = document.getElementById('modal-title');

    try {
        // Show loading
        modal.classList.add('active');
        viewer.innerHTML = '<div style="color: #888;">Loading...</div>';
        title.textContent = 'LOADING...';

        // Fetch markdown
        const response = await fetch(`/api/markdown/${filepath}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to load markdown');
        }

        // Convert markdown to HTML
        const htmlContent = marked.parse(data.content);

        // Fix image paths (make them absolute)
        const fixedHtml = htmlContent.replace(
            /src="(?!http)(.*?)"/g,
            (match, path) => {
                // Extract run directory from filepath
                const runDir = filepath.split('/')[0];
                return `src="/output/${runDir}/${path}"`;
            }
        );

        // Render
        viewer.innerHTML = fixedHtml;
        title.textContent = filepath.split('/').pop().replace('.md', '');

    } catch (error) {
        console.error('[MARKDOWN] Failed to load:', error);
        viewer.innerHTML = `<div style="color: #ff0055;">Error: ${error.message}</div>`;
        title.textContent = 'ERROR';
    }
}

function closeMarkdownModal() {
    const modal = document.getElementById('markdown-modal');
    modal.classList.remove('active');
}

// Info Modal Functions
function openInfoModal() {
    const modal = document.getElementById('info-modal');
    modal.classList.add('active');
}

function closeInfoModal() {
    const modal = document.getElementById('info-modal');
    modal.classList.remove('active');
}

function openSettings() {
    const modal = document.getElementById('settings-modal');
    modal.classList.add('active');
}

function closeSettings() {
    const modal = document.getElementById('settings-modal');
    modal.classList.remove('active');
}

// Close modals on background click
document.addEventListener('click', (e) => {
    const markdownModal = document.getElementById('markdown-modal');
    const infoModal = document.getElementById('info-modal');
    const settingsModal = document.getElementById('settings-modal');

    if (e.target === markdownModal) {
        closeMarkdownModal();
    }

    if (e.target === infoModal) {
        closeInfoModal();
    }

    if (e.target === settingsModal) {
        closeSettings();
    }
});

// =============================================================================
// EVENT LISTENERS
// =============================================================================

function setupEventListeners() {
    // Enter key on task input
    document.getElementById('task-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey && !isRunning) {
            startWorkflow();
        }
    });

    // Escape key to close modals
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeMarkdownModal();
            closeInfoModal();
            closeSettings();
        }
    });
}

// =============================================================================
// ACTION BUTTONS (Guide/Refine)
// =============================================================================

function showActionButtons(showGuide, showRefined) {
    console.log('[BUTTONS] Showing action buttons:', {showGuide, showRefined});

    const actionButtons = document.getElementById('action-buttons');
    const guideBtn = document.getElementById('guide-btn');
    const refineBtn = document.getElementById('refine-btn');
    const refinedGuideBtn = document.getElementById('refined-guide-btn');

    // Show action buttons container
    actionButtons.classList.remove('hidden');
    console.log('[BUTTONS] Container visible');

    // Show/hide individual buttons
    if (showGuide) {
        guideBtn.classList.remove('hidden');
        refineBtn.classList.remove('hidden');
        console.log('[BUTTONS] Guide and Refine buttons visible');
    }

    if (showRefined) {
        refinedGuideBtn.classList.remove('hidden');
        console.log('[BUTTONS] Refined guide button visible');
    }
}

function hideActionButtons() {
    const actionButtons = document.getElementById('action-buttons');
    const guideBtn = document.getElementById('guide-btn');
    const refineBtn = document.getElementById('refine-btn');
    const refinedGuideBtn = document.getElementById('refined-guide-btn');

    actionButtons.classList.add('hidden');
    guideBtn.classList.add('hidden');
    refineBtn.classList.add('hidden');
    refinedGuideBtn.classList.add('hidden');
}

function openGuide() {
    if (currentGuidePath) {
        viewMarkdown(currentGuidePath);
    }
}

function openRefinedGuide() {
    if (currentRefinedGuidePath) {
        viewMarkdown(currentRefinedGuidePath);
    }
}

async function startRefinement() {
    if (!currentJobId || !currentOutputDir) {
        addLog('ERROR: No workflow to refine. Please complete a workflow first.', 'error');
        console.error('[REFINE] Missing data:', {currentJobId, currentOutputDir});
        return;
    }

    addLog('\nStarting refinement...', 'info');
    console.log('[REFINE] Sending refine request with:', {currentJobId, currentOutputDir});

    try {
        const response = await fetch('/api/refine', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: currentJobId,
                output_dir: currentOutputDir
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to start refinement');
        }

        addLog('Refinement started', 'success');

    } catch (error) {
        addLog(`ERROR: ${error.message}`, 'error');
    }
}

// =============================================================================
// SETTINGS MANAGEMENT
// =============================================================================

// Simple encryption/obfuscation for localStorage (not cryptographically secure, but better than plaintext)
function encodeKey(key) {
    if (!key) return '';
    // Base64 encode with simple XOR for obfuscation
    const xorKey = 'FlowPlanner2025';
    let encoded = '';
    for (let i = 0; i < key.length; i++) {
        encoded += String.fromCharCode(key.charCodeAt(i) ^ xorKey.charCodeAt(i % xorKey.length));
    }
    return btoa(encoded);
}

function decodeKey(encoded) {
    if (!encoded) return '';
    try {
        const xorKey = 'FlowPlanner2025';
        const decoded = atob(encoded);
        let key = '';
        for (let i = 0; i < decoded.length; i++) {
            key += String.fromCharCode(decoded.charCodeAt(i) ^ xorKey.charCodeAt(i % xorKey.length));
        }
        return key;
    } catch (e) {
        console.error('[SETTINGS] Failed to decode key:', e);
        return '';
    }
}

// Save settings to localStorage
function saveSettings(settings) {
    try {
        const encoded = {
            gemini_key: encodeKey(settings.gemini_key),
            anthropic_key: encodeKey(settings.anthropic_key),
            gemini_model: settings.gemini_model,
            claude_model: settings.claude_model
        };
        localStorage.setItem('flowplanner_settings', JSON.stringify(encoded));
        console.log('[SETTINGS] Settings saved to localStorage');
    } catch (e) {
        console.error('[SETTINGS] Failed to save settings:', e);
    }
}

// Load settings from localStorage
function loadSettings() {
    try {
        const stored = localStorage.getItem('flowplanner_settings');
        if (!stored) {
            console.log('[SETTINGS] No saved settings found');
            return null;
        }

        const encoded = JSON.parse(stored);
        return {
            gemini_key: decodeKey(encoded.gemini_key),
            anthropic_key: decodeKey(encoded.anthropic_key),
            gemini_model: encoded.gemini_model,
            claude_model: encoded.claude_model
        };
    } catch (e) {
        console.error('[SETTINGS] Failed to load settings:', e);
        return null;
    }
}

// Populate settings form with saved values
function populateSettingsForm() {
    const settings = loadSettings();
    if (!settings) return;

    console.log('[SETTINGS] Populating form with saved settings');

    if (settings.gemini_key) {
        document.getElementById('gemini-api-key').value = settings.gemini_key;
    }

    if (settings.anthropic_key) {
        document.getElementById('anthropic-api-key').value = settings.anthropic_key;
    }

    if (settings.gemini_model) {
        document.getElementById('gemini-model').value = settings.gemini_model;
    }

    if (settings.claude_model) {
        document.getElementById('claude-model').value = settings.claude_model;
    }
}

// Toggle password visibility
function togglePasswordVisibility(fieldId) {
    const field = document.getElementById(fieldId);
    const button = field.nextElementSibling;
    const icon = button.querySelector('.eye-icon');

    if (field.type === 'password') {
        field.type = 'text';
        icon.textContent = '👁️‍🗨️';
    } else {
        field.type = 'password';
        icon.textContent = '👁';
    }
}

// Verify API keys
async function verifyAPIKeys() {
    const geminiKey = document.getElementById('gemini-api-key').value.trim();
    const anthropicKey = document.getElementById('anthropic-api-key').value.trim();

    if (!geminiKey && !anthropicKey) {
        showApiStatus('Please enter at least one API key', 'error');
        return;
    }

    showApiStatus('Verifying API keys...', 'info');

    try {
        const response = await fetch('/api/verify-keys', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                gemini_key: geminiKey,
                anthropic_key: anthropicKey
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to verify keys');
        }

        // Display results
        let messages = [];

        if (geminiKey) {
            if (data.gemini.valid) {
                messages.push('✓ Gemini API key is valid');
            } else {
                messages.push(`✗ Gemini: ${data.gemini.error || 'Invalid key'}`);
            }
        }

        if (anthropicKey) {
            if (data.anthropic.valid) {
                messages.push('✓ Anthropic API key is valid');
            } else {
                messages.push(`✗ Anthropic: ${data.anthropic.error || 'Invalid key'}`);
            }
        }

        const allValid = (!geminiKey || data.gemini.valid) && (!anthropicKey || data.anthropic.valid);
        showApiStatus(messages.join(' | '), allValid ? 'success' : 'error');

    } catch (error) {
        showApiStatus(`Error: ${error.message}`, 'error');
    }
}

// Apply settings
async function applySettings() {
    const geminiKey = document.getElementById('gemini-api-key').value.trim();
    const anthropicKey = document.getElementById('anthropic-api-key').value.trim();
    const geminiModel = document.getElementById('gemini-model').value;
    const claudeModel = document.getElementById('claude-model').value;

    if (!geminiKey && !anthropicKey) {
        showApiStatus('Please enter at least one API key', 'error');
        return;
    }

    // Save to localStorage
    const settings = {
        gemini_key: geminiKey,
        anthropic_key: anthropicKey,
        gemini_model: geminiModel,
        claude_model: claudeModel
    };

    saveSettings(settings);
    showApiStatus('Settings saved successfully! They will be used in the next workflow.', 'success');

    console.log('[SETTINGS] Applied settings:', {
        gemini_model: geminiModel,
        claude_model: claudeModel,
        has_gemini_key: !!geminiKey,
        has_anthropic_key: !!anthropicKey
    });

    // Close modal after a delay
    setTimeout(() => {
        closeSettings();
    }, 2000);
}

// Show API status message
function showApiStatus(message, type) {
    const statusDiv = document.getElementById('api-status');
    const statusText = document.getElementById('api-status-text');

    statusDiv.className = `api-status ${type}`;
    statusText.textContent = message;
    statusDiv.classList.remove('hidden');

    // Auto-hide after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.classList.add('hidden');
        }, 5000);
    }
}

// Get current settings for API calls
function getCurrentSettings() {
    // First check if user has provided settings in the form
    const geminiKey = document.getElementById('gemini-api-key')?.value?.trim();
    const anthropicKey = document.getElementById('anthropic-api-key')?.value?.trim();
    const geminiModel = document.getElementById('gemini-model')?.value;
    const claudeModel = document.getElementById('claude-model')?.value;

    // If form has values, use them
    if (geminiKey || anthropicKey) {
        return {
            gemini_key: geminiKey,
            anthropic_key: anthropicKey,
            gemini_model: geminiModel,
            claude_model: claudeModel
        };
    }

    // Otherwise, load from localStorage
    return loadSettings();
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

function formatTimestamp(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString();
}
