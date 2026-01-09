from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity 
from flask import request
from services.facade import FacadeService
from utils.decorator import admin_required


facade = FacadeService()
doctors_ns = Namespace('doctors', description="Doctor management operations")

# --- DATA MODELS ---

# Input model for creation and updates
doctor_input_model = doctors_ns.model('doctorInput', {
    'first_name': fields.String(required=True, description='Doctor first name'),
    'last_name': fields.String(required=True, description='Doctor last name'),
    'email': fields.String(description='Doctor email address'),
    'address': fields.String(description='Doctor physical address'),
    'specialty': fields.String(description='Medical specialty'),
    'phone': fields.String(description='Contact phone number')
})

# Output model for API responses (Shared by Dashboard and Chatbot)
doctor_output_model = doctors_ns.model('doctorOutput', {
    'id': fields.String(readOnly=True),
    'first_name': fields.String(),
    'last_name': fields.String(),
    'email': fields.String(),
    'address': fields.String(),
    'specialty': fields.String(),
    'phone': fields.String()
})

# --- ROUTES ---

@doctors_ns.route('/')
class DoctorList(Resource):
    @doctors_ns.marshal_list_with(doctor_output_model)
    @jwt_required() 
    def get(self):
        """Fetch all registered doctors"""
        return facade.get_all_doctors(), 200

    @doctors_ns.expect(doctor_input_model, validate=True)
    @doctors_ns.marshal_with(doctor_output_model, code=201)
    @jwt_required()
    def post(self):
        """Register a new doctor"""
        current_user_id = get_jwt_identity()
        data = doctors_ns.payload
        new_doctor = facade.create_doctor(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data.get('email'),
            address=data.get('address'),
            specialty=data.get('specialty'),
            phone=data.get('phone'),
            user_id=current_user_id
        )
        return new_doctor or doctors_ns.abort(400, "Doctor registration failed")

@doctors_ns.route('/search')
class DoctorSearch(Resource):
    @doctors_ns.marshal_list_with(doctor_output_model)
    @jwt_required()
    def get(self):
        """
        Search doctors using a query parameter: /doctors/search?q=Smith
        Returns full profiles to satisfy both Dashboard and Chatbot requirements.
        """
        query = request.args.get('q', '')
        if not query: 
            return [], 200
            
        # Fetches list of DoctorModel objects from Facade
        results = facade.search_doctors(query)
        
        # marshal_list_with handles the conversion of objects to the dictionary structure
        return results, 200

@doctors_ns.route('/<string:doctor_id>')
class DoctorItem(Resource):
    @doctors_ns.marshal_with(doctor_output_model)
    @jwt_required()
    def get(self, doctor_id):
        """Get a specific doctor by UUID"""
        doctor = facade.get_doctor_by_id(doctor_id)
        return doctor or doctors_ns.abort(404, "Doctor not found")

    @doctors_ns.expect(doctor_input_model)
    @doctors_ns.marshal_with(doctor_output_model)
    @jwt_required()
    def put(self, doctor_id):
        """Update doctor details (Admin or Owner)"""
        data = doctors_ns.payload
        updated_doctor = facade.update_doctor(doctor_id, data)
        return updated_doctor or doctors_ns.abort(400, "Update failed")

    @jwt_required()
    @admin_required()
    def delete(self, doctor_id):
        """Delete a doctor record (Admin only)"""
        claims = get_jwt()
        if not claims.get('is_admin'):
            doctors_ns.abort(403, "Administrator privileges required")
            
        if facade.delete_doctor(doctor_id):
            return '', 204
        doctors_ns.abort(404, "Doctor not found")