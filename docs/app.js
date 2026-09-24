/**
 * app.js — Learn & Build Intelligence Studio
 *
 * Responsibilities:
 * 1. Config management (localStorage: owner, repo, PAT, Gemini Key)
 * 2. Fetch knowledge.json from GitHub raw
 * 3. Render entry cards with search, filters & blueprint viewer
 * 4. Trigger GitHub Actions workflow_dispatch with pasted URLs
 * 5. Tab switching (Knowledge Vault vs AI Build Studio)
 * 6. In-browser AI Build Studio: queries Gemini using attached blueprints as context
 */

'use strict';

// ── Config ────────────────────────────────────────────────────────────────────

const CONFIG_KEY = 'kc_config';

function loadConfig() {
  try {
    return JSON.parse(localStorage.getItem(CONFIG_KEY) || '{}');
  } catch {
    return {};
  }
}

function saveConfig(cfg) {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(cfg));
}

function isConfigured(cfg) {
  return cfg.owner && cfg.repo && cfg.pat;
}

// ── GitHub API helpers ────────────────────────────────────────────────────────

const GH_API = 'https://api.github.com';

async function ghFetch(path, cfg, options = {}) {
  const res = await fetch(`${GH_API}${path}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${cfg.pat}`,
      'Accept': 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      ...(options.headers || {}),
    },
  });
  return res;
}

async function triggerWorkflow(cfg, urls) {
  const res = await ghFetch(
    `/repos/${cfg.owner}/${cfg.repo}/actions/workflows/ingest.yml/dispatches`,
    cfg,
    {
      method: 'POST',
      body: JSON.stringify({ ref: 'main', inputs: { urls } }),
    }
  );
  return res.status === 204;
}

async function getLatestRun(cfg) {
  const res = await ghFetch(
    `/repos/${cfg.owner}/${cfg.repo}/actions/workflows/ingest.yml/runs?per_page=1`,
    cfg
  );
  if (!res.ok) return null;
  const data = await res.json();
  return data.workflow_runs?.[0] || null;
}

async function fetchKnowledgeJson(cfg) {
  const url = `https://raw.githubusercontent.com/${cfg.owner}/${cfg.repo}/main/data/knowledge.json`;
  const res = await fetch(url + '?t=' + Date.now());
  if (!res.ok) return [];
  return res.json();
}

// ── Rendering Helpers ─────────────────────────────────────────────────────────

const SOURCE_ICONS = { github: '🔧', youtube: '🎥', web: '📄' };
const STATUS_LABELS = {
  active: '🟢 Active', archived: '🔴 Archived',
  deprecated: '🟡 Deprecated', experimental: '🔵 Experimental',
};

function formatStars(n) {
  if (!n) return null;
  return n >= 1000 ? `⭐ ${(n / 1000).toFixed(1)}k` : `⭐ ${n}`;
}

function highlight(text, query) {
  if (!query) return escHtml(text);
  const re = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return escHtml(text).replace(re, '<mark>$1</mark>');
}

function escHtml(str) {
  return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function formatMarkdown(text) {
  // Simple markdown renderer for AI chat messages & blueprints
  let html = escHtml(text);

  // Code blocks: ```lang ... ```
  html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang}">${code}</code></pre>`;
  });

  // Inline code: `code`
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headers: ###, ##, #
  html = html.replace(/^### (.*$)/gim, '<h4>$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2>$1</h2>');

  // Bold & Italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Lists: - item
  html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');

  // Paragraph breaks
  html = html.replace(/\n\n/g, '<p></p>');

  return html;
}

// ── Entry Card Rendering ──────────────────────────────────────────────────────

function renderEntryCard(entry, query = '') {
  const icon = SOURCE_ICONS[entry.source_type] || '📄';
  const stars = formatStars(entry.stars);
  const status = STATUS_LABELS[entry.status] || entry.status;
  const tags = (entry.tags || []).slice(0, 6);

  return `
    <article class="entry-card">
      <div class="entry-header">
        <div class="entry-title">
          <span class="entry-icon">${icon}</span>
          <a class="entry-name" href="${escHtml(entry.url)}" target="_blank" rel="noopener">
            ${highlight(entry.title, query)}
          </a>
          <span class="source-badge ${escHtml(entry.source_type)}">${escHtml(entry.source_type)}</span>
        </div>
        <div class="entry-meta">
          ${stars ? `<span class="stars">${stars}</span>` : ''}
          <span class="status-badge ${escHtml(entry.status)}">${status}</span>
          ${entry.author ? `<span>👤 ${escHtml(entry.author)}</span>` : ''}
        </div>
      </div>
      <p class="entry-desc">${highlight(entry.description, query)}</p>
      <div class="entry-footer">
        <span class="category-badge">📂 ${escHtml(entry.category)}</span>
        ${tags.map(t => `<span class="tag">${escHtml(t)}</span>`).join('')}
        ${entry.blueprint_file ? `
          <button class="btn btn-ghost btn-sm btn-blueprint" style="margin-left:auto;color:var(--green);border-color:rgba(63,185,80,0.4);" data-bp="${escHtml(entry.blueprint_file)}" data-title="${escHtml(entry.title)}">
            📐 View Blueprint
          </button>
        ` : ''}
      </div>
    </article>
  `;
}

