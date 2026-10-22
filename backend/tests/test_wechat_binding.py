from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.enums import EmploymentStatus, PositionCode, Role
from app.models.staff import Position, Staff
from app.services.auth import bind_wechat_identity


def setup_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_phone_match_binds_openid_and_returns_staff():
    db = setup_db()
    position = Position(code=PositionCode.HEALTH, name="保健")
    db.add(position); db.flush()
    staff = Staff(name="保健老师", employee_no="H-1", phone="13800000001", position_id=position.id, role=Role.EMPLOYEE, employment_status=EmploymentStatus.ACTIVE)
    db.add(staff); db.commit()

    result = bind_wechat_identity(db, "openid-1", "13800000001")
    assert result.status == "bound"
    assert result.staff.openid == "openid-1"


def test_unknown_phone_stays_pending_binding():
    db = setup_db()
    result = bind_wechat_identity(db, "openid-unknown", "13900000000")
    assert result.status == "pending_binding"
    assert result.staff is None


def test_openid_cannot_be_rebound_to_another_staff():
    db = setup_db()
    position = Position(code=PositionCode.HEALTH, name="保健")
    db.add(position); db.flush()
    db.add_all([
        Staff(name="A", employee_no="A", phone="13800000001", openid="openid-A", position_id=position.id, role=Role.EMPLOYEE, employment_status=EmploymentStatus.ACTIVE),
        Staff(name="B", employee_no="B", phone="13800000002", position_id=position.id, role=Role.EMPLOYEE, employment_status=EmploymentStatus.ACTIVE),
    ])
    db.commit()

    result = bind_wechat_identity(db, "openid-A", "13800000002")
    assert result.status == "binding_conflict"
