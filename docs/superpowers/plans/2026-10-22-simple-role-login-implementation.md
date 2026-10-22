# 简化岗位登录与角色首页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为本地演示提供 `0001`、`1001`–`5001` 简单工号和统一 `123456` 密码，并让不同角色登录后在卡通校园首页看到对应功能入口。

**Architecture:** 后端在认证路由前增加集中式演示账号别名解析，将简单工号映射到现有种子账号，不改数据库结构且保留旧账号。小程序登录页展示快捷账号，首页沿用现有校园插画并以角色配置渲染功能卡片，所有卡片连接已有页面。

**Tech Stack:** FastAPI、SQLAlchemy、pytest、微信原生小程序 WXML/WXSS/JavaScript。

**Spec:** `docs/superpowers/specs/2026-10-22-simple-role-login-design.md`

## Global Constraints

- 简单账号必须是 `0001`、`1001`、`2001`、`3001`、`4001`、`5001`。
- 简单演示密码统一为 `123456`。
- 旧账号和旧密码继续有效。
- 不新增数据库表，不移除既有业务数据。
- 登录后继续使用 `miniapp/assets/login/campus-landscape-cc0.webp` 卡通校园视觉。

---

### Task 1: Add backend demo-account aliases

**Files:**
- Modify: `backend/app/services/auth.py`
- Modify: `backend/app/api/auth.py`
- Test: `backend/tests/test_password_login.py`

**Interfaces:**
- Produces `DEMO_ACCOUNT_ALIASES`, `DEMO_PASSWORD`, and `resolve_demo_login(employee_no, password)` in `backend/app/services/auth.py`.
- `password_login` and `dev_login` consume the resolver before querying `Staff`.

- [ ] **Step 1: Write the failing tests**

Add a test that posts each simple employee number with `123456`, expects status 200, and checks the returned role/position. Add an administrator case for `0001`, a wrong-password case, and assert the response exposes `login_employee_no` equal to the simple number.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run from `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_password_login.py -q
```

Expected: the new simple-login cases fail with HTTP 401 and the new response field is absent.

- [ ] **Step 3: Implement the alias resolver**

Use a single mapping such as:

```python
DEMO_PASSWORD = "123456"
DEMO_ACCOUNT_ALIASES = {
    "0001": "ADMIN-001",
    "1001": "EMP-LOGISTICS",
    "2001": "EMP-HEALTH",
    "3001": "EMP-CARE",
    "4001": "EMP-KITCHEN",
    "5001": "EMP-BUSINESS",
}
```

`resolve_demo_login` returns `(canonical_employee_no, True)` only when the alias and `123456` match; otherwise it returns `(employee_no.strip(), False)`. Keep canonical login on the existing password hash path. For alias login, require the simple password before loading the canonical staff record. Return `login_employee_no` from both password and dev login responses, using the submitted alias when present and the canonical employee number otherwise.

