from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import create_access_token
from services.facade import FacadeService 
from datetime import timedelta

# --- INITIALIZATION ---

facade = FacadeService()
auth_ns = Namespace('auth', description="User authentication and token management")

# --- DATA MODELS ---

login_input_model = auth_ns.model('LoginInput', {
    'username': fields.String(required=True, description='The employee username'),
    'password': fields.String(required=True, description='The employee password')
})

register_input_model = auth_ns.model('RegisterInput', {
    'username': fields.String(required=True, description='The new username'),
    'email': fields.String(required=True, description='The new user email'),
    'password': fields.String(required=True, description='The new user password')
})

token_output_model = auth_ns.model('TokenOutput', {
    'access_token': fields.String(description='JWT access token for API requests'),
    'token_type': fields.String(default='Bearer', description='Type of the token'),
    'expires_in_seconds': fields.Integer(description='Access token validity duration'),
    'user_id': fields.String(description='The authenticated user ID'),
    'is_admin': fields.Boolean(description='User administrative status')
})

# --- RESOURCE 1: Login ---

@auth_ns.route('/login')
class UserLogin(Resource):
    
    @auth_ns.doc('user_login')
    @auth_ns.expect(login_input_model)
    @auth_ns.marshal_with(token_output_model, code=200)
    @auth_ns.response(400, 'Missing Username or Password')
    @auth_ns.response(401, 'Invalid Credentials')
    def post(self):
        """
        Authenticates a user and returns a JWT access token.
        """
        data = auth_ns.payload
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            auth_ns.abort(400, message="Username and password are required")
        
        # 1. Authenticate user via Facade service
        user = facade.authenticate_user(username, password)
        
        if not user:
            auth_ns.abort(401, message="Invalid Credentials: Username or password is wrong.")

        # 2. Create Token
        access_expires = timedelta(minutes=15)
        additional_claims = {
            'is_admin': user.is_admin,
            'user_id': user.id
        }
        
        access_token = create_access_token(
            identity=user.id, 
            additional_claims=additional_claims, 
            expires_delta=access_expires
        )
        
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in_seconds': access_expires.total_seconds(),
            'user_id': user.id,
            'is_admin': user.is_admin
        }, 200

# --- RESOURCE 2: Registration ---

@auth_ns.route('/register')
class UserRegister(Resource):
    
    @auth_ns.doc('user_register')
    @auth_ns.expect(register_input_model)
    @auth_ns.response(201, 'User created successfully')
    @auth_ns.response(400, 'Invalid Input')
    @auth_ns.response(409, 'Username or Email already exists')
    def post(self):
        """Register a new user (Employee by default)."""
        data = auth_ns.payload
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            auth_ns.abort(400, "Username, email, and password are required")

        result = facade.create_user(
            username=username,
            email=email,
            password=password,
            is_admin=False
        )
        
        if isinstance(result, str):
            auth_ns.abort(409, message=result)
            return
        
        if result is None:
            auth_ns.abort(500, message="Registration failed")
            return
        
        # Succès
        return {'message': 'User created successfully', 'user_id': str(result.id)}, 201