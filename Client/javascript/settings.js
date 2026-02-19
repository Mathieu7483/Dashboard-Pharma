/**
 * settings.js - Admin Panel Management
 * Calendar events stored in BACKEND API
 */

const API_BASE = 'http://127.0.0.1:5000';

// ============================================
// 1. COOKIE MANAGER
// ============================================
const CookieManager = {
    get: (name) => {
        const nameEQ = name + "=";
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    },
    erase: (name) => {
        document.cookie = name + '=; Max-Age=-99999999; path=/;';
    }
};

// ============================================
// 2. AUTH HELPER
// ============================================
function getAuthInfo() {
    const token = CookieManager.get('access_token');
    if (!token) return { token: null, isAdmin: false };
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const isAdmin = payload.is_admin === true;
        return { token, isAdmin };
    } catch (e) {
        console.error('Token decode error:', e);
        return { token: null, isAdmin: false };
    }
}

function authHeaders(token) {
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

// ============================================
// 3. INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Settings page initializing...');

    const auth = getAuthInfo();
    if (!auth.token) {
        alert('You must be logged in to access this page');
        window.location.href = 'auth.html';
        return;
    }
    if (!auth.isAdmin) {
        alert('Admin access required');
        window.location.href = 'index.html';
        return;
    }

    loadNavbar();
    fetchUsers();
    fetchTickets();
    fetchTodayStats(); // ← STATS DEPUIS LE BACKEND
    setupEventListeners();
    initTabSystem();
    initFilters();
    initTicketFilters();

    // Calendar init après chargement des users
    setTimeout(() => {
        CalendarManager.init();
    }, 600);
});

// ============================================
// 4. TODAY STATS FROM BACKEND
// ============================================
async function fetchTodayStats() {
    const { token } = getAuthInfo();
    if (!token) return;

    console.log('📊 Fetching today stats from backend...');

    try {
        const response = await fetch(`${API_BASE}/calendar/events/stats/today`, {
            method: 'GET',
            headers: authHeaders(token)
        });

        if (!response.ok) {
            console.log('⚠️ Stats endpoint error:', response.status);
            return;
        }

        const stats = await response.json();
        console.log('✅ Today stats:', stats);

        const rdvEl = document.getElementById('stat-today-rdv');
        const gardeEl = document.getElementById('stat-today-garde');
        const totalEl = document.getElementById('stat-total-events');

        if (rdvEl) rdvEl.textContent = stats.rdv_count;
        if (gardeEl) gardeEl.textContent = stats.garde_count;
        if (totalEl) totalEl.textContent = stats.total_all;

    } catch (error) {
        console.error("❌ Stats Fetch Error:", error);
    }
}

// ============================================
// 5. FETCH USERS
// ============================================
async function fetchUsers() {
    const { token, isAdmin } = getAuthInfo();
    if (!token) return;

    console.log('📋 Loading users...');

    try {
        const response = await fetch(`${API_BASE}/users/`, {
            method: 'GET',
            headers: authHeaders(token)
        });

        if (!response.ok) {
            if (response.status === 401) {
                alert('Session expired. Please login again.');
                window.location.href = 'auth.html';
                return;
            }
            if (response.status === 403) {
                alert('Access forbidden. Admin rights required.');
                window.location.href = 'index.html';
                return;
            }
            throw new Error(`Fetch failed: ${response.status}`);
        }

        const users = await response.json();
        console.log('✅ Users loaded:', users.length);
        window.allUsers = users;
        renderUserTable(users, isAdmin);
        updateStats(users, window.allTickets || []);
    } catch (error) {
        console.error("❌ User Fetch Error:", error);
    }
}

