/**
 * Client Management Logic
 * Handles CRUD operations and Dashboard synchronization.
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

/**
 * Decodes JWT and returns token + admin status.
 */
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

/**
 * Fetch all clients and render.
 */
async function fetchClients() {
    const { token, isAdmin } = getAuthInfo();
    try {
        const response = await fetch('http://127.0.0.1:5000/clients/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const clients = await response.json();
        renderTable(clients, isAdmin);
        updateStats(clients);
    } catch (error) {
        console.error("Fetch Error:", error);
    }
}

/**
 * Build table rows with Admin check for buttons.
 */
function renderTable(clients, isAdmin) {
    const tbody = document.getElementById('clients-body');
    if (!tbody) return;
    tbody.innerHTML = '';

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

/**
 * Setup modal controls, logout, and form submission.
 */
function setupEventListeners() {
    const modal = document.getElementById('client-modal');
    const form = document.getElementById('client-form');

    // Logout - Specific selector to avoid conflict with "Add Client" button class
    const logoutBtn = document.querySelector('.top-bar-right .btn-logout-top');
    if (logoutBtn) {
        logoutBtn.onclick = () => {
            CookieManager.erase('access_token');
            window.location.href = 'auth.html';
        };
    }

    // Modal open
    document.getElementById('add-client-btn').onclick = () => {
        form.reset();
        form.removeAttribute('data-client-id');
        document.querySelector('#client-modal h3').textContent = 'Add New Client';
        modal.style.display = 'block';
    };

    // Modal close
    document.getElementById('close-modal').onclick = () => { modal.style.display = 'none'; };

    // Create or Update
    form.onsubmit = async (e) => {
        e.preventDefault();
        const { token } = getAuthInfo();
        const clientId = form.getAttribute('data-client-id');
        const formData = new FormData(form);
        
        const payload = {
            first_name: formData.get('first_name').trim(),
            last_name: formData.get('last_name').trim(),
            email: formData.get('email').trim(),
            phone: formData.get('phone').trim() || null,
            address: formData.get('address').trim() || null
        };

        const url = clientId ? `http://127.0.0.1:5000/clients/${clientId}` : 'http://127.0.0.1:5000/clients/';
        const method = clientId ? 'PUT' : 'POST';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                modal.style.display = 'none';
                fetchClients();
            } else {
                const err = await res.json();
                alert(`Error: ${err.message || 'Operation failed'}`);
            }
        } catch (err) {
            console.error("Request Error:", err);
        }
    };
}

/**
 * Fetch specific client and open edit modal.
 */
window.editClient = async (id) => {
    const { token } = getAuthInfo();
    try {
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
    } catch (err) { console.error("Load Error:", err); }
};

/**
 * Delete client by ID.
 */
window.deleteClient = async (id) => {
    if (!confirm("Confirm client deletion?")) return;
    const { token } = getAuthInfo();
    try {
        const res = await fetch(`http://127.0.0.1:5000/clients/${id}`, { 
            method: 'DELETE',
            headers: { 
                'Authorization': `Bearer ${token}`
            }
        });

        if (res.status === 204 || res.ok) {
            console.log("Deleted successfully");
            await fetchClients();
        } else if (res.status === 403) {
            alert("Permission denied: You must be an administrator.");
        } else {
            const err = await res.json();
            alert(`Error: ${err.message}`);
        }
    } catch (err) {
        console.error("Delete request failed:", err);
        alert("Server connection failed. Check if CORS or the URL is correct (Missing slash?)");
    }
};

/**
 * Filter table rows.
 */
function setupSearch() {
    document.getElementById('clients-search')?.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('#clients-body tr').forEach(row => {
            row.style.display = row.innerText.toLowerCase().includes(term) ? '' : 'none';
        });
    });
}

/**
 * Update Dashboard counters.
 */
function updateStats(clients) {
    const total = document.getElementById('total-clients-count');
    if (total) total.textContent = clients.length;
}

/**
 * Loads shared navbar.
 */
function loadNavbar() {
    fetch('navbar.html')
        .then(res => res.text())
        .then(html => document.getElementById('navbar-placeholder').innerHTML = html)
        .catch(err => console.error("Navbar Error:", err));
}