/**
 * settings.js - Admin Panel Management
 */

// ============================================
// 1. COOKIE MANAGER
// ============================================

const CookieManager = {
    /**
     * Get cookie value by name
     * @param {string} name - Cookie name
     * @returns {string|null} Cookie value or null if not found
     */
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
    
    /**
     * Delete a cookie by setting expiration to past date
     * @param {string} name - Cookie name to delete
     */
    erase: (name) => {
        document.cookie = name + '=; Max-Age=-99999999; path=/;';
    }
};

// ============================================
// 2. AUTH HELPER
// ============================================

/**
 * Extract and decode authentication information from JWT token
 * @returns {Object} Object containing token and admin status
 */
function getAuthInfo() {
    const token = CookieManager.get('access_token');
    if (!token) return { token: null, isAdmin: false };
    
    try {
        // Decode JWT payload (base64)
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
    
    // Check authentication
    const auth = getAuthInfo();
    if (!auth.token) {
        alert('You must be logged in to access this page');
        window.location.href = 'auth.html';
        return;
    }
    
    // Check admin privileges
    if (!auth.isAdmin) {
        alert('Admin access required');
        window.location.href = 'index.html';
        return;
    }
    
    // Initialize all modules
    loadNavbar();
    fetchUsers();
    fetchTickets();           // Load tickets on page load
    setupEventListeners();
    initTabSystem();
    initFilters();
    initTicketFilters();      // Initialize ticket filtering system
    
});

// ============================================
// 4. FETCH USERS
// ============================================

/**
 * Fetch all users from the API
 * Requires admin authentication
 */
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
        
        // Store globally for filtering
        window.allUsers = users;
        renderUserTable(users, isAdmin);
        updateStats(users);
        
    } catch (error) {
        console.error("❌ User Fetch Error:", error);
        alert('Error loading users. Check console for details.');
    }
}

// ============================================
// 5. RENDER USER TABLE
// ============================================

/**
 * Render users in the table
 * @param {Array} users - Array of user objects
 * @param {boolean} isAdmin - Whether current user is admin
 */
function renderUserTable(users, isAdmin) {
    const tbody = document.getElementById('user-table-body');
    const emptyState = document.getElementById('empty-state');
    const currentUserId = localStorage.getItem('user_id');
    
    if (!tbody) {
        console.error('Table body not found!');
        return;
    }

    // Update user count badge
    const countBadge = document.getElementById('users-count');
    if (countBadge) countBadge.textContent = users.length;
    
    // Handle empty state
    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No users found</td></tr>';
        if (emptyState) emptyState.style.display = 'block';
        return;
    }
    
    if (emptyState) emptyState.style.display = 'none';
    
    // Generate table rows
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

/**
 * updateStats - Update dashboard statistics
 * @param {Array} users - list of users (retrieved via API)
 * @param {Array} tickets - List of tickets (optional, for ticketing stats)
 */

function updateStats(users = [], tickets = []) {
    const statActiveUsers = document.getElementById('stat-active-users');
    const statAdmins = document.getElementById('stat-admins');
    const statTickets = document.getElementById('stat-tickets');
    
    if (statActiveUsers) statActiveUsers.textContent = users.length;
    if (statAdmins) statAdmins.textContent = users.filter(u => u.is_admin).length;
    if (statTickets) statTickets.textContent = tickets.length;
}


// ============================================
// 7. USER MODAL MANAGEMENT
// ============================================

/**
 * Open edit modal for a specific user
 * @param {string} userId - UUID of the user to edit
 */
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
        
        // Populate form fields
        document.getElementById('edit-user-id').value = user.id;
        document.getElementById('edit-username').value = user.username;
        document.getElementById('edit-email').value = user.email || '';
        document.getElementById('edit-first-name').value = user.first_name || '';
        document.getElementById('edit-last-name').value = user.last_name || '';
        document.getElementById('edit-is-admin').checked = user.is_admin;
        document.getElementById('edit-password').value = '';
        
        // Show modal
        document.getElementById('edit-modal').classList.add('active');
        
    } catch (error) {
        console.error('Edit modal error:', error);
        alert('Network error while loading user');
    }
};

/**
 * Close the edit user modal
 */
window.closeEditModal = () => {
    document.getElementById('edit-modal').classList.remove('active');
};

/**
 * Open the create user modal
 */
window.openCreateModal = () => {
    document.getElementById('create-user-form').reset();
    document.getElementById('create-modal').classList.add('active');
};

/**
 * Close the create user modal
 */
window.closeCreateModal = () => {
    document.getElementById('create-modal').classList.remove('active');
};

/**
 * Delete a user by ID
 * @param {string} userId - UUID of the user to delete
 */
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

/**
 * Setup all form event listeners
 */
function setupEventListeners() {
    const editForm = document.getElementById('edit-user-form');
    const createForm = document.getElementById('create-user-form');
    
    // ==========================================
    // EDIT USER FORM HANDLER
    // ==========================================
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
            
            // Build payload
            const payload = {
                email: email || null,
                first_name: firstName || null,
                last_name: lastName || null,
                is_admin: isAdmin
            };
            
            // Only include password if provided
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
    
    // ==========================================
    // CREATE USER FORM HANDLER
    // ==========================================
    if (createForm) {
        createForm.onsubmit = async (e) => {
            e.preventDefault();
            const { token } = getAuthInfo();
            
            // Extract form values directly (more reliable than FormData)
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
            
            // Build payload
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
    
    // ==========================================
    // LOGOUT BUTTON HANDLER
    // ==========================================
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

/**
 * Initialize tab switching functionality
 */
function initTabSystem() {
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.target;
            
            // Remove active class from all tabs and contents
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Show target content
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
// 10. USER FILTERS
// ============================================

/**
 * Initialize search and role filtering for users
 */
function initFilters() {
    const searchInput = document.getElementById('user-search');
    const roleFilter = document.getElementById('role-filter');
    
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const { isAdmin } = getAuthInfo();
            
            if (!window.allUsers) return;
            
            // Apply both search and role filters
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
                // Trigger search input to reapply filters
                searchInput.dispatchEvent(new Event('input'));
            }
        });
    }
}

// ============================================
// 11. TICKETING SYSTEM
// ============================================

/**
 * Fetch all tickets from the API
 * Only accessible to admin users
 */
