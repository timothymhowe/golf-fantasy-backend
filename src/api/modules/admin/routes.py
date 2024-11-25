from flask import Blueprint

health_bp = Blueprint('health', __name__)

@health_bp.route('/')
def health_check():
    return {
        'status': 'healthy',
        'message': 'API is running'
    }, 200