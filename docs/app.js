/**
 * app.js — Knowledge Curator Dashboard
 *
 * Responsibilities:
 * 1. Config management (localStorage: owner, repo, PAT)
 * 2. Fetch knowledge.json from the GitHub raw URL
 * 3. Render entry cards with search + category filtering
 * 4. Trigger GitHub Actions workflow_dispatch with pasted URLs
 * 5. Poll for workflow run status and link
 * 6. Toast notifications
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
  return res.status === 204; // 204 No Content = success
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
  const res = await fetch(url + '?t=' + Date.now()); // cache-bust
  if (!res.ok) return [];
  return res.json();
}

// ── Rendering ─────────────────────────────────────────────────────────────────

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

  // Remove old category buttons (keep "All")
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

// ── Setup Modal ───────────────────────────────────────────────────────────────

function showSetupModal(prefill = {}) {
  const overlay = document.getElementById('setup-overlay');
  overlay.classList.remove('hidden');

  if (prefill.owner) document.getElementById('setup-owner').value = prefill.owner;
  if (prefill.repo)  document.getElementById('setup-repo').value  = prefill.repo;

  document.getElementById('setup-save').onclick = async () => {
    const owner = document.getElementById('setup-owner').value.trim();
    const repo  = document.getElementById('setup-repo').value.trim();
    const pat   = document.getElementById('setup-pat').value.trim();
    const err   = document.getElementById('setup-error');

    if (!owner || !repo || !pat) {
      err.textContent = 'All fields are required.';
      err.classList.remove('hidden');
      return;
    }

    // Validate PAT by fetching repo info
    err.classList.add('hidden');
    document.getElementById('setup-save').textContent = 'Validating...';
    document.getElementById('setup-save').disabled = true;

    const cfg = { owner, repo, pat };
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
      document.getElementById('setup-save').textContent = 'Save & Connect';
      document.getElementById('setup-save').disabled = false;
    }
  };
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

  // Disable button during request
  btn.disabled = true;
  document.getElementById('ingest-btn-label').textContent = 'Triggering...';
  statusBar.className = 'status-bar';
  statusBar.classList.remove('hidden');
  statusIcon.textContent = '⏳';
  statusText.textContent = `Triggering GitHub Actions for ${urls.length} URL(s)...`;
  runLink.classList.add('hidden');

  try {
    const ok = await triggerWorkflow(cfg, urls.join('\n'));
    if (!ok) throw new Error('workflow_dispatch returned non-204');

    statusIcon.textContent = '🚀';
    statusText.textContent = `Workflow triggered for ${urls.length} URL(s). Processing in GitHub Actions...`;

    // Poll for run URL (appears after ~2s)
    setTimeout(async () => {
      const run = await getLatestRun(cfg);
      if (run) {
        runLink.href = run.html_url;
        runLink.textContent = 'View live run →';
        runLink.classList.remove('hidden');
      }
    }, 3000);

    toast(`🚀 Ingesting ${urls.length} URL(s) via GitHub Actions!`, 'success');
    urlInput.value = '';

    // Auto-refresh entries after estimated completion (~90s)
    setTimeout(() => {
      toast('🔄 Refreshing knowledge base...', 'success');
      loadAndRender(cfg);
    }, 90_000);

  } catch (e) {
    statusBar.className = 'status-bar error';
    statusIcon.textContent = '❌';
    statusText.textContent = `Failed: ${e.message}. Check your PAT has "workflow" scope.`;
    toast('❌ Failed to trigger workflow', 'error');
  } finally {
    btn.disabled = false;
    document.getElementById('ingest-btn-label').textContent = 'Ingest';
  }
}

// ── Load & Render ─────────────────────────────────────────────────────────────

let _allEntries = [];
let _activeCategory = 'all';
let _searchQuery = '';

async function loadAndRender(cfg) {
  const grid = document.getElementById('entries-grid');
  grid.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Loading knowledge base...</p></div>';

  try {
    _allEntries = await fetchKnowledgeJson(cfg);

    document.getElementById('entry-count').textContent =
      `${_allEntries.length} entr${_allEntries.length !== 1 ? 'ies' : 'y'}`;

    buildFilterSidebar(_allEntries);
    renderEntries(_allEntries, _searchQuery, _activeCategory);

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
        Make sure <code>data/knowledge.json</code> exists in your repo,<br>
        and your token has repository read access.</p>
        <p style="font-size:0.75rem;color:var(--text-dim)">${escHtml(e.message)}</p>
      </div>
    `;
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function toast(msg, type = '') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ── Repo Link ─────────────────────────────────────────────────────────────────

function updateRepoLink(cfg) {
  const link = document.getElementById('repo-link');
  link.href = `https://github.com/${cfg.owner}/${cfg.repo}`;
}

// ── Main Init ─────────────────────────────────────────────────────────────────

function init(cfg) {
  updateRepoLink(cfg);
  loadAndRender(cfg);

  // Search
  const searchInput = document.getElementById('search-input');
  searchInput.addEventListener('input', () => {
    _searchQuery = searchInput.value.trim();
    renderEntries(_allEntries, _searchQuery, _activeCategory);
  });

  // Filter clicks (delegated)
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

  // Ingest button
  const urlInput = document.getElementById('url-input');
  const ingestBtn = document.getElementById('ingest-btn');
  const ingestLabel = document.getElementById('ingest-btn-label');

  urlInput.addEventListener('input', () => {
    const count = urlInput.value.trim().split('\n').filter(l => l.trim()).length;
    ingestBtn.disabled = count === 0;
    ingestLabel.textContent = count > 1 ? `Ingest ${count} URLs` : 'Ingest';
  });

  ingestBtn.addEventListener('click', () => handleIngest(cfg));

  // Clear button
  document.getElementById('clear-btn').addEventListener('click', () => {
    urlInput.value = '';
    ingestBtn.disabled = true;
    ingestLabel.textContent = 'Ingest';
  });

  // Refresh
  document.getElementById('refresh-btn').addEventListener('click', () => {
    toast('🔄 Refreshing...', '');
    loadAndRender(cfg);
  });

  // Settings
  document.getElementById('settings-btn').addEventListener('click', () => {
    showSetupModal(cfg);
  });
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

(function bootstrap() {
  const cfg = loadConfig();
  if (!isConfigured(cfg)) {
    showSetupModal();
  } else {
    init(cfg);
  }
})();
