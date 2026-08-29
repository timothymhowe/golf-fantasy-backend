"""League-scoped authorization checks.

These decorators sit directly below @require_auth, which resolves the Firebase
token and passes the uid as the first positional argument. Flask passes URL
converters as keyword arguments, so each decorator reads its id from kwargs.

Three rules, deliberately kept separate:
  - require_league_member        caller belongs to <int:league_id>
  - require_own_league_member    <int:league_member_id> IS the caller
  - require_shared_league_member <int:league_member_id> is in a league the caller belongs to
"""

from functools import wraps
from flask import jsonify
import logging

from models import LeagueMember
from modules.user.functions import get_league_member_ids

logger = logging.getLogger(__name__)


def find_membership(uid, league_id):
    """The user's membership row for this league, or None.

    For routes that need the league_member_id, not just a yes/no. Note this
    repeats the lookup the decorator already did -- the decorator discards its
    result rather than stashing it, so a route using both pays for two
    membership joins. Acceptable at current traffic; revisit if it matters.

    Returns None both when the user is not a member and when the underlying
    lookup failed, since get_league_member_ids swallows its errors. Callers
    must handle None even directly behind @require_league_member.
    """
    memberships = get_league_member_ids(uid) or []
    return next((m for m in memberships if m['league_id'] == league_id), None)


def user_in_league(uid, league_id):
    """True if the user is a member of this league."""
    return find_membership(uid, league_id) is not None


def user_owns_league_member(uid, league_member_id):
    """True if this league_member row belongs to the user."""
    memberships = get_league_member_ids(uid) or []
    return any(m['league_member_id'] == league_member_id for m in memberships)


def user_shares_league_with_member(uid, league_member_id):
    """True if the user belongs to the same league as this league_member row."""
    member = LeagueMember.query.get(league_member_id)
    if member is None:
        return False
    return user_in_league(uid, member.league_id)


def _denied(uid, what, value):
    logger.warning("User %s denied access to %s %s", uid, what, value)
    return jsonify({'error': 'Not authorized'}), 403


def require_league_member(f):
    """Route takes <int:league_id>. Caller must belong to that league."""
    @wraps(f)
    def decorated(uid, *args, **kwargs):
        league_id = kwargs.get('league_id')
        if not user_in_league(uid, league_id):
            return _denied(uid, 'league', league_id)
        return f(uid, *args, **kwargs)
    return decorated


def require_own_league_member(f):
    """Route takes <int:league_member_id>. It must be the caller's own row."""
    @wraps(f)
    def decorated(uid, *args, **kwargs):
        league_member_id = kwargs.get('league_member_id')
        if not user_owns_league_member(uid, league_member_id):
            return _denied(uid, 'league member', league_member_id)
        return f(uid, *args, **kwargs)
    return decorated


def require_shared_league_member(f):
    """Route takes <int:league_member_id>. Caller must share a league with it."""
    @wraps(f)
    def decorated(uid, *args, **kwargs):
        league_member_id = kwargs.get('league_member_id')
        if not user_shares_league_with_member(uid, league_member_id):
            return _denied(uid, 'league member', league_member_id)
        return f(uid, *args, **kwargs)
    return decorated
