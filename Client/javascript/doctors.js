/**
 * Doctor Management Logic
 * Handles doctor retrieval, creation, update, and deletion via Flask API.
 * Features: Admin check, Server-side search by name/email/specialty, Debounce optimization
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
    fetchDoctors();
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
 * Fetches all doctors from the database.
 */
async function fetchDoctors() {
    const { token, isAdmin } = getAuthInfo();
    if (!token) return;

    try {
        const response = await fetch('http://127.0.0.1:5000/doctors/', {
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

        const doctors = await response.json();
        console.log('Doctors loaded:', doctors);
        
        // Store globally for client-side search fallback
        window.allDoctors = doctors;
        
        renderTable(doctors, isAdmin);
        updateStats(doctors);
    } catch (error) {
        console.error("Doctor Fetch Error:", error);
    }
}

/**
 * Renders doctor data into the HTML table.
 */
function renderTable(doctors, isAdmin) {
    const tbody = document.getElementById('doctors-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!doctors || doctors.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No doctors found</td></tr>';
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
                    <button class="btn-edit" onclick="editDoctor('${d.id}')" title="Edit">✏️ Update</button>
                    <button class="btn-delete" onclick="deleteDoctor('${d.id}')" title="Delete">🗑️ Delete</button>
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
    const modal = document.getElementById('doctor-modal');
    const form = document.getElementById('doctor-form');
    const modalTitle = document.querySelector('#doctor-modal .widget-header h3');

    // Ouvrir modal en mode création
    const addBtn = document.getElementById('add-doctor-btn');
    if (addBtn) {
        addBtn.onclick = () => {
            form.reset();
            form.removeAttribute('data-doctor-id');
            if (modalTitle) modalTitle.textContent = 'Add New Doctor';
            modal.style.display = 'block';
        };
    }

    const closeBtn = document.getElementById('close-modal');
    if (closeBtn) {
        closeBtn.onclick = () => { 
            modal.style.display = 'none'; 
            form.reset();
            form.removeAttribute('data-doctor-id');
        };
    }

    // Logout Logic
    const logoutBtn = document.querySelector('.btn-logout-top');
    if (logoutBtn) {
        logoutBtn.onclick = () => {
            CookieManager.erase('access_token');
            window.location.href = 'auth.html';
        };
    }

    // Doctor Creation (POST) or Update (PUT)
    form.onsubmit = async (e) => {
        e.preventDefault();
        const { token } = getAuthInfo();
        const formData = new FormData(form);
        
        const payload = {
            first_name: formData.get('first_name').trim(),
            last_name: formData.get('last_name').trim(),
            specialty: formData.get('specialty').trim(),
            email: formData.get('email').trim(),
            phone: formData.get('phone')?.trim() || null,
            address: formData.get('address')?.trim() || null
        };

        // Vérifier si on est en mode édition ou création
        const doctorId = form.getAttribute('data-doctor-id');
        const isEditing = !!doctorId;
        const url = isEditing 
            ? `http://127.0.0.1:5000/doctors/${doctorId}` 
            : 'http://127.0.0.1:5000/doctors/';
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
                form.removeAttribute('data-doctor-id');
                await fetchDoctors();
                alert(isEditing ? 'Doctor updated successfully!' : 'Doctor created successfully!');
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
 * Global function to edit a doctor
 */
window.editDoctor = async (id) => {
    const { token } = getAuthInfo();
    
    try {
        const response = await fetch(`http://127.0.0.1:5000/doctors/${id}`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            alert('Failed to load doctor data');
            return;
        }

        const doctor = await response.json();
        
        // Pré-remplir le formulaire
        const form = document.getElementById('doctor-form');
        const modal = document.getElementById('doctor-modal');
        const modalTitle = document.querySelector('#doctor-modal .widget-header h3');
        
        form.querySelector('input[name="first_name"]').value = doctor.first_name;
        form.querySelector('input[name="last_name"]').value = doctor.last_name;
        form.querySelector('input[name="specialty"]').value = doctor.specialty;
        form.querySelector('input[name="email"]').value = doctor.email;
        form.querySelector('input[name="phone"]').value = doctor.phone || '';
        form.querySelector('input[name="address"]').value = doctor.address || '';
        
        // Stocker l'ID pour le mode édition
        form.setAttribute('data-doctor-id', id);
        
        // Changer le titre
        if (modalTitle) modalTitle.textContent = 'Edit Doctor';
        
        modal.style.display = 'block';
        
    } catch (err) {
        console.error('Edit Error:', err);
        alert('Network error while loading doctor');
    }
};

/**
 * Global function to delete a doctor.
 */
window.deleteDoctor = async (id) => {
    if (!confirm("Confirm doctor deletion?")) return;
    const { token } = getAuthInfo();
    
    try {
        const res = await fetch(`http://127.0.0.1:5000/doctors/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (res.ok || res.status === 204) {
            await fetchDoctors();
            alert('Doctor deleted successfully!');
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
 * Setup search functionality with server-side search by name/email/specialty
 */
function setupSearch() {
    const searchInput = document.getElementById('doctors-search');
    if (!searchInput) return;

    let debounceTimer;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        clearTimeout(debounceTimer);

        // Si la recherche est vide, recharger tous les doctors
        if (query.length === 0) {
            fetchDoctors();
            return;
        }

        // Debounce: attendre 300ms après la dernière frappe
        debounceTimer = setTimeout(async () => {
            const { token, isAdmin } = getAuthInfo();
            try {
                const res = await fetch(
                    `http://127.0.0.1:5000/doctors/search?q=${encodeURIComponent(query)}`, 
                    { headers: { 'Authorization': `Bearer ${token}` } }
                );
                
                if (res.ok) {
                    const results = await res.json();
                    renderTable(results, isAdmin);
                } else {
                    console.error('Search failed:', res.status);
                    // Fallback: recherche côté client
                    performClientSideSearch(query, isAdmin);
                }
            } catch (err) {
                console.error("Search error:", err);
                // Fallback: recherche côté client
                performClientSideSearch(query, isAdmin);
            }
        }, 300);
    });
}

/**
 * 🆕 Client-side search fallback - recherche par nom, email ET spécialité
 */
function performClientSideSearch(query, isAdmin) {
    if (!window.allDoctors) return;
    
    const filtered = window.allDoctors.filter(doctor => {
        const firstNameMatch = doctor.first_name && doctor.first_name.toLowerCase().includes(query);
        const lastNameMatch = doctor.last_name && doctor.last_name.toLowerCase().includes(query);
        const emailMatch = doctor.email && doctor.email.toLowerCase().includes(query);
        const specialtyMatch = doctor.specialty && doctor.specialty.toLowerCase().includes(query);
        
        return firstNameMatch || lastNameMatch || emailMatch || specialtyMatch;
    });
    
    renderTable(filtered, isAdmin);
}

/**
 * Update Dashboard KPI cards.
 */
function updateStats(doctors) {
    const total = document.getElementById('total-doctors-count');
    const specialties = document.getElementById('specialties-count');
    
    if (total) total.textContent = doctors.length;
    
    // Compter les spécialités uniques
    const uniqueSpecialties = new Set(doctors.map(d => d.specialty).filter(s => s));
    if (specialties) specialties.textContent = uniqueSpecialties.size;
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