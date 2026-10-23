/**
 * clients.js — Client Management (clients.html)
 * Backend contract: first_name, last_name, email (required on create), phone, address
 * Depends on common.js
 */

let allClients = [];

document.addEventListener('DOMContentLoaded', () => {
    if (!initPage()) return;
    setupEventListeners();
    fetchClients();
    // Coming from the dashboard quick actions banner
    if (new URLSearchParams(window.location.search).get('new')) openClientModal();
});

// ==========================================
// DATA FETCHING & RENDERING
// ==========================================

async function fetchClients() {
    try {
        const res = await apiFetch('/clients/');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        allClients = await res.json();
        applyFilter();
    } catch (err) {
        console.error('Client fetch error:', err);
    }
}

function applyFilter() {
    const q = (document.getElementById('clients-search')?.value || '').trim().toLowerCase();
    const list = q
        ? allClients.filter(c =>
            [c.first_name, c.last_name, c.email, c.phone, c.address]
                .some(v => String(v ?? '').toLowerCase().includes(q)))
        : allClients;
    renderTable(list);
}

function renderTable(clients) {
    const tbody = document.getElementById('clients-body');
    if (!tbody) return;
    const { isAdmin } = getAuthInfo();

    if (!clients || clients.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No clients found</td></tr>';
        return;
    }

    tbody.innerHTML = clients.map(c => `
        <tr>
            <td title="${esc(c.id)}">${esc(shortId(c.id))}</td>
            <td>${esc(c.first_name)}</td>
            <td>${esc(c.last_name)}</td>
            <td>${esc(c.phone || '-')}</td>
            <td>${esc(c.email || '-')}</td>
            <td>${esc(c.address || '-')}</td>
            <td>
                ${isAdmin ? `
                    <button class="btn-edit" data-action="edit" data-id="${esc(c.id)}">✏️ Update</button>
                    <button class="btn-delete" data-action="delete" data-id="${esc(c.id)}">🗑️ Delete</button>
                ` : '-'}
            </td>
        </tr>`).join('');
}

// ==========================================
// MODAL & CRUD
// ==========================================

function openClientModal(client = null) {
    const form = document.getElementById('client-form');
    form.reset();
    document.getElementById('client-id').value = client ? client.id : '';
    document.getElementById('client-modal-title').textContent = client ? 'Edit Client' : 'Add New Client';

    if (client) {
        form.elements['first_name'].value = client.first_name || '';
        form.elements['last_name'].value = client.last_name || '';
        form.elements['phone'].value = client.phone || '';
        form.elements['email'].value = client.email || '';
        form.elements['address'].value = client.address || '';
    }
    document.getElementById('client-modal').style.display = 'block';
}

async function saveClient(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const id = fd.get('id');
    const isUpdate = Boolean(id);

    const payload = {
        first_name: fd.get('first_name').trim(),
        last_name: fd.get('last_name').trim(),
        email: fd.get('email').trim()
    };
    // Optional fields: on create, omit when empty (the API validates types, null is rejected);
    // on update, send '' so a field can be cleared.
    for (const key of ['phone', 'address']) {
        const value = fd.get(key).trim();
        if (value || isUpdate) payload[key] = value;
    }

    try {
        const res = await apiFetch(isUpdate ? `/clients/${id}` : '/clients/', {
            method: isUpdate ? 'PUT' : 'POST',
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            document.getElementById('client-modal').style.display = 'none';
            fetchClients();
        } else {
            alert(await errorMessage(res, 'Save failed'));
        }
    } catch (err) {
        console.error('Client save error:', err);
    }
}

async function deleteClient(id) {
    if (!confirm('Confirm deletion?')) return;
    try {
        const res = await apiFetch(`/clients/${id}`, { method: 'DELETE' });
        if (!res.ok) {
            alert(await errorMessage(res, 'Delete failed'));
            return;
        }
        fetchClients();
    } catch (err) {
        console.error('Client delete error:', err);
    }
}

function setupEventListeners() {
    document.getElementById('add-client-btn').addEventListener('click', () => openClientModal());
    bindModalClose('client-modal', 'close-client-modal');
    document.getElementById('client-form').addEventListener('submit', saveClient);
    document.getElementById('clients-search')?.addEventListener('input', applyFilter);

    // Row actions (event delegation)
    document.getElementById('clients-body').addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-action]');
        if (!btn) return;
        const { action, id } = btn.dataset;
        if (action === 'edit') {
            const client = allClients.find(c => String(c.id) === id);
            if (client) openClientModal(client);
        } else if (action === 'delete') {
            deleteClient(id);
        }
    });
}