import json
import re
from pathlib import Path

#import library


# ══════════════════════════════════════════════════════════════════
#  ส่วนของเรา (B3): platform text + encoding error
# ══════════════════════════════════════════════════════════════════
_ORIGINAL_MARK = re.compile(r"\(\s*Original\s*\)", re.I)
_GOOGLE_TAG = re.compile(
    r"\(?\s*(?:Translated by Google|แปลโดย\s*Google)\s*\)?", re.I
)
_READ_MORE_TH = re.compile(r"(?:\.{2,}|\u2026)\s*อ่านเพิ่มเติม\s*,?|อ่านเพิ่มเติม\s*[,.]?\s*$")
_READ_MORE_EN = re.compile(r"(?:\.{2,}|\u2026)\s*(?:Read more|More)\s*$", re.I)

_MOJI_HINT = re.compile(r"[\u00e0\u00e2\u00c3\u00c2][\u0080-\u00ff\u0152-\u2122]|\u00ef\u00bf\u00bd")
_MOJI_RUN = re.compile(
    r"[\u0080-\u00ff\u0152\u0153\u0160\u0161\u0178\u017d\u017e"
    r"\u0192\u02c6\u02dc\u2013-\u203a\u20ac\u2122]{3,}"
)


def _remove_platform_text(text):
    parts = _ORIGINAL_MARK.split(text)
    if len(parts) > 1:
        text = parts[-1]
    for pattern in (_GOOGLE_TAG, _READ_MORE_TH, _READ_MORE_EN):
        text = pattern.sub(" ", text)
    return text.strip(" ,;")


def _to_bytes(run):
    out = bytearray()
    for ch in run:
        try:
            out += ch.encode("cp1252")
        except UnicodeEncodeError:
            out += ch.encode("latin-1")
    return bytes(out)


def _fix_mojibake(text):
    def _fix(match):
        try:
            return _to_bytes(match.group()).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return match.group()

    return _MOJI_RUN.sub(_fix, text)
# PATTERNS: กฎที่ใช้ร่วมกันระหว่าง DETECT และ CLEAN

# URL ที่ขึ้นต้นด้วย http://, https:// หรือ www.
# รองรับ URL ภาษาอังกฤษและ percent-encoding; ไม่กินข้อความไทย/อีโมจิที่ติดท้าย
_URL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_@])(?:https?://|www\.)"
    r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?"
    r"(?::[0-9]{1,5})?(?:[/?#][A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%+-]*)?",
    re.IGNORECASE,
)

# เบอร์ไทย: มือถือ 10 หลัก / โทรศัพท์พื้นฐาน 9 หลัก และรูปแบบ +66
# ช่องว่างหรือขีดคั่นได้ แต่ไม่ข้ามบรรทัด และไม่จับส่วนหนึ่งของเลขที่ยาวกว่า
_PHONE_PATTERN = re.compile(
    r"(?<![0-9A-Za-z_+])(?:"
    r"(?:0|\+66[ \t-]?)[689](?:[ \t-]?[0-9]){8}"
    r"|(?:0|\+66[ \t-]?)[2-57](?:[ \t-]?[0-9]){7}"
    r")(?![0-9])"
)

# ตรวจชื่อเฉพาะเมื่อมีบริบทพนักงาน/เจ้าหน้าที่ พร้อมคำว่า ชื่อ หรือ คุณ
# เป็นกฎเบื้องต้น ไม่ใช่ระบบรู้จำชื่อบุคคลทุกแบบ
_STAFF_NAME_PATTERN = re.compile(
    r"(?P<prefix>(?:พนักงาน|เจ้าหน้าที่)[ \t]*(?:ชื่อ[ \t]*(?:คุณ[ \t]*)?|คุณ[ \t]*))"
    r"(?!คุณ\[NAME\]|\[NAME\])(?P<name>[ก-๙A-Za-z]+"
    r"(?:[ \t]+(?!(?:ให้|ช่วย|บริการ|แนะนำ|ดูแล|ต้อนรับ|พูด|ทำ|ยิ้ม|น่ารัก|สุภาพ|ดีมาก|มาก|ค่ะ|ครับ|คะ|นะ|เป็น|ที่|และ|ได้|ไม่|มา))"
    r"[ก-๙A-Za-z]+)?)"
)


# DETECT

def detect_duplicate(review, previous_reviews):
    return None


def detect_all_foreign(text):
    return None


def detect_empty_or_emoji_only(text):
    return None


def detect_html(text):
    return None


def detect_zero_width_space(text):
    return None


def detect_different_unicode(text):
    return None


def detect_stacked_tone_mark(text):
    return None


def detect_platform_text(text):
    if not isinstance(text, str):
        return None
    return bool(
        _ORIGINAL_MARK.search(text)
        or _GOOGLE_TAG.search(text)
        or _READ_MORE_TH.search(text)
        or _READ_MORE_EN.search(text)
    )


