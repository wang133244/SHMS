# Kindergarten Personnel MVP Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with tests. The current workspace is not a Git repository, so do not create commits.

**Goal:** Implement a runnable MVP for six-position staff tasks and strict role-scoped RAG in a native WeChat mini-program backed by FastAPI, PostgreSQL/pgvector, and LangGraph.

**Architecture:** Keep task generation, authorization, and task state transitions in deterministic FastAPI services. Persist business and knowledge records in PostgreSQL; LangGraph is a read-only orchestration layer that receives server-derived user and position scope. The WeChat mini-program provides role-specific employee and admin views and never owns authorization decisions.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic Settings, PostgreSQL, pgvector, LangGraph, pytest, native WeChat Mini Program (WXML/WXSS/JavaScript).

**Spec:** `docs/superpowers/specs/mvp开发文档.md`; requirements cross-check: `docs/superpowers/specs/需求分析文档-MVP-v1.0.md`.

## Global Constraints

- Only roles are administrator and ordinary employee.
- Fixed positions are 后勤、保安、保健、保育、厨房、业务人员; each position currently has at most one active employee.
- Ordinary staff access only their own task data and published knowledge for their server-derived position.
- Only administrators upload, parse, review, and publish Excel-backed knowledge.
- Excel parsing creates drafts; incomplete or unreviewed content is neither executable nor retrievable.
- Non-security positions generate tasks only on configured Monday-Friday workdays; holidays and school breaks do not generate tasks. Security schedule rules are explicit and the current single guard receives assigned security tasks directly.
- AI has no write tools. Task generation and transitions are deterministic Python rules.
- RAG answers require retrieved, published, same-position citations; otherwise return the exact refusal: `当前已审核工作细则未包含此要求，请联系管理员确认。`
- User task submissions are append-only and limited to three photos. An approved change request reopens the task; a rejected request requires a reason and keeps the existing submission.
- Do not include deployment environment, domain, or production scheduler configuration in the implementation scope.

---

## File Structure

```text
backend/
  pyproject.toml
  .env.example
  app/main.py
  app/core/{config.py,security.py,dependencies.py}
  app/db/{base.py,session.py}
  app/models/{enums.py,staff.py,task.py,knowledge.py,audit.py}
  app/schemas/{auth.py,staff.py,task.py,knowledge.py,chat.py}
  app/repositories/{staff.py,tasks.py,knowledge.py}
  app/services/{auth.py,tasks.py,calendar.py,excel_import.py,knowledge.py,chat.py}
  app/agents/position_qa.py
  app/api/{auth.py,me.py,tasks.py,admin.py,chat.py}
  tests/{conftest.py,test_auth.py,test_authorization.py,test_task_rules.py,test_task_state.py,test_excel_import.py,test_rag_scope.py}
miniapp/
  app.js
  app.json
  app.wxss
  project.config.json
  services/{request.js,auth.js}
  utils/{roles.js,format.js}
  pages/{login,home,tasks,task-detail,chat,profile,admin-dashboard,admin-tasks,admin-knowledge,admin-management}/
```

---

