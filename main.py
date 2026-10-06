import json
from pathlib import Path

#import library
import re
from pythainlp.util import reorder_vowels


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


# B2 Helper Constants & Functions
_B2_UPPER_VOWELS_SET = set('\u0e31\u0e34\u0e35\u0e36\u0e37\u0e47\u0e4d')
_B2_LOWER_VOWELS_SET = set('\u0e38\u0e39\u0e3a')
_B2_TONE_MARKS_SET = set('\u0e48\u0e49\u0e4a\u0e4b')
_B2_THANTHAKHAT_SET = set('\u0e4c')
_B2_ALL_DIACRITICS_SET = _B2_UPPER_VOWELS_SET | _B2_LOWER_VOWELS_SET | _B2_TONE_MARKS_SET | _B2_THANTHAKHAT_SET

_B2_UPPER_VOWELS = r'\u0e31\u0e34-\u0e37\u0e47\u0e4d'
_B2_LOWER_VOWELS = r'\u0e38\u0e39\u0e3a'
_B2_TONES = r'\u0e48-\u0e4b'
_B2_THANTHAKHAT = r'\u0e4c'
_B2_SARA_AM = '\u0e33'


def detect_different_unicode(text):
    if not isinstance(text, str):
        return False

    # 1. Double Sara E check (exact length == 2 Sara E)
    for m in re.finditer(r'\u0e40+', text):
        if len(m.group(0)) == 2:
            return True

    # 2. Sara Am & Nikhahit misplaced / duplicate / combined checks
    sara_am_pattern = (
        rf'\u0e33[{_B2_TONES}]|'
        rf'[{_B2_UPPER_VOWELS}{_B2_LOWER_VOWELS}][{_B2_TONES}]*\u0e33|'
        rf'\u0e33[{_B2_TONES}]*[{_B2_UPPER_VOWELS}{_B2_LOWER_VOWELS}]|'
        rf'\u0e4d[{_B2_TONES}]*\s*[\u0e32\u0e45]|'
        rf'[{_B2_TONES}]\u0e4d\s*[\u0e32\u0e45]|'
        rf'\u0e4d[\s\r\n]*[\u0e32\u0e45]|'
        rf'\u0e4d[{_B2_TONES}]*\u0e33|'
        rf'\u0e4d{{2,}}'
    )
    if re.search(sara_am_pattern, text):
        return True

    # 3. Detached diacritics after space/newline/tab or at start of string
    if re.search(r'[\s\r\n\t][\u0e31-\u0e3a\u0e47-\u0e4e]|^[\u0e31-\u0e3a\u0e47-\u0e4e]', text):
        return True

    # 4. Cluster-by-cluster analysis for misordered / conflicting diacritics
    clusters = []
    curr_diacritics = []

    for ch in text:
        if ch in _B2_ALL_DIACRITICS_SET:
            curr_diacritics.append(ch)
        else:
            if curr_diacritics:
                clusters.append(curr_diacritics)
                curr_diacritics = []
    if curr_diacritics:
        clusters.append(curr_diacritics)

    for d_list in clusters:
        dedup_d = []
        for d in d_list:
            if d not in dedup_d:
                dedup_d.append(d)

        # Tone mark before Upper Vowel or Lower Vowel
        tone_seen = False
        for d in dedup_d:
            if d in _B2_TONE_MARKS_SET:
                tone_seen = True
            elif d in _B2_UPPER_VOWELS_SET or d in _B2_LOWER_VOWELS_SET:
                if tone_seen:
                    return True

        # Conflicting tone marks or upper/lower vowels on same consonant
        tones = [d for d in d_list if d in _B2_TONE_MARKS_SET or d in _B2_THANTHAKHAT_SET]
        uppers = [d for d in d_list if d in _B2_UPPER_VOWELS_SET]
        lowers = [d for d in d_list if d in _B2_LOWER_VOWELS_SET]

        if len(set(tones)) > 1 or len(set(uppers)) > 1 or len(set(lowers)) > 1 or (uppers and lowers):
            return True

    return False


