/**
 * settings.js - Admin Panel Management
 */

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
        console.log('🔐 Auth Info:', { isAdmin, userId: payload.sub });
        return { token, isAdmin };
    } catch (e) {
        console.error('Token decode error:', e);
        return { token: null, isAdmin: false };
    }
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
    setupEventListeners();
    initTabSystem();
    initFilters();
});

// ============================================
// 4. FETCH USERS
// ============================================

async function fetchUsers() {
    const { token, isAdmin } = getAuthInfo();
    if (!token) return;

    console.log('📋 Loading users...');

    try {
        const response = await fetch('http://127.0.0.1:5000/users/', {
            method: 'GET',
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        console.log('📡 Response status:', response.status);

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
        console.log('✅ Users loaded:', users);
        
        window.allUsers = users;
        renderUserTable(users, isAdmin);
        updateStats(users);
        
    } catch (error) {
        console.error("❌ User Fetch Error:", error);
        alert('Error loading users. Check console for details.');
    }
}

// ============================================
// 5. RENDER TABLE
// ============================================

function renderUserTable(users, isAdmin) {
    const tbody = document.getElementById('user-table-body');
    const emptyState = document.getElementById('empty-state');
    const currentUserId = localStorage.getItem('user_id');
    
    if (!tbody) {
        console.error('Table body not found!');
        return;
    }

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

// ============================================
// 6. UPDATE STATS
// ============================================

function updateStats(users) {
    const totalUsers = users.length;
    const admins = users.filter(u => u.is_admin).length;
    
    const statActiveUsers = document.getElementById('stat-active-users');
    const statAdmins = document.getElementById('stat-admins');
    
    if (statActiveUsers) statActiveUsers.textContent = totalUsers;
    if (statAdmins) statAdmins.textContent = admins;
}

// ============================================
// 7. MODAL MANAGEMENT
// ============================================

window.openEditModal = async (userId) => {
    const { token } = getAuthInfo();
    
    try {
        const response = await fetch(`http://127.0.0.1:5000/users/${userId}`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            alert('Failed to load user data');
            return;
        }

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
        console.error('Edit modal error:', error);
        alert('Network error while loading user');
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
    
    const { token } = getAuthInfo();
    
    try {
        const response = await fetch(`http://127.0.0.1:5000/users/${userId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            await fetchUsers();
            alert('Utilisateur supprimé avec succès');
        } else {
            const error = await response.json();
            alert(error.message || 'Delete failed');
        }
    } catch (error) {
        console.error("Delete Error:", error);
        alert('Network error during deletion');
    }
};

// ============================================
// 8. EVENT LISTENERS & FORMS
// ============================================

function setupEventListeners() {
    const editForm = document.getElementById('edit-user-form');
    const createForm = document.getElementById('create-user-form');
    
    // Edit Form
    if (editForm) {
        editForm.onsubmit = async (e) => {
            e.preventDefault();
            const { token } = getAuthInfo();
            
            const userId = document.getElementById('edit-user-id').value;
            const email = document.getElementById('edit-email').value.trim();
            const firstName = document.getElementById('edit-first-name').value.trim();
            const lastName = document.getElementById('edit-last-name').value.trim();
            const password = document.getElementById('edit-password').value.trim();
            const isAdmin = document.getElementById('edit-is-admin').checked;
            
            const payload = {
                email: email || null,
                first_name: firstName || null,
                last_name: lastName || null,
                is_admin: isAdmin
            };
            
            if (password) payload.password = password;
            
            console.log('📤 Updating user:', userId, payload);
            
            try {
                const response = await fetch(`http://127.0.0.1:5000/users/${userId}`, {
                    method: 'PUT',
                    headers: { 
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                if (response.ok) {
                    closeEditModal();
                    await fetchUsers();
                    alert('Utilisateur modifié avec succès');
                } else {
                    const error = await response.json();
                    console.error('❌ Update error:', error);
                    alert(error.message || 'Update failed');
                }
            } catch (error) {
                console.error('❌ Network error:', error);
                alert('Network error');
            }
        };
    }
    
    // 🆕 FIXED: Create Form with better error handling
    if (createForm) {
        createForm.onsubmit = async (e) => {
            e.preventDefault();
            const { token } = getAuthInfo();
            
            // Direct value extraction (more reliable than FormData)
            const username = document.getElementById('create-username').value.trim();
            const email = document.getElementById('create-email').value.trim();
            const password = document.getElementById('create-password').value.trim();
            const firstName = document.getElementById('create-first-name').value.trim();
            const lastName = document.getElementById('create-last-name').value.trim();
            const isAdmin = document.getElementById('create-is-admin').checked;
            
            // Validation
            if (!username || !email || !password) {
                alert('⚠️ Username, email, and password are required!');
                return;
            }
            
            if (password.length < 6) {
                alert('⚠️ Password must be at least 6 characters!');
                return;
            }
            
            const payload = {
                username: username,
                email: email,
                password: password,
                first_name: firstName || null,
                last_name: lastName || null,
                is_admin: isAdmin
            };
            
            console.log('📤 Creating user:', payload);
            
            try {
                const response = await fetch('http://127.0.0.1:5000/users/', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                console.log('📡 Create response status:', response.status);
                
                if (response.ok) {
                    closeCreateModal();
                    await fetchUsers();
                    alert('✅ Utilisateur créé avec succès');
                } else {
                    const error = await response.json();
                    console.error('❌ Creation error:', error);
                    alert(`❌ Erreur: ${error.message || JSON.stringify(error)}`);
                }
            } catch (error) {
                console.error('❌ Network error:', error);
                alert('❌ Erreur réseau. Vérifiez la console.');
            }
        };
    }
    
    // Logout
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
// 9. TAB SYSTEM
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
// 10. FILTERS
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
            if (searchInput) {
                searchInput.dispatchEvent(new Event('input'));
            }
        });
    }
}

// ============================================
// 11. NAVBAR
// ============================================

function loadNavbar() {
    fetch('navbar.html')
        .then(res => res.text())
        .then(html => {
            const placeholder = document.getElementById('navbar-placeholder');
            if (placeholder) {
                placeholder.innerHTML = html;
                highlightActiveLink();
                
                const firstName = localStorage.getItem('first_name') || "A";
                const avatar = document.getElementById('user-avatar');
                if (avatar) {
                    avatar.textContent = firstName.charAt(0).toUpperCase();
                }
            }
        })
        .catch(err => console.error("Navbar Error:", err));
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