"""Daily Habit Completion Tracking Feature Module"""
import uuid
from datetime import date, datetime
from flask import Blueprint, request, jsonify, g
from sqlalchemy import text
from functools import wraps

# Blueprint definition
bp = Blueprint('daily_habit_completion_tracking', __name__)


# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id') or g.user_id is None:
            return jsonify({
                'error': 'UNAUTHORIZED',
                'message': 'Authentication required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def get_db():
    """Get database connection from Flask g object"""
    if not hasattr(g, 'db'):
        raise RuntimeError('Database connection not available')
    return g.db


def validate_date_format(date_string):
    """Validate date string is in YYYY-MM-DD format"""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False


def check_habit_access(habit_id, user_id):
    """Check if user has access to the habit. Returns True if accessible, False otherwise."""
    db = get_db()
    # Assuming there's a habits table with user_id column
    query = text("SELECT id FROM habits WHERE id = :habit_id AND user_id = :user_id")
    result = db.execute(query, {'habit_id': habit_id, 'user_id': user_id}).fetchone()
    return result is not None


def check_habit_exists(habit_id):
    """Check if habit exists. Returns True if exists, False otherwise."""
    db = get_db()
    query = text("SELECT id FROM habits WHERE id = :habit_id")
    result = db.execute(query, {'habit_id': habit_id}).fetchone()
    return result is not None


@bp.route('/api/habits/<habit_id>/completions', methods=['PUT'])
@require_auth
def mark_habit_complete(habit_id):
    """Creates or updates a completion record to mark a habit as complete for a specific date"""
    user_id = g.user_id
    db = get_db()
    
    # Parse request body
    data = request.get_json()
    if not data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'Request body is required'
        }), 400
    
    completion_date = data.get('completion_date')
    is_completed = data.get('is_completed')
    
    # Validate required fields
    if completion_date is None or is_completed is None:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'completion_date and is_completed are required'
        }), 400
    
    # Validate date format
    if not validate_date_format(completion_date):
        return jsonify({
            'error': 'INVALID_DATE',
            'message': 'completion_date must be a valid date in YYYY-MM-DD format'
        }), 400
    
    # Validate is_completed is boolean
    if not isinstance(is_completed, bool):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'is_completed must be a boolean'
        }), 400
    
    # Check if habit exists
    if not check_habit_exists(habit_id):
        return jsonify({
            'error': 'HABIT_NOT_FOUND',
            'message': 'Habit with the specified ID does not exist'
        }), 404
    
    # Check if user has access to this habit
    if not check_habit_access(habit_id, user_id):
        return jsonify({
            'error': 'FORBIDDEN',
            'message': 'User does not have access to this habit'
        }), 403
    
    # Check if completion record already exists
    check_query = text("""
        SELECT id, is_completed, created_at, updated_at 
        FROM habit_completions 
        WHERE habit_id = :habit_id AND completion_date = :completion_date
    """)
    existing = db.execute(check_query, {
        'habit_id': habit_id,
        'completion_date': completion_date
    }).fetchone()
    
    if existing:
        # Update existing record
        completion_id = existing[0]
        update_query = text("""
            UPDATE habit_completions 
            SET is_completed = :is_completed, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """)
        db.execute(update_query, {
            'id': completion_id,
            'is_completed': is_completed
        })
        db.commit()
        
        # Fetch updated record
        fetch_query = text("""
            SELECT id, habit_id, completion_date, is_completed, created_at, updated_at
            FROM habit_completions
            WHERE id = :id
        """)
        result = db.execute(fetch_query, {'id': completion_id}).fetchone()
    else:
        # Create new record
        completion_id = str(uuid.uuid4())
        insert_query = text("""
            INSERT INTO habit_completions (id, habit_id, completion_date, is_completed, created_at, updated_at)
            VALUES (:id, :habit_id, :completion_date, :is_completed, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """)
        db.execute(insert_query, {
            'id': completion_id,
            'habit_id': habit_id,
            'completion_date': completion_date,
            'is_completed': is_completed
        })
        db.commit()
        
        # Fetch created record
        fetch_query = text("""
            SELECT id, habit_id, completion_date, is_completed, created_at, updated_at
            FROM habit_completions
            WHERE id = :id
        """)
        result = db.execute(fetch_query, {'id': completion_id}).fetchone()
    
    # Format response
    response = {
        'id': result[0],
        'habit_id': result[1],
        'completion_date': result[2].isoformat() if isinstance(result[2], date) else result[2],
        'is_completed': bool(result[3]),
        'created_at': result[4].isoformat() if isinstance(result[4], datetime) else result[4],
        'updated_at': result[5].isoformat() if isinstance(result[5], datetime) else result[5]
    }
    
    return jsonify(response), 200


