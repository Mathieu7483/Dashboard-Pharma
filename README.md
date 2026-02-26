<p align="center"\>
<img src="https://github.com/Mathieu7483/Dashboard-Pharma/blob/Mathieu/Client/assets/img/accueil%20Dasboard%20Pharma.png"\>
</p>
<p align="center">
<img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python" alt="Python">
<img src="https://img.shields.io/badge/Flask-2.0+-green?style=for-the-badge&logo=flask" alt="Flask">
<img src="https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite" alt="SQLite">
<img src="https://img.shields.io/badge/Pattern-Facade-orange?style=for-the-badge" alt="Facade Pattern">
</p>

> **Warning: This dashboard is strictly for internal use by pharmacists for inventory management purposes. It does not handle direct customer interactions but processes personal and sensitive data.**

---
## 📝 Project Description

The Pharmacy-Dashboard project is a responsive web application designed to optimize the management of pharmaceutical stocks and products.

1. Real-time tracking of inventory levels.
2. Automatic alerts for low stock or expired products.
3. Synthesized visualization of data via an ergonomic dashboard.

---
## 🛡️ Legal Compliance and Data Security

🇪🇺 GDPR & French Law
* **Data Minimisation**: Only strictly necessary data is collected.
* **Security by Design**: All connections via HTTPS. Passwords must be hashed (Bcrypt).
* **Retention Period**: Defined and limited retention for personal data.

> **🛑 Critical Point: A Data Protection Impact Assessment (DPIA) is mandatory before any production deployment.**
---

## 🧱 **Technical Architecture**

| Component | Technology | Role |
| --- | --- | --- |
| **Backend (API)** | **Python (Flask)** | RESTful API with Facade Pattern. |
| **Core Logic** | **NLU & NLP** | Custom Natural Language Unit for Chatbot interactions. |
| **ORM / DB Access** | **SQLAlchemy** | Object-Oriented Mapping (OOP). |
| **Frontend** | **HTML5, CSS3, JS** | Responsive Dashboard with Vanilla JS. |
| **Database** | **SQLite** | Portability and ACID compliance. |

### 📂 Directory structure

```text
Directory structure:
└── mathieu7483-dashboard-pharma/
    ├── README.md
    ├── LICENSE
    ├── requirements.txt
    ├── Client/
    │   ├── auth.html
    │   ├── clients.html
    │   ├── doctors.html
    │   ├── index.html
    │   ├── inventory.html
    │   ├── navbar.html
    │   ├── settings.html
    │   ├── css/
    │   │   ├── auth.css
    │   │   ├── calendar.css
    │   │   ├── settings.css
    │   │   └── style.css
    │   └── javascript/
    │       ├── auth.js
    │       ├── clients.js
    │       ├── dashboard.js
    │       ├── doctors.js
    │       ├── inventory.js
    │       └── settings.js
    └── Server/
        ├── app.py
        ├── config.py
        ├── run.py
        ├── api/
        │   ├── __init__.py
        │   ├── analytics.py
        │   ├── auth.py
        │   ├── calendar_events.py
        │   ├── chatbot.py
        │   ├── clients.py
        │   ├── doctors.py
        │   ├── inventory.py
        │   ├── products.py
        │   ├── sales.py
        │   ├── tickets.py
        │   └── users.py
        ├── core/
        │   └── chatbot/
        │       ├── ChatBot_engine.py
        │       └── NLUProcessor.py
        ├── database/
        │   ├── __init__.py
        │   └── data_manager.py
        ├── models/
        │   ├── __init__.py
        │   ├── basemodel.py
        │   ├── calendar.py
        │   ├── client.py
        │   ├── doctor.py
        │   ├── interaction.py
        │   ├── product.py
        │   ├── product_alias.py
        │   ├── sale.py
        │   ├── ticket.py
        │   └── user.py
        ├── services/
        │   ├── __init__.py
        │   └── facade.py
        ├── tests/
        │   ├── test_api_route.py
        │   └── test_chatbot.sh
        └── utils/
            ├── __init__.py
            ├── data_seed.json
            ├── decorator.py
            ├── initial_inventory.csv
            ├── seed_aliases.py
            ├── seed_sales.py
            └── seeder.py



```
---
## 🏗️ Advanced Architecture & Design Patterns
The Facade Pattern Implementation
To ensure a strict separation of concerns (SoC), this project implements the Facade Design Pattern via services/facade.py.

* **Decoupling**: The API controllers (Blueprints) never interact directly with the SQLAlchemy models.

* **Centralized Logic**: Complex operations like stock alerts, sales analytics, and drug interaction checks are encapsulated within the Facade.

* **Maintainability**: Changing the database schema or business rules only requires updates in the Facade, leaving the API layer untouched.

RBAC (Role-Based Access Control)
Security is enforced through a granular RBAC system:

* **Admin (Pharmacist)**: Full access to user management, price auditing, and stock deletion.

* **User (Assistant)**: Access to inventory updates, sales recording, and Chatbot assistance.

* **Security Layer**: Implemented via custom Python decorators (@admin_required) in utils/decorator.py.
---

## 📐 **Business Logic & Design Patterns**

### **Facade Pattern**

The business logic is centered on the inventory lifecycle and the management of users (pharmacists).
The project uses a **Facade Service** (`facade.py`). The API never communicates directly with the models. It goes through the facade, which centralizes complex operations (e.g., calculating sales statistics or checking drug interactions).

### **Simplified Class Mapping**

* **User/Pharmacist**: Access management (RBAC).
* **Product**: Stock, price, and alert thresholds.
* **Interaction**: Contraindication knowledge base (NLU-ready).
* **Sale/Ticket**: Transaction history and customer service requests.

---
## 🤖 NLU & AI Chatbot Engine
The PharmaChat engine (core/chatbot/) is a custom-built Natural Language Understanding (NLU) unit designed for rapid inventory queries.

* **Intent Detection**: Identifies if the user wants to check stock, find a drug interaction, or view a sales summary.

* **Entity Extraction**: Automatically recognizes drug names (Trade names vs. INN/DCI) using product_alias.py.

* **Contextual Awareness**: Uses the user_id to provide personalized greetings and maintain security logs of all AI-driven queries.

---

## 💾 **SQL Methodology (SQLite & SQLAlchemy)**

The project adheres to **3NF** (Third Normal Form). Initialization is automated:

```python
with app.app_context():
    db.create_all()         # Create tables
    seed_all_initial_data() # Fill the database

```
---

## 🧪 Testing & Quality Assurance
The refactoring process (41 commits) was validated through a dual testing strategy:

Backend Unit Tests: test_api_route.py ensures all REST endpoints return correct HTTP status codes (200, 201, 403, 404).

NLU Integration Tests: test_chatbot.sh simulates real-world pharmacist queries to verify the accuracy of the NLU Processor.

---

## ⚙️ **Installation and Setup**

### 1. **Environment Setup**

```bash
python3 -m venv venv
source venv/bin/activate 
pip install -r requirements.txt

```

### 2. **Launch & Initialization**

```bash
cd Server
python3 run.py

```
* **Automated Initialization**
The system features an Auto-Seed mechanism. On the first run, run.py detects the absence of data and automatically:

* Creates all tables via SQLAlchemy.

* Injects core drug data from `utils/initial_inventory.csv `

* Populates users from `utils/data_seed.json`.
Populates products sales from `utils/seed_sales.py`
Populate the product_aliases table with common commercial names from `utils/seed_alias.py`

* **API URL:** `http://127.0.0.1:5000`

---

## 🛡️ **Security Implementation**

* **Passwords:** Hashing via `Bcrypt`.
* **Input Sanitization:** Protection against XSS/SQL injections via SQLAlchemy and query validators in the Chatbot.
* **Context Awareness:** The chatbot uses the user ID to personalize responses without exposing sensitive data.

---

## ✒️ Author

**Mathieu GODALIER** - [GitHub](https://github.com/Mathieu7483)
*Student at Holberton School*
