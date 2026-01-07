/**
 * Client Management Logic
 * Handles client retrieval, creation, update, and deletion via Flask API.
 * Features: Admin check, Server-side search, Debounce optimization
 */

// --- COOKIE MANAGER ---
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
        alert('You must be logged in to access this page');
        window.location.href = 'auth.html';
        return;
    }
    
    loadNavbar();
    fetchClients();
    setupEventListeners();
    setupSearch();
});

/**
 * Extract auth token and admin status from JWT
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
 * Fetches all clients from the database.
 */
async function fetchClients() {
    const { token, isAdmin } = getAuthInfo();
    if (!token) return;

    try {
        const response = await fetch('http://127.0.0.1:5000/clients/', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            if (response.status === 401) {
                alert('Session expired. Please login again.');
                window.location.href = 'auth.html';
                return;
            }
            throw new Error(`Fetch failed: ${response.status}`);
        }

        const clients = await response.json();
        console.log('Clients loaded:', clients);
        renderTable(clients, isAdmin);
        updateStats(clients);
    } catch (error) {
        console.error("Client Fetch Error:", error);
    }
}

/**
 * Renders client data into the HTML table.
 */
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
                    <button class="btn-edit" onclick="editClient('${c.id}')">✎</button>
                    <button class="btn-delete" onclick="deleteClient('${c.id}')">🗑</button>
                ` : '-'}
            </td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * Sets up listeners for buttons, modals, and forms.
 */
function setupEventListeners() {
    const modal = document.getElementById('client-modal');
    const form = document.getElementById('client-form');
    const modalTitle = document.querySelector('#client-modal .widget-header h3');

    // Ouvrir modal en mode création
    document.getElementById('add-client-btn').onclick = () => {
        form.reset();
        form.removeAttribute('data-client-id');
        if (modalTitle) modalTitle.textContent = 'Add New Client';
        modal.style.display = 'block';
    };

    document.getElementById('close-modal').onclick = () => { 
        modal.style.display = 'none'; 
        form.reset();
        form.removeAttribute('data-client-id');
    };

    // Logout Logic
    const logoutBtn = document.querySelector('.btn-logout-top');
    if (logoutBtn) {
        logoutBtn.onclick = () => {
            CookieManager.erase('access_token');
            window.location.href = 'auth.html';
        };
    }

    // Client Creation (POST) or Update (PUT)
    form.onsubmit = async (e) => {
        e.preventDefault();
        const { token } = getAuthInfo();
        const formData = new FormData(form);
        
        const payload = {
            first_name: formData.get('first_name').trim(),
            last_name: formData.get('last_name').trim(),
            email: formData.get('email').trim(),
            phone: formData.get('phone')?.trim() || null,
            address: formData.get('address')?.trim() || null
        };

        // Vérifier si on est en mode édition ou création
        const clientId = form.getAttribute('data-client-id');
        const isEditing = !!clientId;
        const url = isEditing 
            ? `http://127.0.0.1:5000/clients/${clientId}` 
            : 'http://127.0.0.1:5000/clients/';
        const method = isEditing ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                modal.style.display = 'none';
                form.reset();
                form.removeAttribute('data-client-id');
                await fetchClients();
                alert(isEditing ? 'Client updated successfully!' : 'Client created successfully!');
            } else {
                const errorData = await response.json();
                console.error(isEditing ? "Update Failed:" : "Creation Failed:", errorData);
                alert(`Error: ${errorData.message || JSON.stringify(errorData)}`);
            }
        } catch (err) {
            console.error("Network Error:", err);
            alert('Network error. Please try again.');
        }
    };
}

/**
 * Global function to edit a client
 */
window.editClient = async (id) => {
    const { token } = getAuthInfo();
    
    try {
        const response = await fetch(`http://127.0.0.1:5000/clients/${id}`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            alert('Failed to load client data');
            return;
        }

        const client = await response.json();
        
        // Pré-remplir le formulaire
        const form = document.getElementById('client-form');
        const modal = document.getElementById('client-modal');
        const modalTitle = document.querySelector('#client-modal .widget-header h3');
        
        form.querySelector('input[name="first_name"]').value = client.first_name;
        form.querySelector('input[name="last_name"]').value = client.last_name;
        form.querySelector('input[name="email"]').value = client.email;
        form.querySelector('input[name="phone"]').value = client.phone || '';
        form.querySelector('input[name="address"]').value = client.address || '';
        
        // Stocker l'ID pour le mode édition
        form.setAttribute('data-client-id', id);
        
        // Changer le titre
        if (modalTitle) modalTitle.textContent = 'Edit Client';
        
        modal.style.display = 'block';
        
    } catch (err) {
        console.error('Edit Error:', err);
        alert('Network error while loading client');
    }
};

/**
 * Global function to delete a client.
 */
window.deleteClient = async (id) => {
    if (!confirm("Confirm client deletion?")) return;
    const { token } = getAuthInfo();
    
    try {
        const res = await fetch(`http://127.0.0.1:5000/clients/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (res.ok) {
            await fetchClients();
            alert('Client deleted successfully!');
        } else {
            const error = await res.json();
            alert(error.message || 'Delete failed');
        }
    } catch (err) {
        console.error("Delete Error:", err);
        alert('Network error during deletion');
    }
};

/**
 * Setup search functionality with server-side search and debounce
 */
function setupSearch() {
    const searchInput = document.getElementById('clients-search');
    if (!searchInput) return;

    let debounceTimer;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(debounceTimer);

        // Si la recherche est vide, recharger tous les clients
        if (query.length === 0) {
            fetchClients();
            return;
        }

        // Debounce: attendre 300ms après la dernière frappe
        debounceTimer = setTimeout(async () => {
            const { token, isAdmin } = getAuthInfo();
            try {
                const res = await fetch(
                    `http://127.0.0.1:5000/clients/search?q=${encodeURIComponent(query)}`, 
                    { headers: { 'Authorization': `Bearer ${token}` } }
                );
                
                if (res.ok) {
                    const results = await res.json();
                    renderTable(results, isAdmin);
                } else {
                    console.error('Search failed:', res.status);
                }
            } catch (err) {
                console.error("Search error:", err);
            }
        }, 300);
    });
}

/**
 * Update Dashboard KPI cards.
 */
function updateStats(clients) {
    const total = document.getElementById('total-clients-count');
    const newCount = document.getElementById('new-clients-count');
    
    if (total) total.textContent = clients.length;
    
    // Calculer les nouveaux clients du mois
    const thisMonth = new Date().getMonth();
    const newThisMonth = clients.filter(c => {
        if (c.created_at) {
            const clientMonth = new Date(c.created_at).getMonth();
            return clientMonth === thisMonth;
        }
        return false;
    }).length;
    
    if (newCount) newCount.textContent = newThisMonth;
}

/**
 * Loads shared navbar.
 */
function loadNavbar() {
    fetch('navbar.html')
        .then(res => res.text())
        .then(html => {
            const placeholder = document.getElementById('navbar-placeholder');
            if (placeholder) placeholder.innerHTML = html;
        })
        .catch(err => console.error("Navbar Error:", err));
}