def detect_encoding_error(text):
    if not isinstance(text, str):
        return None
    return "\ufffd" in text or _MOJI_HINT.search(text) is not None


def detect_url(text):
    """ตรวจ URL ในข้อความต้นฉบับ แล้วคืน True หรือ False"""
    return _URL_PATTERN.search(text) is not None


def detect_phone(text):
    """ตรวจเบอร์โทร โดยข้ามตัวเลขใน URL และตัวเลขที่ระบุว่าเป็นราคา"""
    url_spans = []
    for match in _URL_PATTERN.finditer(text):
        url = match.group().rstrip('.,!?;:')
        for left, right in [('(', ')'), ('[', ']')]:
            while url.endswith(right) and url.count(right) > url.count(left):
                url = url[:-1]
        url_spans.append((match.start(), match.start() + len(url)))

    for match in _PHONE_PATTERN.finditer(text):
        if any(start <= match.start() < end for start, end in url_spans):
            continue
        before = text[:match.start()]
        after = text[match.end():]
        if re.search(r"(?:฿|ราคา|ราคา[:：]|ราคาเท่ากับ)[ \t]*$", before):
            continue
        if re.match(r"[ \t]*(?:บาท|฿|THB\b)", after, re.IGNORECASE):
            continue
        return True
    return False


def detect_staff_name(text):
    """พบชื่อที่ตามหลังคำระบุพนักงาน/เจ้าหน้าที่หรือไม่"""
    return _STAFF_NAME_PATTERN.search(text) is not None



def detect_number(text):
    # ตรวจเลขทั่วไป แต่ไม่นับเลขใน URL, Email และเบอร์โทรศัพท์

    if not isinstance(text, str) or not text:
        return False

    temp_text = text

    # Email
    email_pattern = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        re.IGNORECASE
    )

    # ลบ Email
    temp_text = email_pattern.sub(" ", temp_text)

    # ลบ URL โดยใช้ pattern กลาง
    temp_text = _URL_PATTERN.sub(" ", temp_text)

    # ลบเฉพาะเลขที่เป็นเบอร์โทรจริง
    def remove_phone(match):
        before = match.string[:match.start()]
        after = match.string[match.end():]

        # ถ้าเลขอยู่ในบริบทราคา ให้เก็บไว้เป็น Number
        price_before = re.search(
            r"(?:฿|ราคา|ราคา[:：]|ราคาเท่ากับ)[ \t]*$",
            before
        )

        price_after = re.match(
            r"[ \t]*(?:บาท|฿|THB\b)",
            after,
            re.IGNORECASE
        )

        if price_before or price_after:
            return match.group()

        return " "

    temp_text = _PHONE_PATTERN.sub(remove_phone, temp_text)

    # ถ้ายังมี digit เหลืออยู่ = พบ Number/Price
    return any(char.isdigit() for char in temp_text)

def detect_emoji(text):
    #ตรวจ Emoji รวมทั้ง emoji ทั่วไป, ธง, symbol, skin tone, keycap และ emoji แบบประกอบ

    if not isinstance(text, str) or not text:
        return False

    emoji_pattern = re.compile(
        "["
        "\U0001F1E6-\U0001F1FF"  # Flags
        "\U0001F170-\U0001F1FF"  # 🅰 🆘 🆗 ฯลฯ
        "\U0001F200-\U0001F2FF"  # Enclosed ideographic emoji
        "\U0001F300-\U0001F5FF"  # Nature / Objects / Symbols
        "\U0001F600-\U0001F64F"  # Faces
        "\U0001F680-\U0001F6FF"  # Transport / Map
        "\U0001F900-\U0001F9FF"  # Supplemental emoji
        "\U0001FA00-\U0001FAFF"  # Newer emoji
        "\U00002600-\U000026FF"  # Misc symbols
        "\U00002700-\U000027BF"  # Dingbats
        "\U00002B00-\U00002BFF"  # Supplemental symbols
        "]"
    )

    if emoji_pattern.search(text):
        return True

    # Keycap เช่น 1️⃣ 2️⃣ #️⃣
    if "\u20e3" in text:
        return True

    # Emoji presentation เช่น ❤️ ☀️ ✈️
    if "\ufe0f" in text:
        return True

    # Skin tone เช่น 👍🏻 👍🏽
    if re.search(r"[\U0001F3FB-\U0001F3FF]", text):
        return True

    return False


def detect_newline(text):
    #ตรวจ line break / line separator

    if not isinstance(text, str) or not text:
        return False

    return bool(
        re.search(
            r"[\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]",
            text
        )
    )

# CLEAN

def clean_encoding_error(text):
    if not detect_encoding_error(text):
        return text
    fixed = _fix_mojibake(text)
    if detect_encoding_error(fixed):
        return text
    return fixed