// ============================================
// 6. RENDER USER TABLE
// ============================================
function renderUserTable(users, isAdmin) {
    const tbody = document.getElementById('user-table-body');
    const emptyState = document.getElementById('empty-state');
    const currentUserId = localStorage.getItem('user_id');

    if (!tbody) return;

    const countBadge = document.getElementById('users-count');
    if (countBadge) countBadge.textContent = users.length;

    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No users found</td></tr>';
        if (emptyState) emptyState.style.display = 'block';
        return;
    }
    if (emptyState) emptyState.style.display = 'none';

    tbody.innerHTML = users.map(user => {
        const initials = (user.first_name?.[0] || user.username[0]).toUpperCase();
        const isCurrentUser = user.id === currentUserId;
        const roleBadge = user.is_admin ?
            '<span class="badge badge-admin">Admin</span>' :
            '<span class="badge badge-staff">Personnel</span>';

        return `
            <tr>
                <td>
                    <div class="user-info">
                        <div class="user-avatar">${initials}</div>
                        <div class="user-details">
                            <h4>${user.username}</h4>
                            <p>${user.first_name || ''} ${user.last_name || ''}</p>
                        </div>
                    </div>
                </td>
                <td>
                    <div>${user.email || 'Not specified'}</div>
                    <small style="color: #6b7280;">ID: ${user.id.slice(0, 8)}...</small>
                </td>
                <td>${roleBadge}</td>
                <td><span class="status-badge status-active">Active</span></td>
                <td><small style="color: #6b7280;">N/A</small></td>
                <td>
                    <div class="action-group">
                        <button class="btn-action" onclick="openEditModal('${user.id}')">✏️ Edit</button>
                        ${!isCurrentUser ?
                            `<button class="btn-danger" onclick="deleteUser('${user.id}')">🗑️ Delete</button>` :
                            '<span class="self-tag">You</span>'}
                    </div>
                </td>
            </tr>`;
    }).join('');
}

// ============================================
// 7. UPDATE STATS
// ============================================
function updateStats(users = [], tickets = []) {
    const el1 = document.getElementById('stat-active-users');
    const el2 = document.getElementById('stat-admins');
    const el3 = document.getElementById('stat-tickets');
    if (el1) el1.textContent = users.length;
    if (el2) el2.textContent = users.filter(u => u.is_admin).length;
    if (el3) el3.textContent = tickets.length;
}

// ============================================
// 8. USER MODAL MANAGEMENT
// ============================================
window.openEditModal = async (userId) => {
    const { token } = getAuthInfo();
    try {
        const response = await fetch(`${API_BASE}/users/${userId}`, {
            headers: authHeaders(token)
        });
        if (!response.ok) return alert('Failed to load user data');

        const user = await response.json();
        document.getElementById('edit-user-id').value = user.id;
        document.getElementById('edit-username').value = user.username;
        document.getElementById('edit-email').value = user.email || '';
        document.getElementById('edit-first-name').value = user.first_name || '';
        document.getElementById('edit-last-name').value = user.last_name || '';
        document.getElementById('edit-is-admin').checked = user.is_admin;
        document.getElementById('edit-password').value = '';
        document.getElementById('edit-modal').classList.add('active');
    } catch (error) {
        alert('Network error while loading user');
    }
};

window.closeEditModal = () => document.getElementById('edit-modal').classList.remove('active');
window.openCreateModal = () => {
    document.getElementById('create-user-form').reset();
    document.getElementById('create-modal').classList.add('active');
};
window.closeCreateModal = () => document.getElementById('create-modal').classList.remove('active');

window.deleteUser = async (userId) => {
    if (!confirm("⚠️ Confirm deletion?")) return;
    const { token } = getAuthInfo();
    try {
        const response = await fetch(`${API_BASE}/users/${userId}`, {
            method: 'DELETE', headers: authHeaders(token)
        });
        if (response.ok) { await fetchUsers(); alert('User deleted'); }
        else { const err = await response.json(); alert(err.message || 'Delete failed'); }
    } catch (e) { alert('Network error'); }
};

