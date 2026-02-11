from functools import wraps
from flask import request, jsonify
import firebase_admin
from firebase_admin import auth, credentials
import os
import json
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Get the key string
key_string = os.getenv('FIREBASE_ADMIN_SDK_KEY')

try:
    key = json.loads(key_string)
except json.JSONDecodeError as e:
    logger.error("JSON Error at position %d: %s", e.pos, e.msg)
    raise

cred = credentials.Certificate(key)
default_app = firebase_admin.initialize_app(cred)

def verify_id_token(id_token):
    try:
        # Verify the ID token and extract the user's UID
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        return uid
    except ValueError:
        # The ID token is invalid
        return None

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
            
        uid = verify_id_token(id_token)
        
        if uid is None:
            return jsonify({'error': 'Invalid token'}), 401
            
        return f(uid, *args, **kwargs)
    
    return decorated