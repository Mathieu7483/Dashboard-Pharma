from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity 
from services.facade import FacadeService 

# --- INITIALIZATION ---
facade = FacadeService()
notes_ns = Namespace('notes', description="User notes management (User and Admin access)")
# --- DATA MODELS (WITH STRICT VALIDATION) ---
# Model for creating/updating a note (Input)
note_input_model = notes_ns.model('NoteInput', {
    'text': fields.String(required=True, description='Content of the note')
})
# Model for serialization and output of note data (Output)
note_output_model = notes_ns.model('NoteOutput', {
    'id': fields.String(description='The note UUID'),
    'text': fields.String(description='Content of the note'),
    'user_id': fields.String(description='UUID of the user who created the note'),
    'created_at': fields.DateTime(description='Timestamp when the note was created')
})
# --- SECURE RESOURCE 1: Note List (GET, POST) ---
@notes_ns.route('/')
class NoteList(Resource):
    
    @notes_ns.doc('get_all_notes')
    @notes_ns.marshal_list_with(note_output_model)
    @jwt_required()
    def get(self):
        """Get all notes for the authenticated user"""
        return facade.get_all_notes()
    
    @notes_ns.doc('create_note')
    @notes_ns.expect(note_input_model, validate=True)
    @notes_ns.marshal_with(note_output_model, code=201)
    @jwt_required()
    def post(self):
        """Create a new note for the authenticated user"""
        user_id = get_jwt_identity()
        data = notes_ns.payload
        
        new_note = facade.create_note(
            user_id=user_id, 
            text=data['text']
        )
        if not new_note:
            notes_ns.abort(400, "Failed to create note. Check the input data.")
        return new_note, 201
    
# --- SECURE RESOURCE 2: Single note (GET, PUT, DELETE) ---
@notes_ns.route('/<string:note_id>')
@notes_ns.param('note_id', 'The note identifier')
class NoteResource(Resource): 
    @notes_ns.doc('get_note')
    @notes_ns.marshal_with(note_output_model)
    @jwt_required()
    def get(self, note_id):
        """Get a specific note by ID (only if owned by the user)"""
        user_id = get_jwt_identity()
        note = facade.get_note_by_id(note_id)
        if not note or not note.is_owned_by(user_id):
            notes_ns.abort(404, "Note not found or access denied.")
        return note, 200
    
    @notes_ns.doc('update_note')
    @notes_ns.expect(note_input_model, validate=True)
    @notes_ns.marshal_with(note_output_model)
    @jwt_required()
    def put(self, note_id): 
        """Update a specific note by ID (only if owned by the user)"""
        user_id = get_jwt_identity()
        data = notes_ns.payload
        note = facade.get_note_by_id(note_id)
        if not note or not note.is_owned_by(user_id):
            notes_ns.abort(404, "Note not found or access denied.")
        
        updated_note = facade.update_note_text(note_id, data['text'])
        if not updated_note:
            notes_ns.abort(400, "Failed to update note. Check the input data.")
        return updated_note, 200
    
    @notes_ns.doc('delete_note')
    @jwt_required()
    def delete(self, note_id):
        """Delete a specific note by ID (only if owned by the user)"""
        user_id = get_jwt_identity()
        note = facade.get_note_by_id(note_id)
        if not note or not note.is_owned_by(user_id):
            notes_ns.abort(404, "Note not found or access denied.")
        
        facade.delete_note(note_id)
        return {'message': 'Note deleted successfully'}, 200
