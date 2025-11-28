

## 🚀 **README: Pharmacy-Dashboard - Inventory Management**

> **Warning: This dashboard is strictly for internal use by pharmacists for inventory management purposes. It does not handle direct customer interactions but processes personal and sensitive data.**

-----

### 🖼️ **Application Overview**

-----

### 📝 **Project Description**

The **Pharmacy-Dashboard** project is a **responsive** web application designed to optimize the management of pharmaceutical stocks and products. The objective is to provide pharmacists with an efficient tool for:

1.  **Real-time tracking** of inventory levels.
2.  **Automatic alerts** for low stock or expired products.
3.  **Synthesized visualization** of data via an ergonomic dashboard.

The application is developed with careful attention to **data security** and **legal compliance**.

-----

### 🛡️ **Legal Compliance and Data Security**

The processing of information managed within this application is subject to an obligation of **maximum confidentiality**.

#### 🇪🇺 **General Data Protection Regulation (GDPR)**

  * **Data Minimisation:** Only information strictly necessary for order traceability and communication (Name, First Name, Address, Phone, Email) is collected for *indirect* customer tracking related to inventory (e.g., availability alerts).
  * **Specific Purpose:** Data is used solely within the scope of pharmaceutical management and order tracking.
  * **Security by Design:** All connections must be made via **HTTPS** (TLS/SSL encryption). Passwords and sensitive data must be **hashed** (one-way hashing, e.g., Argon2 or Bcrypt). Access to the database must be strictly controlled.

#### 🇫🇷 **Loi Informatique et Libertés of 1978 (CNIL)**

  * **Right of Access, Rectification, and Objection:** Internal procedures must be implemented to allow individuals to exercise these rights over stored data (although data is limited).
  * **Declaration/Register:** The use of personal data (Name, First Name, etc.) for inventory and order management must be **formally recorded** in the pharmacy's **Record of Processing Activities**, in accordance with CNIL and GDPR requirements.
  * **Retention Period:** Personal data must have a **defined and limited retention period**.

> **🛑 Critical Point:** Given the sensitivity of the data, a **Data Protection Impact Assessment (DPIA)** is **mandatory** before deployment to production.

-----

### 🧱 **Technical Architecture**

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Backend (API)** | **Python (Flask)** | Business logic, request handling, communication with the DB. |
| **ORM / DB Access** | **SQLAlchemy** | Object-Relational Mapping to interact with the SQL database. |
| **Frontend** | **HTML5, CSS3, JavaScript** | Responsive User Interface (UI), managing dynamic interactions. |
| **Database** | **SQL (e.g., PostgreSQL, SQLite for dev)** | Structured and secure storage for inventory and user data. |

```
Dashboard-Pharma/
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
    
├── Client/
│   ├── index.html
│   ├── assets/
│   │   └── img/
│   ├── css/
│   │   └── style.css
│   └── javascript/
│       └── dashboard.js
    
└── Server/
    ├── run.py
    ├── app.py
    ├── config.py
    ├── setup_db.py
    ├── /api/
    │   ├── __init__.py
    │   ├── routes.py
    │   ├── auth.py
    │   ├── products.py
    │   ├── sales.py
    │   └── users.py
    ├── /core/
    │   ├── chatbot/
    │   │   ├── ChatBot_engine.py
    │   │   └── NLUProcessor.py
    │   └── database/
    │       └── data_manager.py
    ├── /models/
    │   ├── __init__.py
    │   ├── basemodel.py
    │   ├── product.py
    │   ├── sale.py
    │   └── user.py
    ├── /services/
    │   ├── __init__.py
    │   └── facade.py
    └── /tests/
```

-----

### 📐 **Business Logic**

The business logic is centered on the inventory lifecycle and the management of users (pharmacists).

#### 🔗 **UML Diagrams (Classes/Sequence)**

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

-----

### 💾 **SQL Methodology (Database)**

#### 🎯 **Design Principles**

