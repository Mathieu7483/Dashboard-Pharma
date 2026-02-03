from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity 
from services.facade import FacadeService 

# --- INITIALIZATION ---
facade = FacadeService()
tickets_ns = Namespace('tickets', description="Support ticket management (User and Admin access)")
# --- DATA MODELS (WITH STRICT VALIDATION) ---
# Model for creating a new ticket (Input)
ticket_input_model = tickets_ns.model('TicketInput', {
    'subject': fields.String(required=True, description='Subject', max_length=100),
    'description': fields.String(required=True, description='Detailed description'),
    'priority': fields.String(description='Priority level', enum=['low', 'medium', 'high'], default='medium')
})
# Model for serialization and output of ticket data (Output)
ticket_output_model = tickets_ns.model('TicketOutput', {
    'id': fields.Integer(readOnly=True, description='The unique ticket identifier'),
    'subject': fields.String(description='Subject of the support ticket', max_length=100),
    'description': fields.String(description='Detailed description of the issue'),
    'priority': fields.String(description='Priority level of the ticket', enum=['low', 'medium', 'high']),
    'status': fields.String(description='Current status of the ticket', enum=['open', 'in_progress', 'closed']),
    'user_id': fields.Integer(description='ID of the user who created the ticket'),
    'created_at': fields.DateTime(description='Timestamp when the ticket was created'),
    'admin_note': fields.String(description='Notes added by admin to the ticket', nullable=True)
})
# Model for admin updating ticket (Input)
ticket_admin_update_model = tickets_ns.model('TicketAdminUpdate', {
    'status': fields.String(description='Status', enum=['open', 'in_progress', 'closed']),
    'admin_note': fields.String(description='Note from admin')
})
# --- SECURE RESOURCE 1: Ticket List (GET, POST) ---
@tickets_ns.route('/')
class TicketList(Resource):
    
    @tickets_ns.doc('get_all_tickets')
    @tickets_ns.marshal_list_with(ticket_output_model)
    @jwt_required()
    def get(self):
        """Get all tickets (Admin only)"""
        claims = get_jwt()
        if not claims.get('is_admin'):
            tickets_ns.abort(403, "Admin access required to view all tickets.")
        return facade.get_all_tickets()
    
    @tickets_ns.doc('create_ticket')
    @tickets_ns.expect(ticket_input_model, validate=True)
    @tickets_ns.marshal_with(ticket_output_model, code=201)
    @jwt_required()
    def post(self):
        """Create a new support ticket"""
        user_id = get_jwt_identity()
        data = tickets_ns.payload
        
        return facade.create_ticket(
            user_id=user_id, 
            subject=data['subject'], 
            description=data['description'],
            priority=data.get('priority', 'medium')
        ), 201
# --- SECURE RESOURCE 2: Single Ticket (GET, PUT, DELETE) ---
@tickets_ns.route('/<int:ticket_id>')
@tickets_ns.param('ticket_id', 'The ticket identifier')
class TicketResource(Resource):
    
    @tickets_ns.doc('get_ticket')
    @tickets_ns.marshal_with(ticket_output_model)
    @jwt_required()
    def get(self, ticket_id):
        """Get a ticket by ID (User can access own tickets; Admin can access all)"""
        user_id = get_jwt_identity()
        claims = get_jwt()
        ticket = facade.get_ticket_by_id(ticket_id)
        if not ticket:
            tickets_ns.abort(404, "Ticket not found.")
        if ticket.user_id != user_id and not claims.get('is_admin'):
            tickets_ns.abort(403, "Access denied to this ticket.")
        return ticket
    
    @tickets_ns.doc('update_ticket')
    @tickets_ns.expect(ticket_output_model)
    @tickets_ns.marshal_with(ticket_output_model)
    @jwt_required()
    def put(self, ticket_id):
        """Update a ticket (User: subject/desc; Admin: all fields)"""
        user_id = get_jwt_identity()
        claims = get_jwt()
        
        ticket = facade.get_ticket_by_id(ticket_id)
        if not ticket:
            tickets_ns.abort(404, "Ticket not found.")
        
        # Security check: only owner or admin can update
        if ticket.user_id != user_id and not claims.get('is_admin'):
            tickets_ns.abort(403, "Access denied to update this ticket.")
        
        data = tickets_ns.payload
        
        # Security Layer: Prevent standard users from updating admin fields
        if not claims.get('is_admin'):
            data.pop('status', None)
            data.pop('admin_note', None)
            data.pop('priority', None)

        updated_ticket = facade.update_ticket(ticket_id=ticket_id, data=data)
        
        if not updated_ticket:
            tickets_ns.abort(400, "Update failed.")
            
        return updated_ticket
    
    @tickets_ns.doc('delete_ticket')
    @jwt_required()
    def delete(self, ticket_id):
        """Delete a ticket (Admin only)"""
        claims = get_jwt()
        if not claims.get('is_admin'):
            tickets_ns.abort(403, "Admin access required to delete tickets.")
        success = facade.delete_ticket(ticket_id)
        if not success:
            tickets_ns.abort(404, "Ticket not found.")
        return {'message': 'Ticket deleted successfully.'}, 200
  