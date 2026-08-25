const API_BASE = window.location.origin.startsWith('http') ? `${window.location.origin}/api` : 'http://127.0.0.1:8000/api';

// DOM Elements
const statusOllama = document.getElementById('status-ollama');
const statusVectorDb = document.getElementById('status-vector-db');
const statusRag = document.getElementById('status-rag');
const statusMcp = document.getElementById('status-mcp');
const activeModelName = document.getElementById('active-model-name');

const btnNewChat = document.getElementById('btn-new-chat');
const btnClearHistory = document.getElementById('btn-clear-history');
const btnThemeToggle = document.getElementById('btn-theme-toggle');
const btnSend = document.getElementById('btn-send');

const chatInput = document.getElementById('chat-input');
const chatMessages = document.getElementById('chat-messages');
const historyList = document.getElementById('history-list');
const sourcesList = document.getElementById('sources-list');

const fileInput = document.getElementById('file-input');
const uploadZone = document.getElementById('form-upload');
const uploadProgressBox = document.getElementById('upload-progress-box');
const uploadProgressFill = document.getElementById('upload-progress-fill');
const uploadProgressText = document.getElementById('upload-progress-text');
const sourceSearchInput = document.getElementById('source-search-input');

const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebar-overlay');
const btnSidebarToggle = document.getElementById('btn-sidebar-toggle');
const toastContainer = document.getElementById('toast-container');

// State
let conversations = [];
let currentConversationId = null;
let healthCheckInterval = null;

// Initialize Marked Options
if (window.marked) {
    marked.setOptions({
        breaks: true,
        gfm: true
    });
}

// -------------------------------------------------------------
// App Initialization
// -------------------------------------------------------------
window.addEventListener('DOMContentLoaded', () => {
    setupTheme();
    setupTabs();
    setupAutoGrowInput();
    setupPromptChips();
    setupMobileSidebar();
    setupTelemetryWidget();
    
    // Initial health check
    checkServerHealth();
    healthCheckInterval = setInterval(checkServerHealth, 5000);
    
    // Load documents
    fetchSources();
    
    // Bind Event Listeners
    btnSend.addEventListener('click', handleSendMessage);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    chatInput.addEventListener('input', () => {
        btnSend.disabled = chatInput.value.trim().length === 0;
    });

    btnNewChat.addEventListener('click', startNewChat);
    btnClearHistory.addEventListener('click', clearChatHistory);
    btnThemeToggle.addEventListener('click', toggleTheme);

    const btnRunEval = document.getElementById('btn-run-eval');
    if (btnRunEval) {
        btnRunEval.addEventListener('click', runEvaluation);
    }

    // Upload listeners
    uploadZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileUpload);
    
    // Drag and drop upload listeners
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--color-accent)';
    });
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.style.borderColor = 'var(--border-color)';
    });
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--border-color)';
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFileUpload();
        }
    });

    sourceSearchInput.addEventListener('input', filterSourcesList);

    // Modal close listeners
    const modal = document.getElementById('doc-preview-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    if (modalCloseBtn && modal) {
        modalCloseBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
});

// -------------------------------------------------------------
// Mobile Drawer & Prompt Chips Setup
// -------------------------------------------------------------
function setupMobileSidebar() {
    if (btnSidebarToggle && sidebar && sidebarOverlay) {
        btnSidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            sidebarOverlay.classList.toggle('active');
        });
        
        sidebarOverlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('active');
        });
    }
}

function setupPromptChips() {
    document.addEventListener('click', (e) => {
        const chip = e.target.closest('.prompt-chip');
        if (chip) {
            const promptText = chip.getAttribute('data-prompt');
            if (promptText) {
                chatInput.value = promptText;
                btnSend.disabled = false;
                handleSendMessage();
            }
        }
    });
}

function showToast(message, icon = 'fa-circle-info') {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<i class="fa-solid ${icon}" style="color: var(--color-accent);"></i> <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(30px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// -------------------------------------------------------------
// Theme Management
// -------------------------------------------------------------
function setupTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeUI(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeUI(newTheme);
    showToast(`Switched to ${newTheme === 'dark' ? 'Dark' : 'Light'} Mode`, newTheme === 'dark' ? 'fa-moon' : 'fa-sun');
}

function updateThemeUI(theme) {
    const themeIcon = btnThemeToggle.querySelector('.theme-icon');
    const themeText = document.getElementById('theme-text');
    if (theme === 'dark') {
        themeIcon.className = 'fa-solid fa-sun theme-icon';
        themeText.textContent = 'Light Mode';
    } else {
        themeIcon.className = 'fa-solid fa-moon theme-icon';
        themeText.textContent = 'Dark Mode';
    }
}

// -------------------------------------------------------------
// Tabs Handler
// -------------------------------------------------------------
function setupTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(`tab-${tabId}`).classList.add('active');
        });
    });
}

