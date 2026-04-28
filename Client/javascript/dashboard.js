/**
 * dashboard.js - Pharma Dashboard Main JavaScript
 */

// ============================================
// 1. CORE UTILITIES
// ============================================

/**
 * Get a cookie value by name
 * @param {string} name - Cookie name
 * @returns {string|null} Cookie value or null
 */
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

/**
 * Decode JWT payload
 * @returns {Object|null} Decoded JWT payload or null
 */
const getJwtPayload = () => {
    if (!AUTH_TOKEN) return null;
    try { 
        return JSON.parse(atob(AUTH_TOKEN.split('.')[1])); 
    } catch { 
        return null; 
    }
};

/**
 * Check if current user is admin
 * @returns {boolean} True if user is admin
 */
const checkIsAdmin = () => getJwtPayload()?.is_admin === true;

// ============================================
// 2. USER INTERFACE MODULE
// ============================================

/**
 * Refresh user interface with current user data
 */
const refreshUserUI = () => {
    const user = localStorage.getItem('username') || "Operator";

    // Update sidebar
    const sidebarName = document.querySelector('.sidebar-footer strong');
    if (sidebarName) sidebarName.textContent = user;

    // Update avatar initial
    const avatar = document.querySelector('.user-profile .avatar');
    if (avatar) avatar.textContent = user.charAt(0).toUpperCase();
};

// ============================================
// 3. ANALYTICS CHARTS MODULE
// ============================================

class PharmaCharts {
    constructor() {
        this.chartDay = document.getElementById('chartDay');
        this.chartMonth = document.getElementById('chartMonth');
        if (this.chartDay && this.chartMonth) this.load();
    }

    /**
     * Load daily & monthly data from API
     */
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
        } catch (e) { 
            console.error("Analytics Load Failed", e); 
        }
    }

    /**
     * Render chart using Chart.js
     * @param {HTMLCanvasElement} canvas - Canvas element
     * @param {Array} data - Chart data
     * @param {string} type - Chart type (line/bar)
     * @param {string} color - Chart color
     * @param {string} label - Dataset label
     */
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

// ============================================
// 4. AI ASSISTANT MODULE
// ============================================

class PharmaChat {
    constructor() {
        this.window = document.getElementById('chat-window');
        this.input = document.getElementById('user-input');
        this.btn = document.getElementById('send-btn');
        this.logo = document.getElementById('bot-logo'); // AJOUT ICI : Récupère l'image
        if (this.window) this.init();
    }

    /**
     * Initialize event listeners
     */
    init() {
        this.btn?.addEventListener('click', () => this.send());
        this.input?.addEventListener('keypress', (e) => { 
            if(e.key === 'Enter') this.send(); 
        });
    }

    /**
     * Send user message to backend
     */
    async send() {
        const msg = this.input.value.trim();
        if (!msg) return;
        
        this.addMsg('user', msg);
        this.input.value = '';

        // AJOUT ICI : On fait pulser le logo pendant la réflexion
        if (this.logo) this.logo.classList.add('thinking');

        try {
            const res = await fetch(`${API_BASE_URL}/chatbot/`, {
                method: 'POST',
                headers: HEADERS,
                body: JSON.stringify({ message: msg })
            });
            const data = await res.json();
            this.addMsg('bot', data.reply);
        } catch (e) { 
            this.addMsg('bot', "Connection error."); 
        } finally {
            // AJOUT ICI : On arrête l'animation quoi qu'il arrive (succès ou erreur)
            if (this.logo) this.logo.classList.remove('thinking');
        }
    }

    /**
     * Add message to chat window
     */
    addMsg(role, text) {
        const d = document.createElement('div');
        d.className = `message ${role}`;
        
        // OPTIONNEL : Si tu veux l'image détourée aussi à côté de chaque message du bot
        if (role === 'bot') {
            const img = document.createElement('img');
            img.src = "assets/img/Mockup_de_base.png"; // Mets le bon chemin ici
            img.className = "mini-avatar";
            d.appendChild(img);
            
            const span = document.createElement('span');
            span.innerText = text;
            d.appendChild(span);
        } else {
            d.innerText = text;
        }

        this.window.appendChild(d);
        this.window.scrollTop = this.window.scrollHeight;
    }
}

// ============================================
// 5. DASHBOARD MANAGER
// ============================================

class DashboardManager {
    constructor() {
        // DOM references
        this.lists = {
            meds: document.getElementById('meds-list'),
            clients: document.getElementById('client-search-result'),
            doctors: document.getElementById('doctor-search-result'),
            team: document.getElementById('team-list'),
            notifs: document.getElementById('team-notif-list'),
            tickets: document.getElementById('tickets-list')
        };
        
        this.kpis = {
            efficiency: document.getElementById('stock-efficiency'),
            status: document.getElementById('stock-status-text'),
            totalClients: document.getElementById('total-clients'),
            totalDoctors: document.getElementById('total-doctors')
        };

        this.init();
    }

    /**
     * Initialize all modules & fetch data
     */
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
        } catch (e) { 
            console.error("Data Engine Error", e); 
        }
    }

   // ============================================
    // NOTES SYSTEM (Version Corrigée)
    // ============================================

    initNoteSystem() {
        const addBtn = document.getElementById('add-note-btn');
        const noteInput = document.getElementById('new-note-text');

        if (!addBtn || !noteInput) return;

        addBtn.onclick = async () => {
            const text = noteInput.value.trim();
            if (!text) return;

            const success = await this.saveNote(text); 
            if (success) {
                noteInput.value = "";
                // Le rechargement est géré par saveNote ou appelé ici
                await this.loadPersistentNotes();
            }
        };

        noteInput.onkeypress = (e) => { if (e.key === 'Enter') addBtn.click(); };
    }

    async saveNote(text) {
        try {
            const response = await fetch(`${API_BASE_URL}/notes/`, { 
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${AUTH_TOKEN}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text: text })
            });

            if (!response.ok) throw new Error("Erreur sauvegarde");
            return true;
        } catch (error) {
            console.error("Erreur saveNote:", error);
            return false;
        }
    }

    async deleteNote(noteId) {
        if (!checkIsAdmin()) return alert("Admin privileges required");
        try {
            const response = await fetch(`${API_BASE_URL}/notes/${noteId}`, { 
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
            });

            if (response.ok) await this.loadPersistentNotes();
        } catch (error) {
            console.error("Erreur suppression:", error);
        }
    }

    async loadPersistentNotes() {
        if (!this.lists.notifs) return;

        try {
            const response = await fetch(`${API_BASE_URL}/notes/`, {
                headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
            });

            if (!response.ok) throw new Error("Fetch failed");

            const notes = await response.json();
            this.lists.notifs.innerHTML = "";

            if (!notes || notes.length === 0) {
                this.lists.notifs.innerHTML = '<li class="item-entry">No notes available.</li>';
                return;
            }

            // Tri sécurisé : on vérifie que la date existe avant de trier
            notes.sort((a, b) => {
                const dateA = new Date(a.created_at || 0);
                const dateB = new Date(b.created_at || 0);
                return dateB - dateA;
            });

            const isAdmin = checkIsAdmin();

            notes.forEach(note => {
                const dateObj = new Date(note.created_at);
                const timeStr = isNaN(dateObj) ? "N/A" : dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                const li = document.createElement('li');
                li.className = "item-entry";
                li.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                        <div>
                            <strong>📌 Note:</strong> ${note.text}<br>
                            <small>⌚ ${timeStr}</small>
                        </div>
                        ${isAdmin ? `<button class="del-note" data-id="${note.id}">🗑️</button>` : ''}
                    </div>`;

                if (isAdmin) {
                    li.querySelector('.del-note').onclick = () => this.deleteNote(note.id);
                }
                this.lists.notifs.appendChild(li);
            });
        } catch (error) {
            console.error("Erreur rendu notes:", error);
            this.lists.notifs.innerHTML = '<li class="item-entry" style="color:red;">Error loading notes.</li>';
        }
    }

    // ============================================
    // STOCK & PRODUCT MANAGEMENT
    // ============================================

    /**
     * Render critical stock medications
     * @param {Array} meds - Array of medication objects
     */
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

    /**
     * Update KPI displays
     * @param {Array} meds - Medications array
     * @param {number} clientCount - Total clients
     * @param {number} doctorCount - Total doctors
     */
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

    /**
     * Render detailed list for clients or doctors
     * @param {HTMLElement} container - Container element
     * @param {Array} data - Data array
     * @param {string} type - Type (client/doctor)
     */
    renderDetailedList(container, data, type) {
        if (!container) return;
        
        container.innerHTML = data.map(item => {
            const name = item.last_name ? item.last_name.toUpperCase() : 'UNKNOWN';
            const firstName = item.first_name ? item.first_name : '';
            const email = item.email || 'No email';
            const phone = item.phone || 'N/A';
            const address = item.address || 'Address not provided';
            const specialty = item.specialty || '';

            return `
                <div class="item-entry" style="padding: 10px; border-bottom: 1px solid #eee;">
                    <div class="info">
                        <strong>${type === 'doctor' ? 'DR. ' : ''}${name} ${firstName}</strong><br>
                        <small>📧 ${email}</small>
                        <small>📞 ${phone}</small>
                        <small>🏠 ${address}</small>
                        ${type === 'doctor' && specialty ? `<small>💼 Specialty: ${specialty}</small>` : ''}
                    </div>
                </div>`;
        }).join('');
    }

    /**
     * Load team members from API
     */
    async loadTeam() {
        if (!this.lists.team) return;
        
        try {
            const res = await fetch(`${API_BASE_URL}/users/`, { headers: HEADERS });
            const users = await res.json();
            this.lists.team.innerHTML = users.map(u => `
                <li class="item-entry">
                    <strong>${u.username}</strong> (${u.is_admin ? 'Admin' : 'Employee'})
                </li>`).join('');
        } catch (e) { 
            this.lists.team.innerHTML = "<li>You're not allowed to view staff members</li>"; 
        }
    }

    /**
     * Initialize search filters for clients and doctors
     */
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

// ============================================
// 6. TICKETING SYSTEM
// ============================================

/**
 * Setup ticketing system
 */
function setupTicketing() {
    const modal = document.getElementById('ticket-modal');
    const btn = document.getElementById('open-ticket-btn');
    const span = document.getElementById('close-ticket-modal');
    const form = document.getElementById('ticket-form');

    if (!btn) return;

    btn.onclick = () => modal.style.display = "block";
    span.onclick = () => modal.style.display = "none";

    form.onsubmit = async (e) => {
        e.preventDefault();

        const formData = new FormData(form);
        const payload = {
            subject: formData.get('subject'),
            priority: formData.get('priority'),
            description: formData.get('description')
        };

        try {
            const response = await fetch(`${API_BASE_URL}/tickets/`, {
                method: 'POST',
                headers: HEADERS,
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                alert("Ticket sent successfully!");
                modal.style.display = "none";
                form.reset();
            }
        } catch (error) {
            console.error("Error sending ticket:", error);
        }
    };
}

// ============================================
// 7. GLOBAL INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Check authentication
    if (!AUTH_TOKEN) { 
        window.location.href = 'auth.html'; 
        return; 
    }
    
    // Initialize UI
    refreshUserUI();

    // Logout handler
    document.getElementById('logout-btn')?.addEventListener('click', () => {
        document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        localStorage.clear();
        window.location.href = 'auth.html';
    });

    // Initialize modules
    new PharmaCharts();
    new PharmaChat();
    new DashboardManager();
    setupTicketing();
});