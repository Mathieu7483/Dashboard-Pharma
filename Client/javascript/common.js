/**
 * common.js — Shared helpers for index, clients, doctors, inventory.
 * Must be loaded BEFORE the page script.
 */

// Same origin as the page when Flask serves the front (port 5000); otherwise fall back to localhost
const API_ORIGIN = window.location.port === '5000' ? window.location.origin : 'http://127.0.0.1:5000';
const API_BASE = API_ORIGIN;

const CookieManager = {
    get: (name) => {
        const match = document.cookie.split('; ').find(c => c.startsWith(name + '='));
        return match ? match.substring(name.length + 1) : null;
    }
};

const esc = (v) => String(v ?? '').replace(/[&<>"']/g, ch => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
));

const shortId = (id) => String(id ?? '').slice(0, 8);

function getAuthInfo() {
    const token = CookieManager.get('access_token');
    if (!token) return { token: null, isAdmin: false };
    try {
        const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        const payload = JSON.parse(atob(b64));
        const isAdmin = payload.is_admin === true || payload.sub?.role === 'admin';
        return { token, isAdmin };
    } catch {
        return { token: null, isAdmin: false };
    }
}

async function apiFetch(path, options = {}) {
    const { token } = getAuthInfo();
    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            ...options.headers
        }
    });
    if (res.status === 401) {
        logoutUser();
        throw new Error('Session expired');
    }
    return res;
}

// Readable message from a Flask-RESTX error response
async function errorMessage(res, fallback = 'Request failed') {
    const err = await res.json().catch(() => ({}));
    const details = err.errors ? Object.values(err.errors).join(', ') : '';
    return [err.message, details].filter(Boolean).join(' — ') || fallback;
}

function logoutUser() {
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    localStorage.clear();
    window.location.href = 'auth.html';
}

function updateDynamicUserUI() {
    const user = localStorage.getItem('username') || 'Operator';
    document.querySelectorAll('.avatar').forEach(el => el.textContent = user.charAt(0).toUpperCase());
    document.querySelectorAll('.user-name').forEach(el => el.textContent = user);
    const sidebarName = document.querySelector('.sidebar-footer strong');
    if (sidebarName) sidebarName.textContent = user;
}

// The <script> inside navbar.html never runs once injected via innerHTML,
// so the active link is highlighted here instead.
function highlightActiveLink() {
    const page = window.location.pathname.split('/').pop() || 'index.html';
    const ids = {
        'index.html': 'nav-dashboard',
        'inventory.html': 'nav-inventory',
        'clients.html': 'nav-clients',
        'doctors.html': 'nav-doctors',
        'settings.html': 'nav-settings'
    };
    document.getElementById(ids[page])?.classList.add('active');
    // Settings is admin-only (settings.js redirects non-admins anyway)
    if (!getAuthInfo().isAdmin) document.getElementById('nav-settings')?.closest('li')?.remove();
}

function loadNavbar() {
    const placeholder = document.getElementById('navbar-placeholder');
    if (!placeholder) return;
    fetch('navbar.html')
        .then(res => res.text())
        .then(html => {
            placeholder.innerHTML = html;
            highlightActiveLink();
            updateDynamicUserUI();
        })
        .catch(err => console.error('Navbar loading failed:', err));
}

function bindModalClose(modalId, closeBtnId) {
    const modal = document.getElementById(modalId);
    const close = () => { modal.style.display = 'none'; };
    document.getElementById(closeBtnId)?.addEventListener('click', close);
    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });
}

// Common page boot: auth guard, user UI, navbar, logout. Returns false if redirected.
function initPage() {
    if (!getAuthInfo().token) {
        window.location.href = 'auth.html';
        return false;
    }
    updateDynamicUserUI();
    loadNavbar();
    document.getElementById('logout-btn')?.addEventListener('click', logoutUser);
    return true;
}