function renderEntries(entries, query, category) {
  const grid = document.getElementById('entries-grid');
  const label = document.getElementById('results-label');

  let filtered = entries;

  if (category && category !== 'all') {
    filtered = filtered.filter(e => e.category === category);
  }

  if (query) {
    const q = query.toLowerCase();
    filtered = filtered.filter(e =>
      (e.title || '').toLowerCase().includes(q) ||
      (e.description || '').toLowerCase().includes(q) ||
      (e.tags || []).some(t => t.toLowerCase().includes(q)) ||
      (e.category || '').toLowerCase().includes(q) ||
      (e.author || '').toLowerCase().includes(q)
    );
  }

  label.textContent = `${filtered.length} of ${entries.length} entries`;

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="empty-state">
        <span style="font-size:2rem">🔍</span>
        <p>No entries match your search.<br>Try ingesting more resources!</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map(e => renderEntryCard(e, query)).join('');
}

function buildFilterSidebar(entries) {
  const filterList = document.getElementById('filter-list');
  const categoryCounts = {};
  for (const e of entries) {
    categoryCounts[e.category] = (categoryCounts[e.category] || 0) + 1;
  }

  const sorted = Object.entries(categoryCounts).sort(([, a], [, b]) => b - a);
  document.getElementById('count-all').textContent = entries.length;

  const existing = filterList.querySelectorAll('.filter-btn[data-category]:not([data-category="all"])');
  existing.forEach(b => b.remove());

  for (const [cat, count] of sorted) {
    const btn = document.createElement('button');
    btn.className = 'filter-btn';
    btn.dataset.category = cat;
    btn.innerHTML = `
      <span class="filter-label">${escHtml(cat)}</span>
      <span class="filter-count">${count}</span>
    `;
    filterList.appendChild(btn);
  }
}

// ── Blueprint Cache & Selector ────────────────────────────────────────────────

const _blueprintCache = new Map();

async function fetchBlueprintContent(cfg, path) {
  if (_blueprintCache.has(path)) return _blueprintCache.get(path);
  const rawUrl = `https://raw.githubusercontent.com/${cfg.owner}/${cfg.repo}/main/${path}`;
  const res = await fetch(rawUrl + '?t=' + Date.now());
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const text = await res.text();
  _blueprintCache.set(path, text);
  return text;
}

function updateBlueprintSelector(entries) {
  const list = document.getElementById('blueprint-selector-list');
  const withBp = entries.filter(e => e.blueprint_file);

  if (withBp.length === 0) {
    list.innerHTML = '<p class="hint" style="padding:0.5rem;">No blueprints found yet. Ingest repos to generate them.</p>';
    return;
  }

  list.innerHTML = withBp.map(e => `
    <label class="bp-check-item">
      <input type="checkbox" value="${escHtml(e.blueprint_file)}" checked>
      <span class="bp-check-label">${escHtml(e.title)}</span>
    </label>
  `).join('');
}

// ── Ingest Workflow ───────────────────────────────────────────────────────────

