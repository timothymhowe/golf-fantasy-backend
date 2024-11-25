from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector, IPTypes
from google.cloud import firestore
import os
import sqlalchemy
import json
import tempfile
import logging

# Set up logging
logger = logging.getLogger(__name__)

def setup_credentials():
    """Setup Google credentials based on environment"""
    creds_env = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not creds_env:
        logger.warning("No Google credentials found in environment")
        return None
        
    try:
        # Check if it's a JSON string (production)
        json.loads(creds_env)
        logger.info("Found JSON credentials in environment")
        
        # Create temporary file for credentials
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(creds_env)
            temp_path = temp_file.name
            
        # Update environment to point to temp file
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_path
        logger.info("Successfully wrote credentials to temporary file")
        return temp_path
        
    except json.JSONDecodeError:
        # It's already a file path (development)
        logger.info("Using existing credentials file path")
        if os.path.exists(creds_env):
            logger.info("Credentials file exists")
            return creds_env
        else:
            logger.error(f"Credentials file not found at: {creds_env}")
            return None

# Initialize credentials before anything else
creds_path = setup_credentials()
logger.info(f"Using credentials from: {'temporary file' if creds_path else 'default'}")

load_dotenv()

def clean_env(var_name,default=None):
    value = os.getenv(var_name,default)
    return value.strip('"').strip("'").strip() if value else None

username = clean_env('DB_USER')
password = clean_env('DB_PASS')
database_name = clean_env('DB_NAME')

instance_connection_prefix = clean_env('INSTANCE_CONNECTION_PREFIX')
db2_name = clean_env('DB2_NAME')
db2_password = clean_env('DB2_PASS')


password = db2_password
# instance_connection_name = f"{instance_connection_prefix}{db2_name}".strip("'")

instance_connection_name = clean_env('INSTANCE_CONNECTION_STRING_FULL')

print("=== Database Connection Debug Info ===")
print(f"Instance Connection Name FULL: {instance_connection_name}")
print(f"Database Name: {database_name}")
print(f"Username: {username}")
print(f"Connection Prefix: {instance_connection_prefix}")
print(f"DB2 Name: {db2_name}")
print("===================================")

if not all([instance_connection_prefix, db2_name, username, password, database_name]):
    print("WARNING: Some required environment variables are missing!")
    print("Make sure your .env file contains all required variables.")
    
    
# Add this debug section before the connector initialization
print("\n=== Google Cloud Credentials Debug ===")
# print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
# if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
#     print(f"File exists: {os.path.exists(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))}")
#     try:
#         with open(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'), 'r') as f:
#             print("Successfully opened credentials file")
#             # Print first few characters to verify it's JSON (but not the whole thing)
#             content = f.read(50)
#             print(f"File starts with: {content}...")
#     except Exception as e:
#         print(f"Error reading credentials file: {str(e)}")
print("===================================\n")

# Initialize the global connector
connector = Connector()

def getconn():
    try:
        conn = connector.connect(
            instance_connection_name,
            
            "pymysql",
            user=username,
            password=password,
            db=database_name,
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise

db = SQLAlchemy()
firestore_db = firestore.Client()

def init_db(app):
    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800
    )
    
    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://"
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'creator': getconn,
        'pool_pre_ping': True,
        'pool_size': 5,
        'max_overflow': 2,
        'pool_timeout': 30,
        'pool_recycle': 1800
    }
    db.init_app(app)

def cleanup():
    connector.close()
    # Clean up temporary credentials file if it exists
    if creds_path and creds_path.startswith(tempfile.gettempdir()):
        try:
            os.remove(creds_path)
            logger.info("Cleaned up temporary credentials file")
        except Exception as e:
            logger.error(f"Error cleaning up credentials: {str(e)}")