// ============================================
// 9. EVENT LISTENERS & FORMS
// ============================================
function setupEventListeners() {
    const editForm = document.getElementById('edit-user-form');
    const createForm = document.getElementById('create-user-form');

    if (editForm) {
        editForm.onsubmit = async (e) => {
            e.preventDefault();
            const { token } = getAuthInfo();
            const userId = document.getElementById('edit-user-id').value;
            const password = document.getElementById('edit-password').value.trim();
            const payload = {
                email: document.getElementById('edit-email').value.trim() || null,
                first_name: document.getElementById('edit-first-name').value.trim() || null,
                last_name: document.getElementById('edit-last-name').value.trim() || null,
                is_admin: document.getElementById('edit-is-admin').checked
            };
            if (password) payload.password = password;
            try {
                const response = await fetch(`${API_BASE}/users/${userId}`, {
                    method: 'PUT', headers: authHeaders(token), body: JSON.stringify(payload)
                });
                if (response.ok) { closeEditModal(); await fetchUsers(); alert('User updated'); }
                else { const err = await response.json(); alert(err.message || 'Update failed'); }
            } catch (e) { alert('Network error'); }
        };
    }

    if (createForm) {
        createForm.onsubmit = async (e) => {
            e.preventDefault();
            const { token } = getAuthInfo();
            const username = document.getElementById('create-username').value.trim();
            const email = document.getElementById('create-email').value.trim();
            const password = document.getElementById('create-password').value.trim();
            if (!username || !email || !password) return alert('⚠️ All fields required!');
            if (password.length < 6) return alert('⚠️ Password min 6 chars!');
            const payload = {
                username, email, password,
                first_name: document.getElementById('create-first-name').value.trim() || null,
                last_name: document.getElementById('create-last-name').value.trim() || null,
                is_admin: document.getElementById('create-is-admin').checked
            };
            try {
                const response = await fetch(`${API_BASE}/users/`, {
                    method: 'POST', headers: authHeaders(token), body: JSON.stringify(payload)
                });
                if (response.ok) { closeCreateModal(); await fetchUsers(); alert('✅ User created'); }
                else { const err = await response.json(); alert(`❌ ${err.message || JSON.stringify(err)}`); }
            } catch (e) { alert('❌ Network error'); }
        };
    }

    const logoutBtn = document.querySelector('.btn-logout-top');
    if (logoutBtn) {
        logoutBtn.onclick = () => {
            CookieManager.erase('access_token');
            localStorage.clear();
            window.location.href = 'auth.html';
        };
    }
}

// ============================================
// 10. TAB SYSTEM
// ============================================
function initTabSystem() {
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.target;
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            contents.forEach(c => {
                c.classList.remove('active');
                if (c.id === target) c.classList.add('active');
            });
        });
    });
}

// ============================================
// 11. USER FILTERS
// ============================================
function initFilters() {
    const searchInput = document.getElementById('user-search');
    const roleFilter = document.getElementById('role-filter');

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const { isAdmin } = getAuthInfo();
            if (!window.allUsers) return;
            const filtered = window.allUsers.filter(user => {
                const matchesSearch = !query ||
                    user.username.toLowerCase().includes(query) ||
                    (user.email && user.email.toLowerCase().includes(query));
                const role = roleFilter ? roleFilter.value : 'all';
                const matchesRole = role === 'all' ||
                    (role === 'admin' && user.is_admin) ||
                    (role === 'staff' && !user.is_admin);
                return matchesSearch && matchesRole;
            });
            renderUserTable(filtered, isAdmin);
        });
    }

    if (roleFilter) {
        roleFilter.addEventListener('change', () => {
            if (searchInput) searchInput.dispatchEvent(new Event('input'));
        });
    }
}

// ============================================
// 12. TICKETING SYSTEM
// ============================================
async function fetchTickets() {
    const { token } = getAuthInfo();
    if (!token) return;

    try {
        const response = await fetch(`${API_BASE}/tickets/`, {
            method: 'GET', headers: authHeaders(token)
        });

        if (!response.ok) {
            if (response.status === 401) { window.location.href = 'auth.html'; return; }
            if (response.status === 403) return;
            throw new Error(`Fetch failed: ${response.status}`);
        }

        const tickets = await response.json();
        console.log('✅ Tickets loaded:', tickets.length);
        window.allTickets = tickets;
        renderTicketTable(tickets);
        updateStats(window.allUsers || [], tickets);
    } catch (error) {
        console.error("❌ Ticket Fetch Error:", error);
    }
}

