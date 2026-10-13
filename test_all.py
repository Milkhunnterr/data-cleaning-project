import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

EXPECTED_FILE = BASE_DIR / "mockdataANSWER.json"
ACTUAL_FILE = BASE_DIR / "checkoutput.json"


def load_json(path):
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def normalize_expected_item(item):
    """
    รองรับกรณีบางไฟล์ใช้ finalText
    แต่ checkoutput ใช้ cleanText
    """
    normalized = dict(item)

    if "finalText" in normalized and "cleanText" not in normalized:
        normalized["cleanText"] = normalized.pop("finalText")

    return normalized


def compare_results(expected_data, actual_data):
    expected_by_id = {
        item["id"]: normalize_expected_item(item)
        for item in expected_data
    }

    actual_by_id = {
        item["id"]: item
        for item in actual_data
    }

    all_ids = list(dict.fromkeys(
        list(expected_by_id.keys()) +
        list(actual_by_id.keys())
    ))

    passed = 0
    failed = 0

    print("\n========== TEST RESULT ==========\n")

    for case_id in all_ids:
        expected = expected_by_id.get(case_id)
        actual = actual_by_id.get(case_id)

        # Expected มี แต่ Actual ไม่มี
        if actual is None:
            failed += 1
            print(f"❌ {case_id} FAIL")
            print("   ไม่พบ ID นี้ใน checkoutput.json")
            print()
            continue

        # Actual มี แต่ Expected ไม่มี
        if expected is None:
            failed += 1
            print(f"❌ {case_id} FAIL")
            print("   ไม่มี ID นี้ใน mockdataANSWER.json")
            print()
            continue

        differences = []

        # เทียบทุก field ที่อยู่ใน Expected
        for key, expected_value in expected.items():
            actual_value = actual.get(key)

            if actual_value != expected_value:
                differences.append(
                    (key, expected_value, actual_value)
                )

        if differences:
            failed += 1
            print(f"❌ {case_id} FAIL")

            for key, expected_value, actual_value in differences:
                print(f"   Field: {key}")
                print(f"   Expected: {expected_value!r}")
                print(f"   Actual:   {actual_value!r}")

            print()

        else:
            passed += 1
            print(f"✅ {case_id} PASS")

    print("\n========== SUMMARY ==========")
    print(f"Expected ทั้งหมด : {len(expected_data)}")
    print(f"Actual ทั้งหมด   : {len(actual_data)}")
    print(f"PASS             : {passed}")
    print(f"FAIL             : {failed}")
    print("=============================\n")


def main():
    if not EXPECTED_FILE.exists():
        print(f"ไม่พบไฟล์: {EXPECTED_FILE.name}")
        return

    if not ACTUAL_FILE.exists():
        print(f"ไม่พบไฟล์: {ACTUAL_FILE.name}")
        print("ให้รัน python3 main.py ก่อน")
        return

    expected_data = load_json(EXPECTED_FILE)
    actual_data = load_json(ACTUAL_FILE)

    compare_results(
        expected_data,
        actual_data
    )


if __name__ == "__main__":
    main()