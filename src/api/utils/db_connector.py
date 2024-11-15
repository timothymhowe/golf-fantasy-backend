from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector, IPTypes
from google.cloud import firestore
import os
import sqlalchemy

load_dotenv()

username = os.getenv('DB_USER')
password = os.getenv('DB_PASS')
database_name = os.getenv('DB_NAME')

instance_connection_prefix = os.getenv('INSTANCE_CONNECTION_PREFIX')
db2_name = os.getenv('DB2_NAME')
db2_password = os.getenv('DB2_PASS')


password = db2_password
instance_connection_name = f"{instance_connection_prefix}{db2_name}"

print("=== Database Connection Debug Info ===")
print(f"Instance Connection Name: {instance_connection_name}")
print(f"Database Name: {database_name}")
print(f"Username: {username}")
print(f"Connection Prefix: {instance_connection_prefix}")
print(f"DB2 Name: {db2_name}")
print("===================================")

if not all([instance_connection_prefix, db2_name, username, password, database_name]):
    print("WARNING: Some required environment variables are missing!")
    print("Make sure your .env file contains all required variables.")

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