/**
 * Learn & Build — Engineering Knowledge Vault & Blueprint Viewer
 * Client-Side Application Engine
 */

'use strict';

// ── Configuration State ───────────────────────────────────────────────────────
const CONFIG_KEY = 'learn_and_build_cfg';
const DEFAULT_CONFIG = {
  owner: 'siaw-dev',
  repo: 'learn-and-build',
  pat: '',
};

function getConfig() {
  try {
    const raw = localStorage.getItem(CONFIG_KEY);
    return raw ? { ...DEFAULT_CONFIG, ...JSON.parse(raw) } : { ...DEFAULT_CONFIG };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

function saveConfig(cfg) {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(cfg));
}

// ── Application State ─────────────────────────────────────────────────────────
const state = {
  entries: [],
  selectedCategory: 'all',
  selectedSource: 'all',
  searchQuery: '',
  blueprintCache: new Map(),
  activeRunPollTimer: null,
};

// ── SVG Vector Icons (No Emojis) ──────────────────────────────────────────────
const ICONS = {
  github: `<svg class="icon-sm" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>`,
  youtube: `<svg class="icon-sm" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>`,
  web: `<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>`,
  blueprint: `<svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`,
  star: `<svg class="icon-xs" viewBox="0 0 24 24" fill="currentColor"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  external: `<svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`,
};

// ── Markdown Parser (Self-Contained) ──────────────────────────────────────────
function escHtml(str) {
  return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function parseMarkdown(md) {
  if (!md) return '';
  let html = escHtml(md);

  // Fenced code blocks with language support
  html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headings
  html = html.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Blockquotes
  html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

  // Bold & Italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Unordered Lists
  html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // Paragraph breaks
  html = html.replace(/\n\n/g, '<p></p>');

  return html;
}

// ── Toast Notification System ─────────────────────────────────────────────────
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${escHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    toast.style.transition = 'all 0.2s ease';
    setTimeout(() => toast.remove(), 200);
  }, 3200);
}

// ── Data Fetching ─────────────────────────────────────────────────────────────
async function loadKnowledgeVault() {
  const cfg = getConfig();
  const url = `https://raw.githubusercontent.com/${cfg.owner}/${cfg.repo}/main/data/knowledge.json?t=${Date.now()}`;
  
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.entries = Array.isArray(data) ? data : [];
    
    // Update Header Counts
    document.getElementById('total-count-label').textContent = `${state.entries.length} blueprints`;
    document.getElementById('count-all').textContent = state.entries.length;
    document.getElementById('repo-name-label').textContent = `${cfg.owner}/${cfg.repo}`;
    document.getElementById('repo-link').href = `https://github.com/${cfg.owner}/${cfg.repo}`;
    
    const now = new Date();
    document.getElementById('footer-sync-time').textContent = `Last synchronized: ${now.toLocaleTimeString()}`;

    buildCategorySidebar();
    renderCards();
  } catch (err) {
    console.error('Failed to load vault data:', err);
    document.getElementById('cards-container').innerHTML = `
      <div class="empty-state">
        <p>Could not connect to repository <strong>${escHtml(cfg.owner)}/${escHtml(cfg.repo)}</strong>.</p>
        <button id="retry-load-btn" class="btn btn-secondary btn-sm">Check Connection &amp; Retry</button>
      </div>
    `;
    document.getElementById('retry-load-btn')?.addEventListener('click', loadKnowledgeVault);
  }
}

// ── Sidebar Category Navigation ───────────────────────────────────────────────
function buildCategorySidebar() {
  const nav = document.getElementById('category-nav');
  const counts = {};
  
  for (const entry of state.entries) {
    const cat = entry.category || 'Tools & Utilities';
    counts[cat] = (counts[cat] || 0) + 1;
  }

  // Remove existing dynamic items
  nav.querySelectorAll('.category-nav-item:not([data-category="all"])').forEach(el => el.remove());

  const sortedCats = Object.entries(counts).sort(([, a], [, b]) => b - a);
  for (const [cat, count] of sortedCats) {
    const btn = document.createElement('button');
    btn.className = `category-nav-item ${state.selectedCategory === cat ? 'active' : ''}`;
    btn.dataset.category = cat;
    btn.innerHTML = `
      <span class="cat-label">${escHtml(cat)}</span>
      <span class="cat-count">${count}</span>
    `;
    btn.addEventListener('click', () => {
      selectCategory(cat);
    });
    nav.appendChild(btn);
  }
}

function selectCategory(category) {
  state.selectedCategory = category;
  document.querySelectorAll('.category-nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.category === category);
  });
  renderCards();
}

