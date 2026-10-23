from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from services.facade import FacadeService
from utils.text_norm import normalize
from models.specialite import SpecialiteModel
from models.composition import CompositionModel
from models.cip import CipModel

inventory_ns = Namespace('inventory', description='Inventory operations')
facade = FacadeService()

# Model for product representation
product_model = inventory_ns.model('Product', {
    'id': fields.String(description='Product ID'),
    'name': fields.String(description='Product name'),
    'active_ingredient': fields.String(description='Active ingredient'),
    'dosage': fields.String(description='Dosage'),
    'stock': fields.Integer(description='Stock quantity'),
    'price': fields.Float(description='Price'),
    'is_prescription_only': fields.Boolean(description='Prescription required'),
    'cis': fields.String(description='Code CIS ANSM lié'),
    'cip13': fields.String(description='Code CIP13 de la boîte en stock'),
    'user_id': fields.String(description='User ID')
})

# Champs modifiables via l'API (évite que le payload écrase id, user_id, etc.)
EDITABLE_FIELDS = (
    'name', 'active_ingredient', 'dosage', 'stock', 'price',
    'is_prescription_only', 'cis', 'cip13'
)

# Parser pour la recherche ANSM
ansm_search_parser = inventory_ns.parser()
ansm_search_parser.add_argument('q', type=str, required=True, location='args', help='Terme de recherche')


def _is_active_cip(cip):
    """Une présentation 'active' est préférable à une présentation abrogée."""
    return 'active' in (cip.statut_admin or '').lower()


@inventory_ns.route('/search-ansm')
class InventoryANSMSearch(Resource):
    @jwt_required()
    def get(self):
        """Search official ANSM database for smart autocomplete with CIP13"""
        args = ansm_search_parser.parse_args()
        query = normalize(args.get('q', ''))
        tokens = query.split()

        if len(query) < 2 or not tokens:
            return [], 200

        # Tous les mots saisis doivent être présents (dans n'importe quel ordre)
        q = SpecialiteModel.query
        for t in tokens:
            q = q.filter(SpecialiteModel.search_name.like(f"%{t}%"))

        results = (
            q.order_by(
                SpecialiteModel.search_name.like(f"{tokens[0]}%").desc(),
                SpecialiteModel.denomination
            )
            .limit(10)
            .all()
        )
        if not results:
            return [], 200

        cis_list = [s.cis for s in results]

        # Substances actives (SA) et dosages : 1 seule requête pour tous les résultats
        compos = {}
        for c in CompositionModel.query.filter(
                CompositionModel.cis.in_(cis_list),
                CompositionModel.nature_composant == 'SA').all():
            compos.setdefault(c.cis, []).append(c)

        # CIP13 : on préfère une présentation active
        cips = {}
        for c in CipModel.query.filter(CipModel.cis.in_(cis_list)).all():
            best = cips.get(c.cis)
            if best is None or (_is_active_cip(c) and not _is_active_cip(best)):
                cips[c.cis] = c

        data = []
        for spe in results:
            comps = compos.get(spe.cis, [])
            substances = list(dict.fromkeys(
                c.denomination_substance for c in comps if c.denomination_substance))
            dosages = list(dict.fromkeys(
                c.dosage_substance for c in comps if c.dosage_substance))
            dosage = ", ".join(filter(None, [" / ".join(dosages), spe.forme_pharmaceutique]))
            cip = cips.get(spe.cis)

            data.append({
                "cis": spe.cis,
                "denomination": spe.denomination,
                "active_ingredient": ", ".join(substances),
                "dosage": dosage,
                "cip13": cip.cip13 if cip else ''
            })
        return data, 200


@inventory_ns.route('/')
class InventoryList(Resource):
    @jwt_required()
    @inventory_ns.marshal_list_with(product_model)
    def get(self):
        """List all products for the inventory table"""
        return facade.get_all_products_detailed(), 200

    @jwt_required()
    @inventory_ns.expect(product_model)
    @inventory_ns.marshal_with(product_model, code=201)
    def post(self):
        """Create a new product - Available for all logged users"""
        data = inventory_ns.payload or {}
        current_user_id = get_jwt_identity()

        name = (data.get('name') or '').strip()
        active_ingredient = (data.get('active_ingredient') or '').strip()
        if not name or not active_ingredient:
            inventory_ns.abort(400, "Name and active ingredient are required")

        new_product = facade.create_product(
            name=name,
            active_ingredient=active_ingredient,
            dosage=data.get('dosage', ''),
            stock=data.get('stock', 0),
            price=data.get('price', 0.0),
            is_prescription_only=data.get('is_prescription_only', False),
            user_id=current_user_id,
            cis=data.get('cis') or None,
            cip13=data.get('cip13') or None
        )

        if not new_product:
            inventory_ns.abort(400, "Failed to create product")

        return new_product, 201


@inventory_ns.route('/<string:product_id>')
@inventory_ns.param('product_id', 'The product identifier')
class InventoryItem(Resource):

    @jwt_required()
    @inventory_ns.marshal_with(product_model)
    def get(self, product_id):
        """Get a specific product"""
        product = facade.get_product_by_id(product_id)
        if not product:
            inventory_ns.abort(404, "Product not found")
        return product, 200

    @jwt_required()
    @inventory_ns.expect(product_model)
    @inventory_ns.marshal_with(product_model)
    def put(self, product_id):
        """Update a product - Admin only"""
        if not get_jwt().get('is_admin'):
            inventory_ns.abort(403, "Admin privileges required")

        product = facade.get_product_by_id(product_id)
        if not product:
            inventory_ns.abort(404, "Product not found")

        payload = inventory_ns.payload or {}
        data = {k: payload[k] for k in EDITABLE_FIELDS if k in payload}

        # Un code vide efface le lien ANSM / CIP
        for key in ('cis', 'cip13'):
            if key in data:
                data[key] = data[key] or None

        data['user_id'] = get_jwt_identity()

        updated_product = facade.update_product(product_id, data)
        if not updated_product:
            inventory_ns.abort(400, "Update failed")

        return updated_product, 200

    @jwt_required()
    def delete(self, product_id):
        """Delete a product - Admin only"""
        if not get_jwt().get('is_admin'):
            inventory_ns.abort(403, "Admin privileges required")

        if facade.delete_product(product_id):
            return {"message": "Product deleted successfully"}, 200

        return {"message": "Product not found"}, 404