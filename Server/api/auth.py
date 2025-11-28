from flask_restx import Namespace, Resource
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from datetime import timedelta
from services import facade

auth_ns = Namespace('auth', description='Authentication operations')

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

@auth_ns.route('/register')
class UserRegister(Resource): 
    @auth_ns.expect(register_model)
    @auth_ns.marshal_with(success_model, code=201)
    def post(self):
        data = auth_ns.payload
        if UserModel.find_by_username(data['username']):
            auth_ns.abort(400, 'User already exists')
        
        new_user = UserModel(
            username=data['username'],
            email=data['email']
        )
        new_user.set_password(data['password'])
        new_user.save_to_db()
        
        return {'message': 'User created successfully', 'user_id': new_user.id}, 201
    
@auth_ns.route('/login')
class UserLogin(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.marshal_with(login_response_model)
    def post(self):
        data = auth_ns.payload
        user = UserModel.find_by_username(data['username'])
        
        if user and user.check_password(data['password']):
            claims = {
                'is_admin': user.is_admin
            }
            from database.data_manager import create_access_token
            access_token = create_access_token(
                identity=user.id,
                additional_claims=claims)
            return {
                'access_token': access_token,
                'message': 'Login successful',
                'user_id': user.id
            }, 200
        
        auth_ns.abort(401, 'Invalid credentials')

