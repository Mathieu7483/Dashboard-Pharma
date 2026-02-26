<<<<<<< HEAD
Excellent. Préparer un **README.md** pour une application traitant de données sensibles dans le secteur pharmaceutique exige **rigueur** et **clarté**, surtout en respectant le **RGPD** et les lois informatiques de 1978.

Voici une proposition de structure de **README.md**, rédigée avec le ton professoral et direct que vous avez sollicité.

## 🚀 **README : Pharmacie-Dashboard - Gestion des Stocks**

> **Avertissement : Ce tableau de bord est exclusivement destiné à l'usage interne des pharmaciens pour la gestion des stocks. Il ne gère pas les interactions clients directes, mais manipule des données à caractère personnel et sensible.**

-----

### 🖼️ **Aperçu de l'Application**

[Image de la page d'accueil du Dashboard Pharmaceutique - Affichage des stocks et alertes]

-----

### 📝 **Description du Projet**

Le projet **Pharmacie-Dashboard** est une application web **responsive** visant à optimiser la gestion des stocks de médicaments et de produits pharmaceutiques. L'objectif est de fournir aux pharmaciens un outil efficace pour :

1.  **Suivi en temps réel** des niveaux de stocks.
2.  **Alertes automatiques** de bas de stock ou de produits périmés.
3.  **Visualisation synthétique** des données via un tableau de bord ergonomique.

L'application est développée avec une attention particulière à la **sécurité des données** et à la **conformité légale**.

-----

### 🛡️ **Conformité Légale et Sécurité des Données**

Le traitement des informations gérées dans cette application est soumis à une obligation de **confidentialité maximale**.

#### 🇪🇺 **Règlement Général sur la Protection des Données (RGPD)**

  * **Minimisation des Données :** Seules les informations strictement nécessaires à la traçabilité des commandes et à la communication (Nom, Prénom, Adresse, Téléphone, Email) sont collectées pour le suivi client *indirect* lié aux stocks (e.g., alerte de disponibilité).
  * **Finalité Précise :** Les données ne sont utilisées que dans le cadre de la gestion pharmaceutique et du suivi des commandes.
  * **Sécurité par Design :** Toutes les connexions se font via **HTTPS** (chiffrement TLS/SSL). Les mots de passe et données sensibles doivent être **hachés** (hashing unidirectionnel, e.g., Argon2 ou Bcrypt). L'accès à la base de données est strictement contrôlé.

#### 🇫🇷 **Loi Informatique et Libertés de 1978 (CNIL)**

  * **Droit d'Accès, de Rectification et d'Opposition :** Des procédures internes doivent être mises en place pour permettre aux individus d'exercer ces droits sur les données stockées (bien que les données soient limitées).
  * **Déclaration/Registre :** L'utilisation de données personnelles (Nom, Prénom, etc.) pour la gestion des stocks et commandes doit être **formellement inscrite** dans le **Registre des activités de traitement** de la pharmacie, conformément aux exigences de la CNIL et du RGPD.
  * **Durée de Conservation :** Les données à caractère personnel doivent avoir une **durée de conservation définie et limitée**.

> **🛑 Point critique :** Étant donné la sensibilité des données, une **Analyse d'Impact relative à la Protection des Données (AIPD)** est **impérative** avant la mise en production.

-----

### 🧱 **Architecture Technique**

| Composant | Technologie | Rôle |
| :--- | :--- | :--- |
| **Backend (API)** | **Python (Flask)** | Logique métier, gestion des requêtes, communication avec la DB. |
| **ORM / DB Access** | **SQLAlchemy** | Mappage Objet-Relationnel pour interagir avec la base de données SQL. |
| **Frontend** | **HTML5, CSS3, JavaScript** | Interface Utilisateur (UI) responsive, gestion des interactions dynamiques. |
| **Database** | **SQL (e.g., PostgreSQL, SQLite pour le dev)** | Stockage structuré et sécurisé des données de stock et d'utilisateurs. |

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


-----

### 📐 **Logique Métier**

La logique métier est centrée sur le cycle de vie du stock et la gestion des utilisateurs (pharmaciens).

#### 🔗 **Diagrammes UML (Classes/Séquence)**

**1. Diagramme de Classes (Simplifié)**

| **Stock** | **Produit** | **Pharmacien (User)** | **Client (Suivi)** |
| :--- | :--- | :--- | :--- |
| - *id\_stock : INT* | - *id\_produit : INT* | - *id\_pharmacien : INT* | - *id\_client : INT* |
| - *date\_entrée : DATE* | - *nom\_commercial : VARCHAR* | - *email : VARCHAR* (**UNIQUE**) | - *nom : VARCHAR* |
| - *date\_péremption : DATE* | - *DCI : VARCHAR* | - *mot\_de\_passe : HASH* | - *prénom : VARCHAR* |
| - *quantite : INT* | - *dosage : VARCHAR* | - *rôle : VARCHAR (Admin/User)* | - *adresse : VARCHAR* |
| - *fournisseur : VARCHAR* | - *prix\_vente : DECIMAL* | | - *téléphone : VARCHAR* |
| - *id\_produit (FK)* | | | - *email : VARCHAR* |
| + *alerte\_péremption()* | | + *authentification()* | |
| + *alerte\_bas\_stock()* | | + *gestion\_comptes()* | |

**2. Diagramme de Séquence (Exemple : Ajout de Stock)**

1.  **Pharmacien** $\rightarrow$ **Frontend** : Requête *POST /stock/ajouter* (avec données produit/quantité).
2.  **Frontend** $\rightarrow$ **API (Flask)** : Transmet la requête.
3.  **API (Flask)** $\rightarrow$ **DB (SQLAlchemy)** : Exécute `SELECT` pour vérifier l'existence du Produit.
4.  **DB** $\rightarrow$ **API** : Retourne le statut.
5.  **API** $\rightarrow$ **DB** : Exécute `INSERT INTO Stock` (nouvelle entrée) ou `UPDATE Stock` (mise à jour quantité).
6.  **DB** $\rightarrow$ **API** : Retourne statut *201 Created*.
7.  **API** $\rightarrow$ **Frontend** : Retourne JSON de confirmation.
8.  **Frontend** $\rightarrow$ **Pharmacien** : Affichage du succès / mise à jour du dashboard.

-----

### 💾 **Méthodologie SQL (Database)**

#### 🎯 **Principes de Conception**

La base de données doit être en **forme normale 3NF** (Troisième Forme Normale) pour garantir l'intégrité et minimiser la redondance des données.

  * **Séparation des Entités :** Les informations sont réparties en tables distinctes (Produit, Stock, Pharmacien, Client) pour éviter la duplication.
  * **Clés Primaires (PK) et Étrangères (FK) :** Utilisation de clés auto-incrémentées pour la PK et de FK pour lier les tables (`Stock.id_produit` vers `Produit.id_produit`).
  * **Indexation :** Des index doivent être créés sur les colonnes fréquemment utilisées pour les recherches (e.g., `Produit.DCI`, `Pharmacien.email`, `Stock.date_péremption`).

#### 📜 **Exemple de Requêtes et Modélisation (DDL)**

**1. Création de la table `Produit` (pour le catalogue général)**

```sql
CREATE TABLE Produit (
    id_produit SERIAL PRIMARY KEY,
    nom_commercial VARCHAR(100) NOT NULL,
    DCI VARCHAR(150),
    dosage VARCHAR(50),
    forme VARCHAR(50),
    prix_achat DECIMAL(10, 2),
    prix_vente DECIMAL(10, 2),
    stock_securite INT NOT NULL DEFAULT 10
);
```

**2. Création de la table `Client` (Données RGPD sensibles)**

```sql
CREATE TABLE Client (
    id_client SERIAL PRIMARY KEY,
    nom VARCHAR(50) NOT NULL,
    prenom VARCHAR(50) NOTPAS NULL,
    adresse VARCHAR(255),
    telephone VARCHAR(20),
    email VARCHAR(100),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Nécessité de crypter ces colonnes au niveau de l'application (ou de la DB si possible)
);
```

> **Note :** Dans un environnement réel, les champs `adresse`, `telephone`, et `email` devraient idéalement être **chiffrés** (encryption bidirectionnelle) dans la base de données.

-----

### ⚙️ **Installation et Mise en Route**

Cette application est déployée via un serveur web (e.g., Nginx/Apache) en tant que **service sécurisé HTTPS**.

#### 1\. **Prérequis**

  * Python 3.x
  * Un système de gestion de base de données SQL (PostgreSQL recommandé pour la production)
  * **Certificat SSL/TLS** valide pour la connexion HTTPS.

#### 2\. **Installation des Dépendances Backend (Python)**

Créez et activez un environnement virtuel (recommandé) :

```bash
python3 -m venv venv
source venv/bin/activate  # Sous Linux/macOS
# ou .\venv\Scripts\activate # Sous Windows PowerShell
```

Installez les bibliothèques **Flask** et **SQLAlchemy** (ainsi que le driver de DB, e.g., `psycopg2` pour PostgreSQL) :

```bash
pip install Flask Flask-SQLAlchemy python-dotenv
# Pour la sécurité :
pip install Flask-Bcrypt
# Pour les API REST (si nécessaire) :
pip install Flask-RESTful
```

#### 3\. **Configuration de la Base de Données**

1.  Créez une base de données sur votre serveur (e.g., `pharmadb`).

2.  Configurez l'URI de connexion dans un fichier `.env` ou équivalent :

    ```
    DATABASE_URL="postgresql://user:password@host/pharmadb"
    SECRET_KEY="VOTRE_CLE_SECRETE_TRES_LONGUE_ET_COMPLEXE"
    ```

3.  Lancez les migrations (si vous utilisez Flask-Migrate ou un outil similaire) ou exécutez le DDL SQL pour créer les tables.

#### 4\. **Lancement de l'Application (Développement)**

Pour lancer l'application en mode développement (NON SÉCURISÉ EN PROD) :

```bash
export FLASK_APP=app.py
flask run
```

#### 5\. **Déploiement en Production (HTTPS OBLIGATOIRE)**

Le déploiement en production **doit** utiliser un serveur d'application Web (WSGI) comme **Gunicorn** ou **uWSGI**, couplé à un proxy inverse (Nginx/Apache) pour gérer la terminaison **HTTPS**.

1.  Installez Gunicorn : `pip install gunicorn`

2.  Lancement sécurisé (exemple) :

    ```bash
    gunicorn -w 4 -b 0.0.0.0:8000 app:app
    ```

    *Le proxy inverse (Nginx) redirigera le trafic sécurisé (port 443) vers le port Gunicorn (e.g., 8000).*

-----

### 🤝 **Contribution**

  * **Fork** le dépôt.
  * Créez une **branche** pour votre fonctionnalité (`git checkout -b feature/NomDeLaFonctionnalite`).
  * **Committez** vos changements (`git commit -m 'Ajout d’une nouvelle fonctionnalité...'`).
  * **Pushez** sur la branche (`git push origin feature/NomDeLaFonctionnalite`).
  * Ouvrez une **Pull Request**.

-----

### 📄 **Licence**

Ce projet est sous licence [Spécifiez ici la licence, e.g., MIT].
=======
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

>>>>>>> Mathieu
