"""One occurrence audit workbook; all run statistics go to the terminal."""
from collections import Counter, defaultdict
from io import BytesIO
from openpyxl import Workbook
from review_analysis import analyze_tfidf as tf
from review_analysis import pos_rules as pos
from review_analysis.merge_clusters import check_excel_lock, excel_length, style_sheet

HEADERS = ["ลำดับ Input ของ cleaned_data.json (เริ่มจาก 1)", "ข้อความรีวิวต้นฉบับตาม Input",
           "ตำแหน่ง token ก่อนกรอง (เริ่มจาก 1)", "token", "POS ที่ทำนาย",
           "ชนิดคำที่พบใน WordNet", "สถานะการยืนยัน", "ผ่าน noun_verb หรือไม่",
           "ผ่าน remove_adj_adv_conj หรือไม่", "ผ่าน noun_verb_adj หรือไม่", "เหตุผล"]


def occurrence_rows(reviews, documents, tagged, stopwords, lexicon):
    if not len(reviews) == len(documents) == len(tagged):
        raise ValueError("Audit alignment mismatch: document count")
    for index, (review, tokens, tags) in enumerate(zip(reviews, documents, tagged), 1):
        if "".join(tokens) != review or len(tokens) != len(tags):
            raise ValueError(f"Audit alignment mismatch: Input {index}")
        for position, (token, tag) in enumerate(zip(tokens, tags), 1):
            if tf.classify_token(token, stopwords) != "usable":
                continue
            evidence = pos.decide(tag, lexicon.lookup(token))
            flags = [pos.accepts(mode, evidence) for mode in pos.MODES[1:]]
            yield [index, review, position, token, str(tag) if tag is not None else "UNKNOWN",
                   ", ".join(sorted(evidence.wordnet)), evidence.status, *flags, evidence.reason]


def write_review(path, rows, input_path):
    check_excel_lock(path)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "ตรวจ POS และ WordNet"
    sheet.append(HEADERS)
    counts, words = Counter(), defaultdict(set)
    total_words = set()
    examples = {}
    for row_number, row in enumerate(rows, 2):
        if row_number > 1048576:
            raise ValueError("Audit เกินจำนวนแถวสูงสุดของ Excel")
        if any(isinstance(v, str) and excel_length(v) > 32767 for v in row):
            raise ValueError(f"Input {row[0]} token {row[2]}: ข้อความเกินข้อจำกัด Excel; ไม่ตัดข้อความ")
        sheet.append(row)
        counts[row[6]] += 1
        words[row[6]].add(row[3])
        total_words.add(row[3])
        if row[3] in {"อร่อย", "สะอาด", "ความสะอาด", "ร้าน", "นะคะ"}:
            examples.setdefault((row[3], row[4], row[5], row[6]), row)
    style_sheet(sheet, (22, 95, 20, 24, 17, 24, 30, 20, 26, 22, 75))
    for cells in sheet:
        for cell in cells:
            if isinstance(cell.value, str):
                cell.data_type = "s"
    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_bytes(buffer.getvalue())
    except PermissionError as exc:
        raise PermissionError(f"กรุณาปิด Excel: เขียน {path} ไม่ได้") from exc
    print(f"Audit Input = {input_path.resolve()} (ลำดับอ้างถึง cleaned_data.json เมื่อใช้ค่าเริ่มต้น)")
    total = sum(counts.values())
    print(f"Base-usable occurrences={total}; unique words={len(total_words)}")
    for status in (pos.CONFIRMED, pos.CONFLICT, pos.POS_ONLY, pos.UNKNOWN):
        print(f"{status}: occurrences={counts[status]} ({counts[status]/total:.2%})" if total else f"{status}: occurrences=0 (N/A)")
        print(f"  unique={len(words[status])} / {len(total_words)} ({len(words[status])/len(total_words):.2%})" if total_words else "  unique=0 (N/A)")
    print("คำไม่ซ้ำอาจอยู่หลายสถานะในคนละบริบท จึงไม่ควรรวมร้อยละของคำไม่ซ้ำ")
    for key, row in examples.items():
        print(f"ตัวอย่างจริง {key}: Input {row[0]}, token {row[2]}: {row[1]}")
    for token in {"อร่อย", "สะอาด", "ความสะอาด", "ร้าน", "นะคะ"} - {key[0] for key in examples}:
        print(f"{token}: ไม่พบ occurrence ที่ผ่านการกรองพื้นฐาน; ไม่สรุปว่า WordNet ไม่พบคำ")
