from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    return (
        jsonify(
            {
                "status": "UP",
                "service": "employee-management-api",
                "version": "1.0.0",
            }
        ),
        200,
    )