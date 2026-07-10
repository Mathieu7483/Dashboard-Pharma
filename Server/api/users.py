from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from email_validator import validate_email, EmailNotValidError
from services.facade import FacadeService
from utils.decorator import admin_required

# --- INITIALIZATION ---

facade = FacadeService()
users_ns = Namespace('users', description="Employee account management (Admin required for all CUD)")

# --- DATA MODELS ---

user_input_model = users_ns.model('UserInput', {
    'username': fields.String(required=True, description='The unique username (login)'),
    'password': fields.String(required=True, description='The user password (min 6 chars)'),
    'email': fields.String(required=True, description='The user email address (required, must be valid format)'),
    'first_name': fields.String(description='The user first name'),
    'last_name': fields.String(description='The user last name'),
})

user_update_model = users_ns.model('UserUpdate', {
    'email': fields.String(description='The user email address'),
    'first_name': fields.String(description='The user first name'),
    'last_name': fields.String(description='The user last name'),
    'password': fields.String(description='New password (optional)'),
    'is_admin': fields.Boolean(description='Administrative privileges (Admin only field)')
})

user_output_model = users_ns.model('UserOutput', {
    'id': fields.String(readOnly=True, description='The unique user identifier'),
    'username': fields.String(description='The unique username'),
    'email': fields.String(description='The user email address'),
    'first_name': fields.String(description='The user first name'),
    'last_name': fields.String(description='The user last name'),
    'is_admin': fields.Boolean(description='Administrative privileges status'),
    'created_at': fields.DateTime(description='Account creation timestamp')
})


# --- HELPER ---

def validate_and_normalize_email(email, required=True):
    """
    Validates an email's format (RFC compliant) and returns the normalized version.
    Aborts the request with a 400 error if invalid or missing (when required).
    Returns None if email is empty and not required.
    """
    if not email:
        if required:
            users_ns.abort(400, message="Email is required.")
        return None

    try:
        valid = validate_email(email, check_deliverability=False)
        return valid.normalized
    except EmailNotValidError as e:
        users_ns.abort(400, message=f"Invalid email: {str(e)}")


# --- RESOURCE: User List ---

@users_ns.route('/')
class UserList(Resource):

    @users_ns.doc('get_all_users')
    @jwt_required()
    @admin_required()
    @users_ns.marshal_list_with(user_output_model)
    def get(self):
        """
        Retrieves the list of all employees. Admin access required.
        """
        try:
            users = facade.get_all_users()
            print(f"✅ DEBUG: Loaded {len(users)} users")
            for u in users:
                print(f"  - {u.username}: is_admin={u.is_admin}")
            return users, 200
        except Exception as e:
            print(f"❌ ERROR in get_all_users: {e}")
            users_ns.abort(500, message=f"Internal error: {str(e)}")

    @users_ns.doc('create_new_user')
    @jwt_required()
    @admin_required()
    @users_ns.expect(user_input_model)
    @users_ns.marshal_with(user_output_model, code=201)
    def post(self):
        """
        Registers a new employee account. Admin only.
        Email is mandatory and must be a valid format.
        """
        data = users_ns.payload

        # --- Email: mandatory + format validation + normalization ---
        email = validate_and_normalize_email(data.get('email'), required=True)

        # --- Uniqueness checks ---
        if facade.get_user_by_username(data['username']):
            users_ns.abort(400, message=f"Username '{data['username']}' already exists.")

        if facade.get_user_by_email(email):
            users_ns.abort(400, message="Email already in use.")

        try:
            new_user = facade.create_user(
                username=data['username'],
                password=data['password'],
                email=email,
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                is_admin=data.get('is_admin', False)
            )

            if isinstance(new_user, str):
                users_ns.abort(400, message=new_user)

            if not new_user:
                users_ns.abort(500, message="User creation failed.")

            return new_user, 201

        except Exception as e:
            print(f"❌ User creation error: {e}")
            users_ns.abort(500, message=str(e))


# --- RESOURCE: Single User ---

@users_ns.route('/<string:user_id>')
@users_ns.param('user_id', 'The unique user identifier (UUID)')
class UserItem(Resource):

    @users_ns.doc('get_user_by_id')
    @jwt_required()
    @users_ns.marshal_with(user_output_model)
    def get(self, user_id):
        """Get user by ID. Self or Admin only."""
        current_user_id = get_jwt_identity()
        is_admin = get_jwt().get('is_admin')

        if current_user_id != user_id and not is_admin:
            users_ns.abort(403, message="Cannot view other user accounts.")

        user = facade.get_user_by_id(user_id)
        if not user:
            users_ns.abort(404, message="User not found.")
        return user, 200

    @users_ns.doc('update_user')
    @jwt_required()
    @users_ns.expect(user_update_model)
    @users_ns.marshal_with(user_output_model)
    def put(self, user_id):
        """Update user. Self or Admin only."""
        current_user_id = get_jwt_identity()
        is_admin = get_jwt().get('is_admin')
        data = users_ns.payload

        if current_user_id != user_id and not is_admin:
            users_ns.abort(403, message="Can only update own account unless admin.")

        if 'is_admin' in data and not is_admin:
            users_ns.abort(403, message="Only admins can modify is_admin status.")

        # --- Email: optional on update, but if provided it must be valid ---
        if 'email' in data:
            email = validate_and_normalize_email(data.get('email'), required=True)

            existing = facade.get_user_by_email(email)
            if existing and existing.id != user_id:
                users_ns.abort(400, message="Email already in use.")

            data['email'] = email

        user = facade.get_user_by_id(user_id)
        if not user:
            users_ns.abort(404, message="User not found.")

        updated_user = facade.update_user(user_id, data)
        if not updated_user:
            users_ns.abort(400, message="Update failed.")

        return updated_user, 200

    @users_ns.doc('delete_user')
    @jwt_required()
    @admin_required()
    @users_ns.response(204, 'User deleted')
    def delete(self, user_id):
        """Delete user. Admin only. Cannot delete self."""
        current_user_id = get_jwt_identity()

        if current_user_id == user_id:
            users_ns.abort(400, message="Cannot delete your own account.")

        if not facade.delete_user(user_id):
            users_ns.abort(404, message="User not found.")

        return '', 204