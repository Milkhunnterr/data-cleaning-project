"""Load review inputs while preserving row-level provenance."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from openpyxl import load_workbook


TEACHER_SHEET = "open_coding"
TEACHER_EXPECTED_COUNT = 400
TEACHER_REQUIRED_COLUMNS = ("review_id", "text")


@dataclass(frozen=True)
class ReviewRecord:
    record_id: str
    review_id: object
    sheet_name: str | None
    source_row: int | None
    text: str


def checksum(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json_records(path: Path) -> list[ReviewRecord]:
    """Load the legacy pipeline schema: a JSON array containing only strings."""
    try:
        with path.open("r", encoding="utf-8-sig") as stream:
            values = json.load(stream)
    except FileNotFoundError as exc:
        raise ValueError(f"ไม่พบไฟล์ Input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Input ไม่ใช่ JSON ที่ถูกต้อง: {exc}") from exc
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError("Input JSON เดิมต้องเป็น array ที่ทุกรายการเป็น string")
    if not values:
        raise ValueError("Input ไม่มีรีวิว")
    return [
        ReviewRecord(f"input_{index:06d}", None, None, index, text)
        for index, text in enumerate(values, 1)
    ]


def load_teacher_excel(path: Path) -> list[ReviewRecord]:
    """Read only open_coding.review_id/text and preserve every worksheet row."""
    try:
        workbook = load_workbook(path, read_only=True, data_only=False)
    except FileNotFoundError as exc:
        raise ValueError(f"ไม่พบไฟล์ Input: {path}") from exc
    try:
        if TEACHER_SHEET not in workbook.sheetnames:
            raise ValueError(
                f"ไม่พบชีต {TEACHER_SHEET!r}; พบชีต {workbook.sheetnames!r}"
            )
        sheet = workbook[TEACHER_SHEET]
        header_cells = next(sheet.iter_rows(min_row=1, max_row=1), None)
        if header_cells is None:
            raise ValueError(f"ชีต {TEACHER_SHEET!r} ไม่มีหัวตาราง")
        headers = [cell.value for cell in header_cells]
        missing = [name for name in TEACHER_REQUIRED_COLUMNS if name not in headers]
        if missing:
            raise ValueError(f"ชีต {TEACHER_SHEET!r} ขาดคอลัมน์: {missing}")
        if len(headers) != len(set(headers)):
            raise ValueError(f"ชีต {TEACHER_SHEET!r} มีหัวคอลัมน์ซ้ำ")
        review_id_column = headers.index("review_id")
        text_column = headers.index("text")
        records = []
        for source_row, cells in enumerate(sheet.iter_rows(min_row=2), 2):
            review_id_cell = cells[review_id_column]
            text_cell = cells[text_column]
            review_id = review_id_cell.value
            text = text_cell.value
            if not isinstance(review_id, str) or not review_id.strip():
                kind = "ว่าง" if review_id is None or review_id == "" else f"ชนิด {type(review_id).__name__}"
                raise ValueError(f"ชีต {TEACHER_SHEET!r} แถว {source_row}: review_id {kind}")
            if text_cell.data_type == "f":
                raise ValueError(f"ชีต {TEACHER_SHEET!r} แถว {source_row}: text เป็นสูตร")
            if not isinstance(text, str) or not text.strip():
                kind = "ว่าง" if text is None or text == "" else f"ชนิด {type(text).__name__}"
                raise ValueError(f"ชีต {TEACHER_SHEET!r} แถว {source_row}: text {kind}")
            records.append(
                ReviewRecord(
                    record_id=f"teacher_400_{len(records) + 1:04d}",
                    review_id=review_id,
                    sheet_name=TEACHER_SHEET,
                    source_row=source_row,
                    text=text,
                )
            )
        if len(records) != TEACHER_EXPECTED_COUNT:
            raise ValueError(
                f"ชีต {TEACHER_SHEET!r} ต้องมีข้อความ {TEACHER_EXPECTED_COUNT} แถว "
                f"แต่พบ {len(records)} แถว"
            )
        return records
    finally:
        workbook.close()


def load_records(path: Path) -> list[ReviewRecord]:
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return load_json_records(path)
    if suffix == ".xlsx":
        return load_teacher_excel(path)
    raise ValueError("รองรับ Input เฉพาะ .json (schema เดิม) หรือ .xlsx")


def duplicate_review_ids(records: list[ReviewRecord]) -> dict[object, int]:
    counts = Counter(record.review_id for record in records if record.review_id is not None)
    return {value: count for value, count in counts.items() if count > 1}


def write_record_manifest(path: Path, records: list[ReviewRecord], input_path: Path) -> None:
    """Write traceability metadata; text is copied exactly, never normalized."""
    payload = {
        "input_path": str(input_path.resolve()),
        "input_sha256": checksum(input_path),
        "record_count": len(records),
        "records": [asdict(record) for record in records],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