### Task 1: Backend project foundation and test harness

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`

**Interfaces:**
- `Settings`: database URL, JWT secret, WeChat credentials, LLM settings, upload directory, token expiry.
- `create_app() -> FastAPI`: app factory with `/health` endpoint and `/api/v1` router root.
- `get_db()`: request-scoped SQLAlchemy session dependency.

- [ ] Add failing `GET /health` test asserting `{"status":"ok"}`.
- [ ] Run `cd backend; python -m pytest tests/test_health.py -q`; confirm import/route failure.
- [ ] Add minimal FastAPI app, settings and session factory. Use SQLite only for pure app/unit tests; PostgreSQL/pgvector remains the configured application database.
- [ ] Re-run the health test and confirm pass.
- [ ] Add `.env.example` with placeholders only; never put real credentials in the repository.

### Task 2: Domain models, schemas, and database constraints

**Files:**
- Create: `backend/app/models/enums.py`
- Create: `backend/app/models/staff.py`
- Create: `backend/app/models/task.py`
- Create: `backend/app/models/knowledge.py`
- Create: `backend/app/models/audit.py`
- Create: `backend/app/schemas/staff.py`
- Create: `backend/app/schemas/task.py`
- Create: `backend/app/schemas/knowledge.py`
- Create: `backend/tests/test_models.py`

**Interfaces:**
- `Role`: `admin | employee`; `PositionCode`: six fixed岗位 codes; task, calendar, review, and publication enums.
- ORM entities: `Position`, `Staff`, `WorkCalendar`, `TaskTemplate`, `TaskInstance`, `TaskSubmission`, `ChangeRequest`, `KnowledgeDocument`, `KnowledgeChunk`, `AuditLog`.
- Employee phone, employee number, and bound OpenID are unique. Task instances are unique by `(template_id, staff_id, due_date)`. Submission versions are unique by `(task_instance_id, version)`.

- [ ] Write tests for fixed position seeds and uniqueness constraints.
- [ ] Run model tests and confirm they fail because entities are missing.
- [ ] Implement SQLAlchemy 2 declarative models and database-level unique/check constraints.
- [ ] Re-run tests; verify duplicate staff phone and duplicate task instance are rejected.

### Task 3: Authentication and server-side authorization

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/core/dependencies.py`
- Create: `backend/app/repositories/staff.py`
- Create: `backend/app/services/auth.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/api/me.py`
- Create: `backend/tests/test_auth.py`
- Create: `backend/tests/test_authorization.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- `exchange_wechat_code(code: str) -> WeChatIdentity`: injectable provider adapter; test mode can inject a deterministic adapter.
- `bind_or_resolve_staff(identity: WeChatIdentity) -> LoginResult`: matches normalized phone to active staff, binds OpenID once, returns `pending_binding` when absent.
- `get_current_staff(...) -> Staff`: validates bearer token and loads the employee from server-controlled claims.
- `require_admin(staff) -> Staff`: rejects non-admin users with HTTP 403.

- [ ] Write tests for matched phone, unmatched phone, inactive employee, duplicate OpenID, employee blocked from admin API, and admin accepted.
- [ ] Run auth tests and verify expected failures.
- [ ] Implement signed access tokens, auth dependencies, login and `/me`; never trust client-supplied staff or position IDs.
- [ ] Re-run all auth tests and verify staff scope comes from the authenticated database record.

### Task 4: Calendar rules and idempotent task generation

**Files:**
- Create: `backend/app/services/calendar.py`
- Create: `backend/app/repositories/tasks.py`
- Create: `backend/app/services/tasks.py`
- Create: `backend/app/api/tasks.py`
- Create: `backend/tests/test_task_rules.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- `is_workday(target_date, calendar_overrides) -> bool`: explicit override wins; otherwise Monday-Friday excluding school holidays/breaks.
- `template_occurs(template, target_date, calendar) -> bool`: pure function for daily, weekday, weekly weekday, monthly rule, semester range, and explicit security weekend rule.
- `generate_tasks_for_date(db, target_date) -> GenerationResult`: only published/enabled valid templates; assigns the sole active employee for a position; inserts idempotently and records anomalies instead of guessing.
- `list_my_tasks(db, current_staff, target_date=None) -> list[TaskInstance]`: always scopes by authenticated staff ID.

- [ ] Test Monday-Friday, weekends, holiday override, make-up workday, school break, each supported recurrence, security weekend, missing employee/template fields, and duplicate invocation.
- [ ] Run task rule tests and confirm missing implementation failures.
- [ ] Implement pure date functions and transactional generation using database uniqueness for idempotency.
- [ ] Re-run rule tests and add API test proving employee cannot fetch another employee's task by guessed ID.

### Task 5: Append-only task submissions and change-request state machine

