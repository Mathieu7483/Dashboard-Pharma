from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from flask_restx import abort

def admin_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get('is_admin') is True:
                return fn(*args, **kwargs)
            abort(403, message="Access Forbidden: Administrative privileges required.")
        return decorator
    return wrapper