def clean_html(text):
    return text


def clean_zero_width_space(text):
    return text


def clean_different_unicode(text):
    return text


def clean_stacked_tone_mark(text):
    return text


def clean_platform_text(text):
    if not detect_platform_text(text):
        return text
    return _remove_platform_text(text)


def clean_url(text):
    """ค้นหาและแทน URL เอง โดยไม่เรียก Detect; ไม่พบก็คืนข้อความเดิม"""
    spans = []
    for match in _URL_PATTERN.finditer(text):
        url = match.group().rstrip('.,!?;:')
        for left, right in [('(', ')'), ('[', ']')]:
            while url.endswith(right) and url.count(right) > url.count(left):
                url = url[:-1]
        spans.append((match.start(), match.start() + len(url)))

    # แทนจากท้ายข้อความ เพื่อไม่ให้ตำแหน่งรายการก่อนหน้าเลื่อน
    for start, end in reversed(spans):
        text = text[:start] + "[URL]" + text[end:]
    return text


def clean_phone(text):
    """ค้นหาและปิดบังเบอร์โทรเอง โดยไม่เรียก Detect"""
    url_spans = []
    for match in _URL_PATTERN.finditer(text):
        url = match.group().rstrip('.,!?;:')
        for left, right in [('(', ')'), ('[', ']')]:
            while url.endswith(right) and url.count(right) > url.count(left):
                url = url[:-1]
        url_spans.append((match.start(), match.start() + len(url)))

    matches = []
    for match in _PHONE_PATTERN.finditer(text):
        if any(start <= match.start() < end for start, end in url_spans):
            continue
        before = text[:match.start()]
        after = text[match.end():]
        if re.search(r"(?:฿|ราคา|ราคา[:：]|ราคาเท่ากับ)[ \t]*$", before):
            continue
        if re.match(r"[ \t]*(?:บาท|฿|THB\b)", after, re.IGNORECASE):
            continue
        matches.append(match)

    for match in reversed(matches):
        text = text[:match.start()] + '[PHONE]' + text[match.end():]
    return text



def clean_staff_name(text):
    """ปิดบังชื่อพนักงาน โดยคงคำนำหน้าและไม่เรียก Detect"""
    text = _STAFF_NAME_PATTERN.sub(
        lambda m: m['prefix'] + '[NAME]',
        text,
    )
    return text


def clean_number(text):
    return text


def clean_emoji(text):
    return text


def clean_newline(text):
    return text


def clean_review(text):

    clean_text = text

    cleaning_steps = [
        clean_encoding_error,
        clean_html,
        clean_zero_width_space,
        clean_different_unicode,
        clean_stacked_tone_mark,
        clean_platform_text,
        clean_url,
        clean_phone,
        clean_staff_name,
        clean_number,
        clean_emoji,
        clean_newline,
    ]

    for clean_function in cleaning_steps:
        clean_text = clean_function(clean_text)
        if not isinstance(clean_text, str):
            raise TypeError(
                f"{clean_function.__name__} ต้อง return ข้อความ (str)"
            )

    return clean_text


# ตรวจรีวิวหนึ่งรายการ และสร้างผลลัพธ์หนึ่งรายการ

def inspect_review(review, previous_reviews):
    text = review["text"]

    result = {
        "id": review["id"],
        "text": text,
        "cleanText": None,
        "isDuplicate": detect_duplicate(review, previous_reviews),
        "allForeign": detect_all_foreign(text),
        "emptyOrEmojiOnly": detect_empty_or_emoji_only(text),
        "hasHTML": detect_html(text),
        "hasZeroWidthSpace": detect_zero_width_space(text),
        "hasDifferentUnicode": detect_different_unicode(text),
        "hasStackedToneMark": detect_stacked_tone_mark(text),
        "hasPlatformText": detect_platform_text(text),
        "hasEncodingError": detect_encoding_error(text),
        "hasURL": detect_url(text),
        "hasPhoneNumber": detect_phone(text),
        "hasStaffName": detect_staff_name(text),
        "hasNumberOrPrice": detect_number(text),
        "hasEmoji": detect_emoji(text),
        "hasNewline": detect_newline(text),
    }

    result["cleanText"] = clean_review(text)
    return result


def main():
    base_dir = Path(__file__).resolve().parent
    input_path = base_dir / "mockdata.json"
    output_path = base_dir / "checkoutput.json"

    with input_path.open("r", encoding="utf-8-sig") as file:
        reviews = json.load(file)

    results = []
    previous_reviews = []

    for review in reviews:
        result = inspect_review(review, previous_reviews)
        results.append(result)
        previous_reviews.append(review)
        print(f"เรียกฟังก์ชันตรวจและ Clean แล้ว: ID {review['id']}")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"บันทึกผล {len(results)} รายการ: {output_path}")

if __name__ == "__main__":
    main()
    