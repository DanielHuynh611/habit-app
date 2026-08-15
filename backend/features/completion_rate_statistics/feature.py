"""
Completion Rate Statistics Feature Module

This module provides endpoints to calculate and retrieve habit completion rates
for authenticated users. Completion rate is calculated as (completed days / total days tracked) × 100.
"""

from flask import Blueprint, jsonify, request, g
from functools import wraps
from datetime import datetime, date
import uuid
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Assuming these are available from the main application
# from app import db
# from app.auth import get_current_user

bp = Blueprint('completion_rate_statistics', __name__)


def require_auth(f):
    """Decorator to require authentication for endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated (assumes authentication middleware sets g.user)
        if not hasattr(g, 'user') or g.user is None:
            return jsonify({
                'code': 'UNAUTHORIZED',
                'message': 'Authentication required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def get_db():
    """Get database connection from Flask g object"""
    from flask import current_app
    if not hasattr(g, 'db'):
        g.db = current_app.extensions['sqlalchemy'].db
    return g.db


def calculate_completion_rate_for_habit(db, habit_id, user_id):
    """
    Calculate completion rate for a single habit.
    
    Args:
        db: Database session
        habit_id: UUID of the habit
        user_id: UUID of the user
        
    Returns:
        dict with habit_id, completion_rate, completed_days, total_days
        None if habit not found or doesn't belong to user
    """
    # First verify the habit exists and belongs to the user
    habit_query = text("""
        SELECT id, created_at 
        FROM habits 
        WHERE id = :habit_id AND user_id = :user_id
    """)
    
    result = db.session.execute(
        habit_query,
        {'habit_id': habit_id, 'user_id': user_id}
    ).fetchone()
    
    if not result:
        return None
    
    habit_created_at = result[1]
    
    # Calculate total days from creation to today
    if isinstance(habit_created_at, str):
        habit_created_at = datetime.fromisoformat(habit_created_at.replace('Z', '+00:00'))
    
    today = date.today()
    if isinstance(habit_created_at, datetime):
        creation_date = habit_created_at.date()
    else:
        creation_date = habit_created_at
    
    total_days = (today - creation_date).days + 1
    
    if total_days < 1:
        total_days = 1
    
    # Count completed days
    completed_query = text("""
        SELECT COUNT(DISTINCT DATE(completed_at)) as completed_count
        FROM habit_completions
        WHERE habit_id = :habit_id
    """)
    
    completed_result = db.session.execute(
        completed_query,
        {'habit_id': habit_id}
    ).fetchone()
    
    completed_days = completed_result[0] if completed_result and completed_result[0] else 0
    
    # Calculate completion rate
    completion_rate = (completed_days / total_days) * 100 if total_days > 0 else 0.0
    
    # Ensure completion_rate doesn't exceed 100
    completion_rate = min(completion_rate, 100.0)
    
    return {
        'habit_id': habit_id,
        'completion_rate': round(completion_rate, 2),
        'completed_days': completed_days,
        'total_days': total_days
    }


@bp.route('/api/habits/completion-rates', methods=['GET'])
@require_auth
def get_all_habits_completion_rates():
    """
    Retrieves completion rate statistics for all habits belonging to the authenticated user.
    Calculates (completed days / total days tracked) × 100 for each habit.
    """
    try:
        db = get_db()
        user_id = g.user['id'] if isinstance(g.user, dict) else g.user.id
        
        # Get all habits for the user
        habits_query = text("""
            SELECT id, created_at
            FROM habits
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """)
        
        habits = db.session.execute(
            habits_query,
            {'user_id': user_id}
        ).fetchall()
        
        completion_rates = []
        
        for habit in habits:
            habit_id = habit[0]
            habit_created_at = habit[1]
            
            # Calculate total days from creation to today
            if isinstance(habit_created_at, str):
                habit_created_at = datetime.fromisoformat(habit_created_at.replace('Z', '+00:00'))
            
            today = date.today()
            if isinstance(habit_created_at, datetime):
                creation_date = habit_created_at.date()
            else:
                creation_date = habit_created_at
            
            total_days = (today - creation_date).days + 1
            
            if total_days < 1:
                total_days = 1
            
            # Count completed days
            completed_query = text("""
                SELECT COUNT(DISTINCT DATE(completed_at)) as completed_count
                FROM habit_completions
                WHERE habit_id = :habit_id
            """)
            
            completed_result = db.session.execute(
                completed_query,
                {'habit_id': habit_id}
            ).fetchone()
            
            completed_days = completed_result[0] if completed_result and completed_result[0] else 0
            
            # Calculate completion rate
            completion_rate = (completed_days / total_days) * 100 if total_days > 0 else 0.0
            
            # Ensure completion_rate doesn't exceed 100
            completion_rate = min(completion_rate, 100.0)
            
            completion_rates.append({
                'habit_id': str(habit_id),
                'completion_rate': round(completion_rate, 2),
                'completed_days': completed_days,
                'total_days': total_days
            })
        
        return jsonify({
            'completion_rates': completion_rates
        }), 200
        
    except SQLAlchemyError as e:
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to calculate completion rates'
        }), 500
    except Exception as e:
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to calculate completion rates'
        }), 500


@bp.route('/api/habits/<habit_id>/completion-rate', methods=['GET'])
@require_auth
def get_habit_completion_rate(habit_id):
    """
    Retrieves the completion rate statistic for a single habit.
    Calculates (completed days / total days tracked) × 100.
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(habit_id)
        except (ValueError, AttributeError):
            return jsonify({
                'code': 'HABIT_NOT_FOUND',
                'message': 'Habit not found or does not belong to user'
            }), 404
        
        db = get_db()
        user_id = g.user['id'] if isinstance(g.user, dict) else g.user.id
        
        # Calculate completion rate
        result = calculate_completion_rate_for_habit(db, habit_id, user_id)
        
        if result is None:
            return jsonify({
                'code': 'HABIT_NOT_FOUND',
                'message': 'Habit not found or does not belong to user'
            }), 404
        
        # Ensure habit_id is string format
        result['habit_id'] = str(result['habit_id'])
        
        return jsonify(result), 200
        
    except SQLAlchemyError as e:
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to calculate completion rate'
        }), 500
    except Exception as e:
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to calculate completion rate'
        }), 500


def init_app(app):
    """Initialize the blueprint with the Flask app"""
    app.register_blueprint(bp)
