from io import BytesIO

from openpyxl import Workbook

from app.services.excel_import import parse_workbook


def workbook_bytes(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "保健工作细则"
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_parser_keeps_position_and_source_row_and_marks_unknown_rule_for_review():
    data = workbook_bytes([
        ["序号", "周期", "时间", "工作职责", "工作要求"],
        [1, "每日", "7:40-7:50", "晨间巡查", "查看健康记录"],
        [2, "", "", "临时任务", "根据园长安排执行"],
    ])

    result = parse_workbook(data, "2025秋后勤.xlsx")
    rows = result.rows
    assert rows[0].position_code == "health"
    assert rows[0].source_row == 2
    assert rows[0].frequency == "daily"
    assert rows[0].needs_review is False
    assert rows[1].needs_review is True


def test_parser_rejects_non_xlsx_and_unknown_position_instead_of_guessing():
    data = workbook_bytes([["任务"], ["内容"]])
    assert parse_workbook(data, "other.xlsx").rows[0].needs_review
    try:
        parse_workbook(data, "other.csv")
    except ValueError as error:
        assert ".xlsx" in str(error)
    else:
        raise AssertionError("expected unsupported file type")
