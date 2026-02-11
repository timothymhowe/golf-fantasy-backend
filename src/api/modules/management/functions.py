from models import User, db
import logging

logger = logging.getLogger(__name__)

def create_user_in_db(uid: str, data: dict) -> tuple[dict, int]:
    """System management function to create a new user in the database
    
    Args:
        uid (str): Firebase UID from auth token
        data (dict): User data from request
            Required fields:
            - email (str)
            - firebase_id (str)
            Optional fields:
            - display_name (str)
            - first_name (str)
            - last_name (str)
            - avatar_url (str)
    
    Returns:
        tuple: (response_dict, status_code)
    """
    try:
        # Validate required fields
        required_fields = ['email', 'firebase_id']
        for field in required_fields:
            if not data.get(field):
                logger.warning(f"Missing required field: {field}")
                return {'error': f"Missing required field: {field}"}, 400
                
        # Verify Firebase UID matches the token
        if data['firebase_id'] != uid:
            logger.warning("Firebase UID mismatch")
            return {'error': 'Firebase UID mismatch'}, 403

        # Check if user already exists
        existing_user = User.query.filter_by(firebase_id=uid).first()
        if existing_user:
            logger.info(f"User already exists with Firebase ID: {uid}")
            return {
                'message': 'User already exists',
                'user_id': existing_user.id
            }, 200
            
        # Create new user
        new_user = User(
            firebase_id=uid,
            email=data['email'],
            display_name=data.get('display_name') or data['email'].split('@')[0],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            avatar_url=data.get('avatar_url')
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"Created new user with ID: {new_user.id}")
        return {
            'message': 'User created successfully',
            'user_id': new_user.id
        }, 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating user: {str(e)}", exc_info=True)
        return {'error': 'Internal server error'}, 500