async function handleIngest(cfg) {
  const urlInput = document.getElementById('url-input');
  const statusBar = document.getElementById('ingest-status');
  const statusIcon = document.getElementById('status-icon');
  const statusText = document.getElementById('status-text');
  const runLink = document.getElementById('run-link');
  const btn = document.getElementById('ingest-btn');

  const raw = urlInput.value.trim();
  if (!raw) return;

  const urls = raw.split('\n').map(u => u.trim()).filter(Boolean);
  if (urls.length === 0) return;

  btn.disabled = true;
  document.getElementById('ingest-btn-label').textContent = 'Triggering...';
  statusBar.className = 'status-bar';
  statusBar.classList.remove('hidden');
  statusIcon.textContent = '⏳';
  statusText.textContent = `Triggering GitHub Actions for ${urls.length} URL(s)...`;
  runLink.classList.add('hidden');

  try {
    const ok = await triggerWorkflow(cfg, urls.join('\n'));
    if (!ok) throw new Error('workflow_dispatch failed');

    statusIcon.textContent = '🚀';
    statusText.textContent = `GitHub Actions running for ${urls.length} URL(s). Blueprints & knowledge base are updating...`;

    setTimeout(async () => {
      const run = await getLatestRun(cfg);
      if (run) {
        runLink.href = run.html_url;
        runLink.textContent = 'View live extraction run →';
        runLink.classList.remove('hidden');
      }
    }, 3000);

    toast(`🚀 Ingesting & extracting blueprints in GitHub Actions!`, 'success');
    urlInput.value = '';

    setTimeout(() => {
      toast('🔄 Refreshing knowledge base...', 'success');
      loadAndRender(cfg);
    }, 75_000);

  } catch (e) {
    statusBar.className = 'status-bar error';
    statusIcon.textContent = '❌';
    statusText.textContent = `Failed: ${e.message}. Ensure PAT has "repo" and "workflow" scopes.`;
    toast('❌ Failed to trigger extraction', 'error');
  } finally {
    btn.disabled = false;
    document.getElementById('ingest-btn-label').textContent = 'Ingest & Extract';
  }
}

// ── In-Browser AI Build Studio ────────────────────────────────────────────────

