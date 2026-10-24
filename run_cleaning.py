"""
run_cleaning.py
---------------
ทำความสะอาด (Clean) ข้อมูลรีวิวจาก data.json และบันทึกผลเป็น cleaned_data.json

อ้างอิงฟังก์ชัน Detect / Clean จาก main.py ทั้งหมด — ไม่คัดลอกกฎใหม่

วิธีใช้:
    python run_cleaning.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────────
# import จาก main.py  (main.py มี if __name__ == "__main__" guard
# จึง import ได้ปลอดภัย — ส่วน mock ไม่ทำงานอัตโนมัติ)
# ────────────────────────────────────────────────────────────────────────────
from main import (
    inspect_review,          # ตรวจรีวิวครบทุก flag ตามที่ main.py กำหนด
    # import ทีละฟังก์ชัน Clean เพื่อ track ว่าแต่ละตัวถูกใช้กี่ครั้ง
    # (ลำดับเหมือน clean_review() ใน main.py ทุกประการ)
    clean_encoding_error,
    clean_html,
    clean_zero_width_space,
    clean_different_unicode,
    clean_stacked_tone_mark,
    clean_platform_text,
    clean_url,
    clean_phone,
    clean_number,
)

# ─────────────────────────────────────────────────────────────────────────────
# กำหนด path
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "data.json"
OUTPUT_PATH = BASE_DIR / "cleaned_data.json"

# ลำดับ Clean ตรงกับ cleaning_steps ใน main.py ทุกประการ
CLEAN_STEPS = [
    clean_encoding_error,
    clean_html,
    clean_zero_width_space,
    clean_different_unicode,
    clean_stacked_tone_mark,
    clean_platform_text,
    clean_url,
    clean_phone,
    clean_number,
]


# ─────────────────────────────────────────────────────────────────────────────
# ฟังก์ชัน: โหลดและตรวจรูปแบบ Input
# ─────────────────────────────────────────────────────────────────────────────

def load_input(path: Path) -> list[str]:
    """
    อ่าน JSON array ของ string จากไฟล์ path
    รองรับ UTF-8 และ UTF-8 BOM (utf-8-sig)
    ตรวจว่า:
      - เนื้อหาเป็น list
      - ทุก element เป็น str
    หากผิดรูปแบบ ให้แจ้งตำแหน่งที่ผิดแล้ว raise SystemExit
    """
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)

    # ตรวจว่าเป็น list
    if not isinstance(data, list):
        print(f"[ผิดพลาด] Input ต้องเป็น JSON array แต่พบ: {type(data).__name__}")
        sys.exit(1)

    # ตรวจว่าทุก element เป็น str
    bad_indices = [
        i for i, item in enumerate(data) if not isinstance(item, str)
    ]
    if bad_indices:
        for idx in bad_indices:
            print(
                f"[ผิดพลาด] ตำแหน่ง {idx}: ต้องเป็น string "
                f"แต่พบ {type(data[idx]).__name__} = {repr(data[idx])!r}"
            )
        print("หยุดก่อนเขียน Output เนื่องจากรูปแบบ Input ไม่ถูกต้อง")
        sys.exit(1)

    return data


# ─────────────────────────────────────────────────────────────────────────────
# ฟังก์ชัน: Clean ทีละ step พร้อมนับจำนวน
# ─────────────────────────────────────────────────────────────────────────────

def clean_with_tracking(text: str, hit_counter: dict) -> str:
    """
    ทำ Clean ตามลำดับเดิมใน main.py ทีละฟังก์ชัน
    เมื่อฟังก์ชันใดทำให้ข้อความเปลี่ยนแปลง → เพิ่ม counter ของฟังก์ชันนั้น 1
    คืนข้อความหลัง Clean ทุกขั้น
    """
    current = text
    for fn in CLEAN_STEPS:
        after = fn(current)
        if not isinstance(after, str):
            raise TypeError(f"{fn.__name__} ต้อง return str")
        # นับเฉพาะเมื่อข้อความเปลี่ยนจริงเท่านั้น
        if after != current:
            hit_counter[fn.__name__] += 1
        current = after
    return current


# ─────────────────────────────────────────────────────────────────────────────
# ฟังก์ชัน: ประมวลผลรีวิวทั้งหมด
# ─────────────────────────────────────────────────────────────────────────────

def process_reviews(raw_texts: list[str]) -> tuple[list[str], int, int, dict]:
    """
    ประมวลผลรีวิวตามลำดับเดียวกับ main.py:
      1. ห่อข้อความเป็น {"id": เลขลำดับ, "text": ข้อความ} ก่อนส่ง inspect_review
         (ID ใช้เฉพาะภายใน ไม่ปรากฏใน Input หรือ Output)
      2. ตรวจสอบทุก flag ด้วย inspect_review
      3. เก็บประวัติเพื่อตรวจซ้ำตามลำดับ (เหมือน main.py)
      4. คัดทิ้งตามเงื่อนไขเดิม: ซ้ำ / ภาษาต่างประเทศล้วน / ว่าง/อีโมจิเท่านั้น
      5. รีวิวที่ผ่าน → clean ทีละ step พร้อม track
      6. คืน (รายการที่เก็บ, จำนวนคัดทิ้ง, จำนวนที่เข้า Clean, hit_counter)
    """
    kept: list[str] = []
    discarded: int = 0
    entered_clean: int = 0           # นับรีวิวที่เข้าถึงกระบวนการ Clean จริงๆ
    previous_reviews: list[dict] = []

    # เตรียม counter เริ่มต้น 0 ทุกฟังก์ชัน
    hit_counter: dict = {fn.__name__: 0 for fn in CLEAN_STEPS}

    for idx, text in enumerate(raw_texts):
        # สร้าง dict ชั่วคราวสำหรับส่ง inspect_review — ไม่ใส่ใน Input/Output
        review = {"id": idx, "text": text}

        # ตรวจรีวิวครบทุก flag ตามฟังก์ชันเดิม
        result = inspect_review(review, previous_reviews)

        # เก็บประวัติก่อน continue เพื่อให้ตรวจซ้ำตามลำดับข้อมูลต้นฉบับ
        previous_reviews.append(review)

        # รวบรวมเหตุผลที่คัดทิ้ง (ตรงกับ main.py ทุกเงื่อนไข)
        discard_reasons = []
        if result["isDuplicate"] is True:
            discard_reasons.append("รีวิวซ้ำ")
        if result["allForeign"] is True:
            discard_reasons.append("ภาษาต่างประเทศล้วน")
        if result["emptyOrEmojiOnly"] is True:
            discard_reasons.append("ข้อความว่างหรือมีแต่อีโมจิ/สัญลักษณ์ตามกฎ")

        if discard_reasons:
            discarded += 1
            print(f"  คัดทิ้ง [{idx}]: {', '.join(discard_reasons)}")
            continue  # ไม่เข้า Clean เหมือน main.py

        # เฉพาะรีวิวที่ผ่านจึง Clean ทีละ step พร้อม track
        entered_clean += 1
        clean_text = clean_with_tracking(text, hit_counter)

        # ถ้า Clean แล้วเหลือข้อความว่าง → คัดทิ้งเหมือน main.py
        if not clean_text.strip():
            discarded += 1
            print(f"  คัดทิ้ง [{idx}]: ข้อความว่างหลัง Clean")
            continue

        kept.append(clean_text)

    return kept, discarded, entered_clean, hit_counter


# ─────────────────────────────────────────────────────────────────────────────
# ฟังก์ชัน: แสดงสรุปการใช้ Clean function
# ─────────────────────────────────────────────────────────────────────────────

def print_clean_summary(hit_counter: dict, entered_clean: int) -> None:
    """
    แสดงตารางสรุปว่าแต่ละ Clean function ทำงาน (เปลี่ยนข้อความ) กี่รีวิว
    entered_clean = จำนวนรีวิวที่ผ่านการ Detect และเข้า Clean ทั้งหมด
    ตัวเลขแต่ละฟังก์ชัน = รีวิวที่ฟังก์ชันนั้นเปลี่ยนข้อความจริง (before != after)
    """
    print("\n" + "=" * 64)
    print("  สรุปการใช้งาน Clean Function")
    print(f"  (รีวิวที่เข้ากระบวนการ Clean ทั้งหมด: {entered_clean:,} รายการ)")
    print("=" * 64)
    print(f"  {'ฟังก์ชัน':<32}  {'เปลี่ยนข้อความ':>10}  {'%':>6}")
    print("  " + "-" * 56)

    for fn in CLEAN_STEPS:
        name = fn.__name__
        count = hit_counter.get(name, 0)
        pct = (count / entered_clean * 100) if entered_clean > 0 else 0.0
        # ใส่ * เพื่อเน้นฟังก์ชันที่มีผล
        marker = " *" if count > 0 else "  "
        print(f"{marker} {name:<32}  {count:>10,}  {pct:>5.1f}%")

    print("  " + "-" * 56)
    active = sum(1 for fn in CLEAN_STEPS if hit_counter.get(fn.__name__, 0) > 0)
    print(f"   ฟังก์ชันที่มีผล: {active} / {len(CLEAN_STEPS)} ฟังก์ชัน")
    print("=" * 64)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    # ตรวจว่าไฟล์ input มีอยู่จริง
    if not INPUT_PATH.is_file():
        print(f"[ผิดพลาด] ไม่พบไฟล์ input: {INPUT_PATH}")
        sys.exit(1)

    print(f"Input  : {INPUT_PATH}")
    print(f"Output : {OUTPUT_PATH}")
    print("-" * 60)

    # โหลดและตรวจรูปแบบ Input (หยุดทันทีหากรูปแบบผิด)
    raw_texts = load_input(INPUT_PATH)
    total = len(raw_texts)
    print(f"Input ทั้งหมด: {total:,} รายการ")
    print("-" * 60)

    # ประมวลผล (อาจเกิด error ระหว่างทาง → ไม่เขียนทับ Output เดิม)
    try:
        kept, discarded, entered_clean, hit_counter = process_reviews(raw_texts)
    except Exception as exc:
        print(f"\n[ผิดพลาด] เกิดข้อผิดพลาดระหว่างประมวลผล: {exc}")
        print("ไม่เขียนทับ Output เดิม")
        sys.exit(1)

    # สรุปตัวเลขรวม
    kept_count = len(kept)
    print("\n" + "-" * 60)
    print(f"Input ทั้งหมด  : {total:,} รายการ")
    print(f"เก็บไว้        : {kept_count:,} รายการ")
    print(f"คัดทิ้ง        : {discarded:,} รายการ")

    # ตรวจความถูกต้องของตัวเลข
    if kept_count + discarded != total:
        print(
            f"[เตือน] เก็บ ({kept_count}) + คัดทิ้ง ({discarded}) "
            f"≠ Input ({total}) — มีข้อมูลสูญหาย!"
        )

    # แสดงตารางสรุป Clean function
    print_clean_summary(hit_counter, entered_clean)

    # บันทึก Output เป็น JSON array ของ string — ไม่มี id, flags, metadata
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    print(f"\nบันทึกเรียบร้อย -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
