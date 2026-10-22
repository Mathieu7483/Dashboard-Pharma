/**
 * doctors.js — Doctor Management (doctors.html)
 * Backend contract: first_name, last_name, email, specialty, phone, address
 * Depends on common.js
 */

let allDoctors = [];

document.addEventListener('DOMContentLoaded', () => {
    if (!initPage()) return;
    setupEventListeners();
    fetchDoctors();
    // Coming from the dashboard quick actions banner
    if (new URLSearchParams(window.location.search).get('new')) openDoctorModal();
});

// ==========================================
// DATA FETCHING & RENDERING
// ==========================================

async function fetchDoctors() {
    try {
        const res = await apiFetch('/doctors/');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        allDoctors = await res.json();
        applyFilter();
    } catch (err) {
        console.error('Doctor fetch error:', err);
    }
}

function applyFilter() {
    const q = (document.getElementById('doctors-search')?.value || '').trim().toLowerCase();
    const list = q
        ? allDoctors.filter(d =>
            [d.first_name, d.last_name, d.specialty, d.email, d.phone, d.address]
                .some(v => String(v ?? '').toLowerCase().includes(q)))
        : allDoctors;
    renderTable(list);
}

function renderTable(doctors) {
    const tbody = document.getElementById('doctors-body');
    if (!tbody) return;
    const { isAdmin } = getAuthInfo();

    if (!doctors || doctors.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No doctors found</td></tr>';
        return;
    }

    tbody.innerHTML = doctors.map(d => `
        <tr>
            <td title="${esc(d.id)}">${esc(shortId(d.id))}</td>
            <td>${esc(d.first_name)}</td>
            <td>${esc(d.last_name)}</td>
            <td><span class="badge-specialty">${esc(d.specialty || 'General')}</span></td>
            <td>${esc(d.phone || '-')}</td>
            <td>${esc(d.email || '-')}</td>
            <td>${esc(d.address || '-')}</td>
            <td>
                ${isAdmin ? `
                    <button class="btn-edit" data-action="edit" data-id="${esc(d.id)}">✏️ Update</button>
                    <button class="btn-delete" data-action="delete" data-id="${esc(d.id)}">🗑️ Delete</button>
                ` : '-'}
            </td>
        </tr>`).join('');
}

// ==========================================
// MODAL & CRUD
// ==========================================

function openDoctorModal(doctor = null) {
    const form = document.getElementById('doctor-form');
    form.reset();
    document.getElementById('doctor-id').value = doctor ? doctor.id : '';
    document.getElementById('doctor-modal-title').textContent = doctor ? 'Edit Doctor' : 'Add New Doctor';

    if (doctor) {
        form.elements['first_name'].value = doctor.first_name || '';
        form.elements['last_name'].value = doctor.last_name || '';
        form.elements['specialty'].value = doctor.specialty || '';
        form.elements['phone'].value = doctor.phone || '';
        form.elements['email'].value = doctor.email || '';
        form.elements['address'].value = doctor.address || '';
    }
    document.getElementById('doctor-modal').style.display = 'block';
}

async function saveDoctor(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const id = fd.get('id');
    const isUpdate = Boolean(id);

    const payload = {
        first_name: fd.get('first_name').trim(),
        last_name: fd.get('last_name').trim()
    };
    // Optional fields: omitted when empty on create (null is rejected by the API
    // validation), sent as '' on update so a field can be cleared.
    for (const key of ['specialty', 'phone', 'email', 'address']) {
        const value = fd.get(key).trim();
        if (value || isUpdate) payload[key] = value;
    }

    try {
        const res = await apiFetch(isUpdate ? `/doctors/${id}` : '/doctors/', {
            method: isUpdate ? 'PUT' : 'POST',
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            document.getElementById('doctor-modal').style.display = 'none';
            fetchDoctors();
        } else {
            alert(await errorMessage(res, 'Save failed'));
        }
    } catch (err) {
        console.error('Doctor save error:', err);
    }
}

async function deleteDoctor(id) {
    if (!confirm('Confirm deletion?')) return;
    try {
        const res = await apiFetch(`/doctors/${id}`, { method: 'DELETE' });
        if (!res.ok) {
            alert(await errorMessage(res, 'Delete failed'));
            return;
        }
        fetchDoctors();
    } catch (err) {
        console.error('Doctor delete error:', err);
    }
}

function setupEventListeners() {
    document.getElementById('add-doctor-btn').addEventListener('click', () => openDoctorModal());
    bindModalClose('doctor-modal', 'close-doctor-modal');
    document.getElementById('doctor-form').addEventListener('submit', saveDoctor);
    document.getElementById('doctors-search')?.addEventListener('input', applyFilter);

    // Row actions (event delegation)
    document.getElementById('doctors-body').addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-action]');
        if (!btn) return;
        const { action, id } = btn.dataset;
        if (action === 'edit') {
            const doctor = allDoctors.find(d => String(d.id) === id);
            if (doctor) openDoctorModal(doctor);
        } else if (action === 'delete') {
            deleteDoctor(id);
        }
    });
}