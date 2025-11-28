from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity 
from services.facade import FacadeService 

# --- INITIALIZATION ---

facade = FacadeService()
products_ns = Namespace('Products', description="Product management operations")

# --- DATA MODELS ---

# Input model for product creation/update
product_input_model = products_ns.model('ProductInput', {
    'name': fields.String(required=True, description='The product name'),
    'stock': fields.Integer(required=True, description='Current stock quantity'),
    'price': fields.Float(required=True, description='Unit price')
})

# Output model for a single product (including the owner ID for ownership checks)
product_output_model = products_ns.model('ProductOutput', {
    'id': fields.Integer(readOnly=True, description='The unique product identifier'),
    'name': fields.String(description='The product name'),
    'stock': fields.Integer(description='Current stock quantity'),
    'price': fields.Float(description='Unit price'),
    'user_id': fields.Integer(description='ID of the user who created this product') 
})

# --- SECURE RESOURCE 1: Product List (Creation) ---

@products_ns.route('/')
class ProductList(Resource):
    
    @products_ns.doc('get_all_products')
    @products_ns.marshal_list_with(product_output_model)
    # Require a valid JWT token for access
    @jwt_required() 
    def get(self):
        """
        Retrieves all products. Accessible to all authenticated users.
        """
        # Read the identity from the token (useful for logging/filtering later)
        current_user_id = get_jwt_identity() 
        
        # Logic via Facade
        products = facade.get_all_products()
        
        # Return list of product objects (Flask-RESTx handles serialization)
        return products, 200

    @products_ns.doc('create_new_product')
    @products_ns.expect(product_input_model)
    @products_ns.marshal_with(product_output_model, code=201)
    @products_ns.response(403, 'Access Forbidden: Admin privileges required.')
    @jwt_required()
    def post(self):
        """
        Creates a new product. Restricted to administrators only.
        """
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        
        # 1. Authorization Check (Role-Based Access Control - RBAC)
        if not claims.get('is_admin'):
            products_ns.abort(403, message="Access Forbidden. Only administrators can create products.")

        data = products_ns.payload
        
        # 2. Business Logic via Facade (Admin creates the product, and is automatically set as owner)
        new_product = facade.create_product(
            name=data['name'],
            stock=data['stock'],
            price=data['price'],
            user_id=current_user_id # Set the admin as the creator/owner
        )
        
        return new_product, 201

# --- SECURE RESOURCE 2: Single Product Item (Update/Delete) ---

@products_ns.route('/<int:product_id>')
class ProductItem(Resource):
    
    @products_ns.doc('update_product')
    @products_ns.expect(product_input_model)
    @products_ns.marshal_with(product_output_model)
    @products_ns.response(403, 'Access Forbidden: You are not the owner.')
    @jwt_required()
    def put(self, product_id):
        """
        Updates an existing product. Only the owner or an admin can update it.
        """
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        
        # Retrieve the existing product via Facade
        product = facade.get_product_by_id(product_id)
        
        if not product:
            products_ns.abort(404, message="Product not found.")
            
        # 1. Authorization Check (Ownership-Based Access Control)
        # Check if the user is the owner OR is an admin
        is_owner = product.user_id == current_user_id
        is_admin = claims.get('is_admin', False)

        if not (is_owner or is_admin):
            products_ns.abort(403, message="Access Forbidden. You must be the product owner or an administrator to update this item.")
            
        # 2. Business Logic via Facade
        data = products_ns.payload
        updated_product = facade.update_product(product_id, data)

        return updated_product, 200

    @products_ns.doc('delete_product')
    @products_ns.response(204, 'Product successfully deleted.')
    @products_ns.response(403, 'Access Forbidden: Admin privileges required.')
    @jwt_required()
    def delete(self, product_id):
        """
        Deletes a product. Restricted to administrators only.
        """
        claims = get_jwt()
        
        # 1. Authorization Check (RBAC)
        if not claims.get('is_admin'):
            products_ns.abort(403, message="Access Forbidden. Only administrators can delete products.")
            
        # 2. Business Logic via Facade
        if not facade.delete_product(product_id):
            products_ns.abort(404, message="Product not found.")

        return '', 204