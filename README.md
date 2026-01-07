<p align="center"\>
<img src="https://github.com/Mathieu7483/Dashboard-Pharma/blob/Mathieu/Client/assets/img/accueil%20Dasboard%20Pharma.png"\>
</p>

# 🚀 **README: Pharmacy-Dashboard - Inventory Management**

> **Warning: This dashboard is strictly for internal use by pharmacists for inventory management purposes. It does not handle direct customer interactions but processes personal and sensitive data.**

---

## 📝 **Project Description**

The **Pharmacy-Dashboard** project is a **responsive** web application designed to optimize the management of pharmaceutical stocks and products.

1. **Real-time tracking** of inventory levels.
2. **Automatic alerts** for low stock or expired products.
3. **Synthesized visualization** of data via an ergonomic dashboard.

---

## 🛡️ **Legal Compliance and Data Security**

### 🇪🇺 **GDPR & French Law**

* **Data Minimisation:** Only strictly necessary data is collected.
* **Security by Design:** All connections via **HTTPS**. Passwords must be **hashed** (Bcrypt).
* **Retention Period:** Defined and limited retention for personal data.

> **🛑 Critical Point:** A **Data Protection Impact Assessment (DPIA)** is mandatory before any production deployment.

---

## 🧱 **Technical Architecture**

| Component | Technology | Role |
| --- | --- | --- |
| **Backend (API)** | **Python (Flask)** | Business logic and request handling. |
| **ORM / DB Access** | **SQLAlchemy** | Object-Relational Mapping. |
| **Frontend** | **HTML5, CSS3, JS** | Responsive User Interface. |
| **Database** | **SQLite** | **Single-file embedded database** for portability and efficiency. |


```
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
    │   ├── css/
    │   │   ├── auth.css
    │   │   └── style.css
    │   └── javascript/
    │       ├── auth.js
    │       ├── clients.js
    │       ├── dashboard.js
    │       ├── doctors.js
    │       └── inventory.js
    └── Server/
        ├── app.py
        ├── config.py
        ├── run.py
        ├── api/
        │   ├── __init__.py
        │   ├── analytics.py
        │   ├── auth.py
        │   ├── chatbot.py
        │   ├── clients.py
        │   ├── doctors.py
        │   ├── inventory.py
        │   ├── products.py
        │   ├── sales.py
        │   └── users.py
        ├── core/
        │   └── chatbot/
        │       ├── ChatBot_engine.py
        │       └── NLUProcessor.py
        ├── database/
        │   ├── __init__.py
        │   ├── data_manager.py
        │   └── initial_inventory.csv
        ├── models/
        │   ├── __init__.py
        │   ├── basemodel.py
        │   ├── client.py
        │   ├── doctor.py
        │   ├── product.py
        │   ├── sale.py
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
            ├── seed_sales.py
            └── seeder.py


```
----
## 📐 **Business Logic**

The business logic is centered on the inventory lifecycle and the management of users (pharmacists).

### 🔗 **UML Diagrams (Classes/Sequence)**

**1. Class Diagram (Simplified)**

| **Stock** | **Product** | **Pharmacist (User)** | **Customer (Tracking)** |
| :--- | :--- | :--- | :--- |
| - *stock\_id : INT* | - *product\_id : INT* | - *pharmacist\_id : INT* | - *customer\_id : INT* |
| - *entry\_date : DATE* | - *trade\_name : VARCHAR* | - *email : VARCHAR* (**UNIQUE**) | - *last\_name : VARCHAR* |
| - *expiry\_date : DATE* | - *INN : VARCHAR* | - *password : HASH* | - *first\_name : VARCHAR* |
| - *quantity : INT* | - *dosage : VARCHAR* | - *role : VARCHAR (Admin/User)* | - *address : VARCHAR* |
| - *supplier : VARCHAR* | - *selling\_price : DECIMAL* | | - *phone : VARCHAR* |
| - *product\_id (FK)* | | | - *email : VARCHAR* |
| + *expiry\_alert()* | | + *authentication()* | |
| + *low\_stock\_alert()* | | + *account\_management()* | |

**2. Sequence Diagram (Example: Adding Stock)**

1.  **Pharmacist** $\rightarrow$ **Frontend**: Request *POST /stock/add* (with product/quantity data).
2.  **Frontend** $\rightarrow$ **API (Flask)**: Transmits the request.
3.  **API (Flask)** $\rightarrow$ **DB (SQLAlchemy)**: Executes `SELECT` to check Product existence.
4.  **DB** $\rightarrow$ **API**: Returns the status.
5.  **API** $\rightarrow$ **DB**: Executes `INSERT INTO Stock` (new entry) or `UPDATE Stock` (quantity update).
6.  **DB** $\rightarrow$ **API**: Returns status *201 Created*.
7.  **API** $\rightarrow$ **Frontend**: Returns JSON confirmation.
8.  **Frontend** $\rightarrow$ **Pharmacist**: Display success / dashboard update.

----

## 💾 **SQL Methodology (SQLite)**

### 🎯 **Design Principles**

The database is designed in **3NF** (Third Normal Form). Unlike PostgreSQL, SQLite is serverless and stores the entire database in a single `.db` file.

#### 📜 **Query and Modeling Example (DDL - SQLite Syntax)**

**1. Creating the `Product` table**

```sql
CREATE TABLE Product (
    id_product INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_name VARCHAR(100) NOT NULL,
    INN VARCHAR(150),
    dosage VARCHAR(50),
    form VARCHAR(50),
    purchase_price DECIMAL(10, 2),
    selling_price DECIMAL(10, 2),
    safety_stock INTEGER NOT NULL DEFAULT 10
);

```

**2. Creating the `Customer` table**

```sql
CREATE TABLE Customer (
    id_customer INTEGER PRIMARY KEY AUTOINCREMENT,
    last_name VARCHAR(50) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    address VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(100),
    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

```

---

## ⚙️ **Installation and Setup**

### 1. **Prerequisites**

* Python 3.x
* SQLite3 (built-in with Python)
* Valid **SSL/TLS Certificate** for HTTPS.

### 2. **Environment Setup**

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

```

### 3. **Database Configuration**

Configure your `.env` file to point to the SQLite file:

```env
DATABASE_URL="sqlite:///database/pharma_dashboard.db"
SECRET_KEY="YOUR_VERY_LONG_AND_COMPLEX_SECRET_KEY"

```

### 4. **Launching the Application**

```bash
# Development
export FLASK_APP=run.py
flask run

# Production (Gunicorn)
gunicorn -w 4 -b 0.0.0.0:8000 app:app

```
## ✒️ Author

[Mathieu GODALIER](https://github.com/Mathieu7483) - Student at Holberton School

---

## 📄 **License**

This project is licensed under the MIT License.

