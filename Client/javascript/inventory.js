/**
 * Inventory Management Logic
 * Handles product retrieval, creation, and deletion via Flask API.
 */

// --- COOKIE MANAGER (même que dans auth.js) ---
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
    // Vérifier si l'utilisateur est connecté
    const token = CookieManager.get('access_token');
    if (!token) {
        alert('You must be logged in to access this page');
        window.location.href = 'auth.html'; // ou votre page de login
        return;
    }
    
    loadNavbar();
    fetchInventory();
    setupEventListeners();
    setupSearch();
});

/**
 * Extract auth token and admin status from JWT.
 */
function getAuthInfo() {
    const token = CookieManager.get('access_token');
    if (!token) return { isAdmin: false, token: null };
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const isAdmin = payload.is_admin === true || (payload.sub && payload.sub.role === 'admin');
        return { isAdmin, token };
    } catch (e) {
        return { isAdmin: false, token: null };
    }
}

/**
 * Fetches all products from the database.
 */
async function fetchInventory() {
    const { token, isAdmin } = getAuthInfo();
    if (!token) {
        console.error('No token found');
        return;
    }

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
            throw new Error(`Fetch failed: ${response.status}`);
        }

        const products = await response.json();
        console.log('Products loaded:', products); // Pour déboguer
        renderTable(products, isAdmin);
        updateStats(products);
    } catch (error) {
        console.error("Inventory Fetch Error:", error);
    }
}

/**
 * Renders product data into the HTML table.
 */
function renderTable(products, isAdmin) {
    const tbody = document.getElementById('inventory-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!products || products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No products found</td></tr>';
        return;
    }

    products.forEach(p => {
        const row = document.createElement('tr');
        if (p.stock < 10) row.classList.add('low-stock-row');

        row.innerHTML = `
            <td>${p.name}</td>
            <td>${p.active_ingredient}</td>
            <td class="${p.stock < 10 ? 'text-danger fw-bold' : ''}">${p.stock}</td>
            <td>${p.price.toFixed(2)} €</td>
            <td>${p.is_prescription_only ? '✅' : '❌'}</td>
            <td>
                ${isAdmin ? `
                    <button class="btn-edit" onclick="editProduct('${p.id}')">✎</button>
                    <button class="btn-delete" onclick="deleteProduct('${p.id}')">🗑</button>
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
    const modal = document.getElementById('product-modal');
    const form = document.getElementById('product-form');
    const modalTitle = document.querySelector('#product-modal .widget-header h3');

    // Modal Interaction - Ouvrir en mode "création"
    document.getElementById('add-product-btn').onclick = () => {
        form.reset();
        form.removeAttribute('data-product-id'); // Retirer l'ID si présent
        if (modalTitle) modalTitle.textContent = 'Add New Medication';
        modal.style.display = 'block';
    };

    document.getElementById('close-modal').onclick = () => { 
        modal.style.display = 'none'; 
        form.reset();
        form.removeAttribute('data-product-id');
    };

    // Logout Logic
    const logoutBtn = document.querySelector('.btn-logout-top');
    if (logoutBtn) {
        logoutBtn.onclick = () => {
            document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            window.location.href = 'auth.html';
        };
    }

    // Product Creation (POST) or Update (PUT)
    form.onsubmit = async (e) => {
        e.preventDefault();
        const { token } = getAuthInfo();
        const formData = new FormData(form);
        
        const payload = {
            name: formData.get('name').trim(),
            active_ingredient: formData.get('active_ingredient').trim(),
            dosage: formData.get('dosage') || "",
            stock: parseInt(formData.get('stock'), 10) || 0,
            price: parseFloat(formData.get('price')) || 0.0,
            is_prescription_only: formData.get('is_prescription_only') === 'on'
        };

        const productId = form.getAttribute('data-product-id');
        const isEditing = !!productId;
        const url = isEditing 
            ? `http://127.0.0.1:5000/inventory/${productId}` 
            : 'http://127.0.0.1:5000/inventory/';
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
                form.removeAttribute('data-product-id');
                await fetchInventory();
                alert(isEditing ? 'Product updated successfully!' : 'Product created successfully!');
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
 * Global function to edit a product - Opens modal with pre-filled data
 */
window.editProduct = async (id) => {
    const { token } = getAuthInfo();
    
    try {
        const response = await fetch(`http://127.0.0.1:5000/inventory/${id}`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            alert('Failed to load product data');
            return;
        }

        const product = await response.json();
        
        const form = document.getElementById('product-form');
        const modal = document.getElementById('product-modal');
        const modalTitle = document.querySelector('#product-modal .widget-header h3');
        
        form.querySelector('input[name="name"]').value = product.name;
        form.querySelector('input[name="active_ingredient"]').value = product.active_ingredient;
        form.querySelector('input[name="dosage"]').value = product.dosage || '';
        form.querySelector('input[name="stock"]').value = product.stock;
        form.querySelector('input[name="price"]').value = product.price;
        form.querySelector('input[name="is_prescription_only"]').checked = product.is_prescription_only;
        
        form.setAttribute('data-product-id', id);
        

        if (modalTitle) modalTitle.textContent = 'Edit Medication';
        
        modal.style.display = 'block';
        
    } catch (err) {
        console.error('Edit Error:', err);
        alert('Network error while loading product');
    }
};

/**
 * Global function to delete a product.
 */
window.deleteProduct = async (id) => {
    if (!confirm("Confirm product deletion?")) return;
    const { token } = getAuthInfo();
    try {
        const res = await fetch(`http://127.0.0.1:5000/inventory/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            await fetchInventory();
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
 * Placeholder for edit function
 */
window.editProduct = (id) => {
    alert(`Edit functionality for product ${id} - To be implemented`);
};

/**
 * Update Dashboard KPI cards.
 */
function updateStats(products) {
    const total = document.getElementById('total-count');
    const low = document.getElementById('low-stock-count');
    if (total) total.textContent = products.length;
    if (low) low.textContent = products.filter(p => p.stock < 10).length;
}

/**
 * Setup search functionality
 */
function setupSearch() {
    const searchInput = document.getElementById('inventory-search');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();
        const rows = document.querySelectorAll('#inventory-body tr');

        rows.forEach(row => {
            const productName = row.cells[0]?.textContent.toLowerCase() || '';
            const ingredient = row.cells[1]?.textContent.toLowerCase() || '';
            
            const matches = productName.includes(searchTerm) || ingredient.includes(searchTerm);
            row.style.display = matches ? '' : 'none';
        });
    });
}

/**
 * Loads shared navbar.
 */
function loadNavbar() {
    fetch('navbar.html')
        .then(res => res.text())
        .then(html => document.getElementById('navbar-placeholder').innerHTML = html)
        .catch(err => console.error("Navbar Error:", err));
}