**Files:**
- Modify: `backend/app/services/tasks.py`
- Create: `backend/app/schemas/task.py`
- Create: `backend/app/api/tasks.py`
- Create: `backend/app/api/admin.py`
- Create: `backend/tests/test_task_state.py`

**Interfaces:**
- `submit_task(db, task_id, current_staff, note, photo_keys) -> TaskSubmission`: pending tasks only; maximum 3 photos; allocates next version atomically.
- `request_task_change(db, task_id, current_staff, reason) -> ChangeRequest`: submitted tasks only.
- `review_change_request(db, request_id, admin, approve, reason=None) -> ChangeRequest`: rejection reason required; approval reopens task but never deletes submissions.

- [ ] Write transition tests for submit, duplicate submit, request, approve, re-submit version increment, reject with reason, reject without reason, and cross-user operation.
- [ ] Run tests and observe state-machine failures.
- [ ] Implement transitions with row locking/transaction boundaries and audit entries.
- [ ] Re-run transition tests and confirm historical submissions remain unchanged.

### Task 6: Deterministic Excel draft ingestion and admin publication

**Files:**
- Create: `backend/app/services/excel_import.py`
- Create: `backend/app/services/knowledge.py`
- Create: `backend/app/repositories/knowledge.py`
- Create: `backend/app/api/admin.py`
- Create: `backend/tests/test_excel_import.py`

**Interfaces:**
- `parse_workbook(file_bytes, filename) -> ParsedWorkbook`: only `.xlsx`; yields source sheet/row, raw cells, inferred position only from explicit sheet/column mapping, and `needs_review` where ambiguous.
- `create_import_drafts(db, admin, parsed) -> ImportResult`: saves document metadata and creates unpublished knowledge chunks/template drafts.
- `publish_template(db, admin, template_id) -> TaskTemplate`: validates recurrence, dates, time, position, owner/routing and content before enabling.
- `publish_chunk(db, admin, chunk_id) -> KnowledgeChunk`: only admin; keeps source document, sheet and row.

- [ ] Build tiny in-memory XLSX fixtures and test explicit mapping, merged/blank inherited cells, ambiguous row, unsupported extension, file hash, and source row preservation.
- [ ] Run import tests and confirm parser/service failure.
- [ ] Implement parser using `openpyxl` read-only/data-only mode; do not use an LLM to fill missing duties or recurrence.
- [ ] Re-run tests; prove unpublished drafts are excluded from task generation and retrieval.

### Task 7: Strict position-scoped RAG and LangGraph read-only flow

**Files:**
- Create: `backend/app/agents/position_qa.py`
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/api/chat.py`
- Modify: `backend/app/repositories/knowledge.py`
- Create: `backend/tests/test_rag_scope.py`

**Interfaces:**
- `retrieve_published_chunks(db, position_id, query, limit) -> list[KnowledgeChunk]`: SQL enforces `position_id` and published status before vector ranking.
- `build_position_qa_graph(llm) -> CompiledGraph`: nodes are question scope validation, scoped retrieval, answer/refusal, citation validation; graph has no write tools.
- `ask_position_question(db, current_staff, question) -> ChatResponse`: derives position from authenticated staff, ignores client-supplied position, returns exact refusal on empty/insufficient evidence or invalid citations.

- [ ] Test that employee A cannot retrieve position B chunks, drafts never retrieve, invalid model citations are refused, no-model/no-evidence refusal is exact, and graph has no mutation tools.
- [ ] Run RAG tests and confirm missing behavior.
- [ ] Implement pgvector retrieval with mandatory SQL filters and a structured LLM response adapter; return source filename/version/sheet/row.
- [ ] Re-run RAG tests. Use a fake LLM only at the generation boundary; keep authorization/retrieval tests against the real repository logic.

### Task 8: Admin APIs, audit coverage, and API integration

**Files:**
- Modify: `backend/app/api/admin.py`
- Create: `backend/app/api/calendar.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_admin_api.py`

**Interfaces:**
- Admin CRUD for employees, templates, calendar overrides, import drafts, knowledge publication, and change-request review.
- Each sensitive mutation appends an `AuditLog` with actor, action, resource, timestamp, and safe before/after summary.

- [ ] Test employee cannot call any admin route, admin can CRUD in-scope resources, rejection requires reason, and sensitive actions append audit rows.
- [ ] Run API tests and confirm failures.
- [ ] Implement route composition and request schemas; ensure file/photo content and access credentials are redacted from logs.
- [ ] Run the full backend suite.

### Task 9: Native WeChat Mini Program foundations and employee flows

**Files:**
- Create: `miniapp/app.js`
- Create: `miniapp/app.json`
- Create: `miniapp/app.wxss`
- Create: `miniapp/project.config.json`
- Create: `miniapp/services/request.js`
- Create: `miniapp/services/auth.js`
- Create: `miniapp/pages/login/`
- Create: `miniapp/pages/home/`
- Create: `miniapp/pages/tasks/`
- Create: `miniapp/pages/task-detail/`
- Create: `miniapp/pages/chat/`
- Create: `miniapp/pages/profile/`

**Interfaces:**
- `request(path, options)`: attaches token, decodes API errors, clears expired session.
- `loginWithWechat()`: obtains wx.login code and phone authorization credential; server supplies role and position.
- Employee pages use only `/me`, `/tasks/*`, `/chat/ask`; no page controls authorization.

- [ ] Create route smoke checks for all WXML/JS/JSON page names and verify mini-program JSON parses.
- [ ] Add minimal login, employee home/today list, task detail submission/change request, chat citations, and profile screens in WXML/WXSS.
- [ ] Verify no client-selected position or role is sent as authority; test API adapters with local fixture responses.
- [ ] If WeChat DevTools CLI is installed, run its project validation; otherwise run JSON parsing and static route checks and report the limitation.

### Task 10: Admin mini-program flows and final verification

**Files:**
- Create: `miniapp/pages/admin-dashboard/`
- Create: `miniapp/pages/admin-tasks/`
- Create: `miniapp/pages/admin-knowledge/`
- Create: `miniapp/pages/admin-management/`
- Modify: `miniapp/app.json`
- Modify: `miniapp/app.js`
- Create: `backend/README.md`
- Create: root `README.md`

**Interfaces:**
- Admin dashboard loads summary counts and pending review items.
- Admin task page creates/reviews/publishes deterministic templates and handles change requests.
- Admin knowledge page uploads `.xlsx`, shows parser drafts/source rows, and publishes chunks.
- Admin management page maintains staff and calendar overrides.

- [ ] Add page route checks and API adapter tests for the four admin areas.
- [ ] Implement admin views with role-based navigation as presentation only; backend remains authoritative.
- [ ] Write local development instructions, environment variables, migration/init steps, test commands, and WeChat DevTools opening instructions. Do not claim a production deployment recipe.
- [ ] Run `python -m pytest` in `backend`, parse all mini-program JSON files, scan for hard-coded secrets, and verify all routes resolve.
- [ ] Report implemented vs deferred items explicitly.

## Coverage Review

- User roles and six positions: Tasks 2, 3, 9, 10.
- Phone-to-OpenID login and binding: Task 3.
- Strong role and position isolation: Tasks 3, 4, 7, 8.
- Work calendar, recurrence, idempotent deterministic tasks, security exception: Task 4.
- Append-only submissions and change state machine: Task 5.
- Admin-only Excel import, review and publication: Task 6 and Task 8.
- Strict sourced LangGraph RAG and fixed refusal: Task 7.
- Employee/admin mini-program navigation and flows: Tasks 9 and 10.
- Auditing, constraints and error handling: Tasks 2, 5, 8.
- Deployment is explicitly out of scope: Global Constraints and Task 10.
