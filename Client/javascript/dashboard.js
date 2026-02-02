/**
 * PHARMA DASHBOARD - MAIN JAVASCRIPT
 */

// --- CORE UTILITIES ---
// Get a cookie value by name
const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
};

// Auth & API config
const AUTH_TOKEN = getCookie('access_token');
const API_BASE_URL = "http://127.0.0.1:5000";
const HEADERS = { 
    'Authorization': `Bearer ${AUTH_TOKEN}`,
    'Content-Type': 'application/json'
};

// Decode JWT payload
const getJwtPayload = () => {
    if (!AUTH_TOKEN) return null;
    try { return JSON.parse(atob(AUTH_TOKEN.split('.')[1])); }
    catch { return null; }
};

// Check if user is admin
const checkIsAdmin = () => getJwtPayload()?.is_admin === true;

// --- MODULE: USER INTERFACE ---
const refreshUserUI = () => {
    const user = localStorage.getItem('username') || "Operator";

    // Update sidebar
    const sidebarName = document.querySelector('.sidebar-footer strong');
    if (sidebarName) sidebarName.textContent = user;

    // Update avatar initial
    const avatar = document.querySelector('.user-profile .avatar');
    if (avatar) avatar.textContent = user.charAt(0).toUpperCase();
};

// --- MODULE: ANALYTICS (CHARTS) ---
class PharmaCharts {
    constructor() {
        this.chartDay = document.getElementById('chartDay');
        this.chartMonth = document.getElementById('chartMonth');
        if (this.chartDay && this.chartMonth) this.load();
    }

    // Load daily & monthly data from API
    async load() {
        try {
            const [resD, resM] = await Promise.all([
                fetch(`${API_BASE_URL}/analytics/daily`, { headers: HEADERS }),
                fetch(`${API_BASE_URL}/analytics/monthly`, { headers: HEADERS })
            ]);
            const daily = await resD.json();
            const monthly = await resM.json();

            this.render(this.chartDay, daily.graph_data, 'line', '#1E90FF', 'Hourly Revenue (€)');
            this.render(this.chartMonth, monthly.graph_data, 'bar', '#00FF7F', 'Daily Revenue (€)');
        } catch (e) { console.error("Analytics Load Failed", e); }
    }

