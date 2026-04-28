from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity 
<<<<<<< HEAD
from services.facade import FacadeService
from utils.decorator import admin_required 
=======
from services.facade import FacadeService 
>>>>>>> main

# --- INITIALIZATION ---

facade = FacadeService()
<<<<<<< HEAD
products_ns = Namespace('products', description="Product inventory operations (Admin required for CUD)")

# --- DATA MODELS ---

# Model for product creation (POST) - Essential fields are REQUIRED
product_input_model = products_ns.model('ProductInput', {
    'name': fields.String(required=True, description='The trade name of the product', min_length=3, max_length=100),
    'active_ingredient': fields.String(required=True, description='The main active ingredient', min_length=1),
    'dosage': fields.String(required=False, description='The dosage form and strength'),
    'stock': fields.Integer(required=True, description='Current stock quantity', min=0),
    'price': fields.Float(required=True, description='Selling price per unit', min=0.01),
    'is_prescription_only': fields.Boolean(required=False, default=False, description='Requires a prescription')
})

# Model for product update (PUT) - FIX for 400 errors: Fields are NOT required
product_update_model = products_ns.model('ProductUpdate', {
    'name': fields.String(required=False, description='The trade name of the product', min_length=3, max_length=100),
    'active_ingredient': fields.String(required=False, description='The main active ingredient', min_length=1),
    'dosage': fields.String(required=False, description='The dosage form and strength'),
    'stock': fields.Integer(required=False, description='Current stock quantity', min=0),
    'price': fields.Float(required=False, description='Selling price per unit', min=0.01),
    'is_prescription_only': fields.Boolean(required=False, description='Requires a prescription')
})

# Model for serialization and output of product data
product_output_model = products_ns.model('ProductOutput', {
    'id': fields.String(readOnly=True, description='The unique product identifier'),
    'name': fields.String(description='The trade name of the product'),
    'active_ingredient': fields.String(description='The main active ingredient'),
    'dosage': fields.String(description='The dosage form and strength'),
    'stock': fields.Integer(description='Current stock quantity'),
    'price': fields.Float(description='Selling price per unit'),
    'is_prescription_only': fields.Boolean(description='Requires a prescription'),
    'user_id': fields.String(description='ID of the user who last updated this product') 
})

# --- SECURE RESOURCE 1: Product List (GET, POST) ---
=======
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
>>>>>>> main

@products_ns.route('/')
class ProductList(Resource):
    
    @products_ns.doc('get_all_products')
    @products_ns.marshal_list_with(product_output_model)
<<<<<<< HEAD
    @jwt_required() 
    def get(self):
        """
        Retrieves the list of all products in the inventory. Accessible to all authenticated users.
        """
        return facade.get_all_products(), 200

    @products_ns.doc('create_new_product')
    @products_ns.expect(product_input_model, validate=True) # Strict validation for creation
    @products_ns.marshal_with(product_output_model, code=201)
    @products_ns.response(403, 'Access Forbidden: Admin privileges required.')
    @products_ns.response(400, 'Validation Error: Invalid input data.')
    @jwt_required()
    @admin_required()
    def post(self):
        """
        Creates a new product entry. Restricted to administrators only.
        """
        # 1. Get current user ID from JWT            
        current_user_id = get_jwt_identity()
        data = products_ns.payload
        
        # 2. Check for potential name collision (optional, depends on business rule)
        # We will allow products with the same name but different dosage/active ingredient.
            
        # 3. Create the product
        try:
            new_product = facade.create_product(
                name=data['name'],
                active_ingredient=data['active_ingredient'],
                dosage=data.get('dosage'),
                stock=data['stock'],
                price=data['price'],
                is_prescription_only=data.get('is_prescription_only', False),
                user_id=current_user_id
            )
        except Exception:
            products_ns.abort(500, message="Product creation failed due to an internal error.")

        if new_product is None:
             products_ns.abort(500, message="Product creation failed after database operation.")
             
        return new_product, 201

# --- SECURE RESOURCE 2: Single Product Item by UUID ---

@products_ns.route('/<string:product_id>')
@products_ns.param('product_id', 'The unique product identifier (UUID)')
class ProductItem(Resource):
    
    @products_ns.doc('get_product_by_id')
    @products_ns.marshal_with(product_output_model)
    @jwt_required()
    def get(self, product_id):
        """Retrieves a product by ID (UUID)."""
        product = facade.get_product_by_id(product_id)
        if not product:
            products_ns.abort(404, message="Product not found.")
        return product, 200

    @products_ns.doc('update_product')
    @products_ns.expect(product_update_model, validate=True) # FIX: Use non-required model for PUT
    @products_ns.marshal_with(product_output_model)
    @products_ns.response(403, 'Access Forbidden: Admin privileges required.')
    @jwt_required()
    def put(self, product_id):
        """
        Updates an existing product's details. Restricted to administrators only.
        """
        # 1. Admin privilege check
        if not get_jwt().get('is_admin'):
            products_ns.abort(403, message="Access Forbidden. Only administrators can update products.")
        
        product = facade.get_product_by_id(product_id)
        if not product:
            products_ns.abort(404, message="Product not found.")
            
        data = products_ns.payload
        # The update must include the current user's ID
        data['user_id'] = get_jwt_identity() 

        updated_product = facade.update_product(product_id, data)

        if not updated_product:
            products_ns.abort(400, message="Update failed. Check data or internal error.")

=======
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

>>>>>>> main
        return updated_product, 200

    @products_ns.doc('delete_product')
    @products_ns.response(204, 'Product successfully deleted.')
    @products_ns.response(403, 'Access Forbidden: Admin privileges required.')
    @jwt_required()
    def delete(self, product_id):
        """
        Deletes a product. Restricted to administrators only.
        """
<<<<<<< HEAD
        # 1. Admin privilege check
        if not get_jwt().get('is_admin'):
            products_ns.abort(403, message="Access Forbidden. Only administrators can delete products.")
            
        if not facade.delete_product(product_id):
            products_ns.abort(404, message="Product not found.")

        return '', 204
        
# --- SECURE RESOURCE 3: Product Search by Name ---

@products_ns.route('/search/<string:name>')
@products_ns.param('name', 'Product name or part of name for search')
class ProductSearch(Resource):
    
    @products_ns.doc('search_products_by_name')
    @products_ns.marshal_list_with(product_output_model)
    @jwt_required()
    def get(self, name):
        """
        Search for products by name (returns a list of matching results).
        """
        # Assumes the Facade service has a method for fuzzy or partial searching
        products = facade.get_product_by_name(name) 
        if not products:
            products_ns.abort(404, message=f"No products found matching '{name}'.")
        return products, 200
    
=======
        claims = get_jwt()
        
        # 1. Authorization Check (RBAC)
        if not claims.get('is_admin'):
            products_ns.abort(403, message="Access Forbidden. Only administrators can delete products.")
            
        # 2. Business Logic via Facade
        if not facade.delete_product(product_id):
            products_ns.abort(404, message="Product not found.")

        return '', 204
>>>>>>> main
