FROM python:3.10

WORKDIR /app

# Installation des dépendances système nécessaires (compilation, curl)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copie du fichier des dépendances
COPY requirements.txt .

# Installation des dépendances Python (incluant les whl spaCy et les modules)
RUN pip install --no-cache-dir -r requirements.txt

# Copie du reste du projet
COPY . .

# Définition du répertoire de travail sur le serveur pour exécuter l'application
WORKDIR /app/Server

# Exposition du port de l'API Flask (par défaut 5000)
EXPOSE 5000

# Commande pour lancer l'application (ex: via run.py)
CMD ["python", "run.py"]