/**
 * dashboard.js — Overview page (index.html)
 * Uses only existing backend routes: GET /clients/, /doctors/, /products/
 * Depends on common.js
 */

const LOW_STOCK_THRESHOLD = 10;
const MAX_LOW_STOCK_ITEMS = 8;

// ============================================
// HELPERS
// ============================================

const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
};

// One failing endpoint must not blank the whole dashboard: resolve to null instead
async function safeGet(path) {
    try {
        const res = await apiFetch(path);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error(`Dashboard fetch error (${path}):`, err);
        addFeedItem(`Could not load ${path}`);
        return null;
    }
}

const isThisMonth = (iso) => {
    const d = new Date(iso);
    const now = new Date();
    return !isNaN(d) && d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
};

const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

function addFeedItem(text) {
    const list = document.getElementById('activity-feed-list');
    if (!list) return;
    const time = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    const li = document.createElement('li');
    li.className = 'feed-item';
    li.innerHTML = `<span class="feed-time">${esc(time)}</span><span class="feed-text">${esc(text)}</span>`;
    list.prepend(li);
}

// ============================================
// RENDERERS
// ============================================

function renderClients(clients) {
    if (!clients) {
        setText('total-clients', '—');
        setText('clients-trend', 'Unavailable');
        setText('new-clients-count', '—');
        document.getElementById('recent-clients-body').innerHTML =
            '<tr><td colspan="5" class="text-center">Could not load clients</td></tr>';
        return;
    }

    const newThisMonth = clients.filter(c => isThisMonth(c.created_at)).length;
    setText('total-clients', clients.length);
    setText('clients-trend', `+${newThisMonth} this month`);
    setText('new-clients-count', newThisMonth);

    const tbody = document.getElementById('recent-clients-body');
    if (!clients.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">No clients yet</td></tr>';
        return;
    }

    const recent = [...clients]
        .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
        .slice(0, 5);

    tbody.innerHTML = recent.map(c => {
        const d = new Date(c.created_at);
        const dateText = isNaN(d)
            ? '—'
            : d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
        return `
            <tr>
                <td title="${esc(c.id)}">#${esc(shortId(c.id))}</td>
                <td>${esc(`${c.first_name || ''} ${c.last_name || ''}`.trim() || '—')}</td>
                <td>${esc(c.phone || '-')}</td>
                <td>${esc(c.email || '-')}</td>
                <td>${esc(dateText)}</td>
            </tr>`;
    }).join('');
}

function renderDoctors(doctors) {
    if (!doctors) {
        setText('total-doctors', '—');
        setText('doctors-trend', 'Unavailable');
        return;
    }
    const specialties = new Set(doctors.map(d => (d.specialty || '').trim().toLowerCase()).filter(Boolean));
    setText('total-doctors', doctors.length);
    setText('doctors-trend', plural(specialties.size, 'specialty').replace('specialtys', 'specialties'));
}

function renderProducts(products) {
    const list = document.getElementById('low-stock-list');

    if (!products) {
        setText('total-products', '—');
        setText('low-stock-count', 'Unavailable');
        setText('rx-products', '—');
        setText('low-stock-total', '—');
        setText('out-of-stock-count', '—');
        list.innerHTML = '<li class="alert-item">Could not load inventory</li>';
        return 0;
    }

    const low = products
        .filter(p => Number(p.stock) < LOW_STOCK_THRESHOLD)
        .sort((a, b) => Number(a.stock) - Number(b.stock));
    const outOfStock = products.filter(p => Number(p.stock) === 0);
    const rxOnly = products.filter(p => p.is_prescription_only);

    setText('total-products', products.length);
    setText('low-stock-count', `${plural(low.length, 'item')} low`);
    setText('rx-products', rxOnly.length);
    setText('rx-trend', products.length ? `${Math.round(rxOnly.length / products.length * 100)}% of stock` : '');
    setText('low-stock-total', low.length);
    setText('out-of-stock-count', outOfStock.length);

    if (!low.length) {
        list.innerHTML = '<li class="alert-item ok">✅ All stock levels are healthy</li>';
        return 0;
    }

    list.innerHTML = low.slice(0, MAX_LOW_STOCK_ITEMS).map(p => {
        const stock = Number(p.stock);
        return `
            <li class="alert-item ${stock === 0 ? 'critical' : 'warning'}">
                <a href="inventory.html?id=${encodeURIComponent(p.id)}">
                    <strong>${esc(p.name)}</strong>
                    <span>${stock === 0 ? 'Out of stock' : `${stock} left`}</span>
                </a>
            </li>`;
    }).join('') + (low.length > MAX_LOW_STOCK_ITEMS
        ? `<li class="alert-item more">+ ${low.length - MAX_LOW_STOCK_ITEMS} more…</li>`
        : '');

    return low.length;
}

function renderNotificationBadge(count) {
    const badge = document.getElementById('notification-count');
    if (!badge) return;
    badge.textContent = count;
    badge.style.display = count ? '' : 'none';
}

// ============================================
// LOADER & INIT
// ============================================

async function loadDashboard() {
    const [clients, doctors, products] = await Promise.all([
        safeGet('/clients/'),
        safeGet('/doctors/'),
        safeGet('/products/')
    ]);

    renderClients(clients);
    renderDoctors(doctors);
    const lowCount = renderProducts(products);
    renderNotificationBadge(lowCount);

    if (clients && doctors && products) {
        addFeedItem(`Loaded ${clients.length} clients, ${doctors.length} doctors, ${products.length} products`);
    }
}

// ============================================
// CHATBOT (POST /chatbot/ -> { reply })
// ============================================

