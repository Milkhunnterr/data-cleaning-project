"""
extract_text.py
---------------
สกัดข้อความรีวิวจากไฟล์ Excel หลายไฟล์ แล้วรวมออกมาเป็น JSON array

รองรับสองโหมด:
  1. โฟลเดอร์ปกติ  → อ่าน .xlsx โดยตรงในโฟลเดอร์นั้น
  2. โฟลเดอร์ data  → อ่าน .xlsx ที่อยู่ภายในไฟล์ .zip ในโฟลเดอร์นั้น
     (สแกนหา .zip ทุกไฟล์ แล้วอ่าน .xlsx ข้างในผ่าน BytesIO)

วิธีใช้ (โหมดโฟลเดอร์ปกติ):
    python extract_text.py --input-dir "./excel" --output "./data.json"

วิธีใช้ (โหมดโฟลเดอร์ที่มี ZIP):
    python extract_text.py --input-dir "./data" --output "./data.json"

dependency:
    pip install openpyxl
"""

import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

import openpyxl


# ─────────────────────────────────────────────────────────────────────────────
# ฟังก์ชัน: สกัดรีวิวจาก workbook object (ใช้ร่วมกันทั้งสองโหมด)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_from_workbook(wb, display_name: str) -> list[str]:
    """
    รับ openpyxl workbook และชื่อที่ใช้แสดงผล
    คืนรายการข้อความจากชีต 'reviews' คอลัมน์ G ตั้งแต่แถว 3

    ยกเว้น: ValueError ถ้าไม่พบชีต 'reviews'
    """
    # ตรวจว่ามีชีต 'reviews' หรือไม่
    if "reviews" not in wb.sheetnames:
        raise ValueError("ไม่พบชีตชื่อ 'reviews'")

    ws = wb["reviews"]
    reviews: list[str] = []

    # วนอ่านทุกแถวตั้งแต่แถวที่ 3 เป็นต้นไป (col G = index 7)
    for row in ws.iter_rows(min_row=3, min_col=7, max_col=7):
        cell = row[0]

        # ข้ามเซลล์ที่ไม่มีค่า
        if cell.value is None:
            continue

        # ตรวจประเภท: ต้องเป็น str เท่านั้น
        if not isinstance(cell.value, str):
            print(
                f"  [เตือน] {display_name} แถว {cell.row}: "
                f"ค่าไม่ใช่ข้อความ (ประเภท {type(cell.value).__name__}) — ข้าม"
            )
            continue

        # ข้ามข้อความที่ว่างเปล่า (strip() ใช้แค่ตรวจ ไม่แก้ค่าจริง)
        if not cell.value.strip():
            continue

        # เก็บข้อความดิบ — ห้ามแก้ไขเด็ดขาด
        reviews.append(cell.value)

    return reviews


# ─────────────────────────────────────────────────────────────────────────────
# ฟังก์ชัน: สกัดรีวิวจากไฟล์ .xlsx บนดิสก์
# ─────────────────────────────────────────────────────────────────────────────

def extract_reviews_from_file(xlsx_path: Path) -> list[str]:
    """
    อ่านไฟล์ .xlsx บนดิสก์ คืนรายการรีวิวจากชีต 'reviews' คอลัมน์ G

    ยกเว้น: ValueError ถ้าไม่พบชีต 'reviews'
             RuntimeError ถ้าเปิดไฟล์ไม่ได้
    """
    try:
        # read_only=True เพื่อไม่แก้ไขต้นฉบับ, data_only=True เพื่อดึงค่าจากสูตร
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    except Exception as exc:
        raise RuntimeError(f"เปิดไฟล์ไม่ได้: {exc}") from exc

    try:
        return _extract_from_workbook(wb, xlsx_path.name)
    finally:
        wb.close()


# ─────────────────────────────────────────────────────────────────────────────
# ฟังก์ชัน: สกัดรีวิวจากไฟล์ .xlsx ภายใน ZIP (อ่านผ่าน BytesIO)
# ─────────────────────────────────────────────────────────────────────────────

