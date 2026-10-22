from fastapi.testclient import TestClient

from app.main import create_app


def test_employee_can_upload_task_photo_with_jpeg_signature():
    client = TestClient(create_app("sqlite://"))
    client.post("/api/v1/dev/seed")
    token = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]
    response = client.post(
        "/api/v1/tasks/uploads",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("proof.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
    )
    assert response.status_code == 201
    assert response.json()["key"].startswith("tasks/")


def test_task_photo_with_mismatched_file_signature_is_rejected():
    client = TestClient(create_app("sqlite://"))
    client.post("/api/v1/dev/seed")
    token = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]
    response = client.post(
        "/api/v1/tasks/uploads",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("proof.jpg", b"not-a-real-image", "image/jpeg")},
    )
    assert response.status_code == 415


def test_non_image_upload_is_rejected():
    client = TestClient(create_app("sqlite://"))
    client.post("/api/v1/dev/seed")
    token = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]
    response = client.post(
        "/api/v1/tasks/uploads",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("proof.txt", b"text", "text/plain")},
    )
    assert response.status_code == 415
