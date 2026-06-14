// ── STARTUP ───────────────────────────────────────────
const API = '';
let currentUser = null;
let reportsLoaded = false;

Chart.defaults.color = 'rgba(255,255,255,0.5)';
Chart.defaults.font  = { family: 'Inter', size: 11 };

const fmt  = n => '$' + Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 });
const fmt2 = n => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const gridColor    = 'rgba(255,255,255,0.04)';
const tooltipStyle = {
    backgroundColor: '#1a1a2e',
    borderColor:     'rgba(255,255,255,0.1)',
    borderWidth:     1,
    titleColor:      '#fff',
    bodyColor:       'rgba(255,255,255,0.6)',
    padding:         10
};

const apiFetch = (url, options = {}) => fetch(`${API}${url}`, {
    credentials: 'include',
    ...options
});

// ── AUTH ──────────────────────────────────────────────
function switchAuthTab(tab) {
    const isLogin = tab === 'login';
    document.getElementById('login-form').style.display    = isLogin ? 'block' : 'none';
    document.getElementById('register-form').style.display = isLogin ? 'none'  : 'block';
    document.getElementById('login-tab').style.background    = isLogin ? '#3B6BF5' : 'transparent';
    document.getElementById('register-tab').style.background = isLogin ? 'transparent' : '#3B6BF5';
    document.getElementById('login-tab').style.color    = isLogin ? '#fff' : 'rgba(255,255,255,0.5)';
    document.getElementById('register-tab').style.color = isLogin ? 'rgba(255,255,255,0.5)' : '#fff';
}

async function handleLogin() {
    const email    = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const errorEl  = document.getElementById('login-error');
    try {
        const res  = await apiFetch('/api/auth/login', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) { errorEl.textContent = data.error; errorEl.style.display = 'block'; return; }
        currentUser = data.user;
        updateUserUI();
        checkAndShowDashboard();
    } catch(e) {
        errorEl.textContent = 'Connection error. Is the server running?';
        errorEl.style.display = 'block';
    }
}

async function handleRegister() {
    const username = document.getElementById('reg-username').value;
    const email    = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const errorEl  = document.getElementById('register-error');
    try {
        const res  = await apiFetch('/api/auth/register', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ username, email, password })
        });
        const data = await res.json();
        if (!res.ok) { errorEl.textContent = data.error; errorEl.style.display = 'block'; return; }
        currentUser = data.user;
        updateUserUI();
        checkAndShowDashboard();
    } catch(e) {
        errorEl.textContent = 'Connection error.';
        errorEl.style.display = 'block';
    }
}

async function handleLogout() {
    await apiFetch('/api/auth/logout', { method: 'POST' });
    currentUser = null;
    reportsLoaded = false;
    showPage('auth');
}

async function checkAndShowDashboard() {
    const res = await apiFetch('/api/summary');
    if (res.status === 404) { showPage('upload'); return; }
    if (res.ok) {
        showPage('dashboard');
        initDashboard();
        return;
    }
    showPage('auth');
}

function updateUserUI() {
    if (!currentUser) return;
    const name = currentUser.username;
    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening';
    const nameEl   = document.getElementById('nav-username');
    const greetEl  = document.querySelector('#page-dashboard .page-header h1');
    const avatarEl = document.querySelector('.nav-avatar');
    if (nameEl)   nameEl.textContent  = name;
    if (greetEl)  greetEl.textContent = greeting + ', ' + name + ' 👋';
    if (avatarEl) avatarEl.textContent = name.charAt(0).toUpperCase();
}

function showPage(name) {
    document.getElementById('auth-page').style.display   = name === 'auth'   ? 'block' : 'none';
    document.getElementById('upload-page').style.display = name === 'upload' ? 'block' : 'none';
    const appPages  = document.getElementById('app-pages');
    const isAppPage = !['auth', 'upload'].includes(name);
    appPages.style.display = isAppPage ? 'block' : 'none';
    if (isAppPage) switchPage(name);
}

