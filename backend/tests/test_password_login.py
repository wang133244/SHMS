from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.main import _ensure_password_column, _seed, create_app
from app.models.enums import EmploymentStatus, PositionCode, Role
from app.models.staff import Position, Staff


def setup_client():
    client = TestClient(create_app("sqlite://"))
    client.post("/api/v1/dev/seed")
    admin_login = client.post("/api/v1/auth/dev-login", json={"employee_no": "ADMIN-001"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    return client, admin_headers


def test_seeded_staff_can_login_with_employee_number_and_password():
    client, _ = setup_client()

    response = client.post("/api/v1/auth/password-login", json={
        "employee_no": "EMP-HEALTH",
        "password": "Health@2026",
    })

    assert response.status_code == 200
    assert response.json()["role"] == "employee"
    assert response.json()["position"] == "health"
    assert response.json()["status"] == "active"
    assert response.json()["access_token"]


def test_password_login_rejects_wrong_password():
    client, _ = setup_client()

    response = client.post("/api/v1/auth/password-login", json={
        "employee_no": "EMP-HEALTH",
        "password": "not-the-password",
    })

    assert response.status_code == 401


def test_unassigned_employee_is_authenticated_but_cannot_use_position_features():
    client, admin_headers = setup_client()
    created = client.post("/api/v1/admin/staff", headers=admin_headers, json={
        "name": "新保安",
        "employee_no": "EMP-SECURITY-NEW",
        "phone": "13800000009",
        "password": "Security@2026",
        "position_code": None,
    })
    assert created.status_code == 201

    login = client.post("/api/v1/auth/password-login", json={
        "employee_no": "EMP-SECURITY-NEW",
        "password": "Security@2026",
    })
    assert login.status_code == 200
    assert login.json()["status"] == "pending_assignment"
    employee_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/v1/tasks/today", headers=employee_headers).status_code == 403
    assert client.post("/api/v1/chat/ask", headers=employee_headers, json={"question": "我的职责是什么"}).status_code == 403

    assigned = client.patch(
        f"/api/v1/admin/staff/{created.json()['id']}/position",
        headers=admin_headers,
        json={"position_code": "security"},
    )
    assert assigned.status_code == 200
    assert assigned.json()["position"] == "security"
    assert client.post("/api/v1/auth/password-login", json={
        "employee_no": "EMP-SECURITY-NEW",
        "password": "Security@2026",
    }).json()["status"] == "active"


def test_admin_can_password_login_and_security_has_no_seed_account():
    client, _ = setup_client()

    credentials = [
        ("ADMIN-001", "Admin@2026", "admin", None),
        ("EMP-LOGISTICS", "Logi@2026", "employee", "logistics"),
        ("EMP-HEALTH", "Health@2026", "employee", "health"),
        ("EMP-CARE", "Care@2026", "employee", "care"),
        ("EMP-KITCHEN", "Kitchen@2026", "employee", "kitchen"),
        ("EMP-BUSINESS", "Biz@2026", "employee", "business"),
    ]
    for employee_no, password, role, position in credentials:
        login = client.post("/api/v1/auth/password-login", json={"employee_no": employee_no, "password": password})
        assert login.status_code == 200
        assert login.json()["role"] == role
        assert login.json()["position"] == position
    assert client.post("/api/v1/auth/password-login", json={
        "employee_no": "EMP-SECURITY",
        "password": "anything",
    }).status_code == 401


def test_simple_role_aliases_login_with_uniform_demo_password():
    client, _ = setup_client()

    credentials = [
        ("0001", "admin", None),
        ("1001", "employee", "logistics"),
        ("2001", "employee", "health"),
        ("3001", "employee", "care"),
        ("4001", "employee", "kitchen"),
        ("5001", "employee", "business"),
    ]
    for employee_no, role, position in credentials:
        login = client.post("/api/v1/auth/password-login", json={"employee_no": employee_no, "password": "123456"})
        assert login.status_code == 200
        assert login.json()["role"] == role
        assert login.json()["position"] == position
        assert login.json()["login_employee_no"] == employee_no


def test_simple_role_alias_rejects_non_demo_password():
    client, _ = setup_client()

    response = client.post("/api/v1/auth/password-login", json={"employee_no": "2001", "password": "Health@2026"})

    assert response.status_code == 401


def test_legacy_sqlite_staff_data_survives_additive_password_column_migration(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE staff (id INTEGER PRIMARY KEY, name VARCHAR(80) NOT NULL)"))
        connection.execute(text("INSERT INTO staff (id, name) VALUES (1, '既有员工')"))

    _ensure_password_column(engine)

    with engine.connect() as connection:
        member = connection.execute(text("SELECT id, name, password_hash FROM staff WHERE id = 1")).one()
    assert member == (1, "既有员工", None)


def test_seed_retires_only_the_known_legacy_security_demo_account(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy-security.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        security = Position(code=PositionCode.SECURITY, name="保安")
        db.add(security)
        db.flush()
        legacy_demo = Staff(
            name="保安老师", employee_no="EMP-SECURITY", phone="13800000002",
            position_id=security.id, role=Role.EMPLOYEE, employment_status=EmploymentStatus.ACTIVE,
        )
        real_account = Staff(
            name="新保安", employee_no="SECURITY-2026", phone="13800000020",
            position_id=security.id, role=Role.EMPLOYEE, employment_status=EmploymentStatus.ACTIVE,
        )
        db.add_all([legacy_demo, real_account])
        db.commit()

        _seed(db)

        db.refresh(legacy_demo)
        db.refresh(real_account)
        assert legacy_demo.employment_status is EmploymentStatus.INACTIVE
        assert real_account.employment_status is EmploymentStatus.ACTIVE