function setupAutoGrowInput() {
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight - 10) + 'px';
    });
}

function setupTelemetryWidget() {
    const btnToggle = document.getElementById('btn-telemetry-toggle');
    const dropdown = document.getElementById('telemetry-dropdown');
    const btnClose = document.getElementById('btn-telemetry-close');
    const wrapper = document.getElementById('telemetry-widget-wrapper');

    if (!btnToggle || !dropdown) return;

    btnToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = dropdown.classList.contains('open');
        if (isOpen) {
            dropdown.classList.remove('open');
            btnToggle.classList.remove('active');
        } else {
            dropdown.classList.add('open');
            btnToggle.classList.add('active');
        }
    });

    if (btnClose) {
        btnClose.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.remove('open');
            btnToggle.classList.remove('active');
        });
    }

    document.addEventListener('click', (e) => {
        if (wrapper && !wrapper.contains(e.target)) {
            dropdown.classList.remove('open');
            btnToggle.classList.remove('active');
        }
    });
}

// -------------------------------------------------------------
// Connection Status Polling
// -------------------------------------------------------------
async function checkServerHealth() {
    const startTime = performance.now();
    try {
        const res = await fetch(`${API_BASE}/health`);
        const latency = Math.round(performance.now() - startTime);
        const metricLatency = document.getElementById('metric-latency');
        if (metricLatency) metricLatency.textContent = `< ${latency || 4}ms`;

        if (!res.ok) throw new Error('Backend server unhealthy');
        
        const data = await res.json();
        
        // Ollama Status update
        const ollamaOnline = data.ollama === 'Connected';
        updateStatusIndicator(statusOllama, ollamaOnline, `Ollama: ${data.ollama}`);
        if (activeModelName && data.ollama_model) {
            activeModelName.textContent = `Ollama: ${data.ollama_model}`;
        }
        
        // Vector DB Status update
        const vDbReady = data.vector_db === 'Ready';
        const vDbLabel = vDbReady ? `Vector DB: ${data.vector_db_count || 0} chunks` : 'Vector DB: Offline';
        updateStatusIndicator(statusVectorDb, vDbReady, vDbLabel);
        
        // RAG Status
        const ragReady = vDbReady && (data.vector_db_count > 0) && ollamaOnline;
        updateStatusIndicator(statusRag, ragReady, ragReady ? 'RAG: Ready' : 'RAG: Standby');
        
        // MCP Status
        updateStatusIndicator(statusMcp, true, 'System: Online');

        // Update Floating Trigger & Modal Overview
        const mainDot = document.getElementById('telemetry-main-dot');
        const mainBadge = document.getElementById('telemetry-main-badge');
        const overallStatus = document.getElementById('telemetry-overall-status');
        const healthVal = document.getElementById('metric-health-val');

        if (ollamaOnline && vDbReady) {
            if (mainDot) mainDot.className = 'telemetry-pulse-dot online';
            if (mainBadge) {
                mainBadge.textContent = 'Online';
                mainBadge.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                mainBadge.style.color = 'var(--color-success)';
            }
            if (overallStatus) overallStatus.textContent = 'All Nodes Nominal';
            if (healthVal) {
                healthVal.textContent = '100% OK';
                healthVal.className = 'metric-val metric-healthy';
                healthVal.style.color = 'var(--color-success)';
            }
        } else {
            if (mainDot) mainDot.className = 'telemetry-pulse-dot offline';
            if (mainBadge) {
                mainBadge.textContent = ollamaOnline || vDbReady ? 'Partial' : 'Offline';
                mainBadge.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                mainBadge.style.color = 'var(--color-danger)';
            }
            if (overallStatus) overallStatus.textContent = 'Degraded / Offline';
            if (healthVal) {
                healthVal.textContent = 'Standby';
                healthVal.className = 'metric-val';
                healthVal.style.color = 'var(--color-warning)';
            }
        }
        
    } catch (e) {
        updateStatusIndicator(statusOllama, false, 'Ollama: Offline');
        updateStatusIndicator(statusVectorDb, false, 'Vector DB: Offline');
        updateStatusIndicator(statusRag, false, 'RAG: Offline');
        updateStatusIndicator(statusMcp, false, 'MCP: Offline');

        const mainDot = document.getElementById('telemetry-main-dot');
        const mainBadge = document.getElementById('telemetry-main-badge');
        const overallStatus = document.getElementById('telemetry-overall-status');
        const healthVal = document.getElementById('metric-health-val');

        if (mainDot) mainDot.className = 'telemetry-pulse-dot offline';
        if (mainBadge) {
            mainBadge.textContent = 'Offline';
            mainBadge.style.borderColor = 'rgba(239, 68, 68, 0.4)';
            mainBadge.style.color = 'var(--color-danger)';
        }
        if (overallStatus) overallStatus.textContent = 'Server Unreachable';
        if (healthVal) {
            healthVal.textContent = 'Offline';
            healthVal.className = 'metric-val';
            healthVal.style.color = 'var(--color-danger)';
        }
    }
}

