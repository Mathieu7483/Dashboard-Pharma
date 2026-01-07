from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity 
from flask import request
from services.facade import FacadeService 

facade = FacadeService()
clients_ns = Namespace('clients', description="Client management operations")

# --- DATA MODELS ---

client_input_model = clients_ns.model('clientInput', {
    'first_name': fields.String(required=True, description='Client first name'),
    'last_name': fields.String(required=True, description='Client last name'),
    'email': fields.String(required=True, description='Client email address'),
    'phone': fields.String(description='Contact phone number'),
    'address': fields.String(description='Home address')
})

client_output_model = clients_ns.model('clientOutput', {
    'id': fields.String(readOnly=True),
    'first_name': fields.String(),
    'last_name': fields.String(),
    'email': fields.String(),
    'phone': fields.String(),
    'address': fields.String()
})

# --- ROUTES ---

@clients_ns.route('/')
class ClientList(Resource):
    @clients_ns.marshal_list_with(client_output_model)
    @jwt_required() 
    def get(self):
        """Fetch all registered clients"""
        return facade.get_all_clients(), 200

    @clients_ns.expect(client_input_model, validate=True)
    @clients_ns.marshal_with(client_output_model, code=201)
    @jwt_required()
    def post(self):
        """Register a new client"""
        current_user_id = get_jwt_identity()
        data = clients_ns.payload
        new_client = facade.create_client(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data.get('phone'),
            address=data.get('address'),
            user_id=current_user_id
        )
        return new_client or clients_ns.abort(400, "Client registration failed")

@clients_ns.route('/search')
class ClientSearch(Resource):
    @clients_ns.marshal_list_with(client_output_model)
    @jwt_required()
    def get(self):
        """Search clients by name or email: /clients/search?q=Dupont"""
        query = request.args.get('q', '')
        if not query:
            return [], 200
        
        results = facade.search_clients(query)
        return results, 200

@clients_ns.route('/<string:client_id>')
class ClientItem(Resource):
    @clients_ns.marshal_with(client_output_model)
    @jwt_required()
    def get(self, client_id):
        """Get specific client details"""
        client = facade.get_client_by_id(client_id)
        return client or clients_ns.abort(404, "Client not found")

    @clients_ns.expect(client_input_model)
    @clients_ns.marshal_with(client_output_model)
    @jwt_required()
    def put(self, client_id):
        """Update client information"""
        data = clients_ns.payload
        updated_client = facade.update_client(client_id, data)
        return updated_client or clients_ns.abort(400, "Update failed")

    @jwt_required()
    def delete(self, client_id):
        """Delete a client (Admin only)"""
        claims = get_jwt()
        if not claims.get('is_admin'):
            clients_ns.abort(403, "Admin access required")
        
        if facade.delete_client(client_id):
            return '', 204
        clients_ns.abort(404, "Client not found")