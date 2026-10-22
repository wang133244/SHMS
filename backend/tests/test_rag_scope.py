from fastapi.testclient import TestClient

from app.main import create_app


def test_employee_only_retrieves_published_chunks_for_own_position():
    client = TestClient(create_app("sqlite://"))
    client.post("/api/v1/dev/seed")
    token = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]
    response = client.post(
        "/api/v1/chat/ask",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "保安周末需要做什么", "position": "security"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "当前已审核工作细则未包含此要求，请联系管理员确认。"
    assert response.json()["citations"] == []


def test_admin_is_only_role_allowed_to_upload_knowledge():
    client = TestClient(create_app("sqlite://"))
    client.post("/api/v1/dev/seed")
    token = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]
    response = client.post(
        "/api/v1/admin/knowledge-documents/import-excel",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("tasks.xlsx", b"not-an-xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 403
