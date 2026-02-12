from dotenv import load_dotenv
import os
import logging

load_dotenv()

logger = logging.getLogger(__name__)
logger.info("Environment loaded. FIREBASE_ADMIN_SDK_KEY exists: %s", bool(os.getenv('FIREBASE_ADMIN_SDK_KEY')))

from app import create_app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    app.run(debug=os.getenv('FLASK_ENV') == 'development', host="0.0.0.0", port=8000)
