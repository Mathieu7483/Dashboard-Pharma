/**
 * Client Management
 * Handles CRUD operations and advanced Server-side search.
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
    },
    erase: (name) => {
        document.cookie = name + '=; Max-Age=-99999999; path=/;';
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const auth = getAuthInfo();
    if (!auth.token) {
        window.location.href = 'auth.html';
        return;
    }
    
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

async function fetchClients() {
    const { token, isAdmin } = getAuthInfo();
    try {
        const response = await fetch('http://127.0.0.1:5000/clients/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const clients = await response.json();
        renderTable(clients, isAdmin);
        updateStats(clients);
    } catch (error) {
        console.error("Fetch Error:", error);
    }
}

function renderTable(clients, isAdmin) {
    const tbody = document.getElementById('clients-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (clients.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No clients found.</td></tr>';
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
                    <button class="btn-edit" onclick="editClient('${c.id}')">✎</button>
                    <button class="btn-delete" onclick="deleteClient('${c.id}')">🗑</button>
                ` : '-'}
            </td>
        `;
        tbody.appendChild(row);
    });
}

function setupSearch() {
    const searchInput = document.getElementById('clients-search');
    let debounceTimer;

    searchInput?.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(debounceTimer);

        if (query.length === 0) {
            fetchClients();
            return;
        }

        debounceTimer = setTimeout(async () => {
            const { token, isAdmin } = getAuthInfo();
            try {
                const res = await fetch(`http://127.0.0.1:5000/clients/search?q=${encodeURIComponent(query)}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) {
                    const results = await res.json();
                    renderTable(results, isAdmin);
                }
            } catch (err) { console.error("Search error:", err); }
        }, 300);
    });
}

function setupEventListeners() {
    const modal = document.getElementById('client-modal');
    const form = document.getElementById('client-form');

    // Add button logic
    document.getElementById('add-client-btn').onclick = () => {
        form.reset();
        form.removeAttribute('data-client-id');
        document.querySelector('#client-modal h3').textContent = 'Add New Client';
        modal.style.display = 'block';
    };

    document.getElementById('close-modal').onclick = () => { modal.style.display = 'none'; };

    form.onsubmit = async (e) => {
        e.preventDefault();
        const { token } = getAuthInfo();
        const clientId = form.getAttribute('data-client-id');
        const formData = new FormData(form);
        
        const payload = {
            first_name: formData.get('first_name'),
            last_name: formData.get('last_name'),
            email: formData.get('email'),
            phone: formData.get('phone') || null,
            address: formData.get('address') || null
        };

        const url = clientId ? `http://127.0.0.1:5000/clients/${clientId}` : 'http://127.0.0.1:5000/clients/';
        const method = clientId ? 'PUT' : 'POST';

        const res = await fetch(url, {
            method: method,
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            modal.style.display = 'none';
            fetchClients();
        }
    };
}

window.editClient = async (id) => {
    const { token } = getAuthInfo();
    const res = await fetch(`http://127.0.0.1:5000/clients/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
        const c = await res.json();
        const form = document.getElementById('client-form');
        form.querySelector('[name="first_name"]').value = c.first_name;
        form.querySelector('[name="last_name"]').value = c.last_name;
        form.querySelector('[name="email"]').value = c.email;
        form.querySelector('[name="phone"]').value = c.phone || '';
        form.querySelector('[name="address"]').value = c.address || '';
        form.setAttribute('data-client-id', id);
        document.querySelector('#client-modal h3').textContent = 'Edit Client';
        document.getElementById('client-modal').style.display = 'block';
    }
};

window.deleteClient = async (id) => {
    if (!confirm("Delete this client?")) return;
    const { token } = getAuthInfo();
    const res = await fetch(`http://127.0.0.1:5000/clients/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) fetchClients();
};

function updateStats(clients) {
    const total = document.getElementById('total-clients-count');
    if (total) total.textContent = clients.length;
}

function loadNavbar() {
    fetch('navbar.html').then(res => res.text()).then(html => {
        const placeholder = document.getElementById('navbar-placeholder');
        if (placeholder) placeholder.innerHTML = html;
    });
}