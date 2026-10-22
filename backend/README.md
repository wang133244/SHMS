# 后端本地开发

在 `backend` 目录执行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

开发服务器地址为 `http://127.0.0.1:8000`，接口文档为 `/docs`。

开发测试数据库通过 `POST /api/v1/dev/seed` 补齐开发账号和示例数据。小程序支持管理员分配的工号密码登录；本地开发账号如下（仅用于开发联调）。推荐使用简单工号，旧工号仍可兼容登录：

| 身份/岗位 | 简单工号 | 演示密码 | 兼容旧工号/密码 |
| --- | --- | --- | --- |
| 管理员 | `0001` | `123456` | `ADMIN-001` / `Admin@2026` |
| 后勤 | `1001` | `123456` | `EMP-LOGISTICS` / `Logi@2026` |
| 保健 | `2001` | `123456` | `EMP-HEALTH` / `Health@2026` |
| 保育 | `3001` | `123456` | `EMP-CARE` / `Care@2026` |
| 厨房 | `4001` | `123456` | `EMP-KITCHEN` / `Kitchen@2026` |
| 业务人员 | `5001` | `123456` | `EMP-BUSINESS` / `Biz@2026` |

不会自动生成保安账号；请在管理员“员工与岗位”中新增。创建时可以先选“待分配”，之后由管理员分配岗位。旧数据库升级只会为 `staff` 表增加密码哈希列，不删除员工或其他业务数据。微信手机号登录仍可使用，正式微信流程需配置 AppID/Secret 并由服务端交换凭证。

开发专用接口 `POST /api/v1/auth/dev-login` 仅用于自动化测试和本地联调，不在小程序登录页展示。

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

正式数据库配置为 PostgreSQL + pgvector。将 `DATABASE_URL` 指向 PostgreSQL 后，向量检索使用 pgvector；SQLite 仅用作本地测试回退。
