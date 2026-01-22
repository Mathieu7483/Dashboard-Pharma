/**
 * settings.js - Admin Panel Management
 * Handles user CRUD, authentication, and UI interactions
 */

// ============================================
// 1. COOKIE & SESSION UTILITIES
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
    set: (name, value, days = 7) => {
        const expires = new Date(Date.now() + days * 864e5).toUTCString();
        document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax`;
    },
    erase: (name) => {
        document.cookie = name + '=; Max-Age=-99999999; path=/; SameSite=Lax';
    }
};

// ============================================
// 2. TOAST NOTIFICATION SYSTEM
// ============================================

const Toast = {
    show: (message, type = 'info') => {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        
        toast.innerHTML = `
            <span style="font-size: 20px;">${icons[type]}</span>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },
    
    success: (msg) => Toast.show(msg, 'success'),
    error: (msg) => Toast.show(msg, 'error'),
    warning: (msg) => Toast.show(msg, 'warning'),
    info: (msg) => Toast.show(msg, 'info')
};

// ============================================
// 3. LOADING OVERLAY
// ============================================

const Loading = {
    show: () => {
        document.getElementById('loading-overlay').style.display = 'flex';
    },
    hide: () => {
        document.getElementById('loading-overlay').style.display = 'none';
    }
};

// ============================================
// 4. API SERVICE
// ============================================

const API = {
    baseURL: '/api',
    
    async request(endpoint, options = {}) {
        const token = CookieManager.get('access_token');
        
        const config = {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                ...options.headers
            },
            ...options
        };
        
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, config);
            
            // Handle authentication errors
            if (response.status === 401 || response.status === 403) {
                Toast.error('Session expirée. Reconnexion requise.');
                setTimeout(() => {
                    CookieManager.erase('access_token');
                    window.location.href = 'auth.html';
                }, 1500);
                throw new Error('Unauthorized');
            }
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Erreur serveur');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },
    
    // User endpoints
    users: {
        getAll: () => API.request('/users/'),
        getById: (id) => API.request(`/users/${id}`),
        create: (data) => API.request('/users/', {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        update: (id, data) => API.request(`/users/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        }),
        delete: (id) => API.request(`/users/${id}`, { method: 'DELETE' })
    }
};

// ============================================
// 5. STATE MANAGEMENT
// ============================================

const State = {
    users: [],
    currentUser: null,
    filters: {
        search: '',
        role: 'all'
    },
    
    setUsers(users) {
        this.users = users;
        this.render();
    },
    
    getFilteredUsers() {
        return this.users.filter(user => {
            const matchesSearch = !this.filters.search || 
                user.username.toLowerCase().includes(this.filters.search.toLowerCase()) ||
                (user.email && user.email.toLowerCase().includes(this.filters.search.toLowerCase()));
            
            const matchesRole = this.filters.role === 'all' ||
                (this.filters.role === 'admin' && user.is_admin) ||
                (this.filters.role === 'staff' && !user.is_admin);
            
            return matchesSearch && matchesRole;
        });
    },
    
    render() {
        renderUserTable(this.getFilteredUsers());
        updateStats();
    }
};

// ============================================
// 6. INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    const token = CookieManager.get('access_token');
    
    if (!token) {
        window.location.href = 'auth.html';
        return;
    }
    
    await loadNavbar();
    initTabSystem();
    initFilters();
    await loadUsers();
    setupFormHandlers();
    setupUserProfile();
});

// ============================================
// 7. UI COMPONENTS
// ============================================

async function loadNavbar() {
    const placeholder = document.getElementById('navbar-placeholder');
    if (!placeholder) return;
    
    try {
        const response = await fetch('navbar.html');
        if (response.ok) {
            placeholder.innerHTML = await response.text();
            highlightActiveLink();
            setupLogout();
        }
    } catch (error) {
        console.error("Navbar loading error:", error);
    }
}

function highlightActiveLink() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const navLinks = {
        'index.html': 'nav-dashboard',
        'inventory.html': 'nav-inventory',
        'clients.html': 'nav-clients',
        'doctors.html': 'nav-doctors',
        'settings.html': 'nav-settings'
    };
    
    const activeId = navLinks[currentPage];
    if (activeId) {
        const activeLink = document.getElementById(activeId);
        if (activeLink) activeLink.classList.add('active');
    }
}

function setupUserProfile() {
    const firstName = localStorage.getItem('first_name') || "A";
    const avatar = document.getElementById('user-avatar');
    
    if (avatar) {
        avatar.textContent = firstName.charAt(0).toUpperCase();
    }
}

function setupLogout() {
    const logoutBtn = document.querySelector('.btn-logout-top');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm("Êtes-vous sûr de vouloir vous déconnecter ?")) {
                CookieManager.erase('access_token');
                localStorage.clear();
                Toast.success('Déconnexion réussie');
                setTimeout(() => window.location.href = 'auth.html', 1000);
            }
        });
    }
}

// ============================================
// 8. TAB SYSTEM
// ============================================

function initTabSystem() {
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.target;
            
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            contents.forEach(content => {
                content.classList.remove('active');
                if (content.id === target) {
                    content.classList.add('active');
                }
            });
        });
    });
}

// ============================================
// 9. FILTERS
// ============================================

function initFilters() {
    const searchInput = document.getElementById('user-search');
    const roleFilter = document.getElementById('role-filter');
    
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            State.filters.search = e.target.value;
            State.render();
        });
    }
    
    if (roleFilter) {
        roleFilter.addEventListener('change', (e) => {
            State.filters.role = e.target.value;
            State.render();
        });
    }
}

// ============================================
// 10. USER CRUD OPERATIONS
// ============================================

async function loadUsers() {
    Loading.show();
    
    try {
        const users = await API.users.getAll();
        State.setUsers(users);
        Toast.success(`${users.length} utilisateurs chargés`);
    } catch (error) {
        Toast.error('Erreur lors du chargement des utilisateurs');
        console.error(error);
    } finally {
        Loading.hide();
    }
}

function renderUserTable(users) {
    const tableBody = document.getElementById('user-table-body');
    const emptyState = document.getElementById('empty-state');
    const currentUserId = localStorage.getItem('user_id');
    
    // Update count badge
    const countBadge = document.getElementById('users-count');
    if (countBadge) countBadge.textContent = users.length;
    
    if (users.length === 0) {
        tableBody.innerHTML = '';
        if (emptyState) emptyState.style.display = 'block';
        return;
    }
    
    if (emptyState) emptyState.style.display = 'none';
    
    tableBody.innerHTML = users.map(user => {
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
                    <div>${user.email || 'Non renseigné'}</div>
                    <small style="color: #6b7280;">ID: ${user.id.slice(0, 8)}...</small>
                </td>
                <td>${roleBadge}</td>
                <td>
                    <span class="status-badge status-active">Actif</span>
                </td>
                <td>
                    <small style="color: #6b7280;">N/A</small>
                </td>
                <td>
                    <div class="action-group">
                        <button class="btn-action" onclick="openEditModal('${user.id}')">
                            ✏️ Modifier
                        </button>
                        ${!isCurrentUser ? 
                            `<button class="btn-danger" onclick="deleteUser('${user.id}')">🗑️ Supprimer</button>` :
                            '<span class="self-tag">Vous</span>'
                        }
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function updateStats() {
    const totalUsers = State.users.length;
    const admins = State.users.filter(u => u.is_admin).length;
    
    const statActiveUsers = document.getElementById('stat-active-users');
    const statAdmins = document.getElementById('stat-admins');
    
    if (statActiveUsers) statActiveUsers.textContent = totalUsers;
    if (statAdmins) statAdmins.textContent = admins;
}

// ============================================
// 11. MODAL MANAGEMENT
// ============================================

window.openEditModal = async (userId) => {
    Loading.show();
    
    try {
        const user = await API.users.getById(userId);
        
        document.getElementById('edit-user-id').value = user.id;
        document.getElementById('edit-username').value = user.username;
        document.getElementById('edit-email').value = user.email || '';
        document.getElementById('edit-first-name').value = user.first_name || '';
        document.getElementById('edit-last-name').value = user.last_name || '';
        document.getElementById('edit-is-admin').checked = user.is_admin;
        document.getElementById('edit-password').value = '';
        
        document.getElementById('edit-modal').classList.add('active');
    } catch (error) {
        Toast.error('Erreur lors du chargement de l\'utilisateur');
    } finally {
        Loading.hide();
    }
};

window.closeEditModal = () => {
    document.getElementById('edit-modal').classList.remove('active');
};

window.openCreateModal = () => {
    document.getElementById('create-user-form').reset();
    document.getElementById('create-modal').classList.add('active');
};

window.closeCreateModal = () => {
    document.getElementById('create-modal').classList.remove('active');
};

window.deleteUser = async (userId) => {
    if (!confirm("⚠️ Confirmer la suppression ?\nCette action est irréversible.")) return;
    
    Loading.show();
    
    try {
        await API.users.delete(userId);
        Toast.success('Utilisateur supprimé avec succès');
        await loadUsers();
    } catch (error) {
        Toast.error('Erreur lors de la suppression');
    } finally {
        Loading.hide();
    }
};

// ============================================
// 12. FORM HANDLERS
// ============================================

function setupFormHandlers() {
    // Edit User Form
    const editForm = document.getElementById('edit-user-form');
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const userId = document.getElementById('edit-user-id').value;
            const updatedData = {
                email: document.getElementById('edit-email').value,
                first_name: document.getElementById('edit-first-name').value,
                last_name: document.getElementById('edit-last-name').value,
                is_admin: document.getElementById('edit-is-admin').checked
            };
            
            const password = document.getElementById('edit-password').value;
            if (password) updatedData.password = password;
            
            Loading.show();
            
            try {
                await API.users.update(userId, updatedData);
                Toast.success('Utilisateur modifié avec succès');
                closeEditModal();
                await loadUsers();
            } catch (error) {
                Toast.error('Erreur lors de la modification');
            } finally {
                Loading.hide();
            }
        });
    }
    
    // Create User Form
    const createForm = document.getElementById('create-user-form');
    if (createForm) {
        createForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const newUserData = {
                username: document.getElementById('create-username').value,
                email: document.getElementById('create-email').value,
                password: document.getElementById('create-password').value,
                first_name: document.getElementById('create-first-name').value,
                last_name: document.getElementById('create-last-name').value,
                is_admin: document.getElementById('create-is-admin').checked
            };
            
            Loading.show();
            
            try {
                await API.users.create(newUserData);
                Toast.success('Utilisateur créé avec succès');
                closeCreateModal();
                await loadUsers();
            } catch (error) {
                Toast.error('Erreur lors de la création');
            } finally {
                Loading.hide();
            }
        });
    }
}