def detect_stacked_tone_mark(text):
    if not isinstance(text, str):
        return False

    # 1. Triple or more Sara E (e.g. เเเดิน)
    for m in re.finditer(r'\u0e40+', text):
        if len(m.group(0)) >= 3:
            return True

    # 2. Repeated trailing/inline vowels (e.g. าาา, ะะะ)
    if re.search(r'([\u0e30\u0e32\u0e45])\1+', text):
        return True

    # 3. Nikhahit or Sara Am repeats (e.g. ํํ, ำำ)
    if re.search(r'[\u0e4d\u0e33]{2,}', text):
        return True

    # 4. Upper/lower vowels combined with Sara Am (e.g. นิำ, จีำ, ถึ้ำ, นุ้ำ, ทูำ)
    if re.search(rf'[{_B2_UPPER_VOWELS}{_B2_LOWER_VOWELS}][{_B2_TONES}]*\u0e33|\u0e33[{_B2_TONES}]*[{_B2_UPPER_VOWELS}{_B2_LOWER_VOWELS}]', text):
        return True

    clusters = []
    curr_diacritics = []

    for ch in text:
        if ch in _B2_ALL_DIACRITICS_SET:
            curr_diacritics.append(ch)
        else:
            if curr_diacritics:
                clusters.append(curr_diacritics)
                curr_diacritics = []
    if curr_diacritics:
        clusters.append(curr_diacritics)

    for d_list in clusters:
        seen_set = set()
        for d in d_list:
            if d in seen_set:
                return True
            seen_set.add(d)

        tones_in_cluster = [d for d in d_list if d in _B2_TONE_MARKS_SET or d in _B2_THANTHAKHAT_SET]
        if len(tones_in_cluster) > 1:
            return True

        uppers_in_cluster = [d for d in d_list if d in _B2_UPPER_VOWELS_SET]
        lowers_in_cluster = [d for d in d_list if d in _B2_LOWER_VOWELS_SET]
        if len(uppers_in_cluster) > 1 or len(lowers_in_cluster) > 1:
            return True

        if uppers_in_cluster and lowers_in_cluster:
            return True

    return False


def detect_platform_text(text):
    return None


def detect_encoding_error(text):
    return None


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
    return text


def clean_html(text):
    return text


def clean_zero_width_space(text):
    return text


def clean_different_unicode(text):
    if not isinstance(text, str):
        return text

    # Split text into segments around triple or more Sara E (\u0e40{3,})
    # to avoid placeholder collisions while keeping triple Sara E untouched
    parts = re.split(r'(\u0e40{3,})', text)
    cleaned_parts = []

    for part in parts:
        if re.fullmatch(r'\u0e40{3,}', part):
            cleaned_parts.append(part)
        else:
            res = part
            # Replaces exact double Sara E (\u0e40{2})
            res = re.sub(r'(?<!\u0e40)\u0e40{2}(?!\u0e40)', '\u0e41', res)

            # 1. Clean Nikhahit + Sara Am combinations (e.g. ทํำ -> ทำ, นํ้ำ -> น้ำ, ถํ้ำ -> ถ้ำ)
            res = re.sub(rf'\u0e4d+([{_B2_TONES}]*)\u0e33', r'\1' + _B2_SARA_AM, res)

            # 3. Tone(s) + Nikhahit + Sara Aa (e.g. น้ํากัด -> น้ำกัด)
            res = re.sub(rf'([{_B2_TONES}]+)\u0e4d+\s*([\u0e32\u0e45])', r'\1' + _B2_SARA_AM, res)

            # 4. Nikhahit + Tone(s) + Sara Aa (e.g. นํ้า -> น้ำ, ถํํ้้ามรกต -> ถ้ำมรกต)
            res = re.sub(rf'\u0e4d+([{_B2_TONES}]+)\s*([\u0e32\u0e45])', r'\1' + _B2_SARA_AM, res)

            # 5. Sara Am + Tone (e.g. นำ้ -> น้ำ)
            res = re.sub(rf'\u0e33([{_B2_TONES}]+)', r'\1' + _B2_SARA_AM, res)

            # 6. Nikhahit + whitespace/newline + Sara Aa (e.g. นํ า -> นำ)
            res = re.sub(rf'\u0e4d+[\s\r\n]*([\u0e32\u0e45])', _B2_SARA_AM, res)

            # 7. Reorder Tone mark before Upper/Lower Vowel (e.g. น้ัน -> นั้น, ป่ิ -> ปิ่)
            res = re.sub(rf'([{_B2_TONES}]+)([{_B2_UPPER_VOWELS}]+)', r'\2\1', res)
            res = re.sub(rf'([{_B2_TONES}]+)([{_B2_LOWER_VOWELS}]+)', r'\2\1', res)

            res = reorder_vowels(res)
            cleaned_parts.append(res)

    return ''.join(cleaned_parts)


def clean_stacked_tone_mark(text):
    if not isinstance(text, str):
        return text

    res = text
    # Deduplicate repeated identical diacritics
    res = re.sub(rf'([{_B2_TONES}{_B2_THANTHAKHAT}])\1+', r'\1', res)
    res = re.sub(rf'([{_B2_UPPER_VOWELS}])\1+', r'\1', res)
    res = re.sub(rf'([{_B2_LOWER_VOWELS}])\1+', r'\1', res)

    return res


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
