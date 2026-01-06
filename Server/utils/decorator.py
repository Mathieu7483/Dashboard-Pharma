# File: Server/utils/decorator.py (Corrected Imports)

from functools import wraps
from flask_jwt_extended import get_jti, get_jwt
from flask_restx import abort

def admin_required():
    """
    Decorator to restrict access to an endpoint to only users with 'is_admin' set to True
    in their JWT claims.
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            # 1. Get the claims from the current JWT
            try:
                # Use get_jwt() for modern JWT handling
                claims = get_jwt() 
                is_admin = claims.get('is_admin', False)

                if is_admin is True:
                    # User is admin, proceed with the original function
                    return fn(*args, **kwargs)
                else:
                    # User is not admin, abort with 403 Forbidden
                    abort(403, message="Access Forbidden: Administrative privileges required.")
            
            except Exception as e:
                # Handle cases where JWT might be missing or invalid
                abort(401, message="Access Denied: Authentication token required or invalid.")
        return decorator
    return wrapper


#admin login : Mathieu
#admin password : Admin@1234