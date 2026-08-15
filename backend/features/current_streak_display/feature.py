from flask import Blueprint, jsonify, request, g
from functools import wraps
from datetime import datetime, timedelta
import sqlalchemy
from sqlalchemy import text

bp = Blueprint('current_streak_display', __name__)


def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id') or g.user_id is None:
            return jsonify({'code': 'UNAUTHORIZED', 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_db_connection():
    if hasattr(g, 'db_connection'):
        return g.db_connection
    raise RuntimeError('Database connection not available')


def calculate_streak_for_habit(habit_id, user_id, connection):
    """
    Calculate the current streak for a habit by reading completion records
    in reverse chronological order until a gap is found.
    
    Returns tuple: (current_streak, last_completion_date)
    """
    # Get all completion dates for this habit, ordered by date descending
    query = text("""
        SELECT DISTINCT DATE(completion_date) as completion_day
        FROM habit_completions
        WHERE habit_id = :habit_id
        ORDER BY completion_day DESC
    """)
    
    result = connection.execute(query, {'habit_id': habit_id})
    completion_dates = [row[0] for row in result.fetchall()]
    
    if not completion_dates:
        return 0, None
    
    # Start from today and count backwards
    today = datetime.utcnow().date()
    current_streak = 0
    expected_date = today
    last_completion_date = completion_dates[0]
    
    for completion_date in completion_dates:
        # Convert to date if it's a datetime
        if isinstance(completion_date, datetime):
            completion_date = completion_date.date()
        
        # Check if this completion matches our expected date
        if completion_date == expected_date:
            current_streak += 1
            expected_date = expected_date - timedelta(days=1)
        elif completion_date < expected_date:
            # There's a gap, stop counting
            break
    
    return current_streak, last_completion_date


@bp.route('/api/habits/<habit_id>/streak', methods=['GET'])
@require_auth
def get_habit_current_streak(habit_id):
    """
    Calculates and returns the current consecutive completion streak for a specific habit
    by reading completion records in reverse chronological order until a gap is found.
    """
    try:
        connection = get_db_connection()
        
        # First verify the habit exists and belongs to the user
        habit_query = text("""
            SELECT id, user_id
            FROM habits
            WHERE id = :habit_id
        """)
        
        habit_result = connection.execute(habit_query, {'habit_id': habit_id})
        habit_row = habit_result.fetchone()
        
        if not habit_row:
            return jsonify({
                'code': 'HABIT_NOT_FOUND',
                'message': 'Habit does not exist'
            }), 404
        
        habit_user_id = habit_row[1]
        
        if str(habit_user_id) != str(g.user_id):
            return jsonify({
                'code': 'FORBIDDEN',
                'message': 'User does not have access to this habit'
            }), 403
        
        # Calculate the streak
        current_streak, last_completion_date = calculate_streak_for_habit(
            habit_id, g.user_id, connection
        )
        
        response = {
            'habit_id': habit_id,
            'current_streak': current_streak
        }
        
        if last_completion_date:
            if isinstance(last_completion_date, datetime):
                response['last_completion_date'] = last_completion_date.date().isoformat()
            else:
                response['last_completion_date'] = last_completion_date.isoformat()
        else:
            response['last_completion_date'] = None
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': str(e)
        }), 500


@bp.route('/api/habits/streaks', methods=['GET'])
@require_auth
def get_all_habits_streaks():
    """
    Calculates and returns current streaks for all habits belonging to the authenticated user,
    enabling prominent display alongside each habit in the habit list view.
    """
    try:
        connection = get_db_connection()
        
        # Get all habits for the user
        habits_query = text("""
            SELECT id
            FROM habits
            WHERE user_id = :user_id
        """)
        
        habits_result = connection.execute(habits_query, {'user_id': g.user_id})
        habit_rows = habits_result.fetchall()
        
        streaks = []
        
        for habit_row in habit_rows:
            habit_id = habit_row[0]
            
            # Calculate streak for each habit
            current_streak, last_completion_date = calculate_streak_for_habit(
                habit_id, g.user_id, connection
            )
            
            streak_data = {
                'habit_id': str(habit_id),
                'current_streak': current_streak
            }
            
            if last_completion_date:
                if isinstance(last_completion_date, datetime):
                    streak_data['last_completion_date'] = last_completion_date.date().isoformat()
                else:
                    streak_data['last_completion_date'] = last_completion_date.isoformat()
            else:
                streak_data['last_completion_date'] = None
            
            streaks.append(streak_data)
        
        return jsonify({'streaks': streaks}), 200
        
    except Exception as e:
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': str(e)
        }), 500
