from functools import wraps
from flask import request, jsonify
import firebase_admin
from firebase_admin import auth, credentials, exceptions as firebase_exceptions
import os
import json
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# This module is imported transitively by app.py's blueprint imports, which run
# before app.py calls load_dotenv(). Load it here so a .env-supplied key is
# actually visible.
load_dotenv()

key_string = os.getenv('FIREBASE_ADMIN_SDK_KEY')
if not key_string:
    raise RuntimeError(
        "FIREBASE_ADMIN_SDK_KEY is not set. The API cannot verify auth tokens "
        "without it. Set it in the environment or .env before starting."
    )

try:
    key = json.loads(key_string)
except json.JSONDecodeError as e:
    logger.error("FIREBASE_ADMIN_SDK_KEY is not valid JSON (position %d): %s", e.pos, e.msg)
    raise

cred = credentials.Certificate(key)
default_app = firebase_admin.initialize_app(cred)

def verify_id_token(id_token):
    """Resolve a Firebase ID token to a uid.

    Returns None when the token is genuinely bad (malformed, expired, revoked,
    disabled user) so the caller can answer 401.

    Raises FirebaseError when Firebase itself could not be consulted -- most
    often CertificateFetchError, a transient failure fetching Google's signing
    certs. That is a 503, not a 401: the token may well be fine.

    Note: in firebase-admin 6.x none of these exceptions subclass ValueError,
    so the old `except ValueError` caught none of them and every expired token
    surfaced as a 500.
    """
    try:
        # check_revoked=True is what actually makes RevokedIdTokenError and
        # UserDisabledError reachable. With the default (False) a signed-out or
        # disabled user's token stays valid until it expires on its own, and the
        # handler below is dead code. Costs one Firebase lookup per request.
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        return decoded_token['uid']
    except (auth.InvalidIdTokenError, auth.UserDisabledError, ValueError):
        # InvalidIdTokenError covers ExpiredIdTokenError and RevokedIdTokenError.
        # Bare ValueError is raised for a non-string token argument.
        return None
    except firebase_exceptions.FirebaseError:
        logger.error("Firebase could not verify the token", exc_info=True)
        raise

def require_auth(f):
    """
    Decorator function that requires authentication for the decorated function.
    
    Args:
        f (function): The function to be decorated.
        
    Returns:
        function: The decorated function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        # checks the validity of the auth header
        if not auth_header or ' ' not in auth_header:
            return jsonify({'error': 'Invalid authorization header'}), 401

        # Split on first space only
        parts = auth_header.split(' ', 1)
        if len(parts) != 2:
            return jsonify({'error': 'Invalid authorization header format'}), 401
            
        bearer, id_token = parts
        
        if bearer.lower() != 'bearer':
            return jsonify({'error': 'Invalid authorization header'}), 401
            
        try:
            uid = verify_id_token(id_token)
        except firebase_exceptions.FirebaseError:
            return jsonify({'error': 'Authentication temporarily unavailable'}), 503

        if uid is None:
            return jsonify({'error': 'Invalid token'}), 401
            
        return f(uid, *args, **kwargs)
    
    return decorated