async function handleStudioSend(cfg) {
  const input = document.getElementById('studio-prompt-input');
  const prompt = input.value.trim();
  if (!prompt) return;

  const geminiKey = cfg.geminiKey;
  if (!geminiKey) {
    toast('⚠️ Please add your Gemini API Key in Settings (⚙️) to use the Build Studio', 'error');
    showSetupModal(cfg);
    return;
  }

  const messagesContainer = document.getElementById('chat-messages');
  const sendBtn = document.getElementById('studio-send-btn');
  const statusEl = document.getElementById('studio-token-status');

  // Append user message
  messagesContainer.innerHTML += `
    <div class="chat-message user">
      <div class="message-bubble">${escHtml(prompt)}</div>
    </div>
  `;
  input.value = '';
  sendBtn.disabled = true;
  statusEl.textContent = 'Gathering blueprints & querying Gemini...';
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  // Placeholder assistant message
  const assistantId = 'msg-' + Date.now();
  messagesContainer.innerHTML += `
    <div class="chat-message assistant" id="${assistantId}">
      <div class="message-bubble">
        <div class="spinner"></div>
        <span style="font-size:0.85rem;color:var(--text-dim);margin-left:0.5rem;">Synthesizing blueprints &amp; generating code...</span>
      </div>
    </div>
  `;
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  try {
    // 1. Gather checked blueprints
    const checkedBps = Array.from(document.querySelectorAll('#blueprint-selector-list input[type="checkbox"]:checked'))
      .map(cb => cb.value);

    let blueprintsContext = '';
    for (const bpPath of checkedBps) {
      try {
        const content = await fetchBlueprintContent(cfg, bpPath);
        blueprintsContext += `\n\n--- BLUEPRINT: ${bpPath} ---\n${content}`;
      } catch (err) {
        console.warn('Could not load blueprint:', bpPath, err);
      }
    }

    // 2. Call Gemini API
    const systemPrompt = `You are an expert Principal Android Systems & Kernel Engineer.
You specialize in KernelSU, Magisk/Zygisk, APatch, Linux kernel drivers, Android init, and sepolicy.
The user wants you to generate code, scaffold modules, or explain technical mechanics.

Use the following VERIFIED TECHNICAL BLUEPRINTS as your primary ground truth and architectural reference:
${blueprintsContext || 'No specific blueprints attached.'}

Rules:
- Provide COMPLETE, production-ready, compilable code.
- Never use placeholder comments like "// implement here".
- Cite the exact mechanism or blueprint you based your design on.`;

    const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=${geminiKey}`;


    const payload = {
      contents: [
        { role: 'user', parts: [{ text: `${systemPrompt}\n\nUSER REQUEST: ${prompt}` }] }
      ],
      generationConfig: {
        temperature: 0.2,
        maxOutputTokens: 3000,
      }
    };

    const res = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error?.message || `API error ${res.status}`);
    }

    const data = await res.json();
    const replyText = data.candidates?.[0]?.content?.parts?.[0]?.text || 'No response generated.';

    const assistantMsg = document.getElementById(assistantId);
    assistantMsg.querySelector('.message-bubble').innerHTML = formatMarkdown(replyText);

    statusEl.textContent = '✅ Code generated successfully.';
  } catch (err) {
    const assistantMsg = document.getElementById(assistantId);
    assistantMsg.querySelector('.message-bubble').innerHTML = `
      <p style="color:var(--red);">⚠️ Generation failed: ${escHtml(err.message)}</p>
      <p style="font-size:0.8rem;color:var(--text-dim);">Verify your Gemini API key in Settings (⚙️).</p>
    `;
    statusEl.textContent = '❌ Generation error.';
  } finally {
    sendBtn.disabled = false;
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }
}

// ── Setup Modal ───────────────────────────────────────────────────────────────

function showSetupModal(prefill = {}) {
  const overlay = document.getElementById('setup-overlay');
  overlay.classList.remove('hidden');

  if (prefill.owner) document.getElementById('setup-owner').value = prefill.owner;
  if (prefill.repo)  document.getElementById('setup-repo').value  = prefill.repo;
  if (prefill.geminiKey) document.getElementById('setup-gemini-key').value = prefill.geminiKey;

  document.getElementById('setup-save').onclick = async () => {
    const owner = document.getElementById('setup-owner').value.trim();
    const repo  = document.getElementById('setup-repo').value.trim();
    const pat   = document.getElementById('setup-pat').value.trim();
    const geminiKey = document.getElementById('setup-gemini-key').value.trim();
    const err   = document.getElementById('setup-error');

    if (!owner || !repo || !pat) {
      err.textContent = 'GitHub Username, Repo, and PAT are required.';
      err.classList.remove('hidden');
      return;
    }

    err.classList.add('hidden');
    document.getElementById('setup-save').textContent = 'Validating...';
    document.getElementById('setup-save').disabled = true;

    const cfg = { owner, repo, pat, geminiKey };
    try {
      const res = await ghFetch(`/repos/${owner}/${repo}`, cfg);
      if (res.status === 401 || res.status === 403) throw new Error('Invalid token or no access');
      if (res.status === 404) throw new Error('Repository not found');
      if (!res.ok) throw new Error(`GitHub error ${res.status}`);

      saveConfig(cfg);
      overlay.classList.add('hidden');
      toast('✅ Connected to repository!', 'success');
      init(cfg);
    } catch (e) {
      err.textContent = e.message;
      err.classList.remove('hidden');
    } finally {
      document.getElementById('setup-save').textContent = 'Save & Connect';
      document.getElementById('setup-save').disabled = false;
    }
  };
}

// ── Load & Render ─────────────────────────────────────────────────────────────

let _allEntries = [];
let _activeCategory = 'all';
let _searchQuery = '';

async function loadAndRender(cfg) {
  const grid = document.getElementById('entries-grid');
  grid.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Loading knowledge base and blueprints...</p></div>';

  try {
    _allEntries = await fetchKnowledgeJson(cfg);

    document.getElementById('entry-count').textContent =
      `${_allEntries.length} entr${_allEntries.length !== 1 ? 'ies' : 'y'}`;

    buildFilterSidebar(_allEntries);
    renderEntries(_allEntries, _searchQuery, _activeCategory);
    updateBlueprintSelector(_allEntries);

    if (_allEntries.length > 0) {
      const last = _allEntries.reduce((a, b) =>
        a.ingested_at > b.ingested_at ? a : b
      );
      document.getElementById('last-updated').textContent =
        `Last entry: ${new Date(last.ingested_at).toLocaleDateString()}`;
    }
  } catch (e) {
    grid.innerHTML = `
      <div class="error-state">
        <span style="font-size:2rem">⚠️</span>
        <p>Could not load knowledge base.<br>
        Make sure <code>data/knowledge.json</code> exists in your repo.</p>
        <p style="font-size:0.75rem;color:var(--text-dim)">${escHtml(e.message)}</p>
      </div>
    `;
  }
}

function toast(msg, type = '') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ── Init & Tab Switching ──────────────────────────────────────────────────────

function init(cfg) {
  loadAndRender(cfg);

  // Tab switching
  const tabVaultBtn = document.getElementById('tab-vault-btn');
  const tabStudioBtn = document.getElementById('tab-studio-btn');
  const vaultView = document.getElementById('vault-view');
  const studioView = document.getElementById('studio-view');

  tabVaultBtn.addEventListener('click', () => {
    tabVaultBtn.classList.add('active');
    tabStudioBtn.classList.remove('active');
    vaultView.classList.remove('hidden');
    studioView.classList.add('hidden');
  });

  tabStudioBtn.addEventListener('click', () => {
    tabStudioBtn.classList.add('active');
    tabVaultBtn.classList.remove('active');
    studioView.classList.remove('hidden');
    vaultView.classList.add('hidden');
  });

  // Search
  const searchInput = document.getElementById('search-input');
  searchInput.addEventListener('input', () => {
    _searchQuery = searchInput.value.trim();
    renderEntries(_allEntries, _searchQuery, _activeCategory);
  });

  // Filter clicks
  document.getElementById('filter-list').addEventListener('click', e => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    _activeCategory = btn.dataset.category;
    renderEntries(_allEntries, _searchQuery, _activeCategory);
  });

  document.getElementById('clear-filter').addEventListener('click', () => {
    _activeCategory = 'all';
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.filter-btn[data-category="all"]').classList.add('active');
    renderEntries(_allEntries, _searchQuery, _activeCategory);
  });

  // Ingest inputs
  const urlInput = document.getElementById('url-input');
  const ingestBtn = document.getElementById('ingest-btn');
  const ingestLabel = document.getElementById('ingest-btn-label');

  urlInput.addEventListener('input', () => {
    const count = urlInput.value.trim().split('\n').filter(l => l.trim()).length;
    ingestBtn.disabled = count === 0;
    ingestLabel.textContent = count > 1 ? `Ingest ${count} URLs` : 'Ingest & Extract';
  });

  ingestBtn.addEventListener('click', () => handleIngest(cfg));

  document.getElementById('clear-btn').addEventListener('click', () => {
    urlInput.value = '';
    ingestBtn.disabled = true;
    ingestLabel.textContent = 'Ingest & Extract';
  });

  document.getElementById('refresh-btn').addEventListener('click', () => {
    toast('🔄 Refreshing...', '');
    loadAndRender(cfg);
  });

  document.getElementById('settings-btn').addEventListener('click', () => {
    showSetupModal(cfg);
  });

  // Blueprint Viewer modal
  document.getElementById('entries-grid').addEventListener('click', async e => {
    const btn = e.target.closest('.btn-blueprint');
    if (!btn) return;
    const bpPath = btn.dataset.bp;
    const title = btn.dataset.title || 'Technical Blueprint';
    const overlay = document.getElementById('blueprint-overlay');
    const body = document.getElementById('blueprint-body');
    const titleEl = document.getElementById('blueprint-title');
    const rawLink = document.getElementById('blueprint-raw-link');
    const copyBtn = document.getElementById('blueprint-copy');
    const sendToStudioBtn = document.getElementById('blueprint-send-to-studio');

    titleEl.textContent = `📐 Blueprint: ${title}`;
    body.innerHTML = '<div class="spinner"></div><p>Loading blueprint...</p>';
    overlay.classList.remove('hidden');

    rawLink.href = `https://github.com/${cfg.owner}/${cfg.repo}/blob/main/${bpPath}`;

    try {
      const md = await fetchBlueprintContent(cfg, bpPath);
      body.innerHTML = `<div style="line-height:1.6;">${formatMarkdown(md)}</div>`;
      copyBtn.onclick = () => {
        navigator.clipboard.writeText(md);
        toast('📋 Blueprint copied to clipboard!', 'success');
      };
      sendToStudioBtn.onclick = () => {
        overlay.classList.add('hidden');
        tabStudioBtn.click();
        const input = document.getElementById('studio-prompt-input');
        input.value = `Using what is defined in the ${title} blueprint, `;
        input.focus();
      };
    } catch (err) {
      body.innerHTML = `<p style="color:var(--red);">Failed to load blueprint: ${escHtml(err.message)}</p>`;
    }
  });

  document.getElementById('blueprint-close').addEventListener('click', () => {
    document.getElementById('blueprint-overlay').classList.add('hidden');
  });

  // Studio Chat
  document.getElementById('studio-send-btn').addEventListener('click', () => handleStudioSend(cfg));
  document.getElementById('studio-prompt-input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleStudioSend(cfg);
    }
  });

  document.getElementById('clear-chat-btn').addEventListener('click', () => {
    document.getElementById('chat-messages').innerHTML = `
      <div class="chat-message assistant">
        <div class="message-bubble">
          <p>Chat cleared. Select blueprints on the left and ask a question to begin building.</p>
        </div>
      </div>
    `;
  });
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

(function bootstrap() {
  const cfg = loadConfig();
  if (!isConfigured(cfg)) {
    showSetupModal({ owner: 'siaw-dev', repo: 'learn-and-build' });
  } else {
    init(cfg);
  }
})();
