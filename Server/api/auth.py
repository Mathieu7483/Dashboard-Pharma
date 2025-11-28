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