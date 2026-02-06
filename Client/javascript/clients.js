/**
 * clients.js
 * Client Management Logic
 * Handles client CRUD, Search, and Session UI updates.
 */

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
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const auth = getAuthInfo();
    if (!auth.token) {
        window.location.href = 'auth.html';
        return;
    }
    
    // Initial UI update for static elements
    updateDynamicUserUI();

    loadNavbar();
    fetchClients();
    setupEventListeners();
    setupSearch();
});

function getAuthInfo() {
    const token = CookieManager.get('access_token');
    if (!token) return { token: null, isAdmin: false };
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const isAdmin = payload.is_admin === true || (payload.sub && payload.sub.role === 'admin');
        return { token, isAdmin };
    } catch (e) {
        return { token: null, isAdmin: false };
    }
}

// ==========================================
// DATA FETCHING & RENDERING
// ==========================================

async function fetchClients() {
    const { token, isAdmin } = getAuthInfo();
    try {
        const response = await fetch('http://127.0.0.1:5000/clients/', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) throw new Error("Fetch failed");

        const clients = await response.json();
        window.allClients = clients; // Store for fallback search
        renderTable(clients, isAdmin);
        updateStats(clients);
    } catch (error) {
        console.error("Client Fetch Error:", error);
    }
}

function renderTable(clients, isAdmin) {
    const tbody = document.getElementById('clients-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!clients || clients.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No clients found</td></tr>';
        return;
    }

    clients.forEach(c => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${c.first_name}</td>
            <td>${c.last_name}</td>
            <td>${c.email}</td>
            <td>${c.phone || '-'}</td>
            <td>${c.address || '-'}</td>
            <td>
                ${isAdmin ? `
                    <button class="btn-edit" onclick="editClient('${c.id}')">✏️ Update</button>
                    <button class="btn-delete" onclick="deleteClient('${c.id}')">🗑️ delete</button>
                ` : '-'}
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ==========================================
// EVENT LISTENERS & CRUD
// ==========================================

function setupEventListeners() {
    const modal = document.getElementById('client-modal');
    const form = document.getElementById('client-form');

    document.getElementById('add-client-btn').onclick = () => {
        form.reset();
        form.removeAttribute('data-client-id');
        modal.style.display = 'block';
    };

    document.getElementById('close-modal').onclick = () => { modal.style.display = 'none'; };

    // Top-bar Logout
    document.querySelector('.btn-logout-top')?.addEventListener('click', logoutUser);

    form.onsubmit = async (e) => {
        e.preventDefault();
        const { token } = getAuthInfo();
        const formData = new FormData(form);
        const clientId = form.getAttribute('data-client-id');
        
        const payload = {
            first_name: formData.get('first_name').trim(),
            last_name: formData.get('last_name').trim(),
            email: formData.get('email').trim(),
            phone: formData.get('phone') || null,
            address: formData.get('address') || null
        };

        const url = clientId ? `http://127.0.0.1:5000/clients/${clientId}` : 'http://127.0.0.1:5000/clients/';
        const response = await fetch(url, {
            method: clientId ? 'PUT' : 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            modal.style.display = 'none';
            fetchClients();
        }
    };
}

window.editClient = async (id) => {
    const { token } = getAuthInfo();
    const response = await fetch(`http://127.0.0.1:5000/clients/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (response.ok) {
        const c = await response.json();
        const form = document.getElementById('client-form');
        form.querySelector('[name="first_name"]').value = c.first_name;
        form.querySelector('[name="last_name"]').value = c.last_name;
        form.querySelector('[name="email"]').value = c.email;
        form.querySelector('[name="phone"]').value = c.phone || '';
        form.querySelector('[name="address"]').value = c.address || '';
        form.setAttribute('data-client-id', id);
        document.getElementById('client-modal').style.display = 'block';
    }
};

window.deleteClient = async (id) => {
    if (!confirm("Confirm deletion?")) return;
    const { token } = getAuthInfo();
    await fetch(`http://127.0.0.1:5000/clients/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    fetchClients();
};

// ==========================================
// SEARCH & UI UTILS
// ==========================================

function setupSearch() {
    const searchInput = document.getElementById('clients-search');
    if (!searchInput) return;
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const { isAdmin } = getAuthInfo();
        const filtered = window.allClients.filter(c => 
            c.first_name.toLowerCase().includes(query) || 
            c.last_name.toLowerCase().includes(query) || 
            c.email.toLowerCase().includes(query)
        );
        renderTable(filtered, isAdmin);
    });
}

function updateStats(clients) {
    const totalEl = document.getElementById('total-clients-count');
    const newCountEl = document.getElementById('new-clients-count');

    if (totalEl) totalEl.textContent = clients.length;

    if (newCountEl) {
        const now = new Date();
        const currentMonth = now.getMonth();
        const currentYear = now.getFullYear();

        const monthlyNewbies = clients.filter(c => {
            if (!c.created_at) {
                console.warn("Client sans created_at:", c);
                return false;
            }
            
            const creationDate = new Date(c.created_at);
            
            console.log(`Client ${c.first_name}: created ${creationDate.toISOString()} - Month: ${creationDate.getMonth()}, Year: ${creationDate.getFullYear()}`);
            
            return creationDate.getMonth() === currentMonth && 
                   creationDate.getFullYear() === currentYear;
        });

        console.log(`Nouveaux clients ce mois: ${monthlyNewbies.length}`);
        newCountEl.textContent = monthlyNewbies.length;
    }
}

function loadNavbar() {
    const placeholder = document.getElementById('navbar-placeholder');
    if (placeholder) {
        fetch('navbar.html')
            .then(res => res.text())
            .then(html => {
                placeholder.innerHTML = html;
                updateDynamicUserUI(); 
                document.getElementById('logout-btn')?.addEventListener('click', logoutUser);
            });
    }
}

function updateDynamicUserUI() {
    const user = localStorage.getItem('username') || "Operator";
    const initial = user.charAt(0).toUpperCase();
    document.querySelectorAll('.avatar').forEach(el => el.textContent = initial);
    const sidebarName = document.querySelector('.sidebar-footer strong');
    if (sidebarName) sidebarName.textContent = user;
}

function logoutUser() {
    document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    localStorage.clear();
    window.location.href = 'auth.html';
}