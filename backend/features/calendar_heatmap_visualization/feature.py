"""
Calendar Heatmap Visualization Feature Module

This module provides a GitHub-style calendar heatmap visualization for habit tracking,
showing completion patterns, streaks, and gaps over time.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, date, timedelta
from functools import wraps
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import os

# Create Blueprint
calendar_heatmap_bp = Blueprint('calendar_heatmap_visualization', __name__)


# Authentication decorator
def require_authentication(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated (assumes user info is stored in g.user)
        if not hasattr(g, 'user') or g.user is None:
            return jsonify({
                'error': 'UNAUTHORIZED',
                'message': 'Authentication required to view habit heatmap'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def get_db():
    """Get database connection from Flask g object"""
    if not hasattr(g, 'db'):
        raise RuntimeError("Database connection not available")
    return g.db


@calendar_heatmap_bp.route('/api/habits/<habit_id>/heatmap', methods=['GET'])
@require_authentication
def get_habit_heatmap_data(habit_id):
    """
    Retrieves completion data for a specific habit over a date range to render 
    the calendar heatmap grid, showing which days were completed versus missed.
    
    Args:
        habit_id: The unique identifier of the habit to visualize
        
    Query Parameters:
        start_date: ISO 8601 date string for the beginning of the heatmap range (optional)
        end_date: ISO 8601 date string for the end of the heatmap range (optional)
        
    Returns:
        JSON response with heatmap data including days array, streaks, and completion rate
    """
    try:
        db = get_db()
        user_id = g.user['id']
        
        # Parse query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Set default date range (12 weeks back from today)
        today = date.today()
        if end_date_str:
            try:
                end_date_val = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'error': 'INVALID_DATE_RANGE',
                    'message': 'Invalid end_date format. Use ISO 8601 format (YYYY-MM-DD)'
                }), 400
        else:
            end_date_val = today
            
        if start_date_str:
            try:
                start_date_val = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'error': 'INVALID_DATE_RANGE',
                    'message': 'Invalid start_date format. Use ISO 8601 format (YYYY-MM-DD)'
                }), 400
        else:
            start_date_val = end_date_val - timedelta(weeks=12)
        
        # Validate date range
        if start_date_val > end_date_val:
            return jsonify({
                'error': 'INVALID_DATE_RANGE',
                'message': 'Start date must be before or equal to end date'
            }), 400
        
        # Check if habit exists and belongs to user
        habit_query = text("""
            SELECT id, name, user_id
            FROM habits
            WHERE id = :habit_id
        """)
        
        habit_result = db.execute(habit_query, {'habit_id': habit_id}).fetchone()
        
        if not habit_result:
            return jsonify({
                'error': 'HABIT_NOT_FOUND',
                'message': 'The specified habit does not exist'
            }), 404
        
        # Check permission
        if habit_result.user_id != user_id:
            return jsonify({
                'error': 'FORBIDDEN',
                'message': 'User does not have permission to view this habit'
            }), 403
        
        habit_name = habit_result.name
        
        # Fetch completion records for the date range
        completions_query = text("""
            SELECT DATE(completed_at) as completion_date
            FROM habit_completions
            WHERE habit_id = :habit_id
            AND DATE(completed_at) BETWEEN :start_date AND :end_date
            GROUP BY DATE(completed_at)
        """)
        
        completions_result = db.execute(completions_query, {
            'habit_id': habit_id,
            'start_date': start_date_val,
            'end_date': end_date_val
        }).fetchall()
        
        # Create a set of completed dates for fast lookup
        completed_dates = {row.completion_date for row in completions_result}
        
        # Build days array
        days = []
        current_date = start_date_val
        while current_date <= end_date_val:
            days.append({
                'date': current_date.isoformat(),
                'completed': current_date in completed_dates,
                'is_future': current_date > today
            })
            current_date += timedelta(days=1)
        
        # Calculate current streak (consecutive days up to today)
        current_streak = 0
        check_date = today
        
        # Query for streak calculation
        streak_query = text("""
            SELECT DATE(completed_at) as completion_date
            FROM habit_completions
            WHERE habit_id = :habit_id
            AND DATE(completed_at) <= :today
            ORDER BY DATE(completed_at) DESC
            LIMIT 365
        """)
        
        streak_result = db.execute(streak_query, {
            'habit_id': habit_id,
            'today': today
        }).fetchall()
        
        streak_dates = {row.completion_date for row in streak_result}
        
        # Count backwards from today
        while check_date in streak_dates:
            current_streak += 1
            check_date -= timedelta(days=1)
        
        # Calculate completion rate (excluding future dates)
        total_days = 0
        completed_days = 0
        
        for day in days:
            if not day['is_future']:
                total_days += 1
                if day['completed']:
                    completed_days += 1
        
        completion_rate = (completed_days / total_days * 100.0) if total_days > 0 else 0.0
        
        # Build response
        response_data = {
            'habit_id': habit_id,
            'habit_name': habit_name,
            'start_date': start_date_val.isoformat(),
            'end_date': end_date_val.isoformat(),
            'days': days,
            'current_streak': current_streak,
            'completion_rate': round(completion_rate, 2)
        }
        
        return jsonify(response_data), 200
        
    except SQLAlchemyError as e:
        return jsonify({
            'error': 'DATABASE_ERROR',
            'message': 'An error occurred while retrieving heatmap data'
        }), 500
    except Exception as e:
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred'
        }), 500


# Export blueprint for registration
__all__ = ['calendar_heatmap_bp', 'get_habit_heatmap_data']
