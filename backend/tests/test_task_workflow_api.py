from fastapi.testclient import TestClient

from app.main import create_app


def setup_client():
    client = TestClient(create_app("sqlite://"))
    client.post("/api/v1/dev/seed")
    employee = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]
    admin = client.post("/api/v1/auth/dev-login", json={"employee_no": "ADMIN-001"}).json()["access_token"]
    return client, employee, admin


def test_employee_submits_task_and_cannot_submit_twice():
    client, employee, _ = setup_client()
    headers = {"Authorization": f"Bearer {employee}"}
    tasks = client.get("/api/v1/tasks/today", headers=headers).json()
    assert len(tasks) == 1
    task_id = tasks[0]["id"]

    submitted = client.post(f"/api/v1/tasks/{task_id}/submissions", headers=headers, json={"note": "完成", "photo_keys": ["a.jpg"]})
    assert submitted.status_code == 201
    assert submitted.json()["version"] == 1
    assert client.post(f"/api/v1/tasks/{task_id}/submissions", headers=headers, json={"note": "重复"}).status_code == 409


def test_approved_change_reopens_task_and_next_submission_is_new_version():
    client, employee, admin = setup_client()
    employee_headers = {"Authorization": f"Bearer {employee}"}
    admin_headers = {"Authorization": f"Bearer {admin}"}
    task_id = client.get("/api/v1/tasks/today", headers=employee_headers).json()[0]["id"]
    client.post(f"/api/v1/tasks/{task_id}/submissions", headers=employee_headers, json={"note": "提交 1"})
    change = client.post(f"/api/v1/tasks/{task_id}/change-requests", headers=employee_headers, json={"reason": "补充记录"})
    assert change.status_code == 201

    approved = client.post(f"/api/v1/admin/change-requests/{change.json()['id']}/approve", headers=admin_headers)
    assert approved.status_code == 200
    second = client.post(f"/api/v1/tasks/{task_id}/submissions", headers=employee_headers, json={"note": "提交 2"})
    assert second.json()["version"] == 2


def test_rejected_change_requires_reason_and_preserves_submission():
    client, employee, admin = setup_client()
    employee_headers = {"Authorization": f"Bearer {employee}"}
    admin_headers = {"Authorization": f"Bearer {admin}"}
    task_id = client.get("/api/v1/tasks/today", headers=employee_headers).json()[0]["id"]
    client.post(f"/api/v1/tasks/{task_id}/submissions", headers=employee_headers, json={"note": "原提交"})
    change = client.post(f"/api/v1/tasks/{task_id}/change-requests", headers=employee_headers, json={"reason": "申请修改"}).json()

    assert client.post(f"/api/v1/admin/change-requests/{change['id']}/reject", headers=admin_headers, json={"reason": " "}).status_code == 422
    rejected = client.post(f"/api/v1/admin/change-requests/{change['id']}/reject", headers=admin_headers, json={"reason": "当前证据完整"})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_employee_cannot_submit_more_than_three_photos():
    client, employee, _ = setup_client()
    headers = {"Authorization": f"Bearer {employee}"}
    task_id = client.get("/api/v1/tasks/today", headers=headers).json()[0]["id"]
    response = client.post(f"/api/v1/tasks/{task_id}/submissions", headers=headers, json={"photo_keys": ["1", "2", "3", "4"]})
    assert response.status_code == 422
