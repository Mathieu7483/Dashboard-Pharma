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
    setupANSMSuggestions();

    if (new URLSearchParams(window.location.search).get('new')) {
        openProductModal();
    }
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
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;">Inventory is empty.</td></tr>';
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
            <td>${esc(p.cip13 || '-')}</td>
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
    const modal = document.getElementById('product-modal');
    const form = document.getElementById('product-form');
    if (!modal || !form) return;

    form.reset();
    document.getElementById('product-id').value = product ? product.id : '';
    document.getElementById('product-modal-title').textContent = product ? 'Edit Product' : 'Add New Product';

    const suggestionsBox = document.getElementById('ansm-suggestions');
    if (suggestionsBox) {
        suggestionsBox.style.display = 'none';
        suggestionsBox.innerHTML = '';
    }

    if (product) {
        form.elements['name'].value = product.name || '';
        form.elements['active_ingredient'].value = product.active_ingredient || '';
        form.elements['dosage'].value = product.dosage || '';
        form.elements['cip13'].value = product.cip13 || '';
        form.elements['price'].value = product.price ?? '';
        form.elements['stock'].value = product.stock ?? '';
        form.elements['is_prescription_only'].checked = Boolean(product.is_prescription_only);
    }
    modal.style.display = 'block';
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
    const addBtn = document.getElementById('add-product-btn');
    if (addBtn) addBtn.addEventListener('click', () => openProductModal());

    bindModalClose('product-modal', 'close-product-modal');

    const form = document.getElementById('product-form');
    if (form) form.addEventListener('submit', saveProduct);

    const searchInput = document.getElementById('inventory-search');
    if (searchInput) searchInput.addEventListener('input', applyFilter);

    const tbody = document.getElementById('inventory-body');
    if (tbody) {
        tbody.addEventListener('click', (e) => {
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
}

// ==========================================
// RECHERCHE INTELLIGENTE ANSM & AUTOCOMPLÉTION
// ==========================================

function setupANSMSuggestions() {
    const nameInput = document.getElementById('product-name');
    const suggestionsBox = document.getElementById('ansm-suggestions');

    if (!nameInput || !suggestionsBox) {
        setTimeout(setupANSMSuggestions, 500);
        return;
    }

    let debounceTimer;

    nameInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();
        console.log("Saisie utilisateur :", query);

        if (query.length < 2) {
            suggestionsBox.style.display = 'none';
            suggestionsBox.innerHTML = '';
            return;
        }

        debounceTimer = setTimeout(async () => {
            try {
                const res = await apiFetch(`/inventory/search-ansm?q=${encodeURIComponent(query)}`);
                console.log("Statut réponse API:", res.status);
                if (!res.ok) return;

                const items = await res.json();
                console.log("Données JSON reçues de l'ANSM:", items);

                if (!items || items.length === 0) {
                    console.warn("Tableau items vide, aucun résultat à afficher.");
                    suggestionsBox.style.display = 'none';
                    suggestionsBox.innerHTML = '';
                    return;
                }

                suggestionsBox.innerHTML = items.map(item => `
                    <div class="suggestion-item" style="padding: 10px; cursor: pointer; border-bottom: 1px solid #eee; background: #fff;"
                         data-name="${esc(item.denomination)}"
                         data-ingredient="${esc(item.active_ingredient)}"
                         data-dosage="${esc(item.dosage)}"
                         data-cip="${esc(item.cip13 || '')}"
                         data-cis="${esc(item.cis)}">
                        <strong>${esc(item.denomination)}</strong><br>
                        <small style="color: #666;">Substance : ${esc(item.active_ingredient || 'N/A')} | CIP : ${esc(item.cip13 || 'N/A')}</small>
                    </div>
                `).join('');

                suggestionsBox.style.display = 'block';
                console.log("Boîte de suggestions affichée avec succès !");
            } catch (err) {
                console.error('Erreur attrapée dans l\'autocomplétion :', err);
            }
        }, 300);
    });

    suggestionsBox.addEventListener('click', (e) => {
        const itemDiv = e.target.closest('.suggestion-item');
        if (!itemDiv) return;

        const form = document.getElementById('product-form');
        if (!form) return;

        form.elements['name'].value = itemDiv.dataset.name;
        form.elements['active_ingredient'].value = itemDiv.dataset.ingredient;
        form.elements['dosage'].value = itemDiv.dataset.dosage;

        const cipField = form.elements['cip13'];
        if (cipField) cipField.value = itemDiv.dataset.cip;

        suggestionsBox.style.display = 'none';
        suggestionsBox.innerHTML = '';
    });

    document.getElementById('product-modal').addEventListener('click', (e) => {
        if (!nameInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
            suggestionsBox.style.display = 'none';
        }
    });
}