function updateStatusIndicator(element, online, text) {
    if (!element) return;
    const dot = element.querySelector('.status-dot');
    const label = element.querySelector('.status-label');
    
    if (dot) {
        dot.className = online ? 'status-dot online' : 'status-dot offline';
    }
    
    if (label) {
        label.textContent = text;
    }
}

// -------------------------------------------------------------
// Upload / Ingestion Implementation
// -------------------------------------------------------------
async function handleFileUpload() {
    const file = fileInput.files[0];
    if (!file) return;

    // Switch sidebar tab to Knowledge Base if not active
    const kbTabBtn = document.querySelector('.tab-btn[data-tab="knowledge-sources"]');
    if (kbTabBtn && !kbTabBtn.classList.contains('active')) {
        kbTabBtn.click();
    }

    uploadProgressBox.style.display = 'block';
    uploadProgressFill.style.width = '30%';
    uploadProgressText.textContent = 'Uploading & Ingesting file...';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const uploadRes = await fetch(`${API_BASE}/documents/upload`, {
            method: 'POST',
            body: formData
        });
        
        const uploadData = await uploadRes.json();
        
        if (!uploadRes.ok) {
            const errorMsg = uploadData.detail || 'Upload & Ingestion failed';
            throw new Error(errorMsg);
        }

        uploadProgressFill.style.width = '100%';
        uploadProgressText.textContent = uploadData.message || `Ingested ${uploadData.chunks_count || 0} chunks!`;
        
        const uploadedFilename = uploadData.filename || file.name;
        showToast(`Document "${uploadedFilename}" ingested successfully!`, 'fa-circle-check');

        setTimeout(() => {
            uploadProgressBox.style.display = 'none';
            fileInput.value = '';
            fetchSources(uploadedFilename);
            checkServerHealth();
        }, 1200);

    } catch (err) {
        console.error("Upload error:", err);
        uploadProgressFill.style.backgroundColor = 'var(--color-danger)';
        uploadProgressText.textContent = `Error: ${err.message}`;
        showToast(`Failed: ${err.message}`, 'fa-triangle-exclamation');
        setTimeout(() => {
            uploadProgressBox.style.display = 'none';
            uploadProgressFill.style.backgroundColor = '';
            fileInput.value = '';
        }, 4000);
    }
}

async function fetchSources(highlightFilename = null) {
    try {
        const res = await fetch(`${API_BASE}/documents`);
        if (!res.ok) return;
        const docs = await res.json();
        renderSources(docs, highlightFilename);
    } catch (e) {
        console.error('Failed to load KB sources', e);
    }
}

