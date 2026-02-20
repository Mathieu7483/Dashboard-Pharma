# File: Server/utils/decorator.py (Corrected Imports)

from functools import wraps
from flask_jwt_extended import get_jti, get_jwt, get_jwt_identity
from flask_restx import abort

def admin_required():
    """
    Decorator to restrict access to an endpoint to only users with 'is_admin' set to True
    in their JWT claims.
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            claims = get_jwt()
            print(f"DEBUG - User: {get_jwt_identity()} - Is Admin Claim: {claims.get('is_admin')}")
            if claims.get('is_admin') is True:
                return fn(*args, **kwargs)
            
            abort(403, message="Access Forbidden: Administrative privileges required.")
        return decorator
    return wrapper


#admin login : Mathieu
#admin password : Admin@1234