// ── Card Grid Rendering ───────────────────────────────────────────────────────
function renderCards() {
  const container = document.getElementById('cards-container');
  const countBadge = document.getElementById('filtered-count-badge');
  const viewTitle = document.getElementById('active-view-title');

  let filtered = [...state.entries];

  // Category filter
  if (state.selectedCategory !== 'all') {
    filtered = filtered.filter(e => e.category === state.selectedCategory);
    viewTitle.textContent = state.selectedCategory;
  } else {
    viewTitle.textContent = 'All Vault Resources';
  }

  // Source filter
  if (state.selectedSource !== 'all') {
    filtered = filtered.filter(e => e.source_type === state.selectedSource);
  }

  // Search Query filter
  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    filtered = filtered.filter(e =>
      (e.title || '').toLowerCase().includes(q) ||
      (e.description || '').toLowerCase().includes(q) ||
      (e.category || '').toLowerCase().includes(q) ||
      (e.author || '').toLowerCase().includes(q) ||
      (e.tags || []).some(t => t.toLowerCase().includes(q))
    );
  }

  countBadge.textContent = `${filtered.length} of ${state.entries.length} items`;

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <p>No resources found matching your current filter.</p>
        <button id="clear-all-filters-btn" class="btn btn-secondary btn-sm">Reset Filters</button>
      </div>
    `;
    document.getElementById('clear-all-filters-btn')?.addEventListener('click', () => {
      state.selectedCategory = 'all';
      state.selectedSource = 'all';
      state.searchQuery = '';
      document.getElementById('search-input').value = '';
      document.querySelectorAll('.source-pill').forEach(p => p.classList.toggle('active', p.dataset.source === 'all'));
      selectCategory('all');
    });
    return;
  }

  container.innerHTML = filtered.map(entry => createCardHtml(entry)).join('');

  // Attach card event listeners
  container.querySelectorAll('.btn-blueprint').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const bpFile = btn.dataset.blueprint;
      const title = btn.dataset.title;
      const category = btn.dataset.category;
      const sourceUrl = btn.dataset.url;
      openBlueprintViewer(bpFile, title, category, sourceUrl);
    });
  });
}

function createCardHtml(entry) {
  const source = entry.source_type || 'web';
  const icon = ICONS[source] || ICONS.web;
  const stars = entry.stars ? `<span class="stars-badge">${ICONS.star} ${(entry.stars >= 1000 ? (entry.stars / 1000).toFixed(1) + 'k' : entry.stars)}</span>` : '';
  const tags = (entry.tags || []).slice(0, 5);

  return `
    <article class="entry-card">
      <div class="card-top">
        <span class="card-source-badge ${escHtml(source)}">
          ${icon}
          <span>${escHtml(source)}</span>
        </span>
        <div class="card-meta">
          ${stars}
          <span>${escHtml(entry.status || 'active')}</span>
        </div>
      </div>

      <div class="card-title-group">
        <h3>
          <a class="card-title-link" href="${escHtml(entry.url)}" target="_blank" rel="noopener">
            ${escHtml(entry.title || entry.url)}
          </a>
        </h3>
        <p class="card-desc">${escHtml(entry.description || 'No summary available.')}</p>
      </div>

      <div class="card-tags">
        ${tags.map(t => `<span class="card-tag">${escHtml(t)}</span>`).join('')}
      </div>

      <div class="card-footer">
        <span class="card-domain-badge">${escHtml(entry.category || 'General')}</span>
        ${entry.blueprint_file ? `
          <button class="btn-blueprint" 
            data-blueprint="${escHtml(entry.blueprint_file)}"
            data-title="${escHtml(entry.title || entry.url)}"
            data-category="${escHtml(entry.category || 'Domain')}"
            data-url="${escHtml(entry.url)}">
            ${ICONS.blueprint}
            <span>Blueprint</span>
          </button>
        ` : ''}
      </div>
    </article>
  `;
}

// ── Blueprint Modal Viewer ────────────────────────────────────────────────────
let activeBlueprintRaw = '';

async function openBlueprintViewer(blueprintFile, title, category, sourceUrl) {
  const modal = document.getElementById('blueprint-modal');
  const titleEl = document.getElementById('bp-modal-title');
  const catBadge = document.getElementById('bp-category-badge');
  const sourceLink = document.getElementById('bp-source-url');
  const sourceText = document.getElementById('bp-source-url-text');
  const rawGithubLink = document.getElementById('bp-github-raw-link');
  const body = document.getElementById('bp-content-body');

  titleEl.textContent = title;
  catBadge.textContent = category;
  sourceLink.href = sourceUrl;
  sourceText.textContent = sourceUrl.replace(/^https?:\/\//, '').split('/')[0] + '/' + (sourceUrl.split('/')[3] || '');
  
  const cfg = getConfig();
  const rawUrl = `https://raw.githubusercontent.com/${cfg.owner}/${cfg.repo}/main/${blueprintFile}`;
  rawGithubLink.href = rawUrl;

  modal.classList.remove('hidden');
  modal.setAttribute('aria-hidden', 'false');
  body.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Fetching technical blueprint from repository...</p>
    </div>
  `;

  try {
    let md = state.blueprintCache.get(blueprintFile);
    if (!md) {
      const res = await fetch(rawUrl + `?t=${Date.now()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      md = await res.text();
      state.blueprintCache.set(blueprintFile, md);
    }
    activeBlueprintRaw = md;
    body.innerHTML = parseMarkdown(md);
  } catch (err) {
    body.innerHTML = `
      <div class="empty-state">
        <p>Could not fetch blueprint file: <code>${escHtml(blueprintFile)}</code></p>
        <span class="field-hint">${escHtml(err.message)}</span>
      </div>
    `;
  }
}