function renderSources(docs, highlightFilename = null) {
    sourcesList.innerHTML = '';
    if (docs.length === 0) {
        sourcesList.innerHTML = `<div class="empty-state" style="padding: 20px 0;"><p>No documents indexed yet.</p></div>`;
        return;
    }

    docs.forEach(doc => {
        const li = document.createElement('li');
        const isNew = highlightFilename && doc.filename === highlightFilename;
        li.className = `source-li ${isNew ? 'newly-uploaded' : ''}`;
        
        const isPdf = doc.filename.toLowerCase().endsWith('.pdf');
        const iconClass = isPdf ? 'fa-file-pdf' : 'fa-file-lines';

        li.innerHTML = `
            <div class="source-header">
                <i class="fa-solid ${iconClass}" style="color: var(--color-accent);"></i>
                <span>${doc.filename}</span>
            </div>
            <div class="source-meta">
                <span><i class="fa-solid fa-layer-group"></i> ${doc.chunks} chunks</span>
                <div class="source-actions">
                    <button class="btn-xs btn-view" title="Preview Chunks">
                        <i class="fa-solid fa-eye"></i> View
                    </button>
                    <button class="btn-xs btn-danger btn-delete" title="Delete Document">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            </div>
        `;

        li.querySelector('.btn-view').addEventListener('click', (e) => {
            e.stopPropagation();
            showDocPreview(doc.filename);
        });

        li.querySelector('.btn-delete').addEventListener('click', (e) => {
            e.stopPropagation();
            deleteDoc(doc.filename);
        });

        sourcesList.appendChild(li);
    });
}

async function showDocPreview(filename) {
    const modal = document.getElementById('doc-preview-modal');
    const modalTitle = document.getElementById('modal-doc-title');
    const modalContent = document.getElementById('modal-doc-content');

    if (!modal || !modalContent) return;

    modalTitle.innerHTML = `<i class="fa-solid fa-file-lines"></i> ${filename}`;
    modalContent.innerHTML = `<div style="text-align:center; padding: 20px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading document chunks...</div>`;
    modal.style.display = 'flex';

    try {
        const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}/preview`);
        if (!res.ok) throw new Error('Could not fetch document preview');
        const data = await res.json();

        if (!data.chunks || data.chunks.length === 0) {
            modalContent.innerHTML = `<p>No readable content found for this document.</p>`;
            return;
        }

        modalContent.innerHTML = data.chunks.map((chunk, idx) => `
            <div class="chunk-card">
                <div class="chunk-card-header">Chunk #${idx + 1} (ID: ${chunk.id})</div>
                <div class="chunk-card-content">${escapeHtml(chunk.content)}</div>
            </div>
        `).join('');

    } catch (e) {
        modalContent.innerHTML = `<div style="color: var(--color-danger); padding: 10px;">Error: ${e.message}</div>`;
    }
}

async function deleteDoc(filename) {
    if (!confirm(`Are you sure you want to delete "${filename}" from the Knowledge Base?`)) return;

    try {
        const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        if (!res.ok) throw new Error('Failed to delete document');
        showToast(`Document "${filename}" removed`, 'fa-trash-can');
        fetchSources();
        checkServerHealth();
    } catch (e) {
        alert(`Error deleting document: ${e.message}`);
    }
}

function escapeHtml(str) {
    return str.replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#039;");
}

function filterSourcesList() {
    const q = sourceSearchInput.value.toLowerCase();
    const items = sourcesList.querySelectorAll('.source-li');
    items.forEach(item => {
        const name = item.querySelector('.source-header').textContent.toLowerCase();
        if (name.includes(q)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

async function runEvaluation() {
    const btn = document.getElementById('btn-run-eval');
    const resultsDiv = document.getElementById('eval-results');
    const safetyEl = document.getElementById('eval-safety');
    const faithEl = document.getElementById('eval-faith');
    const relEl = document.getElementById('eval-rel');

    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Running...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/evaluate`);
        if (!res.ok) throw new Error('Evaluation failed');
        const data = await res.json();

        safetyEl.textContent = `${data.safety_blocking_rate}%`;
        faithEl.textContent = `${data.average_faithfulness}/5.0`;
        relEl.textContent = `${data.average_relevancy}/5.0`;

        resultsDiv.style.display = 'block';
        showToast('Evaluation completed successfully', 'fa-check');
    } catch (e) {
        showToast(e.message, 'fa-triangle-exclamation');
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-play"></i> Start Assessment';
        btn.disabled = false;
    }
}

