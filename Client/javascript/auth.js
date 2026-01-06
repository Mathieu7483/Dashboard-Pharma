/**
 * PHARMA AUTHENTICATION SYSTEM
 * Handles User Login, Registration, and Cookie-based Session Management.
 * Optimized for Flask-RestX Backend and JWT Security.
 */

// --- UTILITIES: Cookie Management ---

/**
 * Sets a secure cookie in the browser storage.
 * @param {string} name - Key of the cookie.
 * @param {string} value - Data (JWT) to store.
 * @param {number} days - Duration before expiration.
 */
function setCookie(name, value, days) {
    let expires = "";
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    // Using SameSite=Lax to protect against Cross-Site Request Forgery (CSRF)
    document.cookie = `${name}=${value || ""}${expires}; path=/; SameSite=Lax`;
}

/**
 * Main Application Logic
 * Initializes listeners once the DOM is fully parsed.
 */
document.addEventListener('DOMContentLoaded', () => {
    
    // --- DOM Elements ---
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const statusMessage = document.getElementById('status-message');

    /**
     * Displays feedback messages to the user.
     * @param {string} msg - The text to display.
     * @param {boolean} isError - Controls styling based on severity.
     */
    function showMessage(msg, isError = true) {
        statusMessage.textContent = msg;
        statusMessage.style.cssText = `
            display: block; 
            color: ${isError ? 'darkred' : 'darkgreen'}; 
            background-color: ${isError ? '#ffe6e6' : '#e6ffe6'};
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-weight: 600;
            text-align: center;
        `;
    }

    function clearMessage() {
        statusMessage.style.display = 'none';
        statusMessage.textContent = '';
    }

    // --- UI State Management (View Toggles) ---
    const showLogin = (e) => {
        if (e) e.preventDefault();
        clearMessage();
        if (loginForm) loginForm.style.display = 'block';
        if (registerForm) registerForm.style.display = 'none';
    };

    const showRegister = (e) => {
        if (e) e.preventDefault();
        clearMessage();
        if (loginForm) loginForm.style.display = 'none';
        if (registerForm) registerForm.style.display = 'block';
    };
    
    // --- Security UI: Password Visibility Toggle ---
    const toggleButtons = document.querySelectorAll('.password-toggle');
    toggleButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetId = button.getAttribute('data-target');
            const input = document.getElementById(targetId);
            
            if (input && input.type === 'password') {
                input.type = 'text';
                button.textContent = 'Hide'; 
            } else if (input) {
                input.type = 'password';
                button.textContent = 'Show';
            }
        });
    });

    // Binding navigation links to UI toggle functions
    document.querySelector('#login-form .toggle-link a')?.addEventListener('click', showRegister);
    document.querySelector('#register-form .toggle-link a')?.addEventListener('click', showLogin);

    // --- Authentication: Login Logic ---
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            clearMessage();

            const username = document.getElementById('login-username').value;
            const password = document.getElementById('login-password').value;

            try {
                // Fetching the access token from the Flask API
                const response = await fetch('http://127.0.0.1:5000/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (response.ok) {
                    // Storing the JWT in a cookie for secure session persistence
                    setCookie('access_token', data.access_token, 1);
                    
                    showMessage("Authentication successful! Redirecting...", false);
                    
                    // Controlled delay for better User Experience before redirection
                    setTimeout(() => {
                        window.location.href = 'index.html'; 
                    }, 1000);

                } else {
                    showMessage(data.msg || "Invalid credentials. Access denied.");
                }
            } catch (error) {
                console.error('Critical Network Failure:', error);
                showMessage("Database/Server connection failed.");
            }
        });
    }

    // --- Authentication: Registration Logic ---
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            clearMessage();

            const username = document.getElementById('register-username').value;
            const email = document.getElementById('register-email').value;
            const password = document.getElementById('register-password').value;
            const confirmPassword = document.getElementById('register-password-confirm').value;

            // Strict client-side validation for UX speed
            if (password !== confirmPassword) {
                showMessage("Error: Passwords do not match.");
                return;
            }

            try {
                const response = await fetch('http://127.0.0.1:5000/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, email, password })
                });

                if (response.status === 201) {
                    showMessage("Account created. You may now login.", false);
                    showLogin(null); 
                } else {
                    const error = await response.json();
                    showMessage(error.msg || "Registration failed. Check your data.");
                }
            } catch (error) {
                console.error('Registration Exception:', error);
                showMessage("External server error during registration.");
            }
        });
    }
});