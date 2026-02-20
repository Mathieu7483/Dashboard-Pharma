"""
Server/utils/seed_sales.py
Seeds the database with a 30-day history of sales.
"""

import os
import sys
import random
from datetime import datetime, timedelta, timezone

# Ajout du chemin pour l'import des services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.data_manager import db
from services.facade import FacadeService

def seed_product_sales():
    """
    Simule une activité de pharmacie sur les 30 derniers jours.
    """
    facade = FacadeService()

    # 1. Récupération des données nécessaires
    products = facade.get_all_products()
    users = facade.get_all_users()
    clients = facade.get_all_clients()
    doctors = facade.get_all_doctors()

    if not products or not users or not clients:
        print("❌ Erreur : Données manquantes (Produits, Users ou Clients).")
        return

    # IDs par défaut pour la simulation
    user_id = users[0].id
    client_id = clients[0].id
    # On prend un docteur au hasard si disponible
    default_doctor_id = doctors[0].id if doctors else None

    print(f"🚀 Début du seeding des ventes (30 jours)...")
    
    now = datetime.now(timezone.utc)
    total_sales_created = 0

    for i in range(30):
        # On remonte dans le temps
        current_date = now - timedelta(days=i)
        
        # Simulation d'une journée : entre 3 et 12 ventes
        daily_count = random.randint(3, 12)
        
        for _ in range(daily_count):
            product = random.choice(products)
            
            # On ignore si pas de stock pour ce produit
            if product.stock <= 0:
                continue

            # Préparation du panier (1 à 2 articles)
            items_data = [
                {
                    'product_id': product.id,
                    'quantity': random.randint(1, 2)
                }
            ]
            
            try:
                # IMPORTANT : Ton facade.process_sale doit accepter created_at 
                # pour enregistrer la vente à la date passée.
                facade.process_sale(
                    client_id=client_id,
                    doctor_id=default_doctor_id if product.is_prescription_only else None,
                    items_data=items_data,
                    user_id=user_id,
                    created_at=current_date  # <--- Crucial pour l'historique
                )
                total_sales_created += 1
            except Exception as e:
                # Exemple : "Stock insuffisant" ou "Ordonnance requise"
                pass 

    print(f"--- ✅ Seeding terminé ! ---")
    print(f"Nombre total de ventes créées : {total_sales_created}")

if __name__ == "__main__":
    seed_product_sales()