// -------------------------------------------------------------
// Chat flow
// -------------------------------------------------------------
function startNewChat() {
    chatMessages.innerHTML = `
        <div class="welcome-card glass-card">
            <div class="welcome-hero-graphic">
                <div class="hero-ring hero-ring-1"></div>
                <div class="hero-ring hero-ring-2"></div>
                <i class="fa-solid fa-shield-halved welcome-shield"></i>
            </div>
            
            <h2>Aegis Ballistics Intelligence</h2>
            <p class="welcome-desc">
                Explore verified ballistics science, aerodynamics, and trajectory physics powered by <strong>Retrieval-Augmented Generation (RAG)</strong>.
            </p>

            <div class="quick-prompts-section">
                <span class="quick-prompts-title"><i class="fa-solid fa-wand-magic-sparkles"></i> Suggested Explorations:</span>
                <div class="prompt-chips-grid">
                    <button class="prompt-chip" data-prompt="What is sectional density in ballistics?">
                        <i class="fa-solid fa-crosshairs"></i>
                        <span>What is sectional density?</span>
                    </button>
                    <button class="prompt-chip" data-prompt="Explain the difference between internal and external ballistics.">
                        <i class="fa-solid fa-arrow-trend-up"></i>
                        <span>Internal vs External Ballistics</span>
                    </button>
                    <button class="prompt-chip" data-prompt="What key factors influence projectile drag and trajectory drop?">
                        <i class="fa-solid fa-wind"></i>
                        <span>Factors affecting projectile drag</span>
                    </button>
                    <button class="prompt-chip" data-prompt="How does vector similarity search work in this RAG system?">
                        <i class="fa-solid fa-database"></i>
                        <span>How does RAG retrieval work?</span>
                    </button>
                </div>
            </div>

            <div class="safety-advisory">
                <i class="fa-solid fa-shield-cat"></i>
                <div>
                    <strong>Educational Boundary Enforced</strong>
                    <span>This assistant answers pure physics and educational queries. Requests for weapon manufacturing or dangerous assembly are blocked.</span>
                </div>
            </div>

            <div class="welcome-features">
                <span class="feature-pill"><i class="fa-solid fa-bolt"></i> Fast Local LLM</span>
                <span class="feature-pill"><i class="fa-solid fa-layer-group"></i> Chroma Vector Search</span>
                <span class="feature-pill"><i class="fa-solid fa-lock"></i> Privacy Preserved</span>
            </div>
        </div>
    `;
    chatInput.value = '';
    btnSend.disabled = true;
    chatInput.style.height = 'auto';
    
    fetch(`${API_BASE}/chat/history`, { method: 'DELETE' });
    showToast('Started new conversation', 'fa-plus');
}

async function clearChatHistory() {
    if (confirm('Are you sure you want to clear the conversation history?')) {
        conversations = [];
        startNewChat();
        renderHistoryList();
    }
}

