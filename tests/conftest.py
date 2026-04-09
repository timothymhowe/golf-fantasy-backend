"""
Root conftest for the golf fantasy backend test suite.

Mocks Firebase, Cloud SQL, and Firestore at the sys.modules level BEFORE
any application code is imported. This is required because auth.py and
db_connector.py execute side effects (initialize_app, Connector(), etc.)
at import time.
"""

import sys
import os
from unittest.mock import MagicMock

# --------------------------------------------------------------------------- #
# STEP 1: Patch dangerous module-level imports BEFORE any app code loads      #
# --------------------------------------------------------------------------- #

# Mock firebase_admin so auth.py doesn't crash on import
mock_firebase_admin = MagicMock()
mock_firebase_admin._apps = {}
mock_firebase_admin.initialize_app = MagicMock()
sys.modules['firebase_admin'] = mock_firebase_admin
sys.modules['firebase_admin.auth'] = MagicMock()
sys.modules['firebase_admin.credentials'] = MagicMock()
sys.modules['firebase_admin.firestore'] = MagicMock()

# Mock google.cloud modules so db_connector.py doesn't crash
sys.modules['google.cloud.sql.connector'] = MagicMock()
sys.modules['google.cloud.firestore'] = MagicMock()
sys.modules['google.cloud'] = MagicMock()

# Set required env vars so dotenv/auth don't fail
os.environ.setdefault('FIREBASE_ADMIN_SDK_KEY', '{"type":"service_account","project_id":"test"}')
os.environ.setdefault('DB_USER', 'test')
os.environ.setdefault('DB_PASS', 'test')
os.environ.setdefault('DB_NAME', 'test')
os.environ.setdefault('DB2_NAME', 'test')
os.environ.setdefault('DB2_PASS', 'test')
os.environ.setdefault('INSTANCE_CONNECTION_PREFIX', 'test:us:')
os.environ.setdefault('INSTANCE_CONNECTION_STRING_FULL', 'test:us-central1:instance')

# --------------------------------------------------------------------------- #
# STEP 2: Now safe to import app code                                         #
# --------------------------------------------------------------------------- #

import pytest
from flask import Flask
from utils.db_connector import db
from models import (
    User, League, LeagueMember, Pick, Tournament, Golfer,
    TournamentGolfer, TournamentGolferResult, Role,
    ScoringRuleset, ScoringRule, LeagueMemberTournamentScore,
    Schedule, ScheduleTournament, LeagueInviteCode, InviteCodeUsage,
    GolferRanking, GolferStats,
    LegacyMember, LegacyMemberPick, LeagueCommisioner,
)


@pytest.fixture(scope='session')
def app():
    """Create a Flask app configured for testing with SQLite in-memory DB."""
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize SQLAlchemy directly — bypasses init_db() / Cloud SQL entirely
    db.init_app(test_app)

    # Register all blueprints
    from modules.league.routes import league_bp
    from modules.user.routes import user_bp
    from modules.tournament.routes import tournament_bp
    from modules.pick.routes import pick_bp
    from modules.commish.routes import commish_bp
    from modules.management.routes import management_bp
    from modules.admin.routes import health_bp
    from modules.league_picks.routes import league_picks_bp
    from modules.live_tournament.routes import live_tournament_bp

    test_app.register_blueprint(league_bp, url_prefix='/league')
    test_app.register_blueprint(user_bp, url_prefix='/user')
    test_app.register_blueprint(tournament_bp, url_prefix='/tournament')
    test_app.register_blueprint(pick_bp, url_prefix='/pick')
    test_app.register_blueprint(commish_bp, url_prefix='/commish')
    test_app.register_blueprint(management_bp, url_prefix='/management')
    test_app.register_blueprint(health_bp, url_prefix='/health')
    test_app.register_blueprint(league_picks_bp, url_prefix='/league_picks')
    test_app.register_blueprint(live_tournament_bp, url_prefix='/live_results')

    with test_app.app_context():
        db.create_all()

    yield test_app

    with test_app.app_context():
        db.drop_all()


@pytest.fixture(scope='function')
def db_session(app):
    """Provide a clean database session for each test."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture(scope='function')
def client(app, db_session):
    """Flask test client with a clean database."""
    return app.test_client()


@pytest.fixture(scope='function')
def auth_headers():
    """Authorization headers with a mock Bearer token."""
    return {'Authorization': 'Bearer test-firebase-token'}


@pytest.fixture(autouse=True)
def mock_require_auth(monkeypatch):
    """Auto-mock the Firebase auth decorator for all tests.

    Patches verify_id_token to always return a known test UID.
    Tests that need to verify 401 behavior can override this by
    monkeypatching verify_id_token to return None.
    """
    monkeypatch.setattr(
        'modules.authentication.auth.verify_id_token',
        lambda token: 'test-firebase-uid',
    )


@pytest.fixture(scope='function')
def seeded_db(db_session):
    """A fully seeded database with users, league, tournaments, golfers, picks, and scores."""
    from fixtures.data import seed_full_league
    return seed_full_league(db_session)
