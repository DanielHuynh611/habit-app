"""Shared JSON error mapping."""

from flask import jsonify
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


def register_error_handlers(app):
    @app.errorhandler(IntegrityError)
    def integrity_error(_error):
        return jsonify({"error": "database_constraint_violation"}), 409

    @app.errorhandler(SQLAlchemyError)
    def database_error(_error):
        return jsonify({"error": "database_error"}), 500

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "not_found"}), 404

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"error": "internal_error"}), 500
