/**
 * PHARMA DASHBOARD - PROFESSIONAL EDITION
 * Comprehensive management of Stocks, Analytics, Chatbot, and CRM.
 */

// --- CORE UTILITIES ---
const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
};

const AUTH_TOKEN = getCookie('access_token');
const API_BASE_URL = "http://127.0.0.1:5000";
const HEADERS = { 
    'Authorization': `Bearer ${AUTH_TOKEN}`,
    'Content-Type': 'application/json' 
};

// --- Module: Dynamical identification of User ---
const refreshUserUI = () => {
    const user = localStorage.getItem('username') || "Operator";
    
    // Sidebar update with full name
    const sidebarName = document.querySelector('.sidebar-footer strong');
    if (sidebarName) sidebarName.textContent = user;

    // Avatar update with initial
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

// --- MODULE: AI ASSISTANT (CADUCÉE) ---
class PharmaChat {
    constructor() {
        this.window = document.getElementById('chat-window');
        this.input = document.getElementById('user-input');
        this.btn = document.getElementById('send-btn');
        if (this.window) this.init();
    }

    init() {
        this.btn?.addEventListener('click', () => this.send());
        this.input?.addEventListener('keypress', (e) => { if(e.key === 'Enter') this.send(); });
    }

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

    addMsg(role, text) {
        const d = document.createElement('div');
        d.className = `message ${role}`;
        d.innerText = text;
        this.window.appendChild(d);
        this.window.scrollTop = this.window.scrollHeight;
    }
}

// --- MODULE: STOCK & CRM ENGINE ---
class DashboardManager {
    constructor() {
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
            this.loadPersistentNotes(); // Start the 24h note system
            this.initNoteSystem();      
            this.initSearchFilters();

        } catch (e) { console.error("Data Engine Error", e); }
    }

    // --- TEAM NOTES (WITH 24H PERSISTENCE & ADMIN DELETE) ---

    initNoteSystem() {
        const addBtn = document.getElementById('add-note-btn');
        const noteInput = document.getElementById('new-note-text');

        if (addBtn && noteInput) {
            addBtn.addEventListener('click', () => {
                const text = noteInput.value.trim();
                if (!text) return;
                const newNote = { text: text, timestamp: Date.now() };
                this.saveNote(newNote);
                this.loadPersistentNotes(); // Refresh list
                noteInput.value = "";
            });
            noteInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') addBtn.click(); });
        }
    }

    saveNote(note) {
        let notes = JSON.parse(localStorage.getItem('pharma_notes') || '[]');
        notes.push(note);
        localStorage.setItem('pharma_notes', JSON.stringify(notes));
    }

    deleteNote(timestamp) {
        let notes = JSON.parse(localStorage.getItem('pharma_notes') || '[]');
        notes = notes.filter(n => n.timestamp !== timestamp);
        localStorage.setItem('pharma_notes', JSON.stringify(notes));
        this.loadPersistentNotes();
    }

    loadPersistentNotes() {
        if (!this.lists.notifs) return;
        const now = Date.now();
        const expiration = 24 * 60 * 60 * 1000;
        const isAdmin = localStorage.getItem('is_admin') === 'true';

        let notes = JSON.parse(localStorage.getItem('pharma_notes') || '[]');
        const validNotes = notes.filter(n => (now - n.timestamp) < expiration);
        localStorage.setItem('pharma_notes', JSON.stringify(validNotes));

        this.lists.notifs.innerHTML = validNotes.length ? "" : '<li class="item-entry">No current notes.</li>';

        validNotes.sort((a,b) => b.timestamp - a.timestamp).forEach(note => {
            const timeStr = new Date(note.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const li = document.createElement('li');
            li.className = "item-entry";
            li.innerHTML = `
                <div class="info" style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong>📌 Note:</strong> ${note.text}<br>
                        <small>Posted at ${timeStr}</small>
                    </div>
                    ${isAdmin ? `<button class="del-note" style="background:none; border:none; cursor:pointer;">🗑️</button>` : ''}
                </div>
            `;
            
            if(isAdmin) {
                li.querySelector('.del-note').addEventListener('click', () => this.deleteNote(note.timestamp));
            }
            this.lists.notifs.appendChild(li);
        });
    }

    // --- STOCK & CRM METHODS ---

    renderCriticalMeds(meds) {
        if (!this.lists.meds) return;
        const critical = meds.filter(m => m.stock < 10);
        this.lists.meds.innerHTML = critical.length ? critical.map(m => `
            <li class="item-entry ${m.stock === 0 ? 'critical' : 'warning'}">
                <div class="info"><strong>${m.name}</strong> (${m.stock} units left)</div>
            </li>`).join('') : '<li class="item-entry">✅ Stock optimal</li>';
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
            this.kpis.status.innerHTML = `<span style="color:#e74c3c;">${outOfStock} Out</span> | <span style="color:#f1c40f;">${lowStock} Low</span> | <span style="color:#2ecc71;">${healthyStock} OK</span>`;
        }
        if (this.kpis.totalClients) this.kpis.totalClients.innerText = clientCount;
        if (this.kpis.totalDoctors) this.kpis.totalDoctors.innerText = doctorCount;
    }

    renderDetailedList(container, data, type) {
        if (!container) return;
        container.innerHTML = data.map(item => `
            <div class="item-entry">
                <div class="info">
                    <strong>${type === 'doctor' ? 'DR. ' : ''}${item.last_name.toUpperCase()} ${item.first_name || ''}</strong><br>
                    <small>📧 ${item.email || 'N/A'}</small> | <small>📞 ${item.phone || 'N/A'}</small>
                </div>
            </div>`).join('');
    }

    async loadTeam() {
        if (!this.lists.team) return;
        try {
            const res = await fetch(`${API_BASE_URL}/users/`, { headers: HEADERS });
            const users = await res.json();
            this.lists.team.innerHTML = users.map(user => `
                <li class="item-entry"><div class="info"><strong>${user.username}</strong><br><small>${user.role || 'Staff'}</small></div></li>
            `).join('');
        } catch (e) { this.lists.team.innerHTML = "<li>Error loading staff</li>"; }
    }

    initSearchFilters() {
        const setupSearch = (inputId, containerId) => {
            const input = document.getElementById(inputId);
            const container = document.getElementById(containerId);
            if (!input || !container) return;
            input.addEventListener('input', (e) => {
                const term = e.target.value.toLowerCase();
                container.querySelectorAll('.item-entry').forEach(item => {
                    item.style.display = item.innerText.toLowerCase().includes(term) ? "block" : "none";
                });
            });
        };
        setupSearch('search-client', 'client-search-result');
        setupSearch('search-doctor', 'doctor-search-result');
    }
}

// --- GLOBAL ACTIONS ---
const logoutUser = () => {
    document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    localStorage.clear();
    window.location.href = 'auth.html';
};

document.addEventListener('DOMContentLoaded', () => {
    if (!AUTH_TOKEN) { window.location.href = 'auth.html'; return; }
    refreshUserUI();
    document.getElementById('logout-btn')?.addEventListener('click', logoutUser);
    new PharmaCharts();
    new PharmaChat();
    new DashboardManager();
});