async function handleFileUpload(event) {
    const file     = event.target.files[0];
    const statusEl = document.getElementById('upload-status');
    if (!file) return;
    statusEl.textContent = 'Uploading and analyzing...';
    const formData = new FormData();
    formData.append('file', file);
    const res  = await apiFetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if (res.ok) {
        statusEl.textContent = data.message;
        setTimeout(() => { showPage('dashboard'); initDashboard(); }, 1000);
    } else {
        statusEl.style.color = '#f87171';
        statusEl.textContent = 'Error: ' + data.error;
    }
}

function handleFileDrop(event) {
    event.preventDefault();
    handleFileUpload({ target: { files: [event.dataTransfer.files[0]] } });
}

async function useSampleData() {
    const statusEl = document.getElementById('upload-status');
    statusEl.textContent = 'Loading sample data...';
    const res  = await apiFetch('/api/load-sample', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
        statusEl.textContent = data.message;
        setTimeout(() => { showPage('dashboard'); initDashboard(); }, 1000);
    } else {
        statusEl.style.color = '#f87171';
        statusEl.textContent = 'Error: ' + data.error;
    }
}

// ── NAVIGATION ────────────────────────────────────────
function switchPage(name) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const page = document.getElementById('page-' + name);
    const nav  = document.querySelector(`[data-page="${name}"]`);
    if (page) page.classList.add('active');
    if (nav)  nav.classList.add('active');
    if (name === 'transactions') loadAllTransactions();
    if (name === 'reports')      loadReports();
    if (name === 'ai')           loadAIStats();
    if (name === 'compare')      loadComparison();
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => switchPage(item.dataset.page));
    });
});

// ── RIPPLE EFFECT ─────────────────────────────────────
document.addEventListener('click', e => {
    const el = e.target.closest('button, .nav-item, .suggestion-btn');
    if (!el) return;
    const ripple = document.createElement('span');
    const rect   = el.getBoundingClientRect();
    const size   = Math.max(rect.width, rect.height);
    ripple.className = 'ripple';
    ripple.style.cssText = `
        width: ${size}px;
        height: ${size}px;
        left: ${e.clientX - rect.left - size/2}px;
        top: ${e.clientY - rect.top - size/2}px;
    `;
    el.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
});

// ── DRAG AND DROP ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const zone = document.getElementById('upload-zone');
    if (!zone) return;
    zone.addEventListener('dragenter', () => zone.classList.add('drag-active'));
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-active'));
    zone.addEventListener('drop',      () => zone.classList.remove('drag-active'));
});

// ── NUMBER ANIMATION ──────────────────────────────────
function animateNumber(elementId, targetValue, prefix = '$', duration = 1000) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const startTime = performance.now();
    function update(currentTime) {
        const elapsed  = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased    = 1 - Math.pow(1 - progress, 3);
        const current  = Math.floor(targetValue * eased);
        el.textContent = prefix + current.toLocaleString('en-US');
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

// ── SUMMARY ───────────────────────────────────────────
async function loadSummary() {
    const data = await apiFetch('/api/summary').then(r => r.json());
    animateNumber('total-spent', data.total_spent, '$');
    animateNumber('monthly-avg', data.monthly_avg, '$');
    document.getElementById('top-category').textContent      = data.top_category;
    document.getElementById('top-category-amt').textContent  = fmt(data.top_category_amt) + ' annual spend';
    document.getElementById('transaction-count').textContent = data.transaction_count + ' transactions';
    animateNumber('anomaly-count', data.anomaly_count, '');
    document.getElementById('anomaly-badge').textContent = data.anomaly_count + ' flagged';
}

// ── TREND CHART ───────────────────────────────────────
async function loadTrendChart() {
    const data   = await apiFetch('/api/monthly').then(r => r.json());
    const labels = data.map(d => d.Month_Name);
    const values = data.map(d => d.Amount);
    const avg    = values.length > 0 ? values.reduce((a,b) => a+b, 0) / values.length : 0;

    new Chart(document.getElementById('trendChart'), {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Monthly Spend',
                    data: values,
                    borderColor: '#3B6BF5',
                    borderWidth: 2.5,
                    pointBackgroundColor: labels.map(m => ['May','June'].includes(m) ? '#ef4444' : '#3B6BF5'),
                    pointRadius: labels.map(m => ['May','June'].includes(m) ? 8 : 4),
                    pointHoverRadius: 10,
                    pointHoverBackgroundColor: labels.map(m => ['May','June'].includes(m) ? '#ef4444' : '#6B9BF5'),
                    pointHoverBorderColor: '#fff',
                    pointHoverBorderWidth: 2,
                    fill: true,
                    backgroundColor: ctx => {
                        const g = ctx.chart.ctx.createLinearGradient(0,0,0,280);
                        g.addColorStop(0, 'rgba(59,107,245,0.25)');
                        g.addColorStop(1, 'rgba(59,107,245,0)');
                        return g;
                    },
                    tension: 0.35
                },
                {
                    label: `Avg ${fmt(avg)}`,
                    data: Array(values.length).fill(avg),
                    borderColor: 'rgba(249,115,22,0.5)',
                    borderWidth: 1.5,
                    borderDash: [6,4],
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: { ...tooltipStyle, callbacks: { label: ctx => ctx.datasetIndex === 0 ? ` Spent: ${fmt(ctx.raw)}` : ` Avg: ${fmt(ctx.raw)}` } }
            },
            scales: {
                x: { grid: { color: gridColor } },
                y: { grid: { color: gridColor }, ticks: { callback: v => '$' + (v/1000).toFixed(0) + 'k' } }
            }
        }
    });
}