async function handleSendMessage() {
    const messageText = chatInput.value.trim();
    if (!messageText) return;

    // Append User Message
    appendMessage('user', messageText);
    chatInput.value = '';
    btnSend.disabled = true;
    chatInput.style.height = 'auto';

    // Close mobile drawer if open
    if (sidebar && sidebar.classList.contains('open')) {
        sidebar.classList.remove('open');
        if (sidebarOverlay) sidebarOverlay.classList.remove('active');
    }

    // Append Typist Bubble
    const typingBubble = appendTypingIndicator();
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: messageText, top_k: 4 })
        });
        
        typingBubble.remove();
        
        if (!res.ok) throw new Error('Response error');
        
        const data = await res.json();
        
        // Append Assistant Message
        appendMessage('assistant', data.response, data.sources, data.context, data.evaluation);
        
        // Update history sidebar list
        updateHistoryList(messageText);

    } catch (e) {
        typingBubble.remove();
        appendMessage('assistant', `Failed to retrieve answer. Please make sure the backend is running. Details: ${e.message}`);
    }
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendMessage(sender, text, sources = [], context = [], evaluation = null) {
    const welcome = chatMessages.querySelector('.welcome-card');
    if (welcome) welcome.remove();

    const row = document.createElement('div');
    row.className = `msg-row ${sender}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    
    if (sender === 'assistant' && window.marked) {
        bubble.innerHTML = marked.parse(text);
        
        // Add copy button to code snippets
        bubble.querySelectorAll('pre').forEach(pre => {
            const wrapper = document.createElement('div');
            wrapper.className = 'code-wrapper';
            pre.parentNode.insertBefore(wrapper, pre);
            wrapper.appendChild(pre);

            const copyBtn = document.createElement('button');
            copyBtn.className = 'btn-copy-code';
            copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
            copyBtn.addEventListener('click', () => {
                const codeText = pre.querySelector('code')?.innerText || pre.innerText;
                navigator.clipboard.writeText(codeText).then(() => {
                    copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied';
                    showToast('Code snippet copied!', 'fa-clipboard-check');
                    setTimeout(() => { copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy'; }, 2000);
                });
            });
            wrapper.appendChild(copyBtn);
        });

        // Render Source Cards and Evaluation
        if (sources && sources.length > 0) {
            const sourcesPanel = document.createElement('div');
            sourcesPanel.className = 'sources-panel';
            
            let evalHtml = '';
            if (evaluation) {
                const f = evaluation.faithfulness ?? evaluation.Faithfulness ?? 'N/A';
                const r = evaluation.relevancy ?? evaluation.Relevancy ?? 'N/A';
                const reason = evaluation.reasoning ?? evaluation.Reasoning ?? '';

                evalHtml = `
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--border-color);">
                        <div style="font-size: 0.85rem; color: var(--color-accent); font-weight: bold; margin-bottom: 5px;">
                            <i class="fa-solid fa-flask"></i> Auto-Evaluation
                        </div>
                        <div style="display: flex; gap: 15px; font-size: 0.85rem;">
                            <div><strong>Faithfulness:</strong> ${f}/5</div>
                            <div><strong>Relevancy:</strong> ${r}/5</div>
                        </div>
                        <div style="font-size: 0.8rem; color: var(--color-text-dim); margin-top: 5px;">
                            <em>${reason}</em>
                        </div>
                    </div>
                `;
            }

            sourcesPanel.innerHTML = `
                <div class="sources-title"><i class="fa-solid fa-book-open"></i> Grounding Sources & Evaluation</div>
                <div class="sources-cards-grid">
                    ${sources.map(src => `<span class="source-card"><i class="fa-solid fa-file-pdf"></i> ${src}</span>`).join('')}
                </div>
                ${evalHtml}
            `;
            bubble.appendChild(sourcesPanel);
        }

        // Render retrieved context details
        if (context && context.length > 0) {
            const contextDetails = document.createElement('div');
            contextDetails.className = 'retrieved-context-details';
            
            const btn = document.createElement('button');
            btn.className = 'context-summary-btn';
            btn.innerHTML = `<span><i class="fa-solid fa-magnifying-glass-chart"></i> Retrieved RAG Context (${context.length} chunks)</span> <i class="fa-solid fa-chevron-down"></i>`;
            
            const body = document.createElement('div');
            body.className = 'context-details-body';
            body.textContent = context.map((chunk, idx) => {
                return `[Chunk ${idx + 1} - ${chunk.metadata?.source}]\nScore/Distance: ${chunk.distance?.toFixed(4)}\nContent:\n${chunk.content.trim()}\n`;
            }).join('\n=========================\n\n');
            
            btn.addEventListener('click', () => {
                const isOpen = body.classList.toggle('open');
                btn.querySelector('.fa-chevron-down').className = isOpen ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down';
            });
            
            contextDetails.appendChild(btn);
            contextDetails.appendChild(body);
            bubble.appendChild(contextDetails);
        }
    } else {
        bubble.textContent = text;
    }
    
    row.appendChild(bubble);
    chatMessages.appendChild(row);
}

function appendTypingIndicator() {
    const row = document.createElement('div');
    row.className = 'msg-row assistant';
    
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    
    const indicator = document.createElement('div');
    indicator.className = 'typing-bubble';
    indicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    
    bubble.appendChild(indicator);
    row.appendChild(bubble);
    chatMessages.appendChild(row);
    return row;
}

// -------------------------------------------------------------
// History List sidebar helper
// -------------------------------------------------------------
function updateHistoryList(msgText) {
    const truncatedText = msgText.length > 30 ? msgText.substring(0, 30) + '...' : msgText;
    
    const found = conversations.some(c => c.text === truncatedText);
    if (!found) {
        conversations.unshift({ text: truncatedText, time: new Date().toLocaleTimeString() });
        renderHistoryList();
    }
}

function renderHistoryList() {
    historyList.innerHTML = '';
    if (conversations.length === 0) {
        historyList.innerHTML = `
            <div class="empty-state">
                <i class="fa-regular fa-comments"></i>
                <p>No recent conversations</p>
                <span>Start a query to begin tracking</span>
            </div>
        `;
        return;
    }
    
    conversations.forEach(c => {
        const div = document.createElement('div');
        div.className = 'history-item';
        div.innerHTML = `<i class="fa-regular fa-message"></i> <span>${c.text}</span>`;
        historyList.appendChild(div);
    });
}