function closeBlueprintViewer() {
  const modal = document.getElementById('blueprint-modal');
  modal.classList.add('hidden');
  modal.setAttribute('aria-hidden', 'true');
  activeBlueprintRaw = '';
}

// ── Ingestion Dispatch (GitHub Actions) ────────────────────────────────────────
async function dispatchIngestionWorkflow() {
  const cfg = getConfig();
  if (!cfg.pat) {
    showToast('GitHub PAT required. Configure in Settings.', 'error');
    openSettingsModal();
    return;
  }

  const input = document.getElementById('url-input');
  const urls = input.value.trim();
  if (!urls) return;

  const btn = document.getElementById('submit-ingest-btn');
  const statusBar = document.getElementById('ingest-status-bar');
  const statusText = document.getElementById('ingest-status-text');
  const runLink = document.getElementById('ingest-run-link');

  btn.disabled = true;
  statusBar.classList.remove('hidden');
  runLink.classList.add('hidden');
  statusText.textContent = 'Triggering workflow_dispatch in GitHub Actions...';

  try {
    const res = await fetch(`https://api.github.com/repos/${cfg.owner}/${cfg.repo}/actions/workflows/ingest.yml/dispatches`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${cfg.pat}`,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
      },
      body: JSON.stringify({ ref: 'main', inputs: { urls } }),
    });

    if (res.status === 204) {
      showToast('Workflow successfully dispatched!', 'success');
      input.value = '';
      pollLatestRun(cfg);
    } else {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.message || `HTTP ${res.status}`);
    }
  } catch (err) {
    statusBar.classList.remove('hidden');
    statusText.textContent = `Dispatch failed: ${err.message}`;
    btn.disabled = false;
    showToast(`Ingestion error: ${err.message}`, 'error');
  }
}

async function pollLatestRun(cfg) {
  const statusText = document.getElementById('ingest-status-text');
  const runLink = document.getElementById('ingest-run-link');
  const btn = document.getElementById('submit-ingest-btn');

  let attempts = 0;
  clearInterval(state.activeRunPollTimer);

  state.activeRunPollTimer = setInterval(async () => {
    attempts++;
    try {
      const res = await fetch(`https://api.github.com/repos/${cfg.owner}/${cfg.repo}/actions/workflows/ingest.yml/runs?per_page=1`, {
        headers: {
          'Authorization': `Bearer ${cfg.pat}`,
          'Accept': 'application/vnd.github+json',
        }
      });
      if (res.ok) {
        const data = await res.json();
        const latest = data.workflow_runs?.[0];
        if (latest) {
          runLink.href = latest.html_url;
          runLink.classList.remove('hidden');
          statusText.textContent = `Action status: ${latest.status} (${latest.conclusion || 'running'})`;

          if (latest.status === 'completed') {
            clearInterval(state.activeRunPollTimer);
            btn.disabled = false;
            showToast(`Ingestion run finished with: ${latest.conclusion}`, latest.conclusion === 'success' ? 'success' : 'error');
            setTimeout(loadKnowledgeVault, 2000);
          }
        }
      }
    } catch (e) {
      console.warn('Error polling run:', e);
    }

    if (attempts > 60) {
      clearInterval(state.activeRunPollTimer);
      btn.disabled = false;
    }
  }, 4000);
}