// ── CATEGORY CHART ────────────────────────────────────
async function loadCategoryChart() {
    const data   = await apiFetch('/api/categories').then(r => r.json());
    const sorted = [...data].sort((a,b) => a.Amount - b.Amount);

    new Chart(document.getElementById('categoryChart'), {
        type: 'bar',
        data: {
            labels: sorted.map(d => d.Category),
            datasets: [{
                data: sorted.map(d => d.Amount),
                backgroundColor: sorted.map((_,i) => `rgba(59,107,245,${0.3 + (i/sorted.length)*0.7})`),
                borderRadius: 4, borderSkipped: false
            }]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { ...tooltipStyle, callbacks: { label: ctx => ' ' + fmt(ctx.raw) } } },
            scales: {
                x: { grid: { color: gridColor }, ticks: { callback: v => '$' + (v/1000).toFixed(0) + 'k' } },
                y: { grid: { display: false } }
            }
        }
    });
}

// ── BUDGET CHART ──────────────────────────────────────
async function loadBudgetChart() {
    const data = await apiFetch('/api/budget').then(r => r.json());
    if (!data.length) return;

    new Chart(document.getElementById('budgetChart'), {
        type: 'bar',
        data: {
            labels: data.map(d => d.Category),
            datasets: [
                { label: 'Actual', data: data.map(d => d.Actual),        backgroundColor: 'rgba(59,107,245,0.8)',  borderRadius: 4, borderSkipped: false },
                { label: 'Budget', data: data.map(d => d.Annual_Budget), backgroundColor: 'rgba(249,115,22,0.7)', borderRadius: 4, borderSkipped: false }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { ...tooltipStyle, callbacks: { label: ctx => ' ' + fmt(ctx.raw) } } },
            scales: {
                x: { grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 30 } },
                y: { grid: { color: gridColor }, ticks: { callback: v => '$' + (v/1000).toFixed(0) + 'k' } }
            }
        }
    });
}

// ── ANOMALY CHART ─────────────────────────────────────
async function loadAnomalyChart() {
    const existing = Chart.getChart('anomalyChart');
    if (existing) existing.destroy();
    const data = await apiFetch('/api/anomalies').then(r => r.json());
    if (!data.length) return;

    new Chart(document.getElementById('anomalyChart'), {
        type: 'bar',
        data: {
            labels: data.map(d => d.Description + ' (' + d.Category + ')'),
            datasets: [{
                data: data.map(d => d.Times_Over),
                backgroundColor: data.map(d => d.Times_Over >= 10 ? 'rgba(239,68,68,0.8)' : d.Times_Over >= 5 ? 'rgba(249,115,22,0.8)' : 'rgba(245,158,11,0.8)'),
                borderRadius: 4, borderSkipped: false
            }]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { ...tooltipStyle, callbacks: { label: ctx => ' ' + ctx.raw + '× category average' } } },
            scales: {
                x: { grid: { color: gridColor }, ticks: { callback: v => v + 'x' } },
                y: { grid: { display: false }, ticks: { font: { size: 11 } } }
            }
        }
    });
}

