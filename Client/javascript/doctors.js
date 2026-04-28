/**
 * doctors.js
 * Doctor Management Logic
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
    updateDynamicUserUI();
    loadNavbar();
    fetchDoctors();
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

async function fetchDoctors() {
    const { token, isAdmin } = getAuthInfo();
    try {
        const response = await fetch('http://127.0.0.1:5000/doctors/', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error("Fetch failed");
        const doctors = await response.json();
        window.allDoctors = doctors;
        renderTable(doctors, isAdmin);
        updateStats(doctors);
    } catch (error) {
        console.error("Doctor Fetch Error:", error);
    }
}

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
            <td>${d.specialty || 'General'}</td>
            <td>${d.phone || '-'}</td>
            <td>${d.address || '-'}</td>
            <td>
                ${isAdmin ? `
                    <button class="btn-edit" onclick="editDoctor('${d.id}')">✏️ Update</button>
                    <button class="btn-delete" onclick="deleteDoctor('${d.id}')">🗑️ delete</button>
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
    const modal = document.getElementById('doctor-modal');
    const form = document.getElementById('doctor-form');

    document.getElementById('add-doctor-btn').onclick = () => {
        form.reset();
        form.removeAttribute('data-doctor-id');
        modal.style.display = 'block';
    };

    document.getElementById('close-modal').onclick = () => { modal.style.display = 'none'; };
    document.querySelector('.btn-logout-top')?.addEventListener('click', logoutUser);

    form.onsubmit = async (e) => {
        e.preventDefault();
        const { token } = getAuthInfo();
        const formData = new FormData(form);
        const doctorId = form.getAttribute('data-doctor-id');
        
        const payload = {
            first_name: formData.get('first_name').trim(),
            last_name: formData.get('last_name').trim(),
            email: formData.get('email').trim(),
            specialty: formData.get('specialty').trim(),
            phone: formData.get('phone') || null,
            address: formData.get('address') || null
        };

        const url = doctorId ? `http://127.0.0.1:5000/doctors/${doctorId}` : 'http://127.0.0.1:5000/doctors/';
        const response = await fetch(url, {
            method: doctorId ? 'PUT' : 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            modal.style.display = 'none';
            fetchDoctors();
        }
    };
}

window.editDoctor = async (id) => {
    const { token } = getAuthInfo();
    const response = await fetch(`http://127.0.0.1:5000/doctors/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (response.ok) {
        const d = await response.json();
        const form = document.getElementById('doctor-form');
        form.querySelector('[name="first_name"]').value = d.first_name;
        form.querySelector('[name="last_name"]').value = d.last_name;
        form.querySelector('[name="email"]').value = d.email;
        form.querySelector('[name="specialty"]').value = d.specialty || '';
        form.querySelector('[name="phone"]').value = d.phone || '';
        form.querySelector('[name="address"]').value = d.address || '';
        form.setAttribute('data-doctor-id', id);
        document.getElementById('doctor-modal').style.display = 'block';
    }
};

window.deleteDoctor = async (id) => {
    if (!confirm("Confirm deletion?")) return;
    const { token } = getAuthInfo();
    await fetch(`http://127.0.0.1:5000/doctors/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    fetchDoctors();
};

// ==========================================
// SEARCH & UI UTILS
// ==========================================

function setupSearch() {
    const searchInput = document.getElementById('doctors-search');
    if (!searchInput) return;
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const { isAdmin } = getAuthInfo();
        const filtered = window.allDoctors.filter(d => 
            d.first_name.toLowerCase().includes(query) || 
            d.last_name.toLowerCase().includes(query) || 
            d.email.toLowerCase().includes(query) ||
            (d.specialty && d.specialty.toLowerCase().includes(query))
        );
        renderTable(filtered, isAdmin);
    });
}

function updateStats(doctors) {
    const totalEl = document.getElementById('total-doctors-count');
    const newCountEl = document.getElementById('new-doctors-count');

    if (totalEl) totalEl.textContent = doctors.length;

    if (newCountEl) {
        const now = new Date();
        const currentMonth = now.getMonth();
        const currentYear = now.getFullYear();

        const monthlyNewbies = doctors.filter(d => {
            if (!d.created_at) return false;
            const creationDate = new Date(d.created_at);
            return creationDate.getMonth() === currentMonth && 
                   creationDate.getFullYear() === currentYear;
        }).length;

        newCountEl.textContent = monthlyNewbies;
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