@bp.route('/api/habits/<habit_id>/completions', methods=['GET'])
@require_auth
def get_habit_completions(habit_id):
    """Retrieves completion records for a habit within a date range"""
    user_id = g.user_id
    db = get_db()
    
    # Get query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Validate required parameters
    if not start_date or not end_date:
        return jsonify({
            'error': 'INVALID_DATE_RANGE',
            'message': 'start_date and end_date must be valid dates, and start_date must not be after end_date'
        }), 400
    
    # Validate date formats
    if not validate_date_format(start_date) or not validate_date_format(end_date):
        return jsonify({
            'error': 'INVALID_DATE_RANGE',
            'message': 'start_date and end_date must be valid dates, and start_date must not be after end_date'
        }), 400
    
    # Validate date range
    if start_date > end_date:
        return jsonify({
            'error': 'INVALID_DATE_RANGE',
            'message': 'start_date and end_date must be valid dates, and start_date must not be after end_date'
        }), 400
    
    # Check if habit exists
    if not check_habit_exists(habit_id):
        return jsonify({
            'error': 'HABIT_NOT_FOUND',
            'message': 'Habit with the specified ID does not exist'
        }), 404
    
    # Check if user has access to this habit
    if not check_habit_access(habit_id, user_id):
        return jsonify({
            'error': 'FORBIDDEN',
            'message': 'User does not have access to this habit'
        }), 403
    
    # Fetch completion records
    query = text("""
        SELECT id, completion_date, is_completed, created_at, updated_at
        FROM habit_completions
        WHERE habit_id = :habit_id 
        AND completion_date >= :start_date 
        AND completion_date <= :end_date
        ORDER BY completion_date ASC
    """)
    results = db.execute(query, {
        'habit_id': habit_id,
        'start_date': start_date,
        'end_date': end_date
    }).fetchall()
    
    # Format response
    completions = []
    for row in results:
        completions.append({
            'id': row[0],
            'completion_date': row[1].isoformat() if isinstance(row[1], date) else row[1],
            'is_completed': bool(row[2]),
            'created_at': row[3].isoformat() if isinstance(row[3], datetime) else row[3],
            'updated_at': row[4].isoformat() if isinstance(row[4], datetime) else row[4]
        })
    
    response = {
        'habit_id': habit_id,
        'completions': completions
    }
    
    return jsonify(response), 200


@bp.route('/api/completions/today', methods=['GET'])
@require_auth
def get_today_completions():
    """Retrieves all completion records for the current day across all user habits"""
    user_id = g.user_id
    db = get_db()
    
    # Get today's date
    today = date.today().isoformat()
    
    # Fetch all completion records for today for user's habits
    query = text("""
        SELECT hc.id, hc.habit_id, hc.completion_date, hc.is_completed, hc.created_at, hc.updated_at
        FROM habit_completions hc
        INNER JOIN habits h ON hc.habit_id = h.id
        WHERE h.user_id = :user_id AND hc.completion_date = :today
        ORDER BY hc.created_at ASC
    """)
    results = db.execute(query, {
        'user_id': user_id,
        'today': today
    }).fetchall()
    
    # Format response
    completions = []
    for row in results:
        completions.append({
            'id': row[0],
            'habit_id': row[1],
            'completion_date': row[2].isoformat() if isinstance(row[2], date) else row[2],
            'is_completed': bool(row[3]),
            'created_at': row[4].isoformat() if isinstance(row[4], datetime) else row[4],
            'updated_at': row[5].isoformat() if isinstance(row[5], datetime) else row[5]
        })
    
    response = {
        'date': today,
        'completions': completions
    }
    
    return jsonify(response), 200
