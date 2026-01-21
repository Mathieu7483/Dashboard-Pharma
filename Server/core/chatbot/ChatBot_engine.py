"""
Server/core/chatbot/ChatBot_engine.py
Optimized chatbot using database-driven alias resolution
"""

from sqlalchemy import inspect, or_, func, cast, Date
from datetime import datetime, timedelta
from database.data_manager import db
from models.product import ProductModel
from models.client import ClientModel
from models.doctor import DoctorModel
from models.sale import SaleModel
from models.interaction import InteractionModel
from models.product_alias import ProductAliasModel
from core.chatbot.NLUProcessor import NLUProcessor

class ChatBotEngine:
    """
    Core chatbot orchestrator with database-driven product resolution.
    Uses ProductAliasModel for flexible name mapping.
    """

    def __init__(self):
        self.nlu = NLUProcessor()
        
        # Model mapping for entity searches
        self.search_models = {
            "get_product": ProductModel,
            "get_client": ClientModel,
            "get_doctor": DoctorModel
        }

    def process_query(self, user_text: str) -> str:
        """
        Main entry point for chatbot queries.
        
        Args:
            user_text: User's natural language query
            
        Returns:
            Formatted markdown response
        """
        if not user_text or not user_text.strip():
            return "❓ **Posez une question.** Exemples : 'Stock Doliprane' ou 'Ventes du jour'"
        
        # Analyze with NLU
        analysis = self.nlu.analyze(user_text)
        intent = analysis.get("intent")
        entities = analysis.get("entity_list", [])
        
        # Route to specialized handlers
        try:
            if intent == "check_interaction":
                return self._handle_interaction_check(entities)
            
            elif intent == "get_stock_alerts":
                return self._handle_stock_alerts()
            
            elif intent == "get_sales_summary":
                return self._handle_sales_summary()
            
            elif intent == "check_stock":
                return self._handle_stock_query(entities)
            
            elif intent == "check_price":
                return self._handle_price_query(entities)
            
            elif intent == "get_prescription_info":
                return self._handle_prescription_info(entities)
            
            elif intent == "get_contact_info":
                return self._handle_contact_search(entities)
            
            # Standard entity search (products, clients, doctors)
            else:
                if not entities:
                    return self._generate_help_message()
                
                return self._execute_standard_search(intent, entities[0])
        
        except Exception as e:
            print(f"❌ ChatBot Error: {e}")
            import traceback
            traceback.print_exc()
            return f"⚠️ **Erreur lors du traitement.** Reformulez votre demande."

    # ==================== SPECIALIZED HANDLERS ====================

    def _resolve_to_active_ingredient(self, product_name: str) -> tuple:
        """
    Resolves a product name to its active ingredient with multi-result safety.
    """
        name_clean = product_name.strip()
    
        try:
        # 1. Search in ALIASES table (Exact match, case-insensitive)
            alias_result = db.session.execute(
                db.select(ProductAliasModel).where(
                    ProductAliasModel.alias.ilike(f"{name_clean}")
                )
            ).scalars().first()
        
            if alias_result:
                return (alias_result.active_ingredient, name_clean)

        # 2. Search in PRODUCTS table (Fuzzy match)
            product = db.session.execute(
                db.select(ProductModel)
                .where(ProductModel.name.ilike(f"%{name_clean}%"))
                .order_by(func.length(ProductModel.name)) 
            ).scalars().first()
        
            if product:
                return (product.active_ingredient, product.name)

        # 3. Fallback : we could not resolve, return input as-is
            return (name_clean.capitalize(), name_clean.capitalize())

        except Exception as e:
            print(f"⚠️ Erreur résolution produit '{product_name}': {e}")
        # In case of error, return input as-is
            return (name_clean.capitalize(), name_clean.capitalize())

    def _handle_interaction_check(self, entity_list: list) -> str:
        """
        Checks drug-drug interactions with flexible name resolution.
        
        Logic:
        1. Resolve commercial names → active ingredients via database
        2. Query InteractionModel for conflicts
        3. Return safety report
        """
        if len(entity_list) < 2:
            return ("⚠️ **Mentionnez au moins DEUX produits** pour vérifier la compatibilité.\n\n"
                   "**Exemples :**\n"
                   "   • 'Aspirine et Ibuprofène compatibles ?'\n"
                   "   • 'Doliprane avec Advil danger ?'\n"
                   "   • 'Warfarine et Plavix interaction ?'\n"
                   "   • 'Puis-je mélanger Aspirine et Advil ?'")

        # Step 1: Resolve all names to active ingredients
        resolved = []
        display_names = []
        
        for name in entity_list:
            active_ingredient, display_name = self._resolve_to_active_ingredient(name)
            resolved.append(active_ingredient)
            display_names.append(display_name)
        
        # Debug output
        print(f"🔬 Resolved ingredients: {list(zip(display_names, resolved))}")
        
        # Step 2: Query interactions (bidirectional check)
        conflicts = []
        for i in range(len(resolved)):
            for j in range(i + 1, len(resolved)):
                ing_a, ing_b = resolved[i], resolved[j]
                
                # Check both directions (A+B and B+A)
                query = db.select(InteractionModel).where(
                    or_(
                        (InteractionModel.ingredient_a == ing_a) & 
                        (InteractionModel.ingredient_b == ing_b),
                        (InteractionModel.ingredient_a == ing_b) & 
                        (InteractionModel.ingredient_b == ing_a)
                    )
                )
                
                result = db.session.execute(query).scalar_one_or_none()
                if result:
                    conflicts.append({
                        'interaction': result,
                        'name_a': display_names[i],
                        'name_b': display_names[j]
                    })
        
        # Step 3: Format response
        if not conflicts:
            return (f"✅ **Aucune interaction connue** entre :\n"
                   f"   • {' + '.join(display_names)}\n\n"
                   f"*Principes actifs analysés : {', '.join(set(resolved))}*\n\n"
                   f"*Consultez toujours un professionnel de santé pour un avis personnalisé.*")
        
        # Safety warning format
        output = ["## 🚨 ALERTE INTERACTION MÉDICAMENTEUSE\n"]
        output.append(f"**Analyse pour :** {' + '.join(display_names)}\n")
        
        for conflict in conflicts:
            interaction = conflict['interaction']
            severity_emoji = {
                "low": "⚠️",
                "moderate": "🟠",
                "high": "🔴",
                "critical": "🔴🔴"
            }.get(interaction.severity.lower(), "⚠️")
            
            output.append(f"### {severity_emoji} {conflict['name_a']} + {conflict['name_b']}")
            output.append(f"**Principes actifs :** {interaction.ingredient_a} / {interaction.ingredient_b}")
            output.append(f"**Gravité :** {interaction.severity.upper()}")
            output.append(f"**Détails cliniques :** {interaction.description}")
            output.append("---\n")
        
        output.append("⚕️ **IMPORTANT :** Consultez un pharmacien ou médecin avant utilisation.")
        
        return "\n".join(output)

    def _handle_stock_query(self, entities: list) -> str:
        """Check stock for a specific product."""
        if not entities:
            return "❓ Quel produit souhaitez-vous vérifier ?"
        
        # Try fuzzy search
        product = db.session.execute(
            db.select(ProductModel).where(
                ProductModel.name.ilike(f"%{entities[0]}%")
            )
        ).scalar_one_or_none()
        
        if product:
            # Status indicators
            if product.stock > 100:
                emoji, status = "✅", "Stock excellent"
            elif product.stock > 50:
                emoji, status = "🟢", "Stock bon"
            elif product.stock > 20:
                emoji, status = "🟡", "Stock moyen"
            elif product.stock > 5:
                emoji, status = "🟠", "Stock faible"
            else:
                emoji, status = "🔴", "STOCK CRITIQUE"
            
            rx_badge = "🔒 Ordonnance" if product.is_prescription_only else "🔓 Libre"
            
            return (f"{emoji} **{product.name}**\n"
                   f"   • Stock : **{product.stock} unités** ({status})\n"
                   f"   • Principe actif : {product.active_ingredient}\n"
                   f"   • Dosage : {product.dosage}\n"
                   f"   • Prix : {product.price:.2f} €\n"
                   f"   • Type : {rx_badge}")
        
        return f"❌ Produit **'{entities[0]}'** introuvable dans l'inventaire."

    def _handle_price_query(self, entities: list) -> str:
        """Get price for a specific product."""
        if not entities:
            return "❓ Quel produit cherchez-vous ?"
        
        product = db.session.execute(
            db.select(ProductModel).where(
                ProductModel.name.ilike(f"%{entities[0]}%")
            )
        ).scalar_one_or_none()
        
        if product:
            rx_badge = "🔒 Sur ordonnance" if product.is_prescription_only else "🔓 Vente libre"
            
            return (f"💰 **{product.name}**\n"
                   f"   • Prix : **{product.price:.2f} €**\n"
                   f"   • Type : {rx_badge}\n"
                   f"   • Dosage : {product.dosage}\n"
                   f"   • Stock disponible : {product.stock} unités")
        
        return f"❌ Produit **'{entities[0]}'** introuvable."

    def _handle_prescription_info(self, entities: list) -> str:
        """Check if product requires prescription."""
        if not entities:
            return "❓ Quel médicament souhaitez-vous vérifier ?"
        
        product = db.session.execute(
            db.select(ProductModel).where(
                ProductModel.name.ilike(f"%{entities[0]}%")
            )
        ).scalar_one_or_none()
        
        if product:
            if product.is_prescription_only:
                return (f"🔒 **{product.name}** nécessite une ordonnance médicale.\n"
                       f"   • Principe actif : {product.active_ingredient}\n"
                       f"   • Dosage : {product.dosage}\n"
                       f"   • Une autorisation du médecin est obligatoire pour l'achat.")
            else:
                return (f"🔓 **{product.name}** est disponible en vente libre.\n"
                       f"   • Aucune ordonnance nécessaire.\n"
                       f"   • Prix : {product.price:.2f} €\n"
                       f"   • Stock : {product.stock} unités")
        
        return f"❌ Produit **'{entities[0]}'** introuvable."

    def _handle_stock_alerts(self) -> str:
        """Reports products with low stock (< 20 units)."""
        threshold = 20
        low_stock = db.session.execute(
            db.select(ProductModel).where(ProductModel.stock < threshold)
            .order_by(ProductModel.stock)
        ).scalars().all()
        
        if not low_stock:
            return f"✅ **Tous les produits ont un stock suffisant** (≥{threshold} unités)."
        
        output = [f"## ⚠️ Alertes Stock Bas (< {threshold} unités)\n"]
        
        # Group by severity
        critical = [p for p in low_stock if p.stock < 5]
        warning = [p for p in low_stock if 5 <= p.stock < threshold]
        
        if critical:
            output.append("### 🔴 CRITIQUE (< 5 unités)")
            for product in critical:
                output.append(f"   • **{product.name}** : {product.stock} unités")
            output.append("")
        
        if warning:
            output.append("### 🟠 FAIBLE (5-19 unités)")
            for product in warning:
                output.append(f"   • **{product.name}** : {product.stock} unités")
        
        output.append(f"\n📦 **{len(low_stock)} produits** nécessitent un réapprovisionnement.")
        
        return "\n".join(output)

    def _handle_sales_summary(self) -> str:
        """Returns daily/total sales summary using SQL aggregations."""
        try:
            now = datetime.now()
            today = now.date()
            # beginning of the week (Monday)
            week_start = today - timedelta(days=today.weekday())

            # 1. Request for Today
            stats_today = db.session.query(
                func.count(SaleModel.id),
                func.sum(SaleModel.total_amount)
            ).filter(cast(SaleModel.sale_date, Date) == today).first()

            # 2. Request for This Week
            stats_week = db.session.query(
                func.count(SaleModel.id),
                func.sum(SaleModel.total_amount)
            ).filter(SaleModel.sale_date >= week_start).first()

            # 3. Request for All Time
            stats_total = db.session.query(
                func.count(SaleModel.id),
                func.sum(SaleModel.total_amount)
            ).first()

            # Extraction of values
            count_day, rev_day = stats_today[0] or 0, stats_today[1] or 0.0
            count_week, rev_week = stats_week[0] or 0, stats_week[1] or 0.0
            count_all, rev_all = stats_total[0] or 0, stats_total[1] or 0.0

            output = ["## 📈 Performances de Vente\n"]
        
            output.append(f"### Aujourd'hui ({today.strftime('%d/%m/%Y')})")
            output.append(f"   • Transactions : **{count_day}**")
            output.append(f"   • Chiffre d'affaires : **{rev_day:.2f} €**\n")
        
            output.append(f"### Cette semaine (depuis le {week_start.strftime('%d/%m')})")
            output.append(f"   • Transactions : **{count_week}**")
            output.append(f"   • CA : **{rev_week:.2f} €**\n")
        
            output.append(f"### Cumulé total")
            output.append(f"   • Transactions totales : **{count_all}**")
            output.append(f"   • CA total : **{rev_all:.2f} €**")
        
            if count_all > 0:
                avg_ticket = rev_all / count_all
                output.append(f"   • Panier moyen : **{avg_ticket:.2f} €**")
            
            return "\n".join(output)

        except Exception as e:
            return f"⚠️ Erreur lors de l'extraction des statistiques : {str(e)}"
        

    def _handle_contact_search(self, entities: list) -> str:
        """Extract contact info for a doctor or client."""
        if not entities:
            return "❓ **De qui souhaitez-vous obtenir les coordonnées ?**"
    
        search_term = entities[0]
    
    # search in doctors first
        person = self._search_database(DoctorModel, search_term)
        category = "docteur"
    
    # if not found, search in clients
        if not person:
            person = self._search_database(ClientModel, search_term)
            category = "client"
        
        if not person:
            return f"❌ Je n'ai trouvé aucun contact pour **{search_term}**."

    # take the first match
        p = person[0]
        name = f"{p.first_name} {p.last_name}"
    
        output = [f"## 📞 Coordonnées de {name}"]
        output.append(f"📌 **Poste :** {category.capitalize()}")
        output.append(f"📱 **Téléphone :** `{p.phone or 'Non renseigné'}`")
        output.append(f"📧 **Email :** {p.email or 'Non renseigné'}")
    
        if hasattr(p, 'address'):
            output.append(f"📍 **Adresse :** {p.address}")
        
        return "\n".join(output)

    # ==================== STANDARD SEARCH ====================

    def _execute_standard_search(self, intent: str, main_entity: str) -> str:
        """
        Database search with smart fallback.
        """
        results = []
        detected_intent = intent

        # potential results in primary model
        potential_results ={
            "get_product": self._search_database(ProductModel, main_entity),
            "get_client": self._search_database(ClientModel,main_entity),
            "get_doctor": self._search_database(DoctorModel,main_entity)
        }
       
        for model_key, records in potential_results.items():
            if records:
                results = records
                detected_intent = model_key
                break

        return self._format_results(results, detected_intent, main_entity)

    def _search_database(self, model, search_term: str) -> list:
        """Executes fuzzy search using ILIKE."""
        if not model or not search_term:
            return []
        
        term = search_term.lower().strip()
        for p in ['dr', 'doc', 'docteur', 'doctor','m', 'mr', 'mme', 'mlle']:
            if term.startswith(p + " "):
                term = term[len(p)+1 :].strip()

        if model == ProductModel:
            # Search in name AND active_ingredient
            condition = or_(
                model.name.ilike(f"%{term}%"),
                model.active_ingredient.ilike(f"%{term}%")
            )
        else:
            # For Person models (Client, Doctor) - search in ALL name fields
            condition = or_(
                model.last_name.ilike(f"%{term}%"),
                model.first_name.ilike(f"%{term}%")
            )
            
            # Also search in full name combination
            if " " in term:
                parts = term.split()
                condition = or_(
                condition,
                (model.first_name.ilike(f"%{parts[0]}%") & model.last_name.ilike(f"%{parts[1]}%")),
                (model.first_name.ilike(f"%{parts[1]}%") & model.last_name.ilike(f"%{parts[0]}%"))
            )
        
        query = db.select(model).where(condition).limit(5)
        return db.session.execute(query).scalars().all()

    def _format_results(self, records: list, intent: str, search_term: str) -> str:
        """Converts SQLAlchemy records to clean Markdown tables and cards."""
        if not records:
            return (f"❌ **Aucun résultat pour '{search_term}'.**\n\n"
                "**Suggestions :**\n"
                " • Vérifiez l'orthographe\n"
                " • Essayez un nom plus court (ex: 'Doli' au lieu de 'Doliprane')")

        category_map = {
            "get_product": ("📦 PRODUITS", ["Produit", "Stock", "Prix", "Type"]),
            "get_client": ("👤 CLIENTS", ["Nom", "Téléphone", "Email"]),
            "get_doctor": ("⚕️ MÉDECINS", ["Nom", "Spécialité", "Ville"])
        }
    
        title, headers = category_map.get(intent, ("📋 RÉSULTATS", ["Détails"]))
        output = [f"## {title}\n"]

        if intent == "get_product":
            for p in records[:5]:
                rx_status = "🔒 Sur ordonnance" if p.is_prescription_only else "🔓 Vente libre"
                stock_emoji = "✅" if p.stock >= 20 else "⚠️"
                
                output.append(f"### 💊 {p.name.upper()}")
                output.append(f"• **Stock :** {stock_emoji} {p.stock} unités")
                output.append(f"• **Prix :** {p.price:.2f} €")
                output.append(f"• **Statut :** {rx_status}")
                output.append(f"• **Compo :** {p.active_ingredient} ({p.dosage})")
                output.append("---")

        elif intent in ["get_client", "get_doctor"]:
            # Cards for persons
            for person in records[:3]:
                name = f"{person.first_name} {person.last_name}".upper()
                output.append(f"### 🔹 {name}")
                output.append(f"📞 **Tel :** `{person.phone or 'N/A'}`")
                if intent == "get_client":
                    output.append(f"📧 **Email :** {person.email or 'N/A'}")
                    output.append(f"📍 **Adresse :** {getattr(person, 'address', 'N/A')}")
                else:
                    output.append(f"🩺 **Spécialité :** {getattr(person, 'specialty', 'Généraliste')}")
                    output.append(f"📍 **Adresse :** {getattr(person, 'address', 'N/A')}")
                output.append("---")

        return "\n".join(output)

    def _generate_help_message(self) -> str:
        """Help message when no entity detected."""
        return """
## 💡 Comment utiliser le Chatbot

**Recherche de produits :**
• "Stock Doliprane" → Vérifier l'inventaire
• "Prix Amoxicilline" → Connaître le prix
• "Aspirine ordonnance ?" → Vérifier si prescription nécessaire

**Sécurité médicamenteuse :**
• "Aspirine et Ibuprofène compatibles ?"
• "Doliprane avec Advil danger ?"
• "Puis-je mélanger Warfarine et Plavix ?"

**Analyses :**
• "Ventes du jour" → Résumé des ventes
• "Produits en rupture" → Alertes stock

**Recherche personnes :**
• "Trouve Lefevre" → Trouve automatiquement
• "Client Dupont" → Trouver un client

Essayez un de ces exemples !
"""