- [ ] **Step 4: Run focused tests to verify they pass**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_password_login.py -q
```

Expected: all password-login tests pass.

- [ ] **Step 5: Commit the backend change**

```powershell
git add backend/app/services/auth.py backend/app/api/auth.py backend/tests/test_password_login.py
git commit -m "feat: support simple role login aliases"
```

### Task 2: Add login-page quick account controls

**Files:**
- Modify: `miniapp/pages/login/index.js`
- Modify: `miniapp/pages/login/index.wxml`
- Modify: `miniapp/pages/login/index.wxss`

**Interfaces:**
- Produces `demoAccounts` page data and `selectDemoAccount` event handler.
- Uses the existing `app.setSession` and `/auth/password-login` request flow.

- [ ] **Step 1: Add static UI assertions as a lightweight test**

Create a PowerShell check that reads the three files and asserts the six simple account values, `selectDemoAccount`, and the quick-account class are present. Run it before editing and confirm it fails because those strings do not exist.

- [ ] **Step 2: Implement quick account data and event handling**

Add account objects for administrator and five positions with `employeeNo`, `label`, and `password: '123456'`. Implement `selectDemoAccount(event)` to copy the selected values into `employeeNo` and `password`, clear the error, and leave the existing manual login path unchanged.

- [ ] **Step 3: Add the WXML and WXSS controls**

Render a compact “演示账号快捷登录” strip below the password input using a `wx:for` list of buttons. Keep the card readable on narrow screens and reuse the existing orange/blue palette.

- [ ] **Step 4: Run the static check**

Run the same PowerShell assertion and expect `PASS`.

- [ ] **Step 5: Commit the login-page change**

```powershell
git add miniapp/pages/login/index.js miniapp/pages/login/index.wxml miniapp/pages/login/index.wxss
git commit -m "feat: add simple account quick login"
```

### Task 3: Rebuild the role-aware cartoon home dashboard

**Files:**
- Modify: `miniapp/pages/home/index.js`
- Modify: `miniapp/pages/home/index.wxml`
- Modify: `miniapp/pages/home/index.wxss`

**Interfaces:**
- Consumes `app.globalData.session` fields `role`, `position`, `employee_no`, and `login_employee_no`.
- Produces `roleLabel`, `positionLabel`, and a `quickActions` array with URLs `/pages/tasks/index`, `/pages/chat/index`, `/pages/profile/index`, and `/pages/admin/index`.

- [ ] **Step 1: Add static role-action assertions**

Write a PowerShell check requiring the page files to contain administrator and all five position labels plus the four existing page URLs. Run it before implementation and confirm failure.

- [ ] **Step 2: Implement role configuration in `index.js`**

Define label maps for `admin`, `logistics`, `health`, `care`, `kitchen`, and `business`. Build role-specific actions: administrators get “园务管理、员工账号、任务模板、审核记录” cards routed to the admin page; employees get “今日任务、岗位问答、我的账号、岗位工作台” cards routed to the existing task/chat/profile/task pages. Preserve pending-assignment handling and logout.

- [ ] **Step 3: Implement the shared cartoon layout**

Use the existing campus image as an absolute background, add a translucent tint, greeting text, role badge, and responsive rounded action cards. Keep the pending-assignment state functional and visually consistent.

- [ ] **Step 4: Run the static check and JavaScript syntax check**

Run the role-action PowerShell check and, if Node is available, `node --check miniapp/pages/home/index.js` and `node --check miniapp/pages/login/index.js`. Expected: all checks pass.

- [ ] **Step 5: Commit the home-dashboard change**

```powershell
git add miniapp/pages/home/index.js miniapp/pages/home/index.wxml miniapp/pages/home/index.wxss
git commit -m "feat: add role-aware cartoon home dashboard"
```

### Task 4: Full verification and repository setup

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`
- Review: `docs/superpowers/specs/2026-10-22-simple-role-login-design.md`
- Review: all files changed in Tasks 1–3

- [ ] **Step 1: Document the simple credentials**

Update the backend development credential table to list `0001` and `1001`–`5001` with password `123456`, explicitly marking old credentials as compatibility accounts.

- [ ] **Step 2: Run the complete backend suite**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: exit code 0 and no failed tests.

- [ ] **Step 3: Run frontend static checks**

Parse `miniapp/app.json` with PowerShell `ConvertFrom-Json`; run both Node syntax checks; assert all required role labels, account IDs, and navigation URLs.

- [ ] **Step 4: Initialize and connect Git**

```powershell
cd ..
git init
git branch -M main
git remote add origin https://github.com/wang133244/SHMS.git
git add .
git commit -m "feat: simplify role login and add cartoon dashboards"
```

If `origin` already exists, update it with `git remote set-url origin https://github.com/wang133244/SHMS.git` instead of adding a second remote.

- [ ] **Step 5: Push when GitHub authentication is available**

```powershell
git push -u origin main
```

If the remote contains an unrelated initial commit, fetch it and merge with `--allow-unrelated-histories` after reviewing the diff; do not force-push.
