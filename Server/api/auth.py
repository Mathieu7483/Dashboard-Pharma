<<<<<<< HEAD
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
=======
from flask_restx import Namespace, Resource
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from services.facade import FacadeService


# Instantiate the Facade Service (Decoupling)
facade = FacadeService()
auth_ns = Namespace('auth', description='Authentication operations')

# --- Data Models (Marshaling/Swagger Documentation) ---

register_model = auth_ns.model('Register', {
    'username': auth_ns.fields.String(required=True, description='The user username'),
    'password': auth_ns.fields.String(required=True, description='The user password'),
    'email': auth_ns.fields.String(required=True, description='The user email')
})

login_model = auth_ns.model('Login', {
    'username': auth_ns.fields.String(required=True, description='The user username'),
    'password': auth_ns.fields.String(required=True, description='The user password')
})  

login_response_model = auth_ns.model('LoginResponse', {
    'access_token': auth_ns.fields.String(description='JWT Access Token'),
    'message': auth_ns.fields.String(description='Success message'),
    'user_id': auth_ns.fields.Integer(description='ID of the authenticated user')
})
success_model = auth_ns.model('Success', {
    'message': auth_ns.fields.String(description='Success message'),
    'access_token': auth_ns.fields.String(description='JWT Access Token'),
    'user_id': auth_ns.fields.Integer(description='ID of the authenticated user')
})

# --------------------------------------------------------------------------
# Resource 1: User Registration
# --------------------------------------------------------------------------

@auth_ns.route('/register')
class UserRegister(Resource): 
    # Document input and output models
    @auth_ns.expect(register_model)
    @auth_ns.marshal_with(success_model, code=201)
    def post(self):
        """Register a new user (via Facade)."""
        data = auth_ns.payload
        
        # Check if user already exists using the Facade
        if facade.get_user_by_username(data['username']):
            auth_ns.abort(400, 'User already exists')
        
        # Create user via Facade (Facade handles hashing and DB saving - Decoupling)
        new_user = facade.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
        
        # Note: If you want to return a token on registration, you'd generate it here.
        # For simplicity, we only return the success message and ID.
        
        return {'message': 'User created successfully', 'user_id': new_user.id}, 201
    
# --------------------------------------------------------------------------
# Resource 2: User Login
# --------------------------------------------------------------------------

@auth_ns.route('/login')
class UserLogin(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.marshal_with(login_response_model)
    def post(self):
        """Authenticate user and return JWT token."""
        data = auth_ns.payload
        
        # Retrieve user via Facade (Decoupling)
        user = facade.get_user_by_username(data['username'])
        
        # Check if user exists AND if password is correct (Bcrypt check on the model instance)
        if user and user.check_password(data['password']):
            
            # 1. Define Additional Claims (e.g., Role-Based Access Control)
            claims = {
                'is_admin': user.is_admin # Get role from the UserModel instance
            }
            
            # 2. Correctly call the function provided by Flask-JWT-Extended
            access_token = create_access_token(
                identity=user.id,
                additional_claims=claims
            )
            
            return {
                'access_token': access_token,
                'message': 'Login successful',
                'user_id': user.id
            }, 200
        
        # Abort if authentication fails
        auth_ns.abort(401, 'Invalid credentials')
>>>>>>> main