// ── TRANSACTIONS ──────────────────────────────────────
function renderRows(data) {
    if (!data.length) return '<tr><td colspan="6" class="loading">No transactions found</td></tr>';
    return data.map(t => {
        const flagged = t.is_anomaly && t.amount > 500;
        return `<tr class="${flagged ? 'flagged' : ''}">
            <td>${t.date        || '—'}</td>
            <td>${t.description || '—'}</td>
            <td>${t.category    || '—'}</td>
            <td>${t.account     || t.account_name || '—'}</td>
            <td style="text-align:right;" class="amount-cell ${flagged ? 'flagged' : ''}">${fmt2(t.amount || 0)}</td>
            <td style="text-align:right;">
                <span class="status-badge ${flagged ? 'status-flagged' : 'status-cleared'}">
                    ${flagged ? 'Flagged' : 'Cleared'}
                </span>
            </td>
        </tr>`;
    }).join('');
}

async function loadTransactions() {
    const data = await apiFetch('/api/transactions').then(r => r.json());
    document.getElementById('transactions-body').innerHTML = renderRows(data);
}

// ── ALL TRANSACTIONS ──────────────────────────────────
async function loadAllTransactions() {
    const month    = document.getElementById('filter-month')?.value    || 'All';
    const category = document.getElementById('filter-category')?.value || 'All';
    const account  = document.getElementById('filter-account')?.value  || 'All';
    const search   = document.getElementById('search-input')?.value    || '';
    const params   = new URLSearchParams({ month, category, account, search });
    const data     = await apiFetch(`/api/transactions/all?${params}`).then(r => r.json());
    document.getElementById('filter-count').textContent        = data.length + ' results';
    document.getElementById('all-transactions-body').innerHTML = renderRows(data);
}

function filterTransactions() { loadAllTransactions(); }

// ── FILTERS ───────────────────────────────────────────
async function loadFilters() {
    const data = await apiFetch('/api/filters').then(r => r.json());
    const populate = (id, items) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = items.map(i => `<option>${i}</option>`).join('');
    };
    populate('filter-month',    data.months);
    populate('filter-category', data.categories);
    populate('filter-account',  data.accounts);
}