async function fetchTickets() {
    const { token, isAdmin } = getAuthInfo();
    if (!token) return;

    console.log('🎫 Loading tickets...');

    try {
        const response = await fetch('http://127.0.0.1:5000/tickets/', {
            method: 'GET',
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        console.log('📡 Tickets response status:', response.status);

        if (!response.ok) {
            if (response.status === 401) {
                alert('Session expired. Please login again.');
                window.location.href = 'auth.html';
                return;
            }
            if (response.status === 403) {
                console.log('⚠️ Admin access required for tickets');
                return;
            }
            throw new Error(`Fetch failed: ${response.status}`);
        }

        const tickets = await response.json();
        
        // Store globally for filtering
        window.allTickets = tickets;
        renderTicketTable(tickets);
        updateTicketStats(tickets);
        
        return tickets;
    } catch (error) {
        console.error("❌ Ticket Fetch Error:", error);
        alert('Error loading tickets. Check console for details.');
    }
}

/**
 * Render tickets in the table
 * @param {Array} tickets - Array of ticket objects
 */
function renderTicketTable(tickets) {
    const tbody = document.getElementById('ticket-table-body');
    
    if (!tbody) {
        console.error('❌ Ticket table body not found!');
        return;
    }

    // Update ticket count badge
    const countBadge = document.getElementById('tickets-count');
    if (countBadge) countBadge.textContent = tickets.length;
    
    // Handle empty state
    if (!tickets || tickets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No tickets found</td></tr>';
        return;
    }
    
    // Priority badge styles
    const priorityBadges = {
        'high': '<span class="badge" style="background:#ef4444; color:white; padding:4px 8px; border-radius:4px;">🔴 High</span>',
        'medium': '<span class="badge" style="background:#f59e0b; color:white; padding:4px 8px; border-radius:4px;">🟠 Medium</span>',
        'low': '<span class="badge" style="background:#3b82f6; color:white; padding:4px 8px; border-radius:4px;">🔵 Low</span>'
    };
    
    // Generate table rows
    tbody.innerHTML = tickets.map(ticket => {
        // Format creation date
        const date = new Date(ticket.created_at).toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
        
        // Truncate description for preview
        const description = ticket.description.length > 60 
            ? ticket.description.substring(0, 60) + '...'
            : ticket.description;
        
        return `
            <tr>
                <td><strong>#${ticket.id}</strong></td>
                <td>
                    <div style="max-width: 250px;">
                        <strong>${ticket.subject}</strong><br>
                        <small style="color: #6b7280;">${description}</small>
                    </div>
                </td>
                <td>
                    <small style="color: #6b7280;">User ID: ${ticket.user_id.slice(0, 8)}...</small>
                </td>
                <td>${priorityBadges[ticket.priority] || priorityBadges['medium']}</td>
                <td>
                    <select class="status-select" 
                            data-ticket-id="${ticket.id}" 
                            data-current-status="${ticket.status}"
                            onchange="handleStatusChange(${ticket.id}, this.value)">
                        <option value="open" ${ticket.status === 'open' ? 'selected' : ''}>🟢 Open</option>

                        <option value="pending" ${ticket.status === 'pending' ? 'selected' : ''}>🟡 Pending</option>
                        <option value="closed" ${ticket.status === 'closed' ? 'selected' : ''}>🟣 Closed</option>
                    </select>
                </td>
                <td><small>${date}</small></td>
                <td>
                    <div class="action-group">
                        <button class="btn-action" onclick="viewTicket(${ticket.id})" title="View details">
                            👁️ View
                        </button>
                        <button class="btn-action" onclick="openAdminNoteModal(${ticket.id})" title="Edit admin note">
                            📝 Note
                        </button>
                        <button class="btn-danger" onclick="deleteTicket(${ticket.id})" title="Delete ticket">
                            🗑️ Delete
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Handle status change from dropdown
 * @param {number} ticketId - ID of the ticket
 * @param {string} newStatus - New status value
 */
window.handleStatusChange = async (ticketId, newStatus) => {
    const selectElement = document.querySelector(`select[data-ticket-id="${ticketId}"]`);
    const previousStatus = selectElement.dataset.currentStatus;
    
    // Confirm the change
    if (!confirm(`Change ticket #${ticketId} status to "${newStatus}"?`)) {
        // Revert to previous value if cancelled
        selectElement.value = previousStatus;
        return;
    }
    
    const { token } = getAuthInfo();
    
    try {
        const response = await fetch(`http://127.0.0.1:5000/tickets/${ticketId}`, {
            method: 'PUT',
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (response.ok) {
            console.log(`✅ Ticket ${ticketId} updated to ${newStatus}`);
            selectElement.dataset.currentStatus = newStatus;
            
            // Optional: Ask if they want to add a note
            if (confirm('Status updated! Would you like to add an admin note?')) {
                openAdminNoteModal(ticketId);
            } else {
                fetchTickets(); // Refresh the table
            }
        } else {
            alert('Failed to update status');
            selectElement.value = previousStatus;
        }
    } catch (error) {
        console.error('❌ Error:', error);
        alert('Network error');
        selectElement.value = previousStatus;
    }
};

/**
 * Open modal to add/edit admin note
 * @param {number} ticketId - ID of the ticket
 */
window.openAdminNoteModal = async (ticketId) => {
    const { token } = getAuthInfo();
    
    try {
        const response = await fetch(`http://127.0.0.1:5000/tickets/${ticketId}`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            alert('Failed to load ticket');
            return;
        }

        const ticket = await response.json();
        
        const adminNote = prompt(
            `Admin Note for Ticket #${ticket.id}\nCurrent note: ${ticket.admin_note || '(none)'}\n\nEnter new admin note:`,
            ticket.admin_note || ''
        );
        
        if (adminNote === null) return; // User cancelled
        
        // Update ticket with new admin note
        const updateResponse = await fetch(`http://127.0.0.1:5000/tickets/${ticketId}`, {
            method: 'PUT',
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ admin_note: adminNote })
        });
        
        if (updateResponse.ok) {
            alert('✅ Admin note updated successfully');
            fetchTickets();
        } else {
            alert('Failed to update admin note');
        }
        
    } catch (error) {
        console.error('❌ Error:', error);
        alert('Network error');
    }
};

/**
 * Update ticket statistics
 * @param {Array} tickets - Array of ticket objects
 */
function updateTicketStats(tickets) {
    const openTickets = tickets.filter(t => t.status === 'open').length;
    const highPriority = tickets.filter(t => t.priority === 'high').length;
    const inProgress = tickets.filter(t => t.status === 'in_progress').length;
    
    console.log(`📊 Ticket Stats: ${openTickets} open, ${inProgress} in progress, ${highPriority} high priority`);
}

/**
 * View full ticket details
 * @param {number} ticketId - ID of the ticket to view
 */
window.viewTicket = async (ticketId) => {
    const { token } = getAuthInfo();
    
    try {
        const response = await fetch(`http://127.0.0.1:5000/tickets/${ticketId}`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            alert('Failed to load ticket details');
            return;
        }

        const ticket = await response.json();
        
        // Format the ticket details for display
        const createdAt = new Date(ticket.created_at).toLocaleString('fr-FR');
        const adminNoteSection = ticket.admin_note 
            ? `\n\n━━━━━━━━━━━━━━━━\nAdmin Note:\n${ticket.admin_note}`
            : '';
        
        // Display in alert (you can create a better modal later)
        alert(`
🎫 Ticket #${ticket.id}
━━━━━━━━━━━━━━━━
Subject: ${ticket.subject}
Priority: ${ticket.priority.toUpperCase()}
Status: ${ticket.status.toUpperCase()}
Created: ${createdAt}

Description:
${ticket.description}${adminNoteSection}
        `);
        
    } catch (error) {
        console.error('❌ Error loading ticket:', error);
        alert('Network error while loading ticket');
    }
};

/**
 * Delete a ticket by ID
 * @param {number} ticketId - ID of the ticket to delete
 */
window.deleteTicket = async (ticketId) => {
    if (!confirm('⚠️ Delete this ticket?\nThis action is irreversible.')) return;
    
    const { token } = getAuthInfo();
    
    try {
        const response = await fetch(`http://127.0.0.1:5000/tickets/${ticketId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            await fetchTickets(); // Refresh ticket list
            alert('✅ Ticket deleted successfully');
        } else {
            const error = await response.json();
            alert(error.message || 'Delete failed');
        }
    } catch (error) {
        console.error('❌ Delete Error:', error);
        alert('Network error during deletion');
    }
};

/**
 * Initialize ticket filtering system
 */
function initTicketFilters() {
    const statusFilter = document.getElementById('ticket-status-filter');
    const priorityFilter = document.getElementById('ticket-priority-filter');
    
    /**
     * Apply all active filters to ticket list
     */
    const applyFilters = () => {
        if (!window.allTickets) return;
        
        const statusValue = statusFilter ? statusFilter.value : 'all';
        const priorityValue = priorityFilter ? priorityFilter.value : 'all';
        
        console.log('🔍 Applying filters:', { status: statusValue, priority: priorityValue });
        
        // Filter tickets based on selected criteria
        const filtered = window.allTickets.filter(ticket => {
            const matchesStatus = statusValue === 'all' || ticket.status === statusValue;
            const matchesPriority = priorityValue === 'all' || ticket.priority === priorityValue;
            return matchesStatus && matchesPriority;
        });
        
        console.log(`✅ Filtered: ${filtered.length} of ${window.allTickets.length} tickets`);
        renderTicketTable(filtered);
    };
    
    // Attach event listeners to filter controls
    if (statusFilter) {
        statusFilter.addEventListener('change', applyFilters);
    }
    
    if (priorityFilter) {
        priorityFilter.addEventListener('change', applyFilters);
    }
}

// ============================================
// 12. NAVBAR LOADING
// ============================================

/**
 * Load navbar from external HTML file
 */
function loadNavbar() {
    fetch('navbar.html')
        .then(res => res.text())
        .then(html => {
            const placeholder = document.getElementById('navbar-placeholder');
            if (placeholder) {
                placeholder.innerHTML = html;
                highlightActiveLink();
                
                // Update user avatar with first initial
                const firstName = localStorage.getItem('first_name') || "A";
                const avatar = document.getElementById('user-avatar');
                if (avatar) {
                    avatar.textContent = firstName.charAt(0).toUpperCase();
                }
            }
        })
        .catch(err => console.error("Navbar Error:", err));
}

/**
 * Highlight the active navigation link based on current page
 */
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