    // Render chart using Chart.js
    render(canvas, data, type, color, label) {
        new Chart(canvas.getContext('2d'), {
            type: type,
            data: {
                labels: data.map(i => i.hour || i.day),
                datasets: [{
                    label: label,
                    data: data.map(i => i.revenue),
                    borderColor: color,
                    backgroundColor: color + '33',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: { 
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
}

// --- MODULE: AI ASSISTANT ---
class PharmaChat {
    constructor() {
        this.window = document.getElementById('chat-window');
        this.input = document.getElementById('user-input');
        this.btn = document.getElementById('send-btn');
        if (this.window) this.init();
    }

    // Initialize event listeners
    init() {
        this.btn?.addEventListener('click', () => this.send());
        this.input?.addEventListener('keypress', (e) => { if(e.key === 'Enter') this.send(); });
    }

    // Send user message to backend
    async send() {
        const msg = this.input.value.trim();
        if (!msg) return;
        this.addMsg('user', msg);
        this.input.value = '';

        try {
            const res = await fetch(`${API_BASE_URL}/chatbot/`, {
                method: 'POST',
                headers: HEADERS,
                body: JSON.stringify({ message: msg })
            });
            const data = await res.json();
            this.addMsg('bot', data.reply);
        } catch (e) { this.addMsg('bot', "Connection error."); }
    }

    // Add message to chat window
    addMsg(role, text) {
        const d = document.createElement('div');
        d.className = `message ${role}`;
        d.innerText = text;
        this.window.appendChild(d);
        this.window.scrollTop = this.window.scrollHeight;
    }
}

// --- MODULE: DASHBOARD MANAGER ---
class DashboardManager {
    constructor() {
        // DOM references
        this.lists = {
            meds: document.getElementById('meds-list'),
            clients: document.getElementById('client-search-result'),
            doctors: document.getElementById('doctor-search-result'),
            team: document.getElementById('team-list'),
            notifs: document.getElementById('team-notif-list')
        };
        this.kpis = {
            efficiency: document.getElementById('stock-efficiency'),
            status: document.getElementById('stock-status-text'),
            totalClients: document.getElementById('total-clients'),
            totalDoctors: document.getElementById('total-doctors')
        };

        this.init();
    }

    // Initialize all modules & fetch data
    async init() {
        if (!AUTH_TOKEN) return;

        try {
            const [resC, resD, resM] = await Promise.all([
                fetch(`${API_BASE_URL}/clients/`, { headers: HEADERS }),
                fetch(`${API_BASE_URL}/doctors/`, { headers: HEADERS }),
                fetch(`${API_BASE_URL}/products/`, { headers: HEADERS })
            ]);

            const clients = await resC.json();
            const doctors = await resD.json();
            const meds = await resM.json();

            this.updateKPIs(meds, clients.length, doctors.length);
            this.renderCriticalMeds(meds);
            this.renderDetailedList(this.lists.clients, clients, 'client');
            this.renderDetailedList(this.lists.doctors, doctors, 'doctor');

            this.loadTeam();
            this.loadPersistentNotes();
            this.initNoteSystem();
            this.initSearchFilters();
        } catch (e) { console.error("Data Engine Error", e); }
    }

    // --- NOTES SYSTEM ---
    initNoteSystem() {
        const addBtn = document.getElementById('add-note-btn');
        const noteInput = document.getElementById('new-note-text'); // fixed ID

        if (!addBtn || !noteInput) {
            console.error("Note system elements not found");
            return;
        }

        addBtn.onclick = () => {
            const text = noteInput.value.trim();
            if (!text) return;

            this.saveNote({ text, timestamp: Date.now() });
            noteInput.value = "";
            this.loadPersistentNotes();
        };

        noteInput.addEventListener('keypress', e => { if (e.key === 'Enter') addBtn.click(); });
    }

    saveNote(note) {
        const notes = JSON.parse(localStorage.getItem('pharma_notes') || '[]');
        notes.push(note);
        localStorage.setItem('pharma_notes', JSON.stringify(notes));
    }

    deleteNote(timestamp) {
        if (!checkIsAdmin()) return alert("Admin privileges required");
        let notes = JSON.parse(localStorage.getItem('pharma_notes') || '[]');
        notes = notes.filter(n => n.timestamp !== timestamp);
        localStorage.setItem('pharma_notes', JSON.stringify(notes));
        this.loadPersistentNotes();
    }

    loadPersistentNotes() {
        if (!this.lists.notifs) return;

        const now = Date.now();
        const isAdmin = checkIsAdmin();
        let notes = JSON.parse(localStorage.getItem('pharma_notes') || '[]');

        // Remove expired notes
        notes = notes.filter(n => (now - n.timestamp) < 86400000);
        localStorage.setItem('pharma_notes', JSON.stringify(notes));

        this.lists.notifs.innerHTML = "";
        if (notes.length === 0) {
            this.lists.notifs.innerHTML = '<li class="item-entry">No notes available.</li>';
            return;
        }

        notes.sort((a, b) => b.timestamp - a.timestamp);

        notes.forEach(note => {
            const timeStr = new Date(note.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const li = document.createElement('li');
            li.className = "item-entry";

            li.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                    <div>
                        <strong>📌 Note:</strong> ${note.text}<br>
                        <small>⌚ ${timeStr}</small>
                    </div>
                    ${isAdmin ? `<button class="del-note" data-ts="${note.timestamp}">🗑️</button>` : ''}
                </div>`;

            if (isAdmin) {
                li.querySelector('.del-note').onclick = (e) => {
                    const ts = parseInt(e.currentTarget.getAttribute('data-ts'));
                    this.deleteNote(ts);
                };
            }

            this.lists.notifs.appendChild(li);
        });
    }

    // --- STOCK & PRODUCT MANAGEMENT ---
    renderCriticalMeds(meds) {
        if (!this.lists.meds) return;

        const critical = meds.filter(m => m.stock < 10);

        this.lists.meds.innerHTML = critical.length
            ? critical.map(m => `
                <li class="item-entry ${m.stock === 0 ? 'critical' : 'warning'}">
                    <div class="info">
                        <strong>${m.name}</strong> <span>(${m.stock} left)</span>
                    </div>
                    <button class="order-btn ${m.stock === 0 ? 'urgent' : ''}" data-id="${m.id}">
                        Order
                    </button>
                </li>`).join('')
            : '<li class="item-entry">✅ Stock optimal</li>';

        // Event listeners to redirect to product page
        this.lists.meds.querySelectorAll('.order-btn').forEach(btn => {
            btn.onclick = () => {
                const productId = btn.dataset.id;
                window.location.href = `inventory.html?id=${productId}`;
            };
        });
    }

    updateKPIs(meds, clientCount, doctorCount) {
        const total = meds.length;
        const outOfStock = meds.filter(m => m.stock === 0).length;
        const lowStock = meds.filter(m => m.stock > 0 && m.stock < 10).length;
        const healthyStock = meds.filter(m => m.stock >= 10).length;
        const efficiency = total > 0 ? Math.round(((lowStock + healthyStock) / total) * 100) : 0;

        if (this.kpis.efficiency) {
            this.kpis.efficiency.innerText = `${efficiency}%`;
            this.kpis.efficiency.style.color = efficiency > 85 ? "#2ecc71" : "#e67e22";
        }

        if (this.kpis.status) {
            this.kpis.status.innerHTML = `
                <span style="color:#e74c3c;">${outOfStock} Out</span> | 
                <span style="color:#f39c12;">${lowStock} Low</span> | 
                <span style="color:#2ecc71;">${healthyStock} OK</span>`;
        }

        if (this.kpis.totalClients) this.kpis.totalClients.innerText = clientCount;
        if (this.kpis.totalDoctors) this.kpis.totalDoctors.innerText = doctorCount;
    }

    renderDetailedList(container, data, type) {
        if (!container) return;
        container.innerHTML = data.map(item => `
            <div class="item-entry">
                <div class="info">
                    <strong>${type === 'doctor' ? 'DR. ' : ''}${item.last_name.toUpperCase()}</strong><br>
                    <small>📧 ${item.email || 'N/A'}</small>
                </div>
            </div>`).join('');
    }

    async loadTeam() {
        if (!this.lists.team) return;
        try {
            const res = await fetch(`${API_BASE_URL}/users/`, { headers: HEADERS });
            const users = await res.json();
            this.lists.team.innerHTML = users.map(u => `
                <li class="item-entry"><strong>${u.username}</strong> (${u.role || 'Staff'})</li>`).join('');
        } catch (e) { this.lists.team.innerHTML = "<li>Error loading staff</li>"; }
    }

    initSearchFilters() {
        const setup = (inputId, containerId) => {
            const input = document.getElementById(inputId);
            const container = document.getElementById(containerId);
            if (!input || !container) return;
            input.oninput = (e) => {
                const term = e.target.value.toLowerCase();
                container.querySelectorAll('.item-entry').forEach(el => {
                    el.style.display = el.innerText.toLowerCase().includes(term) ? "block" : "none";
                });
            };
        };
        setup('search-client', 'client-search-result');
        setup('search-doctor', 'doctor-search-result');
    }
}

// --- GLOBAL INIT ---
document.addEventListener('DOMContentLoaded', () => {
    if (!AUTH_TOKEN) { window.location.href = 'auth.html'; return; }
    refreshUserUI();

    document.getElementById('logout-btn')?.addEventListener('click', () => {
        document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        localStorage.clear();
        window.location.href = 'auth.html';
    });

    new PharmaCharts();
    new PharmaChat();
    new DashboardManager();
});
