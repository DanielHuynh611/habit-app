"""
Flask Blueprint for Create Habits feature.
Implements habit creation and listing functionality.
"""
from flask import Blueprint, request, jsonify, g
from functools import wraps
import uuid
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os

bp = Blueprint('create_habits', __name__)

def get_db_connection():
    """Get database connection from Flask app context."""
    if not hasattr(g, 'db_engine'):
        database_url = os.environ.get('DATABASE_URL', 'mysql+pymysql://user:password@localhost/habittracker')
        g.db_engine = create_engine(database_url, pool_pre_ping=True)
    return g.db_engine.connect()

def require_auth(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'UNAUTHORIZED', 'message': 'Authentication required'}), 401
        
        # Extract user_id from Authorization header (assuming Bearer token format)
        # In production, this would validate JWT or session token
        try:
            if auth_header.startswith('Bearer '):
                user_id = auth_header.split(' ')[1]
            else:
                user_id = auth_header
            
            # Verify user exists in database
            conn = get_db_connection()
            try:
                result = conn.execute(
                    text("SELECT id FROM users WHERE id = :user_id"),
                    {"user_id": user_id}
                )
                user = result.fetchone()
                if not user:
                    return jsonify({'error': 'USER_NOT_FOUND', 'message': 'User account does not exist'}), 404
                
                g.user_id = user_id
            finally:
                conn.close()
                
        except Exception as e:
            return jsonify({'error': 'UNAUTHORIZED', 'message': 'Authentication required'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/api/habits', methods=['POST'])
@require_auth
def create_habit():
    """
    Creates a new habit record with a user-provided name and associates it 
    with the authenticated user's account.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'INVALID_HABIT_NAME',
                'message': 'Habit name must be between 1 and 255 characters'
            }), 400
        
        habit_name = data.get('name', '').strip()
        
        # Validate habit name
        if not habit_name or len(habit_name) < 1 or len(habit_name) > 255:
            return jsonify({
                'error': 'INVALID_HABIT_NAME',
                'message': 'Habit name must be between 1 and 255 characters'
            }), 400
        
        # Generate UUID and timestamp
        habit_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        user_id = g.user_id
        
        # Insert habit into database
        conn = get_db_connection()
        try:
            conn.execute(
                text("""
                    INSERT INTO habits (id, user_id, name, created_at)
                    VALUES (:id, :user_id, :name, :created_at)
                """),
                {
                    "id": habit_id,
                    "user_id": user_id,
                    "name": habit_name,
                    "created_at": created_at
                }
            )
            conn.commit()
        finally:
            conn.close()
        
        # Return created habit
        return jsonify({
            'id': habit_id,
            'name': habit_name,
            'user_id': user_id,
            'created_at': created_at.isoformat() + 'Z'
        }), 201
        
    except SQLAlchemyError as e:
        return jsonify({
            'error': 'DATABASE_ERROR',
            'message': 'Failed to create habit'
        }), 500
    except Exception as e:
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred'
        }), 500

@bp.route('/api/habits', methods=['GET'])
@require_auth
def list_habits():
    """
    Retrieves all habits associated with the authenticated user's account 
    for display in the habit list.
    """
    try:
        user_id = g.user_id
        
        # Query habits for the authenticated user
        conn = get_db_connection()
        try:
            result = conn.execute(
                text("""
                    SELECT id, user_id, name, created_at
                    FROM habits
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                """),
                {"user_id": user_id}
            )
            
            habits = []
            for row in result:
                habits.append({
                    'id': row[0],
                    'user_id': row[1],
                    'name': row[2],
                    'created_at': row[3].isoformat() + 'Z' if isinstance(row[3], datetime) else row[3]
                })
        finally:
            conn.close()
        
        return jsonify({'habits': habits}), 200
        
    except SQLAlchemyError as e:
        return jsonify({
            'error': 'DATABASE_ERROR',
            'message': 'Failed to retrieve habits'
        }), 500
    except Exception as e:
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred'
        }), 500

@bp.teardown_app_request
def teardown_db(exception=None):
    """Close database connection at the end of request."""
    db_engine = g.pop('db_engine', None)
    if db_engine is not None:
        db_engine.dispose()
