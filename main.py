import json
from pathlib import Path
import re

#import library


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
    return None


def detect_encoding_error(text):
    return None


def detect_url(text):
    return None


def detect_personal_info(text):
    return None


def detect_number(text):
    # ตรวจเลขทั่วไป แต่ไม่นับเลขใน URL, Email และเบอร์โทร

    if not isinstance(text, str) or not text:
        return False

    temp_text = text

    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

    url_pattern = (
        r"https?://\S+|"
        r"www\.\S+|"
        r"(?<!@)\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,63}(?::\d+)?(?:/\S*)?"
    )

    mobile_pattern = (
        r"(?<!\d)"
        r"(?:(?:\+?66)(?:[\s./-]*\(0\))?[\s./-]*[689]\d|0[689]\d)"
        r"[\s./-]*\d{3}[\s./-]*\d{4}"
        r"(?!\d)"
    )

    landline_pattern = (
        r"(?<!\d)"
        r"(?:(?:0[2-7]\d?|(?:\+?66)(?:[\s./-]*\(0\))?[\s./-]*[2-7]\d?))"
        r"[\s./-]*\d{3}[\s./-]*\d{3,4}"
        r"(?!\d)"
    )

    contextual_phone_pattern = (
        r"(?:โทร(?:ศัพท์)?\.?|เบอร์(?:โทร(?:ศัพท์)?)?|"
        r"tel(?:ephone)?\.?|phone|hotline)"
        r"\s*[:：]?\s*"
        r"(?:\+?\d[\d()./-]*(?:\s+\d[\d()./-]*){0,3})"
        r"(?:\s*(?:ต่อ|ext\.?|extension)\s*\d+)?"
    )

    temp_text = re.sub(email_pattern, " ", temp_text, flags=re.IGNORECASE)
    temp_text = re.sub(url_pattern, " ", temp_text, flags=re.IGNORECASE)
    temp_text = re.sub(contextual_phone_pattern, " ", temp_text, flags=re.IGNORECASE)
    temp_text = re.sub(mobile_pattern, " ", temp_text)
    temp_text = re.sub(landline_pattern, " ", temp_text)

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
    return text


def clean_html(text):
    return text


def clean_zero_width_space(text):
    return text


def clean_different_unicode(text):
    return text


def clean_stacked_tone_mark(text):
    return text


def clean_platform_text(text):
    return text


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
