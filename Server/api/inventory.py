from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from services.facade import FacadeService

inventory_ns = Namespace('inventory', description='Inventory operations')
facade = FacadeService()

# Modèle de sortie pour la cohérence
product_model = inventory_ns.model('Product', {
    'id': fields.String(description='Product ID'),
    'name': fields.String(description='Product name'),
    'active_ingredient': fields.String(description='Active ingredient'),
    'dosage': fields.String(description='Dosage'),
    'stock': fields.Integer(description='Stock quantity'),
    'price': fields.Float(description='Price'),
    'is_prescription_only': fields.Boolean(description='Prescription required'),
    'user_id': fields.String(description='User ID')
})

@inventory_ns.route('/')
class InventoryList(Resource):
    @jwt_required()
    @inventory_ns.marshal_list_with(product_model)
    def get(self):
        """List all products for the inventory table"""
        products = facade.get_all_products_detailed()
        
        # Conversion en dictionnaire si to_dict() existe, sinon conversion manuelle
        result = []
        for p in products:
            if hasattr(p, 'to_dict'):
                result.append(p.to_dict())
            else:
                # Conversion manuelle si la méthode to_dict n'existe pas
                result.append({
                    'id': str(p.id),
                    'name': p.name,
                    'active_ingredient': p.active_ingredient,
                    'dosage': p.dosage,
                    'stock': p.stock,
                    'price': float(p.price),
                    'is_prescription_only': p.is_prescription_only,
                    'user_id': str(p.user_id) if p.user_id else None
                })
        
        return result, 200

    @jwt_required()
    @inventory_ns.expect(product_model)
    def post(self):
        """Create a new product - Available for all logged users"""
        data = inventory_ns.payload
        user_id = get_jwt_identity()
        
        # Validation basique
        if not data.get('name') or not data.get('active_ingredient'):
            return {"message": "Name and active ingredient are required"}, 400
        
        new_product = facade.create_product(
            name=data.get('name'),
            active_ingredient=data.get('active_ingredient'),
            dosage=data.get('dosage', ''),
            stock=data.get('stock', 0),
            price=data.get('price', 0.0),
            is_prescription_only=data.get('is_prescription_only', False),
            user_id=user_id
        )
        
        if new_product:
            # Retourner le produit créé
            product_data = {
                'id': str(new_product.id),
                'name': new_product.name,
                'active_ingredient': new_product.active_ingredient,
                'dosage': new_product.dosage,
                'stock': new_product.stock,
                'price': float(new_product.price),
                'is_prescription_only': new_product.is_prescription_only,
                'user_id': str(new_product.user_id)
            }
            return product_data, 201
        
        return {"message": "Failed to create product"}, 400


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
        
        if hasattr(product, 'to_dict'):
            return product.to_dict(), 200
        else:
            return {
                'id': str(product.id),
                'name': product.name,
                'active_ingredient': product.active_ingredient,
                'dosage': product.dosage,
                'stock': product.stock,
                'price': float(product.price),
                'is_prescription_only': product.is_prescription_only,
                'user_id': str(product.user_id) if product.user_id else None
            }, 200
    
    @jwt_required()
    @inventory_ns.expect(product_model)
    def put(self, product_id):
        """Update a product - Admin only"""
        # Vérification admin
        if not get_jwt().get('is_admin'):
            inventory_ns.abort(403, "Admin privileges required")
        
        product = facade.get_product_by_id(product_id)
        if not product:
            inventory_ns.abort(404, "Product not found")
        
        data = inventory_ns.payload
        data['user_id'] = get_jwt_identity()
        
        updated_product = facade.update_product(product_id, data)
        
        if updated_product:
            if hasattr(updated_product, 'to_dict'):
                return updated_product.to_dict(), 200
            else:
                return {
                    'id': str(updated_product.id),
                    'name': updated_product.name,
                    'active_ingredient': updated_product.active_ingredient,
                    'dosage': updated_product.dosage,
                    'stock': updated_product.stock,
                    'price': float(updated_product.price),
                    'is_prescription_only': updated_product.is_prescription_only,
                    'user_id': str(updated_product.user_id)
                }, 200
        
        return {"message": "Update failed"}, 400
    
    @jwt_required()
    def delete(self, product_id):
        """Delete a product - Admin only"""
        # Vérification admin
        if not get_jwt().get('is_admin'):
            inventory_ns.abort(403, "Admin privileges required")
        
        if facade.delete_product(product_id):
            return {"message": "Product deleted successfully"}, 200
        
        return {"message": "Product not found"}, 404