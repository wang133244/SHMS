from datetime import date
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import create_app


def setup_admin():
    client = TestClient(create_app("sqlite://"))
    client.post("/api/v1/dev/seed")
    token = client.post("/api/v1/auth/dev-login", json={"employee_no": "ADMIN-001"}).json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}


def test_admin_cannot_add_second_active_employee_to_same_position():
    client, headers = setup_admin()
    response = client.post("/api/v1/admin/staff", headers=headers, json={
        "name": "第二名保健", "employee_no": "EMP-HEALTH-2", "phone": "13800000008", "password": "Health2@2026", "position_code": "health"
    })
    assert response.status_code == 409


def test_only_published_complete_templates_generate_idempotent_tasks():
    client, headers = setup_admin()
    draft = client.post("/api/v1/admin/task-templates", headers=headers, json={
        "position_code": "health", "title": "工作日巡查", "frequency": "daily", "schedule_rule": {},
        "time_range": "08:00-08:30", "due_time": "09:00", "content": "查看健康记录"
    })
    assert draft.status_code == 201
    template_id = draft.json()["id"]
    assert client.post(f"/api/v1/admin/task-templates/{template_id}/publish", headers=headers).status_code == 200
    target = date.today().isoformat()
    generated = client.post(f"/api/v1/admin/tasks/generate?target_date={target}", headers=headers)
    assert generated.status_code == 200
    first_count = generated.json()["created"]
    second_count = client.post(f"/api/v1/admin/tasks/generate?target_date={target}", headers=headers).json()["created"]
    assert first_count >= 1
    assert second_count == 0


def test_incomplete_template_cannot_be_published():
    client, headers = setup_admin()
    draft = client.post("/api/v1/admin/task-templates", headers=headers, json={
        "position_code": "health", "title": "缺截止时间", "frequency": "daily", "schedule_rule": {},
        "time_range": "08:00-08:30", "content": "工作要求"
    })
    result = client.post(f"/api/v1/admin/task-templates/{draft.json()['id']}/publish", headers=headers)
    assert result.status_code == 422


def test_admin_can_complete_imported_template_draft_before_publishing():
    client, headers = setup_admin()
    draft = client.post("/api/v1/admin/task-templates", headers=headers, json={
        "position_code": "health", "title": "待补充职责", "frequency": "daily", "schedule_rule": {},
        "content": "核对健康记录"
    })
    template_id = draft.json()["id"]
    updated = client.patch(f"/api/v1/admin/task-templates/{template_id}", headers=headers, json={
        "time_range": "08:00-08:30", "due_time": "09:00", "acceptance_criteria": "记录完整"
    })
    assert updated.status_code == 200
    assert updated.json()["status"] == "draft"
    assert client.post(f"/api/v1/admin/task-templates/{template_id}/publish", headers=headers).status_code == 200


def test_template_list_includes_fields_needed_to_review_drafts():
    client, headers = setup_admin()
    created = client.post("/api/v1/admin/task-templates", headers=headers, json={
        "position_code": "health", "title": "草稿字段", "frequency": "weekly", "schedule_rule": {"weekday": 2},
        "time_range": "08:00-08:30", "due_time": "09:00", "content": "核对记录", "acceptance_criteria": "有记录"
    })
    response = client.get("/api/v1/admin/task-templates", headers=headers)
    item = next(row for row in response.json() if row["id"] == created.json()["id"])
    assert item["schedule_rule"] == {"weekday": 2}
    assert item["acceptance_criteria"] == "有记录"


def test_admin_can_classify_unknown_knowledge_chunk_before_publishing():
    client, headers = setup_admin()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "职责清单"
    sheet.append(["工作职责", "工作要求"])
    sheet.append(["巡查", "查看指定区域"])
    content = BytesIO()
    workbook.save(content)
    imported = client.post("/api/v1/admin/knowledge-documents/import-excel", headers=headers, files={
        "file": ("unclassified.xlsx", content.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    })
    document_id = imported.json()["id"]
    chunk = client.get(f"/api/v1/admin/knowledge-documents/{document_id}/drafts", headers=headers).json()["chunks"][0]
    assert chunk["position_code"] is None
    updated = client.patch(f"/api/v1/admin/knowledge-chunks/{chunk['id']}", headers=headers, json={"position_code": "business"})
    assert updated.status_code == 200
    assert updated.json()["position_code"] == "business"
    assert client.post(f"/api/v1/admin/knowledge-chunks/{chunk['id']}/publish", headers=headers).status_code == 200


def test_admin_dashboard_reports_review_and_task_counts():
    client, headers = setup_admin()
    response = client.get("/api/v1/admin/dashboard", headers=headers)
    assert response.status_code == 200
    assert {"active_staff", "today_tasks", "overdue_tasks", "pending_change_requests", "draft_chunks"} <= response.json().keys()


def test_admin_can_list_pending_change_requests():
    client, headers = setup_admin()
    employee_token = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]
    employee_headers = {"Authorization": f"Bearer {employee_token}"}
    task_id = client.get("/api/v1/tasks/today", headers=employee_headers).json()[0]["id"]
    client.post(f"/api/v1/tasks/{task_id}/submissions", headers=employee_headers, json={"note": "待审核的工作记录"})
    client.post(f"/api/v1/tasks/{task_id}/change-requests", headers=employee_headers, json={"reason": "需要补充工作说明"})

    response = client.get("/api/v1/admin/change-requests", headers=headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    item = items[0]
    staff = next(member for member in client.get("/api/v1/admin/staff", headers=headers).json() if member["employee_no"] == "EMP-HEALTH")
    task = client.get(f"/api/v1/tasks/{task_id}", headers=employee_headers).json()
    assert item == {
        "id": 1,
        "task_id": task_id,
        "task_title": task["title"],
        "requester_id": staff["id"],
        "requester_name": staff["name"],
        "position_code": "health",
        "reason": "需要补充工作说明",
        "status": "pending",
    }


def test_employee_cannot_list_pending_change_requests():
    client, _ = setup_admin()
    token = client.post("/api/v1/auth/dev-login", json={"employee_no": "EMP-HEALTH"}).json()["access_token"]
    response = client.get("/api/v1/admin/change-requests", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