function renderTicketTable(tickets) {
    const tbody = document.getElementById('ticket-table-body');
    if (!tbody) return;

    const countBadge = document.getElementById('tickets-count');
    if (countBadge) countBadge.textContent = tickets.length;

    if (!tickets || tickets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No tickets found</td></tr>';
        return;
    }

    const priorityBadges = {
        'high': '<span class="badge" style="background:#ef4444;color:white;padding:4px 8px;border-radius:4px;">🔴 High</span>',
        'medium': '<span class="badge" style="background:#f59e0b;color:white;padding:4px 8px;border-radius:4px;">🟠 Medium</span>',
        'low': '<span class="badge" style="background:#3b82f6;color:white;padding:4px 8px;border-radius:4px;">🔵 Low</span>'
    };

    tbody.innerHTML = tickets.map(ticket => {
        const date = new Date(ticket.created_at).toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' });
        const description = ticket.description.length > 60 ? ticket.description.substring(0, 60) + '...' : ticket.description;
        return `
            <tr>
                <td><strong>#${ticket.id}</strong></td>
                <td><div style="max-width:250px;"><strong>${ticket.subject}</strong><br><small style="color:#6b7280;">${description}</small></div></td>
                <td><small style="color:#6b7280;">User ID: ${ticket.user_id.slice(0, 8)}...</small></td>
                <td>${priorityBadges[ticket.priority] || priorityBadges['medium']}</td>
                <td>
                    <select class="status-select" data-ticket-id="${ticket.id}" data-current-status="${ticket.status}" onchange="handleStatusChange('${ticket.id}', this.value)">
                        <option value="open" ${ticket.status === 'open' ? 'selected' : ''}>🟢 Open</option>
                        <option value="pending" ${ticket.status === 'pending' ? 'selected' : ''}>🟡 Pending</option>
                        <option value="closed" ${ticket.status === 'closed' ? 'selected' : ''}>🟣 Closed</option>
                    </select>
                </td>
                <td><small>${date}</small></td>
                <td>
                    <div class="action-group">
                        <button class="btn-action" onclick="viewTicket('${ticket.id}')">👁️ View</button>
                        <button class="btn-action" onclick="openAdminNoteModal('${ticket.id}')">📝Note</button>
                        <button class="btn-danger" onclick="deleteTicket('${ticket.id}')">🗑️ Delete</button>
                    </div>
                </td>
            </tr>`;
    }).join('');
}

window.handleStatusChange = async (ticketId, newStatus) => {
    const sel = document.querySelector(`select[data-ticket-id="${ticketId}"]`);
    const prev = sel.dataset.currentStatus;
    if (!confirm(`Change ticket #${ticketId} to "${newStatus}"?`)) { sel.value = prev; return; }
    const { token } = getAuthInfo();
    try {
        const res = await fetch(`${API_BASE}/tickets/${ticketId}`, {
            method: 'PUT', headers: authHeaders(token), body: JSON.stringify({ status: newStatus })
        });
        if (res.ok) sel.dataset.currentStatus = newStatus;
        else { alert('Failed'); sel.value = prev; }
    } catch (e) { alert('Network error'); sel.value = prev; }
};

window.openAdminNoteModal = async (ticketId) => {
    const { token } = getAuthInfo();
    try {
        const res = await fetch(`${API_BASE}/tickets/${ticketId}`, { headers: authHeaders(token) });
        if (!res.ok) return alert('Failed');
        const ticket = await res.json();
        const note = prompt(`Admin Note #${ticket.id}\nCurrent: ${ticket.admin_note || '(none)'}`, ticket.admin_note || '');
        if (note === null) return;
        const upd = await fetch(`${API_BASE}/tickets/${ticketId}`, {
            method: 'PUT', headers: authHeaders(token), body: JSON.stringify({ admin_note: note })
        });
        if (upd.ok) { alert('✅ Updated'); fetchTickets(); } else alert('Failed');
    } catch (e) { alert('Network error'); }
};

