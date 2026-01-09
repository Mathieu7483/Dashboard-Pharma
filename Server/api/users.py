from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity 
from services.facade import FacadeService 
from utils.decorator import admin_required

# --- INITIALIZATION ---

facade = FacadeService()
users_ns = Namespace('users', description="Employee account management (Admin required for all CUD)")

# --- DATA MODELS ---

# Model for user input (Registration/Update)
user_input_model = users_ns.model('UserInput', {
    'username': fields.String(required=True, description='The unique username (login)'),
    'password': fields.String(required=True, description='The user password (min 6 chars)'),
    'email': fields.String(description='The user email address'),
    'first_name': fields.String(description='The user first name'),
    'last_name': fields.String(description='The user last name'),
    # Note: is_admin is excluded from input model to prevent unauthorized self-promotion
})

# Model for updating user details (without password and username)
user_update_model = users_ns.model('UserUpdate', {
    'email': fields.String(description='The user email address'),
    'first_name': fields.String(description='The user first name'),
    'last_name': fields.String(description='The user last name'),
    'is_admin': fields.Boolean(description='Administrative privileges (Admin only field)')
})


# Model for serialization and output of user data
user_output_model = users_ns.model('UserOutput', {
    'id': fields.String(readOnly=True, description='The unique user identifier'),
    'username': fields.String(description='The unique username'),
    'email': fields.String(description='The user email address'),
    'first_name': fields.String(description='The user first name'),
    'last_name': fields.String(description='The user last name'),
    'is_admin': fields.Boolean(description='Administrative privileges status'),
    'created_at': fields.DateTime(description='Account creation timestamp')
})

# --- SECURE RESOURCE 1: User List (GET, POST) ---

@users_ns.route('/')
class UserList(Resource):
    
    @users_ns.doc('get_all_users')
    @users_ns.marshal_list_with(user_output_model)
    @jwt_required() 
    @admin_required()
    @users_ns.marshal_list_with(user_output_model)
    def get(self):
        """
        Retrieves the list of all employees. Accessible to all authenticated users.
        """
        return facade.get_all_users(), 200

    @users_ns.doc('create_new_user')
    @users_ns.expect(user_input_model)
    @users_ns.marshal_with(user_output_model, code=201)
    @users_ns.response(403, 'Access Forbidden: Admin privileges required.')
    @jwt_required()
    def post(self):
        """
        Registers a new employee account. Restricted to administrators only.
        """
        # 1. Admin privilege check
        if not get_jwt().get('is_admin'):
            users_ns.abort(403, message="Access Forbidden. Only administrators can create new users.")
            
        data = users_ns.payload
        
        # 2. Check for uniqueness
        if facade.get_user_by_username(data['username']):
            users_ns.abort(400, message=f"User with username '{data['username']}' already exists.")
            
        # 3. Create the user (non-admin by default)
        try:
            new_user = facade.create_user(
                username=data['username'],
                password=data['password'],
                email=data.get('email'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                is_admin=False # Default to False upon creation
            )
        except Exception:
            users_ns.abort(500, message="User creation failed due to internal error.")


        return new_user, 201

# --- SECURE RESOURCE 2: Single User Item by UUID ---

@users_ns.route('/<string:user_id>')
@users_ns.param('user_id', 'The unique user identifier (UUID)')
class UserItem(Resource):
    
    @users_ns.doc('get_user_by_id')
    @users_ns.marshal_with(user_output_model)
    @jwt_required()
    def get(self, user_id):
        """
        Retrieves a user by ID. Accessible to the user themselves or administrators.
        """
        current_user_id = get_jwt_identity()
        is_admin = get_jwt().get('is_admin')

        # Check if the user is asking for their own profile or is an admin
        if current_user_id != user_id and not is_admin:
            users_ns.abort(403, message="Access Forbidden. Cannot view other user accounts.")
            
        user = facade.get_user_by_id(user_id)
        if not user:
            users_ns.abort(404, message="User not found.")
        return user, 200

    @users_ns.doc('update_user')
    @users_ns.expect(user_update_model)
    @users_ns.marshal_with(user_output_model)
    @users_ns.response(403, 'Access Forbidden: Only admin can modify accounts, or self-modification.')
    @jwt_required()
    def put(self, user_id):
        """
        Updates an existing user. Restricted to the user themselves or administrators.
        Admins can modify the 'is_admin' field.
        """
        current_user_id = get_jwt_identity()
        is_admin = get_jwt().get('is_admin')
        data = users_ns.payload
        
        # 1. Authorization check
        if current_user_id != user_id and not is_admin:
            users_ns.abort(403, message="Access Forbidden. You can only update your own account unless you are an administrator.")
        
        # 2. Security check for 'is_admin' field
        if 'is_admin' in data and not is_admin:
            users_ns.abort(403, message="Access Forbidden. Only administrators can modify 'is_admin' status.")
        
        user = facade.get_user_by_id(user_id)
        if not user:
            users_ns.abort(404, message="User not found.")
            
        updated_user = facade.update_user(user_id, data)

        if not updated_user:
            users_ns.abort(400, message="Update failed. Check data or internal error.")

        return updated_user, 200

    @users_ns.doc('delete_user')
    @users_ns.response(204, 'User successfully deleted.')
    @users_ns.response(403, 'Access Forbidden: Admin privileges required.')
    @jwt_required()
    def delete(self, user_id):
        """
        Deletes a user. Restricted to administrators only. Cannot delete self.
        """
        current_user_id = get_jwt_identity()
        
        # 1. Authorization check: Must be admin and not deleting self
        if not get_jwt().get('is_admin'):
            users_ns.abort(403, message="Access Forbidden. Only administrators can delete users.")
            
        if current_user_id == user_id:
             users_ns.abort(400, message="Cannot delete your own active account.")
            
        if not facade.delete_user(user_id):
            users_ns.abort(404, message="User not found.")

        return '', 204