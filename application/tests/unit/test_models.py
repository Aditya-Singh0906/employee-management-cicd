"""Unit tests for SQLAlchemy domain models."""
from app.models.employee import Employee
from app.models.user import User


def test_create_employee_model(db):
    """Test creating an Employee model instance."""
    employee = Employee(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        department="Engineering",
        designation="Senior Engineer",
        salary=120000.0
    )
    db.session.add(employee)
    db.session.commit()

    retrieved = db.session.get(Employee, employee.id)
    assert retrieved is not None
    assert retrieved.email == "jane.doe@example.com"
    assert retrieved.salary == 120000.0


def test_create_user_model(db):
    """Test creating a User model instance."""
    user = User(
        username="admin_test",
        password="hashed_secure_password",
        role="admin"
    )
    db.session.add(user)
    db.session.commit()

    retrieved = db.session.get(User, user.id)
    assert retrieved is not None
    assert retrieved.username == "admin_test"
    assert retrieved.role == "admin"
