from flask import Flask
from modules.league.routes import league_bp
from modules.user.routes import user_bp
from modules.tournament.routes import tournament_bp
from modules.pick.routes import pick_bp

from utils.db_connector import db, init_db

from apscheduler.schedulers.background import BackgroundScheduler
from jobs.scheduler import update_database

def create_app():
    app = Flask(__name__)
    init_db(app)
    
    app.register_blueprint(league_bp, url_prefix="/league")
    
    app.register_blueprint(user_bp, url_prefix="/user")
    
    app.register_blueprint(tournament_bp, url_prefix="/tournament")
    
    app.register_blueprint(pick_bp, url_prefix="/pick")
    #   TODO: create a rate limiter for each user to prevent DDOS attacks, overuse, etc.






    @app.route("/")
    def hello():
        return "<p>Hello, World!</p>"
    
    return app
    
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=update_database, trigger="interval", seconds=3600)
    scheduler.start()

app = create_app()
start_scheduler()

if __name__ == "__main__":
    app.run()