// ── Settings Modal ────────────────────────────────────────────────────────────
function openSettingsModal() {
  const cfg = getConfig();
  document.getElementById('cfg-owner').value = cfg.owner || '';
  document.getElementById('cfg-repo').value = cfg.repo || '';
  document.getElementById('cfg-pat').value = cfg.pat || '';
  const modal = document.getElementById('settings-modal');
  modal.classList.remove('hidden');
  modal.setAttribute('aria-hidden', 'false');
}

function closeSettingsModal() {
  const modal = document.getElementById('settings-modal');
  modal.classList.add('hidden');
  modal.setAttribute('aria-hidden', 'true');
}

function saveSettings() {
  const owner = document.getElementById('cfg-owner').value.trim() || 'siaw-dev';
  const repo = document.getElementById('cfg-repo').value.trim() || 'learn-and-build';
  const pat = document.getElementById('cfg-pat').value.trim();

  saveConfig({ owner, repo, pat });
  closeSettingsModal();
  showToast('Settings saved successfully.', 'success');
  loadKnowledgeVault();
}

// ── Application Initialization & Listeners ────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Load Initial Data
  loadKnowledgeVault();

  // Search input reactive
  const searchInput = document.getElementById('search-input');
  searchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value.trim();
    renderCards();
  });

  // Keyboard shortcut '/' to search
  window.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== searchInput && !e.metaKey && !e.ctrlKey) {
      e.preventDefault();
      searchInput.focus();
    } else if (e.key === 'Escape') {
      closeBlueprintViewer();
      closeSettingsModal();
      document.getElementById('ingest-drawer').classList.add('hidden');
    }
  });

  // Source Pills Filtering
  document.querySelectorAll('.source-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.source-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.selectedSource = pill.dataset.source;
      renderCards();
    });
  });

  // Reset category button
  document.getElementById('reset-category-btn').addEventListener('click', () => {
    selectCategory('all');
  });

  // Refresh Vault button
  document.getElementById('refresh-vault-btn').addEventListener('click', () => {
    showToast('Syncing vault with GitHub...', 'info');
    loadKnowledgeVault();
  });

  // Ingestion Drawer Toggle
  const toggleIngestBtn = document.getElementById('toggle-ingest-btn');
  const ingestDrawer = document.getElementById('ingest-drawer');
  toggleIngestBtn.addEventListener('click', () => {
    const isHidden = ingestDrawer.classList.toggle('hidden');
    toggleIngestBtn.classList.toggle('active', !isHidden);
    if (!isHidden) {
      document.getElementById('url-input').focus();
    }
  });

  document.getElementById('close-ingest-drawer').addEventListener('click', () => {
    ingestDrawer.classList.add('hidden');
    toggleIngestBtn.classList.remove('active');
  });

  // URL input change validation
  const urlInput = document.getElementById('url-input');
  const submitIngestBtn = document.getElementById('submit-ingest-btn');
  urlInput.addEventListener('input', () => {
    submitIngestBtn.disabled = !urlInput.value.trim();
  });

  document.getElementById('clear-urls-btn').addEventListener('click', () => {
    urlInput.value = '';
    submitIngestBtn.disabled = true;
  });

  submitIngestBtn.addEventListener('click', dispatchIngestionWorkflow);

  // Blueprint Modal Actions
  document.getElementById('bp-close-btn').addEventListener('click', closeBlueprintViewer);
  document.getElementById('blueprint-modal').addEventListener('click', (e) => {
    if (e.target.id === 'blueprint-modal') closeBlueprintViewer();
  });

  document.getElementById('bp-copy-btn').addEventListener('click', async () => {
    if (!activeBlueprintRaw) return;
    try {
      await navigator.clipboard.writeText(activeBlueprintRaw);
      const label = document.getElementById('bp-copy-label');
      label.textContent = 'Copied!';
      showToast('Blueprint markdown copied to clipboard!', 'success');
      setTimeout(() => { label.textContent = 'Copy MD'; }, 2000);
    } catch {
      showToast('Failed to copy to clipboard', 'error');
    }
  });

  // Settings Modal Actions
  document.getElementById('settings-btn').addEventListener('click', openSettingsModal);
  document.getElementById('settings-close-btn').addEventListener('click', closeSettingsModal);
  document.getElementById('settings-cancel-btn').addEventListener('click', closeSettingsModal);
  document.getElementById('settings-save-btn').addEventListener('click', saveSettings);
  document.getElementById('settings-modal').addEventListener('click', (e) => {
    if (e.target.id === 'settings-modal') closeSettingsModal();
  });
});
