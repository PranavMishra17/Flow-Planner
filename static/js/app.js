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

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeSocketIO();
    loadHistory();
    setupEventListeners();
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
        const response = await fetch('/api/workflow', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                task: task,
                app_url: appUrlInput.value.trim() || null,
                app_name: appNameInput.value.trim() || null
            })
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

function resetUI() {
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
    document.getElementById('job-info').textContent = 'No active job';
    currentJobId = null;

    // Hide action buttons
    hideActionButtons();
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

    // Auto-scroll to bottom (use requestAnimationFrame to ensure DOM is updated)
    requestAnimationFrame(() => {
        logsContainer.scrollTop = logsContainer.scrollHeight;
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
            addLog(`Output directory: ${data.output_dir}`, 'info');
        }

        // Reset UI first (re-enables inputs, but we'll show buttons after)
        resetUI();

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

// Close modals on background click
document.addEventListener('click', (e) => {
    const markdownModal = document.getElementById('markdown-modal');
    const infoModal = document.getElementById('info-modal');

    if (e.target === markdownModal) {
        closeMarkdownModal();
    }

    if (e.target === infoModal) {
        closeInfoModal();
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
    if (!currentJobId || !currentGuidePath) {
        addLog('ERROR: No workflow to refine', 'error');
        return;
    }

    addLog('\nStarting refinement...', 'info');

    try {
        const response = await fetch('/api/refine', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: currentJobId,
                guide_path: currentGuidePath
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
// UTILITY FUNCTIONS
// =============================================================================

function formatTimestamp(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString();
}