def extract_reviews_from_zip_entry(
    zf: zipfile.ZipFile, entry_name: str, zip_filename: str
) -> list[str]:
    """
    อ่านไฟล์ .xlsx จาก entry ภายใน zipfile object โดยใช้ BytesIO
    ไม่สกัดไฟล์ลงดิสก์ — ทุกอย่างเกิดใน RAM

    display_name ที่ใช้แสดงเตือน: "ชื่อzip/ชื่อentry"

    ยกเว้น: ValueError ถ้าไม่พบชีต 'reviews'
             RuntimeError ถ้าอ่าน entry ไม่ได้
    """
    # ชื่อที่ใช้แสดงในข้อความเตือน เช่น "Dream_Team_2.1.zip/01_xx.xlsx"
    entry_basename = Path(entry_name).name
    display_name = f"{zip_filename}/{entry_basename}"

    try:
        # อ่าน bytes ของ .xlsx เข้า RAM แล้วห่อด้วย BytesIO
        data = zf.read(entry_name)
        xlsx_buffer = io.BytesIO(data)
        wb = openpyxl.load_workbook(xlsx_buffer, read_only=True, data_only=True)
    except Exception as exc:
        raise RuntimeError(f"อ่าน entry ไม่ได้: {exc}") from exc

    try:
        return _extract_from_workbook(wb, display_name)
    finally:
        wb.close()


# ─────────────────────────────────────────────────────────────────────────────
# ฟังก์ชัน: รวบรวมรีวิวจากโฟลเดอร์ (โหมดไฟล์บนดิสก์)
# ─────────────────────────────────────────────────────────────────────────────

def collect_reviews_from_dir(input_dir: Path) -> list[str]:
    """
    ค้นหา .xlsx โดยตรงในโฟลเดอร์ (ไม่รวมโฟลเดอร์ย่อย)
    เรียงตามชื่อไฟล์จากน้อยไปมาก
    """
    xlsx_files = sorted(
        [
            f for f in input_dir.glob("*.xlsx")
            if not f.name.startswith("~$")  # ข้ามไฟล์ชั่วคราวของ Excel
        ],
        key=lambda f: f.name,
    )

    if not xlsx_files:
        print(f"[ผิดพลาด] ไม่พบไฟล์ .xlsx ในโฟลเดอร์: {input_dir}")
        return []

    all_reviews: list[str] = []

    for xlsx_path in xlsx_files:
        print(f"\nกำลังอ่าน: {xlsx_path.name}")
        try:
            file_reviews = extract_reviews_from_file(xlsx_path)
        except ValueError as exc:
            print(f"  [เตือน] {xlsx_path.name}: {exc} — ข้ามไฟล์นี้")
            continue
        except RuntimeError as exc:
            print(f"  [ผิดพลาด] {xlsx_path.name}: {exc} — ข้ามไฟล์นี้")
            continue

        print(f"  -> สกัดได้ {len(file_reviews):,} รีวิว")
        all_reviews.extend(file_reviews)

    return all_reviews


# ─────────────────────────────────────────────────────────────────────────────
# ฟังก์ชัน: รวบรวมรีวิวจากโฟลเดอร์ที่มีไฟล์ ZIP (โหมด ZIP)
# ─────────────────────────────────────────────────────────────────────────────

def collect_reviews_from_zips(input_dir: Path) -> list[str]:
    """
    ค้นหาไฟล์ .zip ในโฟลเดอร์ input_dir (ไม่รวมโฟลเดอร์ย่อย)
    เรียง ZIP จากน้อยไปมาก จากนั้นสำหรับแต่ละ ZIP:
      - เรียงรายชื่อ .xlsx ภายใน ZIP จากน้อยไปมาก
      - ข้าม entry ที่เป็นโฟลเดอร์ หรือชื่อขึ้นต้นด้วย ~$
      - อ่านแต่ละ .xlsx ผ่าน BytesIO (ไม่แตะดิสก์)
    """
    zip_files = sorted(
        [f for f in input_dir.glob("*.zip")],
        key=lambda f: f.name,
    )

    if not zip_files:
        print(f"[ผิดพลาด] ไม่พบไฟล์ .zip ในโฟลเดอร์: {input_dir}")
        return []

    all_reviews: list[str] = []

    for zip_path in zip_files:
        print(f"\n=== เปิด ZIP: {zip_path.name} ===")

        try:
            zf = zipfile.ZipFile(zip_path, "r")
        except Exception as exc:
            print(f"  [ผิดพลาด] เปิด ZIP ไม่ได้: {exc} — ข้าม")
            continue

        with zf:
            # กรองเฉพาะ entry ที่เป็น .xlsx และไม่ใช่โฟลเดอร์
            xlsx_entries = sorted(
                [
                    name for name in zf.namelist()
                    if name.lower().endswith(".xlsx")
                    and not name.endswith("/")                    # ไม่ใช่โฟลเดอร์
                    and not Path(name).name.startswith("~$")     # ไม่ใช่ชั่วคราว
                ],
                key=lambda name: name,  # เรียงตาม path ภายใน ZIP
            )

            if not xlsx_entries:
                print(f"  [เตือน] ไม่พบไฟล์ .xlsx ใน {zip_path.name} — ข้าม")
                continue

            for entry_name in xlsx_entries:
                entry_basename = Path(entry_name).name
                print(f"\n  กำลังอ่าน: {entry_name}")
                try:
                    file_reviews = extract_reviews_from_zip_entry(
                        zf, entry_name, zip_path.name
                    )
                except ValueError as exc:
                    print(f"    [เตือน] {entry_basename}: {exc} — ข้ามไฟล์นี้")
                    continue
                except RuntimeError as exc:
                    print(f"    [ผิดพลาด] {entry_basename}: {exc} — ข้ามไฟล์นี้")
                    continue

                print(f"    -> สกัดได้ {len(file_reviews):,} รีวิว")
                all_reviews.extend(file_reviews)

    return all_reviews


# ─────────────────────────────────────────────────────────────────────────────
# ฟังก์ชัน: ตัดสินใจโหมดและเรียกใช้ฟังก์ชันที่เหมาะสม
# ─────────────────────────────────────────────────────────────────────────────

def collect_reviews(input_dir: Path) -> list[str]:
    """
    ตรวจโฟลเดอร์ input_dir:
      - ถ้ามีไฟล์ .zip อยู่ → ใช้โหมด ZIP
      - ถ้ามีแต่ .xlsx      → ใช้โหมดไฟล์ปกติ
      - ถ้าไม่มีเลย         → แจ้งเตือนแล้วคืน list ว่าง
    """
    has_zip = any(input_dir.glob("*.zip"))
    has_xlsx = any(
        f for f in input_dir.glob("*.xlsx") if not f.name.startswith("~$")
    )

    if has_zip:
        print("[โหมด] พบไฟล์ .zip — อ่านจาก ZIP")
        return collect_reviews_from_zips(input_dir)
    elif has_xlsx:
        print("[โหมด] พบไฟล์ .xlsx — อ่านจากโฟลเดอร์โดยตรง")
        return collect_reviews_from_dir(input_dir)
    else:
        print(f"[ผิดพลาด] ไม่พบไฟล์ .xlsx หรือ .zip ในโฟลเดอร์: {input_dir}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """กำหนดและแยก command-line arguments"""
    parser = argparse.ArgumentParser(
        description=(
            "สกัดข้อความรีวิวจากไฟล์ Excel (.xlsx) และบันทึกเป็น JSON array\n"
            "รองรับทั้งโฟลเดอร์ที่มี .xlsx โดยตรง และโฟลเดอร์ที่มีไฟล์ .zip ซึ่งภายในบรรจุ .xlsx"
        )
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        metavar="DIR",
        help="โฟลเดอร์ที่เก็บไฟล์ .xlsx หรือ .zip",
    )
    parser.add_argument(
        "--output",
        required=True,
        metavar="FILE",
        help="ไฟล์ output เช่น ./data.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    # ตรวจว่าโฟลเดอร์ input มีอยู่จริง
    if not input_dir.is_dir():
        print(f"[ผิดพลาด] ไม่พบโฟลเดอร์: {input_dir}")
        sys.exit(1)

    print(f"โฟลเดอร์ input : {input_dir.resolve()}")
    print(f"ไฟล์ output    : {output_path.resolve()}")
    print("-" * 60)

    # รวบรวมรีวิวจากทุกไฟล์ (ตัดสินใจโหมดอัตโนมัติ)
    all_reviews = collect_reviews(input_dir)

    print("\n" + "-" * 60)
    print(f"รวมทั้งหมด: {len(all_reviews):,} รีวิว")

    # ถ้าไม่ได้ข้อความเลย → ไม่เขียนทับ output เดิม
    if not all_reviews:
        print("[ผิดพลาด] ไม่มีรีวิวที่สกัดได้ — ไม่บันทึกไฟล์ output")
        sys.exit(1)

    # บันทึก JSON array ด้วย UTF-8
    # ensure_ascii=False: อีโมจิ ภาษาไทย ตัวล่องหน ออกมาตรง ๆ ไม่ถูก escape
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_reviews, f, ensure_ascii=False, indent=2)

    print(f"บันทึกเรียบร้อย -> {output_path}")


if __name__ == "__main__":
    main()
