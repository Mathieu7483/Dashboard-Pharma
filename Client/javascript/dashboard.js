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

            console.log(daily, monthly)

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
                scales: {
                y: { beginAtZero: true }
                }
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
            team: document.getElementById('team-list')
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
            this.renderAll(meds, clients, doctors);
            this.loadTeam();
            this.initSearchFilters();

        } catch (e) { console.error("Data Engine Error", e); }
    }

    updateKPIs(meds, clientCount, doctorCount) {
        const total = meds.length;
        const available = meds.filter(m => m.stock > 0).length;
        const lowStock = meds.filter(m => m.stock > 0 && m.stock < 10).length;
        const outOfStock = total - available;
        const efficiency = total > 0 ? Math.round((available / total) * 100) : 0;

        if (this.kpis.efficiency) {
            this.kpis.efficiency.innerText = `${efficiency}%`;
            this.kpis.efficiency.style.color = efficiency > 85 ? "#2ecc71" : "#e67e22";
        }

        if (this.kpis.status) {
            this.kpis.status.innerHTML = `
                <span style="color: #e74c3c">${outOfStock} Out</span> | 
                <span style="color: #f1c40f">${lowStock} Low</span> | 
                <span style="color: #2ecc71">${available} OK</span>
            `;
        }

        if (this.kpis.totalClients) this.kpis.totalClients.innerText = clientCount;
        if (this.kpis.totalDoctors) this.kpis.totalDoctors.innerText = doctorCount;
    }

    renderAll(meds, clients, doctors) {
        // Render Medicines
        if (this.lists.meds) {
            this.lists.meds.classList.add('scroll-container');
            this.lists.meds.innerHTML = meds.map(m => {
                const statusClass = m.stock === 0 ? 'critical' : (m.stock < 10 ? 'warning' : 'good');
                const icon = m.stock === 0 ? '❌' : (m.stock < 10 ? '⚠️' : '✅');
                return `
                    <li class="item-entry ${statusClass}">
                        <div class="info">
                            <strong>${m.name}</strong> ${icon}<br>
                            <small>Stock: ${m.stock} units | ${m.price}€</small>
                        </div>
                    </li>`;
            }).join('');
        }

        // Render detailed CRM lists
        this.renderDetailedList(this.lists.clients, clients, 'client');
        this.renderDetailedList(this.lists.doctors, doctors, 'doctor');
    }

    /**
     * Renders detailed information for Patients and Doctors
     */
    renderDetailedList(container, data, type) {
        if (!container) return;
        container.classList.add('scroll-container');
        
        container.innerHTML = data.map(item => {
            if (type === 'doctor') {
                return `
                    <div class="item-entry">
                        <div class="info">
                            <strong>DR. ${item.last_name.toUpperCase()} ${item.first_name || ''}</strong><br>
                            <span class="tag-specialty">${item.specialty || 'Generalist'}</span><br>
                            <small>📧 ${item.email || 'No email'}</small>
                            <small>📍 ${item.address || 'No address stored'}</small>
                            <small>📞 ${item.phone || 'No phone'}</small>
                        </div>
                    </div>`;
            } else {
                return `
                    <div class="item-entry">
                        <div class="info">
                            <strong>${item.last_name.toUpperCase()} ${item.first_name}</strong><br>
                            <small>📧 ${item.email}</small>
                            <small>📍 ${item.address || 'No address stored'}</small>
                            <small>📞 ${item.phone || 'No phone'}</small>
                        </div>
                    </div>`;
            }
        }).join('');
    }

    async loadTeam() {
        if (!this.lists.team) return;
        try {
            const res = await fetch(`${API_BASE_URL}/users/`, { headers: HEADERS });
            const users = await res.json();
            
            this.lists.team.innerHTML = users.map(user => `
                <li class="item-entry">
                    <div class="info">
                        <strong>${user.username}</strong><br>
                        <small>Role: ${user.role || 'Staff Member'}</small>
                    </div>
                </li>
            `).join('');
        } catch (e) {
            this.lists.team.innerHTML = "<li>Staff information unavailable</li>";
        }
    }

    initSearchFilters() {
        const setupSearch = (inputId, containerId) => {
            const input = document.getElementById(inputId);
            const container = document.getElementById(containerId);
            if (!input || !container) return;

            input.addEventListener('input', (e) => {
                const term = e.target.value.toLowerCase();
                const items = container.querySelectorAll('.item-entry');
                items.forEach(item => {
                    const isVisible = item.innerText.toLowerCase().includes(term);
                    item.style.display = isVisible ? "block" : "none";
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
    localStorage.removeItem('username');
    window.location.href = 'auth.html';
};

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    // Security Check
    if (!AUTH_TOKEN) { window.location.href = 'auth.html'; return; }
    
    // Bind Logout
    document.getElementById('logout-btn')?.addEventListener('click', logoutUser);

    // Start Modules
    new PharmaCharts();
    new PharmaChat();
    new DashboardManager();
    
    console.log("Systems synchronized. Monitoring active.");
});