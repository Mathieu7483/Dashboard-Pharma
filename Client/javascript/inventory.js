/**
 * Inventory Management Logic
 * Handles product retrieval, creation, update, and deletion via Flask API.
 * Optimized for Pharmacy Dashboard 2026.
 */

// --- COOKIE MANAGER ---
// Utility to retrieve the JWT token stored during login
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
    // Security Check: Redirect to login if no token is found
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
 * Extracts authentication details from the JWT payload.
 */
function getAuthInfo() {
    const token = CookieManager.get('access_token');
    if (!token) return { isAdmin: false, token: null };
    try {
        // Decoding the Base64 payload of the JWT
        const payload = JSON.parse(atob(token.split('.')[1]));
        const isAdmin = payload.is_admin === true || (payload.sub && payload.sub.role === 'admin');
        return { isAdmin, token };
    } catch (e) {
        console.error("JWT Decoding Error:", e);
        return { isAdmin: false, token: null };
    }
}

/**
 * API CALL: Fetches the list of medications from the backend.
 */
async function fetchInventory() {
    const { token, isAdmin } = getAuthInfo();
    
    try {
        const response = await fetch('http://127.0.0.1:5000/inventory/', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            if (response.status === 401) {
                alert('Session expired. Please login again.');
                window.location.href = 'auth.html';
                return;
            }
            throw new Error(`HTTP Error: ${response.status}`);
        }

        const products = await response.json();
        renderTable(products, isAdmin);
        updateStats(products);
    } catch (error) {
        console.error("Fetch Inventory Error:", error);
    }
}

/**
 * DOM MANIPULATION: Updates the HTML table with product data.
 */
function renderTable(products, isAdmin) {
    const tbody = document.getElementById('inventory-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!products || products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No medications found in inventory.</td></tr>';
        return;
    }

    products.forEach(p => {
        const row = document.createElement('tr');
        // Apply warning style if stock is low
        if (p.stock < 10) row.classList.add('low-stock-row');

        row.innerHTML = `
            <td>${p.name}</td>
            <td>${p.active_ingredient || 'N/A'}</td>
            <td class="${p.stock < 10 ? 'text-danger fw-bold' : ''}">${p.stock}</td>
            <td>${parseFloat(p.price).toFixed(2)} €</td>
            <td style="text-align:center;">${p.is_prescription_only ? '✅' : '❌'}</td>
            <td>
                ${isAdmin ? `
                    <button class="btn-edit" onclick="editProduct('${p.id}')" title="Edit">✎</button>
                    <button class="btn-delete" onclick="deleteProduct('${p.id}')" title="Delete">🗑</button>
                ` : '<span class="text-muted">Read Only</span>'}
            </td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * EVENT LISTENERS: Handles UI interactions (Modals, Forms, Logout).
 */
function setupEventListeners() {
    const modal = document.getElementById('product-modal');
    const form = document.getElementById('product-form');
    const modalTitle = document.querySelector('#product-modal h3');

    // Open Modal for New Product
    document.getElementById('add-product-btn').onclick = () => {
        form.reset();
        form.removeAttribute('data-product-id'); 
        if (modalTitle) modalTitle.textContent = 'Add New Medication';
        modal.style.display = 'block';
    };

    // Close Modal
    document.getElementById('close-modal').onclick = () => { 
        modal.style.display = 'none'; 
    };

    // Logout Action
    const logoutBtn = document.querySelector('.btn-logout-top');
    if (logoutBtn) {
        logoutBtn.onclick = () => {
            document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            window.location.href = 'auth.html';
        };
    }

    // Handle Form Submission (POST for new, PUT for existing)
    form.onsubmit = async (e) => {
        e.preventDefault();
        const { token } = getAuthInfo();
        const formData = new FormData(form);
        
        const productId = form.getAttribute('data-product-id');
        const isEditing = !!productId;

        // Constructing JSON Payload
        const payload = {
            name: formData.get('name').trim(),
            active_ingredient: formData.get('active_ingredient').trim(),
            dosage: formData.get('dosage') || "",
            stock: parseInt(formData.get('stock'), 10) || 0,
            price: parseFloat(formData.get('price')) || 0.0,
            is_prescription_only: formData.get('is_prescription_only') === 'on'
        };

        const url = isEditing 
            ? `http://127.0.0.1:5000/inventory/${productId}` 
            : 'http://127.0.0.1:5000/inventory/';
        
        try {
            const response = await fetch(url, {
                method: isEditing ? 'PUT' : 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                modal.style.display = 'none';
                await fetchInventory(); // Refresh table
                alert(isEditing ? 'Product updated!' : 'Product added!');
            } else {
                const err = await response.json();
                alert(`Error: ${err.message || 'Operation failed'}`);
            }
        } catch (err) {
            console.error("Submit Error:", err);
        }
    };
}

/**
 * GLOBAL SCOPE: Opens the modal and pre-fills it with existing product data.
 */
window.editProduct = async (id) => {
    const { token } = getAuthInfo();
    const modal = document.getElementById('product-modal');
    const form = document.getElementById('product-form');
    const modalTitle = document.querySelector('#product-modal h3');

    try {
        const response = await fetch(`http://127.0.0.1:5000/inventory/${id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) throw new Error("Could not fetch product details");

        const p = await response.json();
        
        // Populate form fields
        form.querySelector('[name="name"]').value = p.name;
        form.querySelector('[name="active_ingredient"]').value = p.active_ingredient || '';
        form.querySelector('[name="dosage"]').value = p.dosage || '';
        form.querySelector('[name="stock"]').value = p.stock;
        form.querySelector('[name="price"]').value = p.price;
        form.querySelector('[name="is_prescription_only"]').checked = p.is_prescription_only;
        
        // Store ID in form for the PUT request
        form.setAttribute('data-product-id', id);
        if (modalTitle) modalTitle.textContent = 'Edit Medication';
        modal.style.display = 'block';

    } catch (err) {
        console.error("Load Product Error:", err);
    }
};

/**
 * GLOBAL SCOPE: Deletes a product after confirmation.
 */
window.deleteProduct = async (id) => {
    if (!confirm("Are you sure you want to delete this medication?")) return;
    
    const { token } = getAuthInfo();
    try {
        const response = await fetch(`http://127.0.0.1:5000/inventory/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            await fetchInventory();
        } else {
            alert("Failed to delete product.");
        }
    } catch (err) {
        console.error("Delete Error:", err);
    }
};

/**
 * UI: Updates the KPI dashboard numbers.
 */
function updateStats(products) {
    const totalEl = document.getElementById('total-count');
    const lowEl = document.getElementById('low-stock-count');
    
    if (totalEl) totalEl.textContent = products.length;
    if (lowEl) lowEl.textContent = products.filter(p => p.stock < 10).length;
}

/**
 * SEARCH: Real-time filtering of the visible table rows.
 */
function setupSearch() {
    const searchInput = document.getElementById('inventory-search');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase().trim();
        const rows = document.querySelectorAll('#inventory-body tr');

        rows.forEach(row => {
            const text = row.innerText.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    });
}

/**
 * NAVIGATION: Injects the shared navbar HTML.
 */
function loadNavbar() {
    const placeholder = document.getElementById('navbar-placeholder');
    if (!placeholder) return;

    fetch('navbar.html')
        .then(res => res.text())
        .then(html => { placeholder.innerHTML = html; })
        .catch(err => console.error("Navbar loading failed:", err));
}