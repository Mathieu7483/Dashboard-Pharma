#!/bin/bash

# Configuration
API_BASE_URL="http://127.0.0.1:5000"
LOGIN_URL="$API_BASE_URL/auth/login"
API_URL="$API_BASE_URL/chatbot/"

# Couleurs pour la lisibilité
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Initialisation des tests Chatbot ===${NC}"

# 1. Authentification
RESPONSE=$(curl -s -X POST "$LOGIN_URL" \
  -H "Content-Type: application/json" \
  -d '{"username": "Mathieu", "password": "Admin@1234"}')

TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}Erreur d'authentification !${NC}"
    exit 1
fi

echo -e "${GREEN}Connecté avec succès.${NC}\n"

# 2. Fonction de test améliorée
# Usage: run_test "Nom du test" "Message à envoyer" "Intention attendue"
run_test() {
    local desc=$1
    local msg=$2
    local expected_intent=$3

    echo -e "${BLUE}[TEST] $desc${NC}"
    echo "Phrase: \"$msg\""

    # Envoi de la requête
    RAW_RES=$(curl -s -X POST "$API_URL" \
         -H "Authorization: Bearer $TOKEN" \
         -H "Content-Type: application/json" \
         -d "{\"message\": \"$msg\"}")

    # Extraction des données avec JQ
    # On suppose que ton API renvoie maintenant l'intention pour le debug
    REPLY=$(echo "$RAW_RES" | jq -r '.reply // "Erreur de réponse"')
    
    echo -e "Bot: $REPLY"
    echo "-----------------------------------------------"
}

# --- SÉRIE DE TESTS FONCTIONNELS ---

# Test de politesse et aide
run_test "Salutations" "Bonjour" "greeting"
run_test "Aide" "Aide moi" "get_help"

# Test Pharmacie (Entités)
run_test "Stock Produit" "Stock de Doliprane" "check_stock"
run_test "Interaction" "Aspirine avec Ibuprofène" "check_interaction"

# Test Admin / Dashboard
run_test "Ventes" "Ventes du jour" "get_sales_summary"
run_test "Agenda" "Mon planning de demain" "calendar"

# Test de robustesse (Edge Cases)
run_test "Chaîne vide" "" "unknown"
run_test "Injection SQL" "1; DROP TABLE users;" "unknown"

echo -e "${GREEN}=== Tests terminés ===${NC}"