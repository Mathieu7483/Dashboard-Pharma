/**
 * inventory.js
 * Comprehensive Inventory & Sales Management
 * Professional version with English documentation and RESTx compliance.
 */

const CookieManager = {
    /**
     * Retrieves a specific cookie value by name.
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
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // Check for authentication token before initialization
    const token = CookieManager.get('access_token');
    if (!token) {
        window.location.href = 'auth.html';
        return;
    }
    
    loadNavbar();
    fetchInventory();
    setupEventListeners();
    setupSearch();
});

/**
 * Extracts JWT payload data to determine user role and ID.
 */
function getAuthInfo() {
    const token = CookieManager.get('access_token');
    if (!token) return { isAdmin: false, token: null };
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const isAdmin = payload.is_admin === true || (payload.sub && payload.sub.role === 'admin');
        return { isAdmin, token };
    } catch (e) {
        console.error("JWT Decoding Error:", e);
        return { isAdmin: false, token: null };
    }
}

// ==========================================
// DATA FETCHING & RENDERING
// ==========================================

/**
 * Fetches products from the inventory namespace.
 */
async function fetchInventory() {
    const { token, isAdmin } = getAuthInfo();
    try {
        const response = await fetch('http://127.0.0.1:5000/inventory/', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error("Could not retrieve inventory data");
        
        const products = await response.json();
        renderTable(products, isAdmin);
        updateStats(products);
    } catch (error) {
        console.error("Inventory Fetch Error:", error);
    }
}

/**
 * Injects product rows into the DOM.
 * Includes the specific column for quick sales.
 */
function renderTable(products, isAdmin) {
    const tbody = document.getElementById('inventory-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!products || products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Inventory is empty.</td></tr>';
        return;
    }

    products.forEach(p => {
        const row = document.createElement('tr');
        if (p.stock < 10) row.classList.add('low-stock-row');

        row.innerHTML = `
            <td>${p.name}</td>
            <td>${p.active_ingredient || 'N/A'}</td>
            <td class="${p.stock < 10 ? 'text-danger fw-bold' : ''}">${p.stock}</td>
            <td>${parseFloat(p.price).toFixed(2)} €</td>
            <td style="text-align:center;">${p.is_prescription_only ? '✅' : '❌'}</td>
            
            <td style="text-align:center;">
                <div style="display: flex; gap: 5px; justify-content: center;">
                    <input type="number" id="qty-${p.id}" value="1" min="1" max="${p.stock}" class="qty-input">
                    <button class="btn-sell" onclick="sellProduct('${p.id}')" title="Record sale">💰</button>
                </div>
            </td>

            <td>
                ${isAdmin ? `
                    <button class="btn-edit" onclick="editProduct('${p.id}')">✎</button>
                    <button class="btn-delete" onclick="deleteProduct('${p.id}')">🗑</button>
                ` : '<span class="text-muted">No Permissions</span>'}
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ==========================================
// SALES TRANSACTIONS (RESTx COMPLIANT)
// ==========================================

/**
 * Executes a sale transaction.
 * Must comply with the nested 'SaleInput' model: { client_id: str, items: [{product_id, quantity}] }
 */
window.sellProduct = async (productId) => {
    const { token } = getAuthInfo();
    const qtyInput = document.getElementById(`qty-${productId}`);
    const quantity = parseInt(qtyInput.value);

    if (isNaN(quantity) || quantity <= 0) {
        alert("Invalid quantity.");
        return;
    }

    try {
        // Step 1: Retrieve a valid client ID (required by backend logic)
        const clientRes = await fetch('http://127.0.0.1:5000/clients/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const clients = await clientRes.json();
        
        if (!clients || clients.length === 0) {
            alert("No clients found. Sales require a linked client record.");
            return;
        }

        // Step 2: Construct the nested payload for the Sales Namespace
        const salePayload = {
            client_id: clients[0].id, // Defaulting to the first available client for testing
            items: [
                {
                    product_id: productId,
                    quantity: quantity
                }
            ]
        };

        const response = await fetch('http://127.0.0.1:5000/sales/', {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify(salePayload)
        });

        if (response.ok) {
            qtyInput.style.backgroundColor = "#d4edda"; // Success feedback
            setTimeout(() => { fetchInventory(); }, 300);
        } else {
            const err = await response.json();
            alert(`Transaction Error (400): ${err.message}`);
        }
    } catch (err) {
        console.error("Sale Processing Failure:", err);
    }
};

// ==========================================
// CRUD OPERATIONS
// ==========================================

function setupEventListeners() {
    const modal = document.getElementById('product-modal');
    const form = document.getElementById('product-form');

    document.getElementById('add-product-btn').onclick = () => {
        form.reset();
        form.removeAttribute('data-product-id'); 
        modal.style.display = 'block';
    };

    document.getElementById('close-modal').onclick = () => { modal.style.display = 'none'; };

    form.onsubmit = async (e) => {
        e.preventDefault();
        const { token } = getAuthInfo();
        const productId = form.getAttribute('data-product-id');
        const formData = new FormData(form);
        
        const payload = {
            name: formData.get('name').trim(),
            active_ingredient: formData.get('active_ingredient').trim(),
            stock: parseInt(formData.get('stock')),
            price: parseFloat(formData.get('price')),
            is_prescription_only: formData.get('is_prescription_only') === 'on'
        };

        const url = productId ? `http://127.0.0.1:5000/inventory/${productId}` : 'http://127.0.0.1:5000/inventory/';
        
        const response = await fetch(url, {
            method: productId ? 'PUT' : 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            modal.style.display = 'none';
            fetchInventory();
        }
    };
}

window.editProduct = async (id) => {
    const { token } = getAuthInfo();
    const response = await fetch(`http://127.0.0.1:5000/inventory/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (response.ok) {
        const p = await response.json();
        const form = document.getElementById('product-form');
        form.querySelector('[name="name"]').value = p.name;
        form.querySelector('[name="active_ingredient"]').value = p.active_ingredient || '';
        form.querySelector('[name="stock"]').value = p.stock;
        form.querySelector('[name="price"]').value = p.price;
        form.querySelector('[name="is_prescription_only"]').checked = p.is_prescription_only;
        form.setAttribute('data-product-id', id);
        document.getElementById('product-modal').style.display = 'block';
    }
};

window.deleteProduct = async (id) => {
    if (!confirm("Confirm deletion?")) return;
    const { token } = getAuthInfo();
    await fetch(`http://127.0.0.1:5000/inventory/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    fetchInventory();
};

// ==========================================
// UI UTILITIES
// ==========================================

function updateStats(products) {
    document.getElementById('total-count').textContent = products.length;
    document.getElementById('low-stock-count').textContent = products.filter(p => p.stock < 10).length;
}

function setupSearch() {
    const searchInput = document.getElementById('inventory-search');
    if (!searchInput) return;
    searchInput.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('#inventory-body tr').forEach(row => {
            row.style.display = row.innerText.toLowerCase().includes(term) ? '' : 'none';
        });
    });
}

function loadNavbar() {
    const placeholder = document.getElementById('navbar-placeholder');
    if (placeholder) {
        fetch('navbar.html').then(res => res.text()).then(html => placeholder.innerHTML = html);
    }
}