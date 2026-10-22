from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok():
    client = TestClient(create_app("sqlite://"))
    assert client.get("/health").json() == {"status": "ok"}


def test_employee_cannot_read_admin_endpoint():
    app = create_app("sqlite://")
    client = TestClient(app)
    client.post("/api/v1/dev/seed")
    token = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]

    response = client.get("/api/v1/admin/staff", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_employee_only_receives_own_tasks():
    app = create_app("sqlite://")
    client = TestClient(app)
    client.post("/api/v1/dev/seed")
    token = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]

    response = client.get("/api/v1/tasks/today", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert all(task["staff_id"] == 2 for task in response.json())


def test_employee_today_endpoint_only_returns_today_records():
    app = create_app("sqlite://")
    client = TestClient(app)
    client.post("/api/v1/dev/seed")
    token = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]
    response = client.get("/api/v1/tasks/today", headers={"Authorization": f"Bearer {token}"})
    assert all(task["due_date"] == __import__("datetime").date.today().isoformat() for task in response.json())


def test_employee_cannot_read_another_employees_task_detail():
    client = TestClient(create_app("sqlite://"))
    client.post("/api/v1/dev/seed")
    token = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/admin/tasks/generate?target_date=2026-10-21", headers={"Authorization": f"Bearer {client.post('/api/v1/auth/dev-login', json={'employee_no':'ADMIN-001'}).json()['access_token']}"})
    response = client.get("/api/v1/tasks/2", headers=headers)
    assert response.status_code == 404


def test_employee_can_read_own_task_detail_with_template_content():
    client = TestClient(create_app("sqlite://"))
    client.post("/api/v1/dev/seed")
    token = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]
    task_id = client.get("/api/v1/tasks/today", headers={"Authorization": f"Bearer {token}"}).json()[0]["id"]
    response = client.get(f"/api/v1/tasks/{task_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["content"]
    assert response.json()["submissions"] == []
