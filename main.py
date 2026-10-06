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
    return None


def detect_personal_info(text):
    return None


def detect_number(text):
    return None


def detect_emoji(text):
    return None


def detect_newline(text):
    return None


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
    return text


def clean_personal_info(text):
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
        clean_personal_info,
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
        "hasPersonalInfo": detect_personal_info(text),
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
    