window.viewTicket = async (ticketId) => {
    const { token } = getAuthInfo();
    try {
        const res = await fetch(`${API_BASE}/tickets/${ticketId}`, { headers: authHeaders(token) });
        if (!res.ok) return alert('Failed');
        const t = await res.json();
        const adminNote = t.admin_note ? `\n\nAdmin Note:\n${t.admin_note}` : '';
        alert(`🎫 #${t.id}\nSubject: ${t.subject}\nPriority: ${t.priority}\nStatus: ${t.status}\n\n${t.description}${adminNote}`);
    } catch (e) { alert('Network error'); }
};

window.deleteTicket = async (ticketId) => {
    if (!confirm('Delete this ticket?')) return;
    const { token } = getAuthInfo();
    try {
        const res = await fetch(`${API_BASE}/tickets/${ticketId}`, { method: 'DELETE', headers: authHeaders(token) });
        if (res.ok) { await fetchTickets(); alert('✅ Deleted'); }
        else { const err = await res.json(); alert(err.message || 'Failed'); }
    } catch (e) { alert('Network error'); }
};

function initTicketFilters() {
    const statusFilter = document.getElementById('ticket-status-filter');
    const priorityFilter = document.getElementById('ticket-priority-filter');
    const apply = () => {
        if (!window.allTickets) return;
        const sv = statusFilter ? statusFilter.value : 'all';
        const pv = priorityFilter ? priorityFilter.value : 'all';
        const filtered = window.allTickets.filter(t =>
            (sv === 'all' || t.status === sv) && (pv === 'all' || t.priority === pv)
        );
        renderTicketTable(filtered);
    };
    if (statusFilter) statusFilter.addEventListener('change', apply);
    if (priorityFilter) priorityFilter.addEventListener('change', apply);
}

// ============================================
// 13. NAVBAR
// ============================================
function loadNavbar() {
    fetch('navbar.html').then(r => r.text()).then(html => {
        const el = document.getElementById('navbar-placeholder');
        if (el) {
            el.innerHTML = html;
            highlightActiveLink();
            const avatar = document.getElementById('user-avatar');
            if (avatar) avatar.textContent = (localStorage.getItem('first_name') || 'A').charAt(0).toUpperCase();
        }
    }).catch(e => console.error("Navbar Error:", e));
}

function highlightActiveLink() {
    const page = window.location.pathname.split('/').pop() || 'index.html';
    const map = {
        'index.html': 'nav-dashboard', 'inventory.html': 'nav-inventory',
        'clients.html': 'nav-clients', 'doctors.html': 'nav-doctors', 'settings.html': 'nav-settings'
    };
    const id = map[page];
    if (id) { const link = document.getElementById(id); if (link) link.classList.add('active'); }
}

