import json

from openpyxl import Workbook
import pytest

from review_analysis import review_input as source


def make_teacher_workbook(path, *, count=400, duplicate=False, bad_text=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = source.TEACHER_SHEET
    sheet.append(["review_id", "text", "coder_A", "หมายเหตุ / กรณีกำกวม"])
    for index in range(1, count + 1):
        review_id = "ID-1" if duplicate and index in (1, 2) else f"ID-{index}"
        text = f"ต้นฉบับ {index}" if bad_text != index else None
        sheet.append([review_id, text, f"ห้ามอ่าน {index}", f"หมายเหตุ {index}"])
    decoy = workbook.create_sheet("สัดส่วนที่สุ่ม")
    decoy.append(["text", "review_id"])
    decoy.append(["ห้ามเป็นรีวิว", "DECOY"])
    workbook.save(path)
    workbook.close()


def test_teacher_excel_reads_only_required_sheet_columns_and_keeps_duplicate_ids(tmp_path):
    path = tmp_path / "teacher.xlsx"
    make_teacher_workbook(path, duplicate=True)
    records = source.load_teacher_excel(path)
    assert len(records) == 400
    assert len({record.record_id for record in records}) == 400
    assert records[0].record_id == "teacher_400_0001"
    assert records[0].review_id == records[1].review_id == "ID-1"
    assert records[0].sheet_name == source.TEACHER_SHEET
    assert records[0].source_row == 2 and records[-1].source_row == 401
    assert [record.text for record in records[:2]] == ["ต้นฉบับ 1", "ต้นฉบับ 2"]
    assert source.duplicate_review_ids(records) == {"ID-1": 2}


def test_teacher_excel_reports_actual_missing_text_and_wrong_count(tmp_path):
    missing = tmp_path / "missing.xlsx"
    make_teacher_workbook(missing, bad_text=17)
    with pytest.raises(ValueError, match="แถว 18: text ว่าง"):
        source.load_teacher_excel(missing)
    short = tmp_path / "short.xlsx"
    make_teacher_workbook(short, count=399)
    with pytest.raises(ValueError, match="ต้องมีข้อความ 400 แถว แต่พบ 399"):
        source.load_teacher_excel(short)


def test_legacy_json_schema_and_manifest_round_trip(tmp_path):
    legacy = tmp_path / "cleaned_data.json"
    legacy.write_text(json.dumps(["หนึ่ง", "สอง"], ensure_ascii=False), encoding="utf-8")
    records = source.load_records(legacy)
    assert [record.text for record in records] == ["หนึ่ง", "สอง"]
    assert [record.record_id for record in records] == ["input_000001", "input_000002"]
    manifest = tmp_path / "input_records.json"
    source.write_record_manifest(manifest, records, legacy)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["record_count"] == 2
    assert payload["records"][0]["text"] == "หนึ่ง"
    bad = tmp_path / "bad.json"
    bad.write_text('{"text": "wrong schema"}', encoding="utf-8")
    with pytest.raises(ValueError, match="array"):
        source.load_records(bad)