// ── REPORTS ───────────────────────────────────────────
async function loadReports() {
    if (reportsLoaded) return;
    reportsLoaded = true;
    const data = await apiFetch('/api/reports').then(r => r.json());

    document.getElementById('monthly-report-body').innerHTML = data.monthly.map(m => `
        <tr>
            <td>${m.Month_Name || m.month_name}</td>
            <td style="text-align:right;">${fmt(m.total)}</td>
            <td style="text-align:right;">${m.count}</td>
            <td style="text-align:right;">${fmt(m.avg)}</td>
        </tr>
    `).join('');

    new Chart(document.getElementById('accountChart'), {
        type: 'doughnut',
        data: {
            labels: data.by_account.map(a => a.account),
            datasets: [{
                data: data.by_account.map(a => a.total),
                backgroundColor: ['rgba(59,107,245,0.8)', 'rgba(249,115,22,0.8)', 'rgba(34,197,94,0.8)'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { padding: 16, font: { size: 12 } } },
                tooltip: { ...tooltipStyle, callbacks: { label: ctx => ' ' + fmt(ctx.raw) } }
            }
        }
    });

    document.getElementById('merchants-body').innerHTML = data.top_merchants.map(m => `
        <tr>
            <td>${m.Description || m.description}</td>
            <td style="text-align:right;">${fmt(m.Amount || m.amount)}</td>
        </tr>
    `).join('');
}

// ── AI COACH ──────────────────────────────────────────
let chatHistory = [];

async function loadAIStats() {
    const data = await apiFetch('/api/summary').then(r => r.json());
    document.getElementById('ai-total').textContent     = fmt(data.total_spent);
    document.getElementById('ai-health').textContent    = data.health_score?.score + '/100' || '—';
    document.getElementById('ai-anomalies').textContent = data.anomaly_count + ' detected';
    document.getElementById('ai-top-cat').textContent   = data.top_category;
}

function askSuggestion(btn) {
    document.getElementById('chat-input').value = btn.textContent;
    sendMessage();
}

async function sendMessage() {
    const input   = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;
    input.value = '';

    const messages = document.getElementById('chat-messages');
    messages.innerHTML += `<div class="user-message"><div class="user-bubble">${message}</div></div>`;

    const typingId = 'typing-' + Date.now();
    messages.innerHTML += `<div class="ai-message" id="${typingId}"><div class="typing-bubble">Nomi is thinking...</div></div>`;
    messages.scrollTop = messages.scrollHeight;

    try {
        const res  = await apiFetch('/api/ai/chat', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ message, history: chatHistory })
        });
        const data = await res.json();
        document.getElementById(typingId)?.remove();

        if (data.response) {
            chatHistory.push(
                { role: 'user',      content: message },
                { role: 'assistant', content: data.response }
            );
            messages.innerHTML += `<div class="ai-message"><div class="ai-bubble">${data.response.replace(/\n/g, '<br>')}</div></div>`;
        } else {
            messages.innerHTML += `<div class="ai-message"><div class="ai-bubble" style="color:#f87171;">Error: ${data.error || 'Something went wrong'}</div></div>`;
        }
    } catch(e) {
        document.getElementById(typingId)?.remove();
        messages.innerHTML += `<div class="ai-message"><div class="ai-bubble" style="color:#f87171;">Connection error. Please try again.</div></div>`;
    }
    messages.scrollTop = messages.scrollHeight;
}

// ── SETTINGS ──────────────────────────────────────────
async function handleSettingsUpload(event) {
    const file     = event.target.files[0];
    const statusEl = document.getElementById('settings-upload-status');
    if (!file) return;
    statusEl.style.color = 'rgba(255,255,255,0.4)';
    statusEl.textContent = 'Uploading and analyzing...';
    const formData = new FormData();
    formData.append('file', file);
    const res  = await apiFetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if (res.ok) {
        statusEl.style.color = '#4ade80';
        statusEl.textContent = '✅ ' + data.message;
        reportsLoaded = false;
        setTimeout(() => { showPage('dashboard'); initDashboard(); }, 1500);
    } else {
        statusEl.style.color = '#f87171';
        statusEl.textContent = '❌ Error: ' + data.error;
    }
}

async function reloadSampleData() {
    const statusEl = document.getElementById('settings-upload-status');
    statusEl.style.color = 'rgba(255,255,255,0.4)';
    statusEl.textContent = 'Loading sample data...';
    const res  = await apiFetch('/api/load-sample', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
        statusEl.style.color = '#4ade80';
        statusEl.textContent = '✅ ' + data.message;
        reportsLoaded = false;
        setTimeout(() => { showPage('dashboard'); initDashboard(); }, 1500);
    } else {
        statusEl.style.color = '#f87171';
        statusEl.textContent = '❌ Error: ' + data.error;
    }
}