// ============================================
// 14. CALENDAR MANAGER — BACKEND VERSION
// ============================================
const CalendarManager = {
    currentDate: new Date(),
    events: [],
    hours: [
        '08:00','09:00','10:00','11:00','12:00','13:00',
        '14:00','15:00','16:00','17:00','18:00','19:00',
        '20:00','21:00','22:00','23:00','00:00','01:00',
        '02:00','03:00','04:00','05:00','06:00','07:00'
    ],

    // ─── INIT ───
    init: async () => {
        console.log('📅 Initializing Calendar (Backend Mode)...');
        await CalendarManager.loadEvents();
        CalendarManager.render();
        CalendarManager.setupListeners();
    },

    // ─── LOAD FROM BACKEND (remplace localStorage) ───
    loadEvents: async () => {
        const { token } = getAuthInfo();
        if (!token) return;

        try {
            const response = await fetch(`${API_BASE}/calendar/events/`, {
                method: 'GET',
                headers: authHeaders(token)
            });

            if (!response.ok) {
                console.error('❌ Failed to load events:', response.status);
                CalendarManager.events = [];
                return;
            }

            CalendarManager.events = await response.json();
            console.log(`✅ Loaded ${CalendarManager.events.length} events from backend`);

        } catch (error) {
            console.error('❌ Calendar load error:', error);
            CalendarManager.events = [];
        }
    },

    // ─── SAVE TO BACKEND (remplace localStorage) ───
    saveEvent: async (eventData, existingId = null) => {
        const { token } = getAuthInfo();
        if (!token) return false;

        const method = existingId ? 'PUT' : 'POST';
        const url = existingId
            ? `${API_BASE}/calendar/events/${existingId}`
            : `${API_BASE}/calendar/events/`;

        console.log(`📤 ${method} event:`, eventData);

        try {
            const response = await fetch(url, {
                method: method,
                headers: authHeaders(token),
                body: JSON.stringify(eventData)
            });

            if (!response.ok) {
                const error = await response.json();
                alert(`❌ Error: ${error.message || 'Save failed'}`);
                return false;
            }

            const saved = await response.json();
            console.log(`✅ Event ${existingId ? 'updated' : 'created'}:`, saved);

            // Reload everything from backend
            await CalendarManager.loadEvents();
            CalendarManager.render();
            fetchTodayStats(); // Refresh stats

            return true;

        } catch (error) {
            console.error('❌ Save error:', error);
            alert('Network error while saving event');
            return false;
        }
    },

    // ─── DELETE FROM BACKEND ───
    deleteEvent: async () => {
        const id = document.getElementById('event-id').value;
        if (!id || !confirm('Supprimer cet événement ?')) return;

        const { token } = getAuthInfo();

        try {
            const response = await fetch(`${API_BASE}/calendar/events/${id}`, {
                method: 'DELETE',
                headers: authHeaders(token)
            });

            if (!response.ok) {
                alert('Failed to delete event');
                return;
            }

            CalendarManager.closeModal();
            await CalendarManager.loadEvents();
            CalendarManager.render();
            fetchTodayStats();
            alert('✅ Événement supprimé');

        } catch (error) {
            console.error('❌ Delete error:', error);
            alert('Network error');
        }
    },

    // ─── WEEK NAVIGATION ───
    getStartOfWeek: (date) => {
        const d = new Date(date);
        const day = d.getDay();
        const diff = d.getDate() - day + (day === 0 ? -6 : 1);
        return new Date(d.setDate(diff));
    },

    changeWeek: (direction) => {
        CalendarManager.currentDate.setDate(
            CalendarManager.currentDate.getDate() + (direction * 7)
        );
        CalendarManager.render();
    },

    // ─── EVENT ACTIVE CHECK ───
    isEventActiveAt: (event, dateString, hour) => {
        // Handle both camelCase (from backend to_dict) and snake_case
        const startDate = event.startDate || event.start_date;
        const endDate = event.endDate || event.end_date || startDate;
        const startTime = event.startTime || event.start_time;
        const endTime = event.endTime || event.end_time;

        const eventStart = new Date(startDate + 'T' + startTime);
        const eventEnd = new Date(endDate + 'T' + endTime);
        const slotTime = new Date(dateString + 'T' + hour);

        return slotTime >= eventStart && slotTime < eventEnd;
    },

    // ─── RENDER CALENDAR ───
    render: () => {
        const grid = document.getElementById('calendar-grid');
        const label = document.getElementById('current-week-label');
        if (!grid) return;

        grid.innerHTML = '';
        const startOfWeek = CalendarManager.getStartOfWeek(CalendarManager.currentDate);

        const endOfWeek = new Date(startOfWeek);
        endOfWeek.setDate(endOfWeek.getDate() + 6);
        label.textContent = `Semaine du ${startOfWeek.getDate()}/${startOfWeek.getMonth()+1} au ${endOfWeek.getDate()}/${endOfWeek.getMonth()+1}`;

        const headers = document.querySelectorAll('.day-header');
        const days = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];

        for (let i = 0; i < 7; i++) {
            const dayDate = new Date(startOfWeek);
            dayDate.setDate(dayDate.getDate() + i);
            headers[i].textContent = `${days[dayDate.getDay()]} ${dayDate.getDate()}`;

            if (dayDate.toDateString() === new Date().toDateString()) {
                headers[i].style.color = '#2563eb';
                headers[i].style.background = '#eff6ff';
            } else {
                headers[i].style.color = '';
                headers[i].style.background = '';
            }
        }

        CalendarManager.hours.forEach(hour => {
            const timeLabel = document.createElement('div');
            timeLabel.className = 'time-slot-label';
            timeLabel.textContent = hour;
            grid.appendChild(timeLabel);

            for (let i = 0; i < 7; i++) {
                const currentDay = new Date(startOfWeek);
                currentDay.setDate(currentDay.getDate() + i);
                const dateString = currentDay.toISOString().split('T')[0];

                const cell = document.createElement('div');
                cell.className = 'calendar-slot';
                cell.dataset.date = dateString;
                cell.dataset.time = hour;

                cell.onclick = (e) => {
                    if (e.target === cell) CalendarManager.openModal(null, dateString, hour);
                };

                const cellEvents = CalendarManager.events.filter(evt =>
                    CalendarManager.isEventActiveAt(evt, dateString, hour)
                );

                cellEvents.forEach(evt => {
                    const div = document.createElement('div');
                    const evtType = evt.type;
                    const evtId = evt.id;
                    const startTime = evt.startTime || evt.start_time;
                    const endTime = evt.endTime || evt.end_time;

                    div.className = `event-block event-${evtType}`;

                    if (evtType === 'garde') {
                        // Use backend assignedUserName or fallback
                        let userName = evt.assignedUserName || 'Inconnu';
                        if (userName === 'Inconnu' && window.allUsers && evt.assignedUser) {
                            const u = window.allUsers.find(user => user.id === evt.assignedUser);
                            if (u) userName = u.username;
                        }
                        div.innerHTML = `<strong>🚨 GARDE</strong><br>${userName}<br><small>${startTime} - ${endTime}</small>`;
                    } else {
                        div.innerHTML = `<strong>📅 ${startTime}</strong> ${evt.title}`;
                    }

                    div.onclick = (e) => {
                        e.stopPropagation();
                        CalendarManager.openModal(evtId);
                    };
                    cell.appendChild(div);
                });

                grid.appendChild(cell);
            }
        });
    },

    // ─── OPEN MODAL ───
    openModal: (id = null, date = null, time = null) => {
        const modal = document.getElementById('event-modal');
        const form = document.getElementById('event-form');
        const deleteBtn = document.getElementById('btn-delete-event');

        CalendarManager.populateUserSelects();

        if (id) {
            const evt = CalendarManager.events.find(e => e.id == id);
            if (!evt) return;

            document.getElementById('event-modal-title').textContent = 'Modifier l\'événement';
            document.getElementById('event-id').value = evt.id;
            document.getElementById('event-type').value = evt.type;
            document.getElementById('event-notes').value = evt.notes || '';
            document.getElementById('event-start-date').value = evt.startDate || evt.start_date;
            document.getElementById('event-end-date').value = evt.endDate || evt.end_date || evt.startDate || evt.start_date;
            document.getElementById('event-start-time').value = evt.startTime || evt.start_time;
            document.getElementById('event-end-time').value = evt.endTime || evt.end_time;

            if (evt.type === 'rdv') {
                document.getElementById('event-title').value = evt.title || '';
                document.getElementById('event-sales-rep').value = evt.salesRep || '';
            } else {
                document.getElementById('event-assigned-user').value = evt.assignedUser || '';
            }

            deleteBtn.style.display = 'block';
        } else {
            form.reset();
            document.getElementById('event-modal-title').textContent = 'Nouveau Planning';
            document.getElementById('event-id').value = '';
            document.getElementById('event-start-date').value = date || new Date().toISOString().split('T')[0];
            document.getElementById('event-end-date').value = date || new Date().toISOString().split('T')[0];

            if (time) {
                document.getElementById('event-start-time').value = time;
                let h = parseInt(time.split(':')[0]) + 1;
                document.getElementById('event-end-time').value = h.toString().padStart(2, '0') + ':00';
            } else {
                document.getElementById('event-start-time').value = '09:00';
                document.getElementById('event-end-time').value = '10:00';
            }
            deleteBtn.style.display = 'none';
        }

        CalendarManager.toggleFields();
        modal.classList.add('active');
    },

    closeModal: () => {
        document.getElementById('event-modal').classList.remove('active');
    },

    // ─── POPULATE USER SELECTS ───
    populateUserSelects: () => {
        const repSelect = document.getElementById('event-sales-rep');
        const userSelect = document.getElementById('event-assigned-user');
        if (!window.allUsers) return;

        const createOptions = (selectElement) => {
            // Clear all except first option
            while (selectElement.children.length > 1) {
                selectElement.removeChild(selectElement.lastChild);
            }
            window.allUsers.forEach(u => {
                const opt = document.createElement('option');
                opt.value = u.id;
                opt.textContent = `${u.username} (${u.first_name || ''} ${u.last_name || ''})`;
                selectElement.appendChild(opt);
            });
        };

        createOptions(repSelect);
        createOptions(userSelect);
    },

    // ─── TOGGLE FIELDS ───
    toggleFields: () => {
        const type = document.getElementById('event-type').value;
        const groupRdv = document.getElementById('group-rdv');
        const groupGarde = document.getElementById('group-garde');

        if (type === 'garde') {
            groupRdv.style.display = 'none';
            groupGarde.style.display = 'block';
            document.getElementById('event-title').required = false;
            document.getElementById('event-assigned-user').required = true;
        } else {
            groupRdv.style.display = 'block';
            groupGarde.style.display = 'none';
            document.getElementById('event-title').required = true;
            document.getElementById('event-assigned-user').required = false;
        }
    },

    // ─── FORM SUBMIT → BACKEND ───
    setupListeners: () => {
        const form = document.getElementById('event-form');

        if (form) {
            form.onsubmit = async (e) => {
                e.preventDefault();

                const id = document.getElementById('event-id').value;
                const type = document.getElementById('event-type').value;
                const startDate = document.getElementById('event-start-date').value;
                const endDate = document.getElementById('event-end-date').value || startDate;
                const startTime = document.getElementById('event-start-time').value;
                const endTime = document.getElementById('event-end-time').value;

                // Validation
                if (endDate < startDate) {
                    return alert("La date de fin ne peut pas être avant la date de début !");
                }
                if (startDate === endDate && endTime <= startTime) {
                    return alert("L'heure de fin doit être après l'heure de début !");
                }

                // Build payload for backend
                let payload = {
                    type: type,
                    startDate: startDate,
                    endDate: endDate,
                    startTime: startTime,
                    endTime: endTime,
                    notes: document.getElementById('event-notes').value || null
                };

                if (type === 'rdv') {
                    payload.title = document.getElementById('event-title').value;
                    payload.salesRep = document.getElementById('event-sales-rep').value || null;
                    payload.assignedUser = null;
                } else {
                    payload.title = 'Garde';
                    payload.assignedUser = document.getElementById('event-assigned-user').value;
                    payload.salesRep = null;
                }

                // Save to backend (POST or PUT)
                const success = await CalendarManager.saveEvent(payload, id || null);

                if (success) {
                    CalendarManager.closeModal();
                    alert('✅ Événement enregistré !');
                }
            };
        }

        const typeSelect = document.getElementById('event-type');
        if (typeSelect) {
            typeSelect.addEventListener('change', () => CalendarManager.toggleFields());
        }
    }
};