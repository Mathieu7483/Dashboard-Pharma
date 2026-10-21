/**
 * inventory.js — Inventory Management (inventory.html)
 * Backend contract (/inventory/): name, active_ingredient, dosage, stock, price,
 * is_prescription_only, cis, cip13
 * Depends on common.js
 */

const LOW_STOCK_THRESHOLD = 10;

let allProducts = [];
let pendingDeepLinkId = new URLSearchParams(window.location.search).get('id');

document.addEventListener('DOMContentLoaded', () => {
    if (!initPage()) return;
    setupEventListeners();
    fetchInventory();
});

// ==========================================
// DATA FETCHING & RENDERING
// ==========================================

async function fetchInventory() {
    try {
        const res = await apiFetch('/inventory/');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        allProducts = await res.json();
        applyFilter();

        // ?id=... deep link coming from the dashboard "Order" button
        if (pendingDeepLinkId) {
            handleDeepLinking(pendingDeepLinkId);
            pendingDeepLinkId = null;
        }
    } catch (err) {
        console.error('Inventory fetch error:', err);
    }
}

function applyFilter() {
    const q = (document.getElementById('inventory-search')?.value || '').trim().toLowerCase();
    const list = q
        ? allProducts.filter(p =>
            [p.name, p.active_ingredient, p.dosage, p.cip13]
                .some(v => String(v ?? '').toLowerCase().includes(q)))
        : allProducts;
    renderTable(list);
}

function renderTable(products) {
    const tbody = document.getElementById('inventory-body');
    if (!tbody) return;
    const { isAdmin } = getAuthInfo();

    if (!products || products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Inventory is empty.</td></tr>';
        return;
    }

    tbody.innerHTML = products.map(p => {
        const low = Number(p.stock) < LOW_STOCK_THRESHOLD;
        return `
        <tr data-id="${esc(p.id)}" class="${low ? 'low-stock-row' : ''}">
            <td title="${esc(p.id)}">${esc(shortId(p.id))}</td>
            <td>${esc(p.name)} ${p.cis ? '<span title="Linked to the ANSM database">🔗</span>' : ''}</td>
            <td>${esc(p.active_ingredient || 'N/A')}</td>
            <td>${esc(p.dosage || 'N/A')}</td>
            <td>${Number(p.price).toFixed(2)} €</td>
            <td class="${low ? 'text-danger fw-bold' : ''}">${esc(p.stock)}</td>
            <td style="text-align:center;">${p.is_prescription_only ? '✅' : '❌'}</td>
            <td>
                ${isAdmin ? `
                    <button class="btn-edit" data-action="edit" data-id="${esc(p.id)}">✏️ Update</button>
                    <button class="btn-delete" data-action="delete" data-id="${esc(p.id)}">🗑️ Delete</button>
                ` : '-'}
            </td>
        </tr>`;
    }).join('');
}

function handleDeepLinking(productId) {
    setTimeout(() => {
        const row = document.querySelector(`tr[data-id="${CSS.escape(String(productId))}"]`);
        if (!row) return;
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        row.style.backgroundColor = 'rgba(255, 193, 7, 0.2)';
        row.style.outline = '2px solid #ffc107';
        setTimeout(() => {
            row.style.backgroundColor = '';
            row.style.outline = '';
        }, 3000);
    }, 150);
}

// ==========================================
// MODAL & CRUD
// ==========================================

function openProductModal(product = null) {
    const form = document.getElementById('product-form');
    form.reset();
    document.getElementById('product-id').value = product ? product.id : '';
    document.getElementById('product-modal-title').textContent = product ? 'Edit Product' : 'Add New Product';

    if (product) {
        form.elements['name'].value = product.name || '';
        form.elements['active_ingredient'].value = product.active_ingredient || '';
        form.elements['dosage'].value = product.dosage || '';
        form.elements['cip13'].value = product.cip13 || '';
        form.elements['price'].value = product.price ?? '';
        form.elements['stock'].value = product.stock ?? '';
        form.elements['is_prescription_only'].checked = Boolean(product.is_prescription_only);
    }
    document.getElementById('product-modal').style.display = 'block';
}

async function saveProduct(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const id = fd.get('id');
    const isUpdate = Boolean(id);

    const payload = {
        name: fd.get('name').trim(),
        active_ingredient: fd.get('active_ingredient').trim(),
        dosage: fd.get('dosage').trim(),
        stock: parseInt(fd.get('stock'), 10),
        price: parseFloat(fd.get('price')),
        is_prescription_only: fd.get('is_prescription_only') === 'on'
    };
    const cip13 = fd.get('cip13').trim();
    if (cip13 || isUpdate) payload.cip13 = cip13;

    try {
        const res = await apiFetch(isUpdate ? `/inventory/${id}` : '/inventory/', {
            method: isUpdate ? 'PUT' : 'POST',
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            alert(await errorMessage(res, 'Save failed'));
            return;
        }

        // POST /inventory/ ignores cip13 (the route does not forward it to the facade):
        // set it with a follow-up update. PUT is admin-only, so skipped for other users.
        if (!isUpdate && cip13 && getAuthInfo().isAdmin) {
            const created = await res.json().catch(() => null);
            if (created?.id) {
                await apiFetch(`/inventory/${created.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ cip13 })
                });
            }
        }

        document.getElementById('product-modal').style.display = 'none';
        fetchInventory();
    } catch (err) {
        console.error('Product save error:', err);
    }
}

async function deleteProduct(id) {
    if (!confirm('Confirm deletion?')) return;
    try {
        const res = await apiFetch(`/inventory/${id}`, { method: 'DELETE' });
        if (!res.ok) {
            alert(await errorMessage(res, 'Delete failed'));
            return;
        }
        fetchInventory();
    } catch (err) {
        console.error('Product delete error:', err);
    }
}

function setupEventListeners() {
    document.getElementById('add-product-btn').addEventListener('click', () => openProductModal());
    bindModalClose('product-modal', 'close-product-modal');
    document.getElementById('product-form').addEventListener('submit', saveProduct);
    document.getElementById('inventory-search')?.addEventListener('input', applyFilter);

    // Row actions (event delegation)
    document.getElementById('inventory-body').addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-action]');
        if (!btn) return;
        const { action, id } = btn.dataset;
        if (action === 'edit') {
            const product = allProducts.find(p => String(p.id) === id);
            if (product) openProductModal(product);
        } else if (action === 'delete') {
            deleteProduct(id);
        }
    });
}