// ── SQL INSIGHTS ──────────────────────────────────────
async function loadSQLInsights() {
    try {
        const res = await apiFetch('/api/sql-insights');
        if (!res.ok) return;
        const data = await res.json();

        const merchantsBody = document.getElementById('sql-merchants-body');
        if (merchantsBody && data.top_merchants) {
            merchantsBody.innerHTML = data.top_merchants.map(r => `
                <tr>
                    <td>${r.description}</td>
                    <td style="text-align:right;">$${r.total_spent.toLocaleString()}</td>
                    <td style="text-align:right;">${r.transaction_count}</td>
                </tr>
            `).join('');
        }

        const accountsBody = document.getElementById('sql-accounts-body');
        if (accountsBody && data.by_account) {
            accountsBody.innerHTML = data.by_account.map(r => `
                <tr>
                    <td>${r.account}</td>
                    <td style="text-align:right;">$${r.total.toLocaleString()}</td>
                    <td style="text-align:right;">$${r.avg_amount}</td>
                </tr>
            `).join('');
        }

        const biggestBody = document.getElementById('sql-biggest-body');
        if (biggestBody && data.biggest) {
            biggestBody.innerHTML = data.biggest.map(r => `
                <tr>
                    <td>${r.description}</td>
                    <td>${r.category}</td>
                    <td style="text-align:right; color:#f87171;">$${r.amount.toLocaleString()}</td>
                </tr>
            `).join('');
        }

        const categoriesBody = document.getElementById('sql-categories-body');
        if (categoriesBody && data.categories) {
            categoriesBody.innerHTML = data.categories.map(r => `
                <tr>
                    <td>${r.category}</td>
                    <td style="text-align:right;">$${r.total.toLocaleString()}</td>
                    <td style="text-align:right;">${r.percentage}%</td>
                </tr>
            `).join('');
        }

    } catch(e) {
        console.error('SQL insights error:', e);
    }
}
// ── YEAR COMPARISON ──────────────────────────────────
let compareChart1 = null;
let compareChart2 = null;
let compareMonthlyChart = null;

async function loadComparison() {
    const year1 = document.getElementById('year1-select').value;
    const year2 = document.getElementById('year2-select').value;

    const res  = await apiFetch(`/api/yearly-comparison?year1=${year1}&year2=${year2}`);
    const json = await res.json();

    const d1 = json.data[year1];
    const d2 = json.data[year2];

    // Update labels
    document.getElementById('compare-year1-label').textContent = year1;
    document.getElementById('compare-year2-label').textContent = year2;
    document.getElementById('legend-year1').textContent = year1;
    document.getElementById('legend-year2').textContent = year2;
    document.getElementById('compare-cat-title-1').textContent = year1 + ' — Top Categories';
    document.getElementById('compare-cat-title-2').textContent = year2 + ' — Top Categories';

    // KPI cards
    document.getElementById('compare-total-1').textContent = fmt(d1.total);
    document.getElementById('compare-total-2').textContent = fmt(d2.total);
    document.getElementById('compare-avg-1').textContent   = fmt(d1.avg);
    document.getElementById('compare-avg-2').textContent   = fmt(d2.avg);
    document.getElementById('compare-anomalies-1').textContent = d1.anomalies;
    document.getElementById('compare-anomalies-2').textContent = d2.anomalies;

    // Difference
    const diff    = d2.total - d1.total;
    const diffPct = d1.total > 0 ? ((diff / d1.total) * 100).toFixed(1) : 0;
    const diffEl  = document.getElementById('compare-diff-pct');
    const diffLbl = document.getElementById('compare-diff-label');
    const totalDiffEl = document.getElementById('compare-total-diff');
    diffEl.textContent  = (diff > 0 ? '+' : '') + diffPct + '%';
    diffEl.style.color  = diff > 0 ? '#FF3B30' : '#34C759';
    diffLbl.textContent = diff > 0 ? year2 + ' spent more' : year2 + ' spent less';
    totalDiffEl.textContent = (diff > 0 ? '▲ ' : '▼ ') + fmt(Math.abs(diff)) + ' difference';
    totalDiffEl.style.color = diff > 0 ? '#FF3B30' : '#34C759';

    // Monthly trend chart
    const allMonths = ['January','February','March','April','May','June','July','August','September','October','November','December'];
    const getMonthly = (d) => allMonths.map(m => {
        const found = d.monthly.find(x => x.month === m);
        return found ? found.total : null;
    });

    if (compareMonthlyChart) compareMonthlyChart.destroy();
    compareMonthlyChart = new Chart(document.getElementById('compareMonthlyChart'), {
        type: 'line',
        data: {
            labels: allMonths.map(m => m.slice(0,3)),
            datasets: [
                {
                    label: year1,
                    data: getMonthly(d1),
                    borderColor: '#3B6BF5',
                    backgroundColor: 'rgba(59,107,245,0.1)',
                    borderWidth: 2.5,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    fill: true,
                    tension: 0.35,
                    spanGaps: true
                },
                {
                    label: year2,
                    data: getMonthly(d2),
                    borderColor: '#f97316',
                    backgroundColor: 'rgba(249,115,22,0.1)',
                    borderWidth: 2.5,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    fill: true,
                    tension: 0.35,
                    spanGaps: true
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: { ...tooltipStyle, callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmt(ctx.raw)}` } }
            },
            scales: {
                x: { grid: { color: gridColor } },
                y: { grid: { color: gridColor }, ticks: { callback: v => '$' + (v/1000).toFixed(0) + 'k' } }
            }
        }
    });

    // Category charts
    if (compareChart1) compareChart1.destroy();
    compareChart1 = new Chart(document.getElementById('compareCat1Chart'), {
        type: 'bar',
        data: {
            labels: d1.categories.map(c => c.name.split(' ')[0]),
            datasets: [{ data: d1.categories.map(c => c.total), backgroundColor: 'rgba(59,107,245,0.7)', borderRadius: 4, borderSkipped: false }]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { ...tooltipStyle, callbacks: { label: ctx => ' ' + fmt(ctx.raw) } } },
            scales: { x: { grid: { color: gridColor }, ticks: { callback: v => '$' + (v/1000).toFixed(0) + 'k' } }, y: { grid: { display: false } } }
        }
    });

    if (compareChart2) compareChart2.destroy();
    compareChart2 = new Chart(document.getElementById('compareCat2Chart'), {
        type: 'bar',
        data: {
            labels: d2.categories.map(c => c.name.split(' ')[0]),
            datasets: [{ data: d2.categories.map(c => c.total), backgroundColor: 'rgba(249,115,22,0.7)', borderRadius: 4, borderSkipped: false }]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { ...tooltipStyle, callbacks: { label: ctx => ' ' + fmt(ctx.raw) } } },
            scales: { x: { grid: { color: gridColor }, ticks: { callback: v => '$' + (v/1000).toFixed(0) + 'k' } }, y: { grid: { display: false } } }
        }
    });

    // Insights
    const insights = [];
    if (diff < 0) insights.push(`✅ Spent ${fmt(Math.abs(diff))} less in ${year2} than ${year1} — a ${Math.abs(diffPct)}% improvement`);
    else insights.push(`⚠️ Spent ${fmt(diff)} more in ${year2} than ${year1} — a ${diffPct}% increase`);

    const top1 = d1.categories[0];
    const top2 = d2.categories[0];
    if (top1) insights.push(`📌 ${year1} biggest category: ${top1.name} at ${fmt(top1.total)}`);
    if (top2) insights.push(`📌 ${year2} biggest category: ${top2.name} at ${fmt(top2.total)}`);

    if (d1.anomalies !== d2.anomalies) {
        const anomDiff = d2.anomalies - d1.anomalies;
        insights.push(`${anomDiff > 0 ? '⚠️' : '✅'} Anomalies ${anomDiff > 0 ? 'increased' : 'decreased'} from ${d1.anomalies} to ${d2.anomalies}`);
    }

    document.getElementById('compare-insights').innerHTML = insights.map(i =>
        `<div style="padding:10px 14px; background:rgba(255,255,255,0.03); border-radius:8px; font-size:13px; color:rgba(255,255,255,0.8); border-left:3px solid #3B6BF5;">${i}</div>`
    ).join('');
}

// ── SQL TOGGLE ────────────────────────────────────────
function toggleSQL(btn) {
    const pre = btn.nextElementSibling;
    const visible = pre.style.display === 'block';
    pre.style.display = visible ? 'none' : 'block';
    btn.textContent = visible ? 'Show SQL ▼' : 'Hide SQL ▲';
}

// ── INIT ──────────────────────────────────────────────
async function initDashboard() {
    await Promise.all([
        loadSummary(),
        loadTrendChart(),
        loadCategoryChart(),
        loadBudgetChart(),
        loadAnomalyChart(),
        loadTransactions(),
        loadFilters(),
        loadSQLInsights()
    ]);
    updateUserUI();
}

async function startup() {
    const res = await apiFetch('/api/auth/me');
    if (res.ok) {
        currentUser = await res.json();
        updateUserUI();
        checkAndShowDashboard();
    } else {
        showPage('auth');
    }
}

startup();