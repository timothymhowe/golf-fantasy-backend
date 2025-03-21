from flask import Blueprint
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from utils.db_connector import db, init_db

health_bp = Blueprint('health', __name__)

@health_bp.route('/')
def health_check():
    return {
        'status': 'healthy',
        'message': 'API is running'
    }, 200

@health_bp.route('/db-health')
def db_health_check():
    try:
        # Use text() to properly format the SQL query
        result = db.session.execute(text('SELECT 1'))
        result.fetchone()
        
        return {
            'status': 'healthy',
            'message': 'Database connection successful',
            'database': 'connected'
        }, 200
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': 'Database connection failed',
            'error': str(e)
        }, 500
    
    
    