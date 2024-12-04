import random
import unicodedata
from datetime import datetime, timedelta
from models import db, LeagueInviteCode, Golfer, League
from utils.db_connector import init_db
from flask import Flask

def clean_name(name: str) -> str:
    """
    Clean a name by removing accents and special characters.
    Example: 'Rahm Rodríguez' -> 'RAHMRODRIGUEZ'
    
    Args:
        name (str): Name to clean
        
    Returns:
        str: Cleaned name in uppercase
    """
    # Normalize unicode characters (decompose accented characters)
    normalized = unicodedata.normalize('NFKD', name)
    # Remove non-ASCII characters (like accent marks)
    ascii_name = normalized.encode('ASCII', 'ignore').decode()
    # Remove any remaining non-alphanumeric characters and convert to uppercase
    return ''.join(c for c in ascii_name if c.isalnum()).upper()

def generate_invite_code() -> str:
    """
    Generate a unique, readable invite code using golfer names.
    Format: {FirstGolfer}{2digits}{SecondGolfer}{2digits}
    Example: RAHM23SCHEFFLER45
    
    Returns:
        str: A unique invite code
    """
    while True:
        # Get two random golfers from the database
        golfers = Golfer.query.order_by(db.func.random()).limit(2).all()
        
        if len(golfers) < 2:
            raise Exception("Not enough golfers in database to generate code")
        
        # Generate random numbers
        num1 = str(random.randint(10, 99))
        num2 = str(random.randint(10, 99))
        
        # Clean and combine names
        name1 = clean_name(golfers[0].last_name)
        name2 = clean_name(golfers[1].last_name)
        
        code = f"{name1}{num1}{name2}{num2}"
        
        # Skip if code is too long or already exists
        if len(code) > 20:
            continue
            
        exists = db.session.query(
            LeagueInviteCode.query.filter_by(code=code).exists()
        ).scalar()
        
        if not exists:
            return code

def create_league_invite(league_id: int, created_by_id: int, role_id: int, 
                        max_uses: int = None, expires_at = None) -> LeagueInviteCode:
    """
    Create a new league invite code.
    
    Args:
        league_id (int): ID of the league
        created_by_id (int): ID of the user creating the code
        role_id (int): Role to assign to users who join with this code
        max_uses (int, optional): Maximum number of times this code can be used
        expires_at (datetime, optional): When this code should expire
    
    Returns:
        LeagueInviteCode: The created invite code object
        
    Example:
        Creates codes like: RAHM23SCHEFFLER45
    """
    code = generate_invite_code()
    
    invite = LeagueInviteCode(
        code=code,
        league_id=league_id,
        created_by_id=created_by_id,
        role_id=role_id,
        max_uses=max_uses,
        expires_at=expires_at
    )
    
    db.session.add(invite)
    db.session.commit()
    
    return invite

if __name__ == "__main__":
    app = Flask(__name__)
    init_db(app)

    with app.app_context():
        try:
            # Get league ID
            while True:
                league_id = input("\nEnter league ID: ").strip()
                try:
                    league_id = int(league_id)
                    league = League.query.get(league_id)
                    if league:
                        print(f"\nFound league: {league.name}")
                        break
                    else:
                        print("\nLeague not found. Please try again.")
                except ValueError:
                    print("\nPlease enter a valid number.")

            # Get role ID
            while True:
                role_id = input("\nEnter role ID (2: Commissioner, 3: Member): ").strip()
                try:
                    role_id = int(role_id)
                    if role_id in [2, 3]:
                        break
                    print("\nPlease enter 2 for Comissioner, 3 for Member.")
                except ValueError:
                    print("\nPlease enter a valid number.")

            # Get expiration days
            while True:
                days = input("\nEnter number of days until expiration (default 7): ").strip()
                if not days:
                    expires_at = datetime.utcnow() + timedelta(days=7)
                    break
                try:
                    days = int(days)
                    if days > 0:
                        expires_at = datetime.utcnow() + timedelta(days=days)
                        break
                    print("\nPlease enter a positive number.")
                except ValueError:
                    print("\nPlease enter a valid number.")

            # Get max uses
            while True:
                max_uses = input("\nEnter maximum number of uses (default 1): ").strip()
                if not max_uses:
                    max_uses = 1
                    break
                try:
                    max_uses = int(max_uses)
                    if max_uses > 0:
                        break
                    print("\nPlease enter a positive number.")
                except ValueError:
                    print("\nPlease enter a valid number.")

            # Create the invite using the existing function
            invite = create_league_invite(league_id, 1, role_id, max_uses, expires_at)
            print(f"\nCreated invite code: {invite.code}")
        except Exception as e:
            print(f"\nAn error occurred: {e}")
