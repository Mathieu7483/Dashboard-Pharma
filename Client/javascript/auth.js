/**
 * PHARMA DASHBOARD - AUTHENTICATION SYSTEM
 * Handles JWT-based session management and UI toggling.
 */

// --- CONFIGURATION ---
const API_BASE_URL = 'http://127.0.0.1:5000/auth';

/**
 * Helper to manage JWT storage via cookies (SameSite=Lax for CSRF protection)
 */
const CookieManager = {
    set: (name, value, days) => {
        let expires = "";
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = "; expires=" + date.toUTCString();
        }
        document.cookie = `${name}=${value || ""}${expires}; path=/; SameSite=Lax`;
    },
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
    
    // --- DOM Elements ---
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const statusMessage = document.getElementById('status-message');

    // --- UI Feedback ---
    function showMessage(text, isError = true) {
        statusMessage.textContent = text;
        statusMessage.className = `message ${isError ? 'error' : 'success'}`;
        statusMessage.style.display = 'block';
        statusMessage.style.backgroundColor = isError ? '#ffe6e6' : '#e6ffe6';
        statusMessage.style.color = isError ? 'darkred' : 'darkgreen';
    }

    function clearMessage() {
        statusMessage.style.display = 'none';
        statusMessage.textContent = '';
    }

    // --- View Switching Logic ---
    const toggleView = (showLogin) => {
        clearMessage();
        loginForm.style.display = showLogin ? 'block' : 'none';
        registerForm.style.display = showLogin ? 'none' : 'block';
    };

    document.querySelector('#login-form .toggle-link a')?.addEventListener('click', (e) => {
        e.preventDefault();
        toggleView(false);
    });

    document.querySelector('#register-form .toggle-link a')?.addEventListener('click', (e) => {
        e.preventDefault();
        toggleView(true);
    });

    // --- Password Visibility Toggle ---
    document.querySelectorAll('.password-toggle').forEach(button => {
        button.addEventListener('click', () => {
            const target = document.getElementById(button.getAttribute('data-target'));
            if (target) {
                const isPassword = target.type === 'password';
                target.type = isPassword ? 'text' : 'password';
                button.textContent = isPassword ? 'Hide' : 'Show';
            }
        });
    });

    // --- LOGIN SUBMIT ---
    loginForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        clearMessage();

        const payload = {
            username: document.getElementById('login-username').value,
            password: document.getElementById('login-password').value
        };

        try {
            const response = await fetch(`${API_BASE_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok) {
                CookieManager.set('access_token', data.access_token, 1);
                showMessage("Login successful! Redirecting...", false);
                setTimeout(() => window.location.href = 'index.html', 1200);
            } else {
                showMessage(data.msg || "Authentication failed. Please check your credentials.");
            }
        } catch (err) {
            showMessage("Server unreachable. Please check if the Flask backend is running.");
        }
    });

    // --- REGISTER SUBMIT ---
    registerForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        clearMessage();

        const password = document.getElementById('register-password').value;
        const confirm = document.getElementById('register-password-confirm').value;

        if (password !== confirm) {
            showMessage("Passwords do not match.");
            return;
        }

        const payload = {
            username: document.getElementById('register-username').value,
            email: document.getElementById('register-email').value,
            password: password
        };

        try {
            const response = await fetch(`${API_BASE_URL}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.status === 201) {
                showMessage("Account created successfully! You can now login.", false);
                setTimeout(() => toggleView(true), 2000);
            } else {
                const data = await response.json();
                showMessage(data.msg || "Registration failed. Username or Email might already exist.");
            }
        } catch (err) {
            showMessage("Connection error. Could not reach the registration service.");
        }
    });
});