const BOT_AVATAR = 'assets/img/Mockup_de_base.png';

function initChatbot() {
    const win = document.getElementById('chat-window');
    const input = document.getElementById('user-input');
    const btn = document.getElementById('send-btn');
    const logo = document.getElementById('bot-logo');
    if (!win || !input || !btn) return;

    // textContent only: bot replies are never interpreted as HTML
    const addMsg = (role, text) => {
        const div = document.createElement('div');
        div.className = `message ${role}`;
        if (role === 'bot') {
            const img = document.createElement('img');
            img.src = BOT_AVATAR;
            img.alt = '';
            img.className = 'mini-avatar';
            img.onerror = () => img.remove();
            div.appendChild(img);
        }
        const span = document.createElement('span');
        span.textContent = text;
        div.appendChild(span);
        win.appendChild(div);
        win.scrollTop = win.scrollHeight;
    };

    let busy = false;
    const send = async () => {
        const msg = input.value.trim();
        if (!msg || busy) return;
        busy = true;
        btn.disabled = true;
        addMsg('user', msg);
        input.value = '';
        logo?.classList.add('thinking');

        try {
            const res = await apiFetch('/chatbot/', { method: 'POST', body: JSON.stringify({ message: msg }) });
            if (!res.ok) throw new Error(await errorMessage(res, `HTTP ${res.status}`));
            const data = await res.json();
            addMsg('bot', data.reply || '…');
        } catch (err) {
            console.error('Chatbot error:', err);
            addMsg('bot', 'Connection error.');
        } finally {
            busy = false;
            btn.disabled = false;
            logo?.classList.remove('thinking');
            input.focus();
        }
    };

    btn.addEventListener('click', send);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
    addMsg('bot', 'Hello! Ask me about a drug, an interaction or your stock.');
}

// ============================================
// TEAM NOTES (GET/POST /notes/, DELETE /notes/<id>)
// ============================================

async function loadNotes() {
    const list = document.getElementById('team-notif-list');
    if (!list) return;
    try {
        const res = await apiFetch('/notes/');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const notes = await res.json();

        if (!notes || !notes.length) {
            list.innerHTML = '<li class="item-entry">No notes available.</li>';
            return;
        }

        const { isAdmin } = getAuthInfo();
        notes.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));

        list.innerHTML = notes.map(note => {
            const d = new Date(note.created_at);
            const when = isNaN(d)
                ? 'N/A'
                : d.toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
            return `
                <li class="item-entry">
                    <div class="info">
                        <strong>📌</strong> ${esc(note.text)}
                        <small>⌚ ${esc(when)}</small>
                    </div>
                    ${isAdmin ? `<button type="button" class="del-note" data-id="${esc(note.id)}" title="Delete">🗑️</button>` : ''}
                </li>`;
        }).join('');
    } catch (err) {
        console.error('Notes load error:', err);
        list.innerHTML = '<li class="item-entry text-danger">Error loading notes.</li>';
    }
}

function initNotes() {
    const input = document.getElementById('new-note-text');
    const addBtn = document.getElementById('add-note-btn');
    const list = document.getElementById('team-notif-list');
    if (!input || !addBtn || !list) return;

    const add = async () => {
        const text = input.value.trim();
        if (!text) return;
        addBtn.disabled = true;
        try {
            const res = await apiFetch('/notes/', { method: 'POST', body: JSON.stringify({ text }) });
            if (!res.ok) throw new Error(await errorMessage(res, 'Could not save the note'));
            input.value = '';
            await loadNotes();
        } catch (err) {
            console.error('Note save error:', err);
            alert(err.message);
        } finally {
            addBtn.disabled = false;
        }
    };

    addBtn.addEventListener('click', add);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') add(); });

    list.addEventListener('click', async (e) => {
        const btn = e.target.closest('.del-note');
        if (!btn) return;
        if (!getAuthInfo().isAdmin) return alert('Admin privileges required');
        try {
            const res = await apiFetch(`/notes/${btn.dataset.id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error(await errorMessage(res, 'Delete failed'));
            await loadNotes();
        } catch (err) {
            console.error('Note delete error:', err);
            alert(err.message);
        }
    });

    loadNotes();
}

// ============================================
// TICKETS (POST /tickets/ { subject, priority, description })
// ============================================

function initTickets() {
    const modal = document.getElementById('ticket-modal');
    const openBtn = document.getElementById('open-ticket-btn');
    const closeBtn = document.getElementById('close-ticket-modal');
    const form = document.getElementById('ticket-form');
    if (!modal || !openBtn || !form) return;

    const close = () => { modal.style.display = 'none'; };
    openBtn.addEventListener('click', () => { modal.style.display = 'block'; });
    closeBtn?.addEventListener('click', close);
    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        const payload = {
            subject: fd.get('subject').trim(),
            priority: fd.get('priority'),
            description: fd.get('description').trim()
        };
        try {
            const res = await apiFetch('/tickets/', { method: 'POST', body: JSON.stringify(payload) });
            if (!res.ok) throw new Error(await errorMessage(res, 'Could not send the ticket'));
            alert('Ticket sent successfully!');
            addFeedItem(`Ticket sent: ${payload.subject}`);
            form.reset();
            close();
        } catch (err) {
            console.error('Ticket error:', err);
            alert(err.message);
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    if (!initPage()) return;
    highlightActiveLink();
    initChatbot();
    initNotes();
    initTickets();
    setText('welcome-text', `Welcome back, ${localStorage.getItem('username') || 'Operator'}`);
    addFeedItem('Session started');
    loadDashboard();
});