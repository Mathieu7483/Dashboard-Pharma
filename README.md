# 🚀 **README: Pharmacy-Dashboard - Inventory Management**

<p align="center"\>
<img src="https://github.com/Mathieu7483/Dashboard-Pharma/blob/Mathieu/Client/assets/img/accueil%20Dasboard%20Pharma.png"\>
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
. Data Minimisation: Only strictly necessary data is collected.
. Security by Design: All connections via HTTPS. Passwords must be hashed (Bcrypt).
. Retention Period: Defined and limited retention for personal data.

### 🛑 Critical Point: A Data Protection Impact Assessment (DPIA) is mandatory before any production deployment.
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

## 💾 **SQL Methodology (SQLite & SQLAlchemy)**

The project adheres to **3NF** (Third Normal Form). Initialization is automated:

```python
with app.app_context():
    db.create_all()         # Create tables
    seed_all_initial_data() # Fill the database

```

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

* **API URL:** `http://127.0.0.1:5000`
* **Auto-seed:** Test data (sales, products, interactions) is injected from `utils/data_seed.json`.

---

## 🛡️ **Security Implementation**

* **Passwords:** Hashing via `Bcrypt`.
* **Input Sanitization:** Protection against XSS/SQL injections via SQLAlchemy and query validators in the Chatbot.
* **Context Awareness:** The chatbot uses the user ID to personalize responses without exposing sensitive data.

---

## ✒️ Author

**Mathieu GODALIER** - [GitHub](https://github.com/Mathieu7483)
*Student at Holberton School*
