from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity
from flask_restx import abort

def admin_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            print(f"DEBUG - User: {get_jwt_identity()} - Is Admin: {claims.get('is_admin')}")
            if claims.get('is_admin') is True:
                return fn(*args, **kwargs)
            abort(403, message="Access Forbidden: Administrative privileges required.")
        return decorator
    return wrapper


#admin login : Mathieu
#admin password : Admin@1234