The database must be in **3NF** (Third Normal Form) to ensure data integrity and minimize redundancy.

  * **Entity Separation:** Information is distributed into distinct tables (Product, Stock, Pharmacist, Customer) to prevent duplication.
  * **Primary (PK) and Foreign (FK) Keys:** Use auto-incrementing keys for the PK and FKs to link tables (`Stock.product_id` to `Product.product_id`).
  * **Indexing:** Indexes must be created on columns frequently used for searching (e.g., `Product.INN`, `Pharmacist.email`, `Stock.expiry_date`).

#### 📜 **Query and Modeling Example (DDL)**

**1. Creating the `Product` table (for the general catalog)**

```sql
CREATE TABLE Product (
    id_product SERIAL PRIMARY KEY,
    trade_name VARCHAR(100) NOT NULL,
    INN VARCHAR(150),
    dosage VARCHAR(50),
    form VARCHAR(50),
    purchase_price DECIMAL(10, 2),
    selling_price DECIMAL(10, 2),
    safety_stock INT NOT NULL DEFAULT 10
);
```

**2. Creating the `Customer` table (GDPR sensitive data)**

```sql
CREATE TABLE Customer (
    id_customer SERIAL PRIMARY KEY,
    last_name VARCHAR(50) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    address VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(100),
    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Necessity to encrypt these columns at the application level (or DB if possible)
);
```

> **Note:** In a real-world environment, the fields `address`, `phone`, and `email` should ideally be **encrypted** (bi-directional encryption) in the database.

-----

### ⚙️ **Installation and Setup**

This application is deployed via a web server (e.g., Nginx/Apache) as a **secure HTTPS service**.

#### 1\. **Prerequisites**

  * Python 3.x
  * A SQL database management system (PostgreSQL recommended for production)
  * Valid **SSL/TLS Certificate** for HTTPS connection.

#### 2\. **Backend Dependencies Installation (Python)**

Create and activate a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/macOS
# or .\venv\Scripts\activate # On Windows PowerShell
```

Install the **Flask** and **SQLAlchemy** libraries (along with the DB driver, e.g., `psycopg2` for PostgreSQL):

```bash
pip install Flask Flask-SQLAlchemy python-dotenv
# For security:
pip install Flask-Bcrypt
# For REST APIs (if needed):
pip install Flask-RESTful
```

#### 3\. **Database Configuration**

1.  Create a database on your server (e.g., `pharmadb`).

2.  Configure the connection URI in an `.env` file or equivalent:

    ```
    DATABASE_URL="postgresql://user:password@host/pharmadb"
    SECRET_KEY="YOUR_VERY_LONG_AND_COMPLEX_SECRET_KEY"
    ```

3.  Run migrations (if you are using Flask-Migrate or a similar tool) or execute the SQL DDL to create the tables.

#### 4\. **Launching the Application (Development)**

To launch the application in development mode (NOT SECURE FOR PROD):

```bash
export FLASK_APP=app.py
flask run
```

#### 5\. **Production Deployment (HTTPS MANDATORY)**

Production deployment **must** use a Web Server Gateway Interface (WSGI) application server like **Gunicorn** or **uWSGI**, coupled with a reverse proxy (Nginx/Apache) to handle **HTTPS** termination.

1.  Install Gunicorn: `pip install gunicorn`

2.  Secure launch (example):

    ```bash
    gunicorn -w 4 -b 0.0.0.0:8000 app:app
    ```

    *The reverse proxy (Nginx) will redirect secure traffic (port 443) to the Gunicorn port (e.g., 8000).*

-----

### 🤝 **Contribution**

  * **Fork** the repository.
  * Create a **branch** for your feature (`git checkout -b feature/NewFeatureName`).
  * **Commit** your changes (`git commit -m 'Adding a new feature...'`).
  * **Push** to the branch (`git push origin feature/NewFeatureName`).
  * Open a **Pull Request**.

-----

### 📄 **License**

This project is licensed under [Specify the license here, e.g., MIT].