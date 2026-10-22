from datetime import date

from fastapi import Depends, FastAPI
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.api import admin, auth, chat, tasks
from app.db.base import Base
from app.db.session import build_engine, engine as default_engine, get_db
from app.models import Position, Staff, TaskInstance, TaskTemplate
from app.models.enums import EmploymentStatus, Frequency, PositionCode, PublicationStatus, Role, TaskStatus
from app.core.security import hash_password


def _ensure_password_column(engine) -> None:
    if inspect(engine).has_table("staff") and "password_hash" not in {column["name"] for column in inspect(engine).get_columns("staff")}:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE staff ADD COLUMN password_hash VARCHAR(256)"))


def _seed(db: Session) -> None:
    position_names = [
        (PositionCode.LOGISTICS, "后勤"),
        (PositionCode.SECURITY, "保安"),
        (PositionCode.HEALTH, "保健"),
        (PositionCode.CARE, "保育"),
        (PositionCode.KITCHEN, "厨房"),
        (PositionCode.BUSINESS, "业务人员"),
    ]
    existing_positions = {item.code: item for item in db.query(Position).all()}
    for code, name in position_names:
        if code not in existing_positions:
            position = Position(code=code, name=name)
            db.add(position)
            existing_positions[code] = position
    db.flush()
    staff_by_no = {staff.employee_no: staff for staff in db.query(Staff).all()}
    legacy_security_demo = staff_by_no.get("EMP-SECURITY")
    if (
        legacy_security_demo is not None
        and legacy_security_demo.name == "保安老师"
        and legacy_security_demo.phone == "13800000002"
        and legacy_security_demo.role is Role.EMPLOYEE
        and legacy_security_demo.password_hash is None
    ):
        legacy_security_demo.employment_status = EmploymentStatus.INACTIVE
    seed_accounts = [
        ("园务管理员", "ADMIN-001", "13800000000", None, Role.ADMIN, "Admin@2026"),
        ("保健老师", "EMP-HEALTH", "13800000001", PositionCode.HEALTH, Role.EMPLOYEE, "Health@2026"),
        ("后勤老师", "EMP-LOGISTICS", "13800000003", PositionCode.LOGISTICS, Role.EMPLOYEE, "Logi@2026"),
        ("保育老师", "EMP-CARE", "13800000004", PositionCode.CARE, Role.EMPLOYEE, "Care@2026"),
        ("厨房老师", "EMP-KITCHEN", "13800000005", PositionCode.KITCHEN, Role.EMPLOYEE, "Kitchen@2026"),
        ("业务老师", "EMP-BUSINESS", "13800000006", PositionCode.BUSINESS, Role.EMPLOYEE, "Biz@2026"),
    ]
    for name, employee_no, phone, position_code, role, password in seed_accounts:
        staff = staff_by_no.get(employee_no)
        if staff is None:
            staff = Staff(name=name, employee_no=employee_no, phone=phone, position_id=existing_positions[position_code].id if position_code else None, role=role, employment_status=EmploymentStatus.ACTIVE)
            db.add(staff)
            staff_by_no[employee_no] = staff
        if staff.password_hash is None:
            staff.password_hash = hash_password(password)
    db.flush()
    template = db.query(TaskTemplate).filter(TaskTemplate.title == "晨间巡查").first()
    if template is None:
        template = TaskTemplate(position_code=PositionCode.HEALTH, title="晨间巡查", frequency=Frequency.DAILY, schedule_rule={}, content="检查晨间卫生与健康记录", status=PublicationStatus.PUBLISHED)
        db.add(template)
        db.flush()
    if db.query(TaskInstance).filter(TaskInstance.template_id == template.id, TaskInstance.staff_id == staff_by_no["EMP-HEALTH"].id, TaskInstance.due_date == date.today()).first() is None:
        db.add(TaskInstance(template_id=template.id, template_version=1, staff_id=staff_by_no["EMP-HEALTH"].id, position_code_snapshot=PositionCode.HEALTH, due_date=date.today(), status=TaskStatus.PENDING, generation_reason="seed"))
    db.commit()


def create_app(database_url: str | None = None) -> FastAPI:
    app = FastAPI(title="幼儿园人员与岗位职责 MVP")
    if database_url:
        engine = build_engine(database_url)
        Base.metadata.create_all(engine)
        _ensure_password_column(engine)

        def test_get_db():
            db = Session(engine)
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = test_get_db
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(tasks.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/v1/dev/seed")
    def seed(db: Session = Depends(get_db)):
        _seed(db)
        return {"status": "seeded"}

    return app


Base.metadata.create_all(default_engine)
_ensure_password_column(default_engine)
app = create_app()
