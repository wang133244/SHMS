from datetime import date
import unittest

from app.domain.tasks import (
    CalendarDay,
    CalendarKind,
    Frequency,
    PositionCode,
    TaskStatus,
    TemplateSchedule,
    can_generate_for_date,
    next_submission_version,
    transition_task,
)


class TaskRuleTests(unittest.TestCase):
    def test_non_security_task_runs_only_on_configured_weekday(self):
        schedule = TemplateSchedule(PositionCode.HEALTH, Frequency.DAILY)

        self.assertTrue(can_generate_for_date(schedule, date(2026, 10, 21), CalendarDay(CalendarKind.WORKDAY)))
        self.assertFalse(can_generate_for_date(schedule, date(2026, 10, 24), CalendarDay(CalendarKind.WEEKEND)))
        self.assertFalse(can_generate_for_date(schedule, date(2026, 10, 21), CalendarDay(CalendarKind.HOLIDAY)))


    def test_makeup_workday_allows_weekend_task_for_non_security_position(self):
        schedule = TemplateSchedule(PositionCode.CARE, Frequency.DAILY)

        self.assertTrue(can_generate_for_date(schedule, date(2026, 10, 24), CalendarDay(CalendarKind.MAKEUP_WORKDAY)))


    def test_security_weekend_rule_is_explicit(self):
        schedule = TemplateSchedule(PositionCode.SECURITY, Frequency.SECURITY_WEEKEND)

        self.assertTrue(can_generate_for_date(schedule, date(2026, 10, 24), CalendarDay(CalendarKind.WEEKEND)))
        self.assertFalse(can_generate_for_date(schedule, date(2026, 10, 21), CalendarDay(CalendarKind.WORKDAY)))


    def test_monthly_and_semester_templates_require_explicit_match_dates(self):
        monthly = TemplateSchedule(PositionCode.KITCHEN, Frequency.MONTHLY, matching_dates=frozenset({date(2026, 10, 30)}))
        semester = TemplateSchedule(PositionCode.BUSINESS, Frequency.SEMESTER, matching_dates=frozenset({date(2026, 10, 30)}))

        self.assertTrue(can_generate_for_date(monthly, date(2026, 10, 30), CalendarDay(CalendarKind.WORKDAY)))
        self.assertFalse(can_generate_for_date(monthly, date(2026, 10, 31), CalendarDay(CalendarKind.WEEKEND)))
        self.assertTrue(can_generate_for_date(semester, date(2026, 10, 30), CalendarDay(CalendarKind.WORKDAY)))


    def test_task_change_approval_reopens_task_without_changing_submission_history(self):
        status = transition_task(TaskStatus.CHANGE_PENDING, "approve")
        self.assertIs(status, TaskStatus.PENDING)
        self.assertEqual(next_submission_version([1, 2]), 3)


    def test_change_rejection_requires_reason_and_keeps_submission(self):
        with self.assertRaisesRegex(ValueError, "reason"):
            transition_task(TaskStatus.CHANGE_PENDING, "reject", reason=" ")
        self.assertIs(transition_task(TaskStatus.CHANGE_PENDING, "reject", reason="照片不清晰"), TaskStatus.SUBMITTED)


    def test_invalid_task_transition_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "transition"):
            transition_task(TaskStatus.PENDING, "approve")
