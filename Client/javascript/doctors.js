/**
 * Doctor and Medical Management
 * Handles CRUD operations, Dashboard synchronization, and Server-side search.
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
    fetchDoctors();
    setupEventListeners();
    setupSearch(); // Integrated advanced search
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
 * Fetch all doctors and render the table.
 */
async function fetchDoctors() {
    const { token, isAdmin } = getAuthInfo();
    try {
        const response = await fetch('http://127.0.0.1:5000/doctors/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const doctors = await response.json();
        renderTable(doctors, isAdmin);
        updateStats(doctors);
    } catch (error) {
        console.error("Fetch Error:", error);
    }
}

/**
 * Build table rows with Admin check for action buttons.
 */
function renderTable(doctors, isAdmin) {
    const tbody = document.getElementById('doctors-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (doctors.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No records found.</td></tr>';
        return;
    }

    doctors.forEach(d => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${d.first_name}</td>
            <td>${d.last_name}</td>
            <td>${d.email}</td>
            <td><span class="badge-specialty">${d.specialty || '-'}</span></td>
            <td>${d.phone || '-'}</td>
            <td>${d.address || '-'}</td>
            <td>
                ${isAdmin ? `
                    <button class="btn-edit" onclick="editDoctor('${d.id}')" title="Edit">✎</button>
                    <button class="btn-delete" onclick="deleteDoctor('${d.id}')" title="Delete">🗑</button>
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
    const modal = document.getElementById('doctor-modal');
    const form = document.getElementById('doctor-form');

    // Logout operation
    const logoutBtn = document.querySelector('.top-bar-right .btn-logout-top');
    if (logoutBtn) {
        logoutBtn.onclick = () => {
            CookieManager.erase('access_token');
            window.location.href = 'auth.html';
        };
    }

    // Modal opening (Create mode)
    const addBtn = document.getElementById('add-doctor-btn');
    if (addBtn) {
        addBtn.onclick = () => {
            form.reset();
            form.removeAttribute('data-doctor-id');
            document.querySelector('#doctor-modal h3').textContent = 'Add New Doctor';
            modal.style.display = 'block';
        };
    }

    // Modal closing
    const closeBtn = document.getElementById('close-modal');
    if (closeBtn) {
        closeBtn.onclick = () => { modal.style.display = 'none'; };
    }

    // Create or Update submission
    form.onsubmit = async (e) => {
        e.preventDefault();
        const { token } = getAuthInfo();
        const doctorId = form.getAttribute('data-doctor-id');
        const formData = new FormData(form);
        
        const payload = {
            first_name: formData.get('first_name').trim(),
            last_name: formData.get('last_name').trim(),
            email: formData.get('email').trim(),
            phone: formData.get('phone').trim() || null,
            specialty: formData.get('specialty').trim(),
            address: formData.get('address').trim() || null
        };

        const url = doctorId ? `http://127.0.0.1:5000/doctors/${doctorId}` : 'http://127.0.0.1:5000/doctors/';
        const method = doctorId ? 'PUT' : 'POST';

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
                fetchDoctors(); // Refresh list
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
 * Advanced Server-Side Search with Debounce Logic.
 */
function setupSearch() {
    const searchInput = document.getElementById('doctors-search');
    let debounceTimer;

    searchInput?.addEventListener('input', (e) => {
        const query = e.target.value.trim();

        // Clear previous timer to avoid multiple API calls
        clearTimeout(debounceTimer);

        // If query is empty, revert to full list
        if (query.length === 0) {
            fetchDoctors();
            return;
        }

        // Wait 300ms after last keystroke before calling API
        debounceTimer = setTimeout(async () => {
            const { token, isAdmin } = getAuthInfo();
            try {
                const response = await fetch(`http://127.0.0.1:5000/doctors/search?q=${encodeURIComponent(query)}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (response.ok) {
                    const searchResults = await response.json();
                    // We reuse renderTable since we updated the Backend to return full models
                    renderTable(searchResults, isAdmin);
                }
            } catch (error) {
                console.error("Search API Error:", error);
            }
        }, 300);
    });
}

/**
 * Fetch specific doctor data and open the edit modal.
 */
window.editDoctor = async (id) => {
    const { token } = getAuthInfo();
    try {
        const res = await fetch(`http://127.0.0.1:5000/doctors/${id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const d = await res.json();
            const form = document.getElementById('doctor-form');
            form.querySelector('[name="first_name"]').value = d.first_name;
            form.querySelector('[name="last_name"]').value = d.last_name;
            form.querySelector('[name="email"]').value = d.email;
            form.querySelector('[name="phone"]').value = d.phone || '';
            form.querySelector('[name="specialty"]').value = d.specialty || '';
            form.querySelector('[name="address"]').value = d.address || '';
            
            form.setAttribute('data-doctor-id', id);
            document.querySelector('#doctor-modal h3').textContent = 'Edit Doctor';
            document.getElementById('doctor-modal').style.display = 'block';
        }
    } catch (err) { console.error("Load Error:", err); }
};

/**
 * Delete a doctor record by ID.
 */
window.deleteDoctor = async (id) => {
    if (!confirm("Are you sure you want to delete this doctor?")) return;
    const { token } = getAuthInfo();
    try {
        const res = await fetch(`http://127.0.0.1:5000/doctors/${id}`, { 
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.status === 204 || res.ok) {
            await fetchDoctors();
        } else {
            const err = await res.json();
            alert(`Error: ${err.message}`);
        }
    } catch (err) {
        console.error("Delete request failed:", err);
    }
};

/**
 * Update the dashboard counters (KPIs).
 */
function updateStats(doctors) {
    const total = document.getElementById('total-doctors-count');
    if (total) total.textContent = doctors.length;
}

/**
 * Injects the shared navigation bar.
 */
function loadNavbar() {
    fetch('navbar.html')
        .then(res => res.text())
        .then(html => {
            const placeholder = document.getElementById('navbar-placeholder');
            if (placeholder) placeholder.innerHTML = html;
        })
        .catch(err => console.error("Navbar Loading Error:", err));
}