from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity 
from services.facade import FacadeService 

# --- INITIALIZATION ---

facade = FacadeService()
sales_ns = Namespace('sales', description="Sales transactions and reporting (Admin required for Delete)")

# --- DATA MODELS (WITH STRICT VALIDATION) ---

# Model for an item in the list of sold products (Input)
sale_item_model = sales_ns.model('SaleItem', {
    'product_id': fields.String(required=True, description='UUID of the product sold'),
    'quantity': fields.Integer(required=True, description='Quantity of the product sold', min=1),
    'price_at_sale': fields.Float(readOnly=True, description='Price of the product at the time of sale'),
    'name': fields.String(readOnly=True, description='Name of the product')

})


# Model for creating a new sale (Input)
sale_input_model = sales_ns.model('SaleInput', {
    'client_id': fields.String(required=True, description='UUID of the client making the purchase', format='uuid'),
    'doctor_id': fields.String(required=False, description='UUID of the doctor who issued the prescription (if required)', format='uuid'),
    
    'items': fields.List(
        fields.Nested(sale_item_model), 
        required=True, 
        description='List of products and quantities for the sale',
        min_items=1
    )
})

# Model for serialization and output of sale data (Output)
sale_output_model = sales_ns.model('SaleOutput', {
    'id': fields.String(readOnly=True, description='The unique sale identifier', format='uuid'),
    'client_id': fields.String(description='UUID of the client', format='uuid'),
    'doctor_id': fields.String(description='UUID of the doctor (optional)', format='uuid'),
    'sale_date': fields.DateTime(description='Timestamp of the sale'),
    'total_amount': fields.Float(description='The total final amount of the sale', min=0.0), 
    
    # Nested output model for items
    'items': fields.List(fields.Nested(sales_ns.model('SaleItemOutput', {
        'product_id': fields.String(description='UUID of the product sold', format='uuid'),
        'quantity': fields.Integer(description='Quantity of the product sold'),
        'price_at_sale': fields.Float(description='Price of the product at the time of sale', min=0.01), 
        'name': fields.String(description='Name of the product')
    })), description='Details of products sold'),
    
    'user_id': fields.String(description='ID of the employee who processed the sale', format='uuid') 
})

# --- SECURE RESOURCE 1: Sale List (GET, POST) ---

@sales_ns.route('/')
class SaleList(Resource):
    
    @sales_ns.doc('get_all_sales')
    @sales_ns.marshal_list_with(sale_output_model)
    @jwt_required() 
    def get(self):
        """
        Retrieves the list of all sales. Accessible to all authenticated users.
        """
        return facade.get_all_sales(), 200

    @sales_ns.doc('create_new_sale')
    @sales_ns.expect(sale_input_model, validate=True) 
    @sales_ns.marshal_with(sale_output_model, code=201)
    @sales_ns.response(400, 'Validation Error (Input format, empty cart, invalid ID format).')
    @jwt_required()
    def post(self):
        """
        Processes a new sale transaction. Accessible to all authenticated users (Employees).
        Performs stock and prescription checks.
        """
        current_user_id = get_jwt_identity()
        data = sales_ns.payload 
        
        # 1. Entity existence check (Format is already validated by RESTx)
        if not facade.get_client_by_id(data['client_id']):
            sales_ns.abort(400, message="Client not found.")
        
        if data.get('doctor_id') and not facade.get_doctor_by_id(data['doctor_id']):
            sales_ns.abort(400, message="Doctor ID provided but doctor not found.") 

        # 2. Sale Logic (Complex checks in the Facade service)
        try:
            new_sale = facade.process_sale(
                client_id=data['client_id'],
                doctor_id=data.get('doctor_id'),
                items_data=data['items'],
                user_id=current_user_id
            )
        except ValueError as e:
            # Captures errors for insufficient stock or missing prescription raised by Facade
            sales_ns.abort(400, message=str(e))
        except Exception:
            sales_ns.abort(500, message="Sale processing failed due to internal error.") 

        if new_sale is None:
             sales_ns.abort(500, message="Sale creation failed after processing.") 
             
        return new_sale, 201 

# --- SECURE RESOURCE 2: Single Sale Item by UUID (GET, DELETE) ---

@sales_ns.route('/<string:sale_id>')
@sales_ns.param('sale_id', 'The unique sale identifier (UUID)')
class SaleItem(Resource):
    
    @sales_ns.doc('get_sale_by_id')
    @sales_ns.marshal_with(sale_output_model)
    @jwt_required()
    def get(self, sale_id):
        """Retrieves a sale transaction by ID (UUID)."""
        sale = facade.get_sale_by_id(sale_id)
        if not sale:
            sales_ns.abort(404, message="Sale transaction not found.")
        return sale, 200


    @sales_ns.doc('delete_sale')
    @sales_ns.response(204, 'Sale successfully deleted (and stock reverted).')
    @sales_ns.response(403, 'Access Forbidden: Admin privileges required.')
    @jwt_required()
    def delete(self, sale_id):
        """
        Deletes a sale transaction and reverts stock. Restricted to administrators only.
        """
        # 1. Admin privilege check
        if not get_jwt().get('is_admin'):
            sales_ns.abort(403, message="Access Forbidden. Only administrators can delete sales.") 
            
        try:
            if not facade.delete_sale(sale_id):
                sales_ns.abort(404, message="Sale transaction not found.") 
        except Exception as e:
            sales_ns.abort(500, message=f"Deletion failed or stock could not be reverted: {str(e)}") 

        return '', 204