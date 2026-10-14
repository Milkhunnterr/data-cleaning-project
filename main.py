import json
import html
import re
from pathlib import Path

#import library
HTML_ENTITY_PATTERN = re.compile(r"&(?:#\d+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]{1,31});")
HTML_TAG_PATTERN = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>")
ZERO_WIDTH_CHARS = {"\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"}
from pythainlp.util import reorder_vowels
import unicodedata


# ══════════════════════════════════════════════════════════════════
#  ส่วนของเรา (B3): platform text + encoding error
# ══════════════════════════════════════════════════════════════════

# ---------- platform text ----------
_ORIGINAL_MARK = re.compile(r"\(\s*Original\s*\)", re.I)
_GOOGLE_TAG = re.compile(
    r"[ \t]*\(?\s*(?:Translated by Google|แปลโดย\s*Google)\s*\)?[ \t]*", re.I
)
# "...อ่านเพิ่มเติม" ที่ใดก็ได้ / "อ่านเพิ่มเติม" หรือ "แสดงเพิ่มเติม" ที่ท้ายข้อความ
_READ_MORE_TH = re.compile(
    r"[ \t]*(?:\.{2,}|\u2026)\s*(?:อ่าน|แสดง)เพิ่มเติม\s*,?[ \t]*"
    r"|[ \t]*(?:อ่าน|แสดง)เพิ่มเติม\s*[,.]?\s*$"
)
_READ_MORE_EN = re.compile(
    r"[ \t]*(?:\.{2,}|\u2026)\s*(?:Read more|See more|Show more|More)\s*$", re.I
)
# ป้ายของแพลตฟอร์มที่ยืนเป็นวลีเดี่ยว (ไม่ติดกับตัวอักษรไทย/อังกฤษ)
_UI_LABEL = re.compile(
    r"(?<![A-Za-z\u0e00-\u0e7f])[ \t]*"
    r"(?:ดูคำแปล|See translation|Google Review)"
    r"(?![A-Za-z\u0e00-\u0e7f])[ \t]*",
    re.I,
)

_PLATFORM_PATTERNS = (_GOOGLE_TAG, _READ_MORE_TH, _READ_MORE_EN, _UI_LABEL)


def _tidy_spaces(text):
    """ยุบช่องว่างซ้อนที่เกิดจากการลบ และลบช่องว่างท้ายบรรทัด"""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text


def _remove_platform_text(text):
    parts = _ORIGINAL_MARK.split(text)
    if len(parts) > 1:
        text = parts[-1]
    for pattern in _PLATFORM_PATTERNS:
        text = pattern.sub(" ", text)
    return _tidy_spaces(text).strip(" ,;\n")


# ---------- encoding error ----------
# ร่องรอย mojibake: à/â/Ã/Â ตามด้วยอักขระช่วง cp1252/latin-1 หรือ "ï¿½"
_MOJI_HINT = re.compile(r"[\u00e0\u00e2\u00c3\u00c2][\u0080-\u00ff\u0152-\u2122]|\u00ef\u00bf\u00bd")
# เศษ mojibake ที่ยืนเดี่ยว เช่น "รับ Ã" (ไม่ได้เป็นส่วนหนึ่งของคำละติน)
_MOJI_RESIDUE = re.compile(r"(?<![A-Za-z\u00c0-\u00ff])[\u00c3\u00c2](?![A-Za-z\u00c0-\u00ff])")
_MOJI_RUN = re.compile(
    r"[\u0080-\u00ff\u0152\u0153\u0160\u0161\u0178\u017d\u017e"
    r"\u0192\u02c6\u02dc\u2013-\u203a\u20ac\u2122]{3,}"
)
_REPLACEMENT_CHAR = "\ufffd"
# ไบต์ที่ cp1252 ไม่มีตัวอักษรรองรับ จึงมักหายไปตอนเกิด mojibake
# ในภาษาไทยไบต์ที่หายบ่อยที่สุดคือ 0x81 (ก หรือ แ)
_LOST_BYTE_GUESS = 0x81
_MAX_GUESS_RATIO = 0.2


def _to_bytes(run):
    out = bytearray()
    for ch in run:
        try:
            out += ch.encode("cp1252")
        except UnicodeEncodeError:
            out += ch.encode("latin-1")
    return bytes(out)


def _restore_lost_thai_bytes(raw):
    """เติมไบต์ที่หายของอักษรไทย (E0 B8/B9 ?) คืนจำนวนที่เติม"""
    out = bytearray()
    guesses = 0
    i = 0
    while i < len(raw):
        b = raw[i]
        if b == 0xE0 and i + 1 < len(raw) and raw[i + 1] in (0xB8, 0xB9):
            third = raw[i + 2] if i + 2 < len(raw) else None
            out += raw[i:i + 2]
            if third is None or not (0x80 <= third <= 0xBF):
                out.append(_LOST_BYTE_GUESS)
                guesses += 1
                i += 2
            else:
                out.append(third)
                i += 3
            continue
        out.append(b)
        i += 1
    return bytes(out), guesses


def _is_plausible(decoded):
    """ผลถอดรหัสต้องเป็นไทย/ASCII/สัญลักษณ์/อีโมจิ ไม่ใช่อักษรภาษาอื่นแปลกๆ"""
    for ch in decoded:
        cp = ord(ch)
        if cp < 0x80 or 0x0E00 <= cp <= 0x0E7F:
            continue
        if cp >= 0x2000 and not ch.isalpha():  # เครื่องหมาย, อีโมจิ
            continue
        return False
    return True


def _decode_run(run):
    raw = _to_bytes(run)
    try:
        decoded = raw.decode("utf-8")
        if _is_plausible(decoded):
            return decoded
    except UnicodeDecodeError:
        pass

    repaired, guesses = _restore_lost_thai_bytes(raw)
    if guesses == 0:
        return None
    try:
        decoded = repaired.decode("utf-8")
    except UnicodeDecodeError:
        return None
    thai_count = sum(1 for ch in decoded if "\u0e00" <= ch <= "\u0e7f")
    # เดาได้เฉพาะเมื่อไบต์หายไม่มาก ถ้าหายเยอะแปลว่ากู้ไม่ได้จริง
    if thai_count == 0 or guesses / thai_count > _MAX_GUESS_RATIO:
        return None
    return decoded if _is_plausible(decoded) else None


def _fix_mojibake(text):
    def _fix(match):
        decoded = _decode_run(match.group())
        return decoded if decoded is not None else match.group()

    return _MOJI_RUN.sub(_fix, text)


# PATTERNS: กฎที่ใช้ร่วมกันระหว่าง DETECT และ CLEAN

# กฎเดิมที่ detect_number ของเพื่อนใช้อยู่ คงไว้เพื่อไม่เปลี่ยนพฤติกรรมงานอื่น
_URL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_@])(?:https?://|www\.)"
    r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?"
    r"(?::[0-9]{1,5})?(?:[/?#][A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%+-]*)?",
    re.IGNORECASE,
)

_PHONE_PATTERN = re.compile(
    r"(?<![0-9A-Za-z_+])(?:"
    r"(?:0|\+66[ \t-]?)[689](?:[ \t-]?[0-9]){8}"
    r"|(?:0|\+66[ \t-]?)[2-57](?:[ \t-]?[0-9]){7}"
    r")(?![0-9])"
)

# URL แบบ ASCII / percent-encoding: ต้องมีชื่อโดเมนและส่วนท้าย
# ไม่รองรับโดเมน/พาธภาษาไทยที่ยังไม่ได้ encode หรือโดเมนเปล่าที่ไม่มี www./scheme
_CONTACT_URL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_@])(?:https?://|www\.)"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"(?:[A-Za-z]{2,63}|xn--[A-Za-z0-9-]{2,59})"
    r"(?![A-Za-z0-9_-])"
    r"(?::[0-9]{1,5})?"
    r"(?:[/?#][A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%+-]*)?",
    re.IGNORECASE,
)

# ตรวจรูปแบบเบอร์ ไม่ยืนยันว่าเบอร์มีอยู่จริง และไม่เดาตัวอักษรที่พิมพ์ผิดเป็นเลข
_CONTACT_PHONE_PATTERN = re.compile(
    r"(?<![0-9A-Za-z_+])(?:"
    r"(?:0|\+66[ \t.-]*(?:\(0\)[ \t.-]*)?)[689](?:[ \t.-]?[0-9]){8}"
    r"|(?:0|\+66[ \t.-]*(?:\(0\)[ \t.-]*)?)[2-57](?:[ \t.-]?[0-9]){7}"
    r")(?![0-9A-Za-z_]|[.-][0-9])"
)
_CONTACT_EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.IGNORECASE
)
_PHONE_PRICE_BEFORE = re.compile(
    r"(?:ราคา(?:เท่ากับ)?|ยอด(?:เงิน|รวม)?|จำนวนเงิน|฿|THB)"
    r"[ \t]*(?:[:：=][ \t]*)?(?:฿[ \t]*)?$", re.IGNORECASE
)
_PHONE_PRICE_AFTER = re.compile(
    r"[ \t]*(?:\+\+[ \t]*)?(?:บาท|฿|THB\b)", re.IGNORECASE
)

# ต้องมีบริบทพนักงาน/เจ้าหน้าที่/สมาชิก ไม่เดาชื่อจากข้อความทั่วไป
# ใช้ตัวอักษรไทยจริง ไม่ใช้ [ก-๙] ซึ่งรวมเลขไทยและเครื่องหมายบางตัว
# stop phrases ช่วยแยกคำบรรยายที่ติดชื่อ แต่ยังไม่ใช่ระบบ NER
_STAFF_STOP = (
    r"แนะนำ|บริการ|ช่วย|ดูแล|ต้อนรับ|พูด|ยิ้ม|น่ารัก|สุภาพ|ใจดี|"
    r"ดีมาก|ให้บริการ|ให้คำ|ทำงาน|ทำให้|บอกทาง|แถม|จำได้|"
    r"ครับ|ค่ะ|คะ|นะคะ|มากๆ|เป็นพนักงาน|และ|\[NAME\]"
)
_STAFF_WORD = rf"(?:(?!(?:{_STAFF_STOP}))[ก-ฮะ-ฺเ-๎A-Za-z])+"
_STAFF_NAME_PATTERN = re.compile(
    r"(?P<prefix>(?:พนักงาน|เจ้าหน้าที่|สมาชิก)[ \t]*"
    r"(?:ชื่อ[ \t]*(?:[:：][ \t]*)?(?:(?:คุณ|นางสาว|นาย|นาง)[ \t]*)?"
    r"|(?:คุณ|นางสาว|นาย|นาง)[ \t]*))"
    r"(?!(?:(?:คุณ|นางสาว|นาย|นาง)[ \t]*)?\[NAME\])"
    rf"(?P<name>{_STAFF_WORD}(?:[ \t]+{_STAFF_WORD})?)"
)


# DETECT

def detect_duplicate(review, previous_reviews):
    current_text = review.get("text", "").strip()
    for prev in previous_reviews:
        if prev.get("text", "").strip() == current_text:
            return True
    return False


def detect_all_foreign(text):
    has_thai = any("\u0e00" <= ch <= "\u0e7f" for ch in text)
    if has_thai:
        return False
    return any(unicodedata.category(ch).startswith("L") for ch in text)


def detect_empty_or_emoji_only(text):
    if not text.strip():
        return True
    has_letters = any(unicodedata.category(ch).startswith("L") for ch in text)
    has_numbers = any(unicodedata.category(ch).startswith("N") for ch in text)
    has_punctuation = any(unicodedata.category(ch).startswith("P") for ch in text)
    if has_letters or has_numbers or has_punctuation:
        return False
    non_ws = [ch for ch in text if not ch.isspace()]
    return bool(non_ws) and all(
        unicodedata.category(ch).startswith("S") or unicodedata.category(ch) in ("Mn", "Cf")
        for ch in non_ws
    )


def detect_html(text):
    for match in HTML_ENTITY_PATTERN.findall(text):
        if html.unescape(match) != match:
            return True
    return bool(HTML_TAG_PATTERN.search(text))


def detect_zero_width_space(text):
    for i, char in enumerate(text):
        if char not in ZERO_WIDTH_CHARS:
            continue
        if char == "\u200d":
            prev_char = text[i - 1] if i > 0 else ""
            next_char = text[i + 1] if i + 1 < len(text) else ""
            if (prev_char and ord(prev_char) >= 0x2190) or (
                next_char and ord(next_char) >= 0x2190
            ):
                continue
        return True
    return False


# B2 Helper Constants & Functions
# ----------------------------------------------------------
# This section belongs to B2 only. No team-owned functions are changed.
# DifferentUnicode = alternate encoding, misplaced order, detached marks.
# StackedToneMark = duplicated/incompatible Thai combining marks.
# One malformed span may meet both rule families. Keep that evidence.

_B2_UPPER_VOWELS_SET = set('\u0e31\u0e34\u0e35\u0e36\u0e37\u0e47\u0e4d')
_B2_LOWER_VOWELS_SET = set('\u0e38\u0e39\u0e3a')
_B2_TONE_MARKS_SET = set('\u0e48\u0e49\u0e4a\u0e4b')
_B2_THANTHAKHAT_SET = set('\u0e4c')
_B2_SARA_AM = '\u0e33'

_B2_MARK_RUN = re.compile(r'[\u0e31\u0e34-\u0e3a\u0e47-\u0e4d]+')
_B2_DOUBLE_SARA_E = re.compile(r'(?<!\u0e40)\u0e40{2}(?!\u0e40)')
_B2_TRIPLE_SARA_E = re.compile(r'\u0e40{3,}')
_B2_SPLIT_AM_1 = re.compile(r'\u0e4d+([\u0e48-\u0e4b]*)[ \t]?\u0e32')
_B2_SPLIT_AM_2 = re.compile(r'([\u0e48-\u0e4b]+)\u0e4d+[ \t]?\u0e32')
_B2_REDUNDANT_AM = re.compile(r'\u0e4d+([\u0e48-\u0e4b]*)\u0e33')
_B2_AM_THEN_TONE = re.compile(r'\u0e33([\u0e48-\u0e4b]+)')
_B2_MISORDERED_TONE = re.compile(
    r'[\u0e48-\u0e4b][\u0e31\u0e34-\u0e37\u0e38-\u0e39\u0e47]'
)
_B2_DETACHED = re.compile(r'(?:^|[ \t\r\n])[\u0e31-\u0e3a\u0e47-\u0e4e]')
_B2_TAB_BEFORE_MARK = re.compile(
    r'(?<=[\u0e01-\u0e2e])\t+(?=[\u0e31-\u0e3a\u0e47-\u0e4e])'
)
_B2_SARA_AM_CONFLICT = re.compile(
    r'[\u0e31\u0e34-\u0e37\u0e38-\u0e39\u0e47][\u0e48-\u0e4b]*\u0e33|'
    r'\u0e33[\u0e48-\u0e4b]*[\u0e31\u0e34-\u0e37\u0e38-\u0e39\u0e47]'
)
_B2_REPEATED_AM_MARK = re.compile(r'[\u0e4d\u0e33]{2,}')
_B2_REPEATED_MARK = re.compile(r'([\u0e31\u0e34-\u0e3a\u0e47-\u0e4d])\1+')
_B2_DUPLICATED_TONE_AROUND_VOWEL = re.compile(
    r'([\u0e48-\u0e4b])([\u0e31\u0e34-\u0e37\u0e38-\u0e39\u0e47])\1'
)

# Single source of truth: Detect functions and detailed evidence use the
# exact same compiled patterns. Changes to rules cannot silently diverge.
_B2_DIFFERENT_RULES = (
    ('D01', 'สระเอสองตัว (เเ แทน แ)', _B2_DOUBLE_SARA_E),
    ('D02', 'นิคหิต + วรรณยุกต์ + สระอา', _B2_SPLIT_AM_1),
    ('D03', 'วรรณยุกต์ + นิคหิต + สระอา', _B2_SPLIT_AM_2),
    ('D04', 'นิคหิตเกินก่อนสระอำ', _B2_REDUNDANT_AM),
    ('D05', 'สระอำอยู่ก่อนวรรณยุกต์', _B2_AM_THEN_TONE),
    ('D06', 'วรรณยุกต์อยู่ก่อนสระบน/ล่าง', _B2_MISORDERED_TONE),
    ('D07', 'เครื่องหมายภาษาไทยแยกจากฐาน', _B2_DETACHED),
)
_B2_STACKED_RULES = (
    ('S01', 'สระเอสามตัวขึ้นไป (ไม่แก้โดยเดา)', _B2_TRIPLE_SARA_E),
    ('S02', 'นิคหิต/สระอำซ้อน', _B2_REPEATED_AM_MARK),
    ('S03', 'นิคหิตเกินก่อนสระอำ', _B2_REDUNDANT_AM),
    ('S04', 'สระบน/ล่างขัดกับสระอำ', _B2_SARA_AM_CONFLICT),
)


def _b2_conflict_reasons(run):
    """Describe a mark cluster; only conflicting marks count as stacked."""
    tones = [ch for ch in run if ch in _B2_TONE_MARKS_SET]
    karans = [ch for ch in run if ch in _B2_THANTHAKHAT_SET]
    uppers = [ch for ch in run if ch in _B2_UPPER_VOWELS_SET]
    lowers = [ch for ch in run if ch in _B2_LOWER_VOWELS_SET]
    reasons = []
    if len(tones) > 1:
        reasons.append('วรรณยุกต์ซ้ำหรือขัดกัน')
    if len(karans) > 1:
        reasons.append('ทัณฑฆาตซ้ำ')
    if tones and karans:
        reasons.append('วรรณยุกต์ชนกับทัณฑฆาต')
    if len(uppers) > 1:
        reasons.append('สระ/เครื่องหมายบนหลายตัว')
    if len(lowers) > 1:
        reasons.append('สระล่างหลายตัว')
    if uppers and lowers:
        reasons.append('สระบนและสระล่างขัดกัน')
    return reasons


def _b2_is_conflicting_run(run):
    return bool(_b2_conflict_reasons(run))


def _b2_reorder_safe_marks(match):
    """Reorder one tone after one upper/lower vowel, not conflicting runs."""
    run = match.group(0)
    if _b2_is_conflicting_run(run):
        return run
    if sum(ch in _B2_TONE_MARKS_SET for ch in run) != 1:
        return run
    return re.sub(
        r'([\u0e48-\u0e4b])([\u0e31\u0e34-\u0e37\u0e38-\u0e39\u0e47])',
        r'\2\1', run
    )


def b2_detection_evidence(text):
    """Return exact matched spans in ORIGINAL text (Python 0-based offsets).

    Each record has category, rule ID, explanation, start/end, matched text
    and Unicode code points. A span may have more than one matching rule.
    This is B2-only diagnostics; inspect_review() JSON schema is untouched.
    """
    if not isinstance(text, str):
        return []
    found = []
    for category, rules in (
        ('DifferentUnicode', _B2_DIFFERENT_RULES),
        ('StackedToneMark', _B2_STACKED_RULES),
    ):
        for rule_id, reason, pattern in rules:
            for hit in pattern.finditer(text):
                s, e = hit.span()
                if rule_id == 'D07':
                    # Regex includes the preceding whitespace, which is not
                    # the malformed Thai mark itself.
                    while s < e and text[s].isspace():
                        s += 1
                if s >= e:
                    continue
                found.append({
                    'category': category,
                    'rule_id': rule_id,
                    'reason': reason,
                    'start': s,
                    'end': e,
                    'matched': text[s:e],
                    'codepoints': ' '.join(f'U+{ord(ch):04X}' for ch in text[s:e]),
                })
    for hit in _B2_MARK_RUN.finditer(text):
        reasons = _b2_conflict_reasons(hit.group(0))
        if reasons:
            found.append({
                'category': 'StackedToneMark',
                'rule_id': 'S05',
                'reason': ' / '.join(reasons),
                'start': hit.start(),
                'end': hit.end(),
                'matched': hit.group(0),
                'codepoints': ' '.join(f'U+{ord(ch):04X}' for ch in hit.group(0)),
            })
    return sorted(found, key=lambda x: (x['start'], x['end'], x['category'], x['rule_id']))


def detect_different_unicode(text):
    """Detect Unicode variants / wrong order / detached combining marks."""
    if not isinstance(text, str):
        return False
    return any(e['category'] == 'DifferentUnicode' for e in b2_detection_evidence(text))


def detect_stacked_tone_mark(text):
    """Detect duplicated/conflicting marks, not expressive word stretching."""
    if not isinstance(text, str):
        return False
    return any(e['category'] == 'StackedToneMark' for e in b2_detection_evidence(text))



def detect_platform_text(text):
    if not isinstance(text, str):
        return None
    return bool(_ORIGINAL_MARK.search(text)) or any(
        p.search(text) for p in _PLATFORM_PATTERNS
    )


def detect_encoding_error(text):
    if not isinstance(text, str):
        return None
    return (
        _REPLACEMENT_CHAR in text
        or _MOJI_HINT.search(text) is not None
        or _MOJI_RESIDUE.search(text) is not None
    )


def detect_url(text):
    """ตรวจ URL ในข้อความต้นฉบับ แล้วคืน True หรือ False"""
    return _CONTACT_URL_PATTERN.search(text) is not None


def detect_phone(text):
    """ตรวจเบอร์โทร โดยข้ามตัวเลขใน URL และตัวเลขที่ระบุว่าเป็นราคา"""
    url_spans = []
    for match in _CONTACT_URL_PATTERN.finditer(text):
        url = match.group().rstrip('.,!?;:')
        for left, right in [('(', ')'), ('[', ']')]:
            while url.endswith(right) and url.count(right) > url.count(left):
                url = url[:-1]
        url_spans.append((match.start(), match.start() + len(url)))

    email_spans = [(m.start(), m.end()) for m in _CONTACT_EMAIL_PATTERN.finditer(text)]
    for match in _CONTACT_PHONE_PATTERN.finditer(text):
        if any(match.start() < end and match.end() > start
               for start, end in url_spans + email_spans):
            continue
        before = text[:match.start()]
        after = text[match.end():]
        if _PHONE_PRICE_BEFORE.search(before):
            continue
        if _PHONE_PRICE_AFTER.match(after):
            continue
        return True
    return False


def detect_staff_name(text):
    """ตรวจชื่อ/นามสกุลหลังบริบทพนักงาน เจ้าหน้าที่ หรือสมาชิกตามกฎ"""
    return _STAFF_NAME_PATTERN.search(text) is not None



def detect_number(text):
    # ตรวจ Number/Price
    # - นับเลขอารบิก 0-9
    # - นับเลขไทย ๐-๙
    # - นับ keycap number เช่น 1️⃣
    # - ไม่นับเลขใน URL, Email, เบอร์โทร
    # - ไม่นับ superscript เช่น ²

    if not isinstance(text, str) or not text:
        return False

    temp_text = text

    # ลบ Email ออกก่อน เพื่อไม่ให้เลขใน email ถูกนับ
    temp_text = _CONTACT_EMAIL_PATTERN.sub(" ", temp_text)

    # ลบ URL ออกก่อน
    temp_text = _URL_PATTERN.sub(" ", temp_text)

    # ลบเบอร์โทรออก ยกเว้นถ้าอยู่ในบริบทราคา
    def remove_phone(match):
        before = match.string[:match.start()]
        after = match.string[match.end():]

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

    temp_text = _CONTACT_PHONE_PATTERN.sub(remove_phone, temp_text)

    # keycap เช่น 1️⃣ 2️⃣ 3️⃣
    if re.search(r"[0-9]\ufe0f?\u20e3", temp_text):
        return True

    # เลขปกติ + เลขไทย
    return bool(re.search(r"[0-9๐-๙]", temp_text))



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
    # กู้ไม่ได้แล้ว ลบทิ้ง: อักขระแทนที่ (�) และเศษ Ã/Â ที่ยืนเดี่ยว
    junk = r"[ \t]*(?:\ufffd|" + _MOJI_RESIDUE.pattern + r")+[ \t]*"
    fixed = re.sub(junk, lambda m: " " if m.group() != m.group().strip() else "", fixed)
    fixed = _tidy_spaces(fixed).strip() if fixed != text else fixed
    return fixed if fixed else text


def clean_html(text):
    text = HTML_TAG_PATTERN.sub("", text)
    text = html.unescape(text)
    return text.replace("\u00a0", " ")


def clean_zero_width_space(text):
    # ลบตัวอักษรล่องหน ยกเว้น ZWJ ที่เชื่อมอีโมจิ
    cleaned = []
    for i, char in enumerate(text):
        if char not in ZERO_WIDTH_CHARS:
            cleaned.append(char)
            continue
        if char == "\u200d":
            prev_char = text[i - 1] if i > 0 else ""
            next_char = text[i + 1] if i + 1 < len(text) else ""
            if (prev_char and prev_char not in ZERO_WIDTH_CHARS and ord(prev_char) >= 0x2190) or (
                next_char and next_char not in ZERO_WIDTH_CHARS and ord(next_char) >= 0x2190
            ):
                cleaned.append(char)
    return "".join(cleaned)


def clean_different_unicode(text):
    """Normalize only safe encodings/order; preserve ambiguity and paragraphs."""
    if not isinstance(text, str):
        return text

    # Only EXACTLY two Sara E characters -> Sara Ae.
    text = _B2_DOUBLE_SARA_E.sub('\u0e41', text)

    # Remove tabs ONLY when between a Thai consonant and a combining mark:
    # น\t้ำ -> น้ำ. Preserve paragraph newlines and other whitespace.
    text = _B2_TAB_BEFORE_MARK.sub('', text)

    # Normal forms of split Sara Am; retain the tone where present.
    text = _B2_SPLIT_AM_2.sub(lambda m: m.group(1) + _B2_SARA_AM, text)
    text = _B2_SPLIT_AM_1.sub(lambda m: m.group(1) + _B2_SARA_AM, text)
    text = _B2_REDUNDANT_AM.sub(lambda m: m.group(1) + _B2_SARA_AM, text)
    text = _B2_AM_THEN_TONE.sub(lambda m: m.group(1) + _B2_SARA_AM, text)

    # Same tone before and after the same vowel: ช่ั่น -> ชั่น.
    # Do not guess which tone to keep if they differ, e.g. ม่้.
    text = _B2_DUPLICATED_TONE_AROUND_VOWEL.sub(r'\2\1', text)

    # Misordered pair: คร้ึม -> ครึ้ม, ไม่รู้ -> ไม่รู้.
    text = _B2_MARK_RUN.sub(_b2_reorder_safe_marks, text)
    return text


def clean_stacked_tone_mark(text):
    """Reduce identical stacked combining marks, not expressive plain vowels."""
    if not isinstance(text, str):
        return text
    # One correction can expose another malformed mark in the same cluster.
    # Iterate to a fixed point; never guess which different tone to keep.
    # Safe edits either shrink a sequence or move marks to their canonical
    # ordering; the number of required iterations is bounded by text length.
    for _ in range(len(text) + 1):
        cleaned = clean_different_unicode(_B2_REPEATED_MARK.sub(r'\1', text))
        if cleaned == text:
            return text
        text = cleaned
    return text


def clean_platform_text(text):
    if not detect_platform_text(text):
        return text
    return _remove_platform_text(text)


def clean_url(text):
    """ค้นหาและแทน URL เอง โดยไม่เรียก Detect; ไม่พบก็คืนข้อความเดิม"""
    spans = []
    for match in _CONTACT_URL_PATTERN.finditer(text):
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
    for match in _CONTACT_URL_PATTERN.finditer(text):
        url = match.group().rstrip('.,!?;:')
        for left, right in [('(', ')'), ('[', ']')]:
            while url.endswith(right) and url.count(right) > url.count(left):
                url = url[:-1]
        url_spans.append((match.start(), match.start() + len(url)))

    matches = []
    email_spans = [(m.start(), m.end()) for m in _CONTACT_EMAIL_PATTERN.finditer(text)]
    for match in _CONTACT_PHONE_PATTERN.finditer(text):
        if any(match.start() < end and match.end() > start
               for start, end in url_spans + email_spans):
            continue
        before = text[:match.start()]
        after = text[match.end():]
        if _PHONE_PRICE_BEFORE.search(before):
            continue
        if _PHONE_PRICE_AFTER.match(after):
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
    if not isinstance(text, str):
        return text

    # แปลงเลขไทย ๐-๙ เป็นเลขอารบิก 0-9
    thai_to_arabic = str.maketrans(
        "๐๑๒๓๔๕๖๗๘๙",
        "0123456789"
    )
    text = text.translate(thai_to_arabic)

    # แปลง keycap number เช่น 1️⃣ -> 1
    text = re.sub(r"([0-9])\ufe0f?\u20e3", r"\1", text)

    return text


def clean_emoji(text):
    if not isinstance(text, str):
        return text

    # กลุ่ม emoji ที่สื่ออารมณ์/ความรู้สึก
    # เช่น หน้า, สีหน้า, gesture, hand sign, heart
    emotion_emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # faces
        "\U0001F910-\U0001F92F"  # supplemental faces/gestures
        "\U0001F970-\U0001F976"  # newer face emojis
        "\U0001F97A"              # pleading face
        "\U0001FAE0-\U0001FAE8"  # newer expressive faces
        "\U0001F44A-\U0001F64F"  # hands / gestures / people gestures
        "\U00002764"              # ❤️
        "\U0001F493-\U0001F49F"  # hearts
        "]"
    )

    # เก็บ emoji อารมณ์ไว้ชั่วคราว
    kept = {}
    counter = 0

    def protect_emotion(match):
        nonlocal counter

        start = match.start()
        end = match.end()

        # รวม variation selector / skin tone ถ้ามี
        while end < len(text) and (
            text[end] == "\ufe0f"
            or "\U0001F3FB" <= text[end] <= "\U0001F3FF"
        ):
            end += 1

        emoji = text[start:end]
        placeholder = f"__EMOTION_{counter}__"
        kept[placeholder] = emoji
        counter += 1
        return placeholder

    text = emotion_emoji_pattern.sub(protect_emotion, text)

    # ลบ emoji อื่นที่ไม่ต้องการเก็บ
    other_emoji_pattern = re.compile(
        "["
        "\U0001F1E6-\U0001F1FF"  # flags
        "\U0001F170-\U0001F1FF"
        "\U0001F200-\U0001F2FF"
        "\U0001F300-\U0001F5FF"  # nature / objects
        "\U0001F680-\U0001F6FF"  # transport / map
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U00002700-\U000027BF"
        "\U00002B00-\U00002BFF"
        "]"
    )

    text = other_emoji_pattern.sub("", text)

    # ลบ variation selector / skin tone ที่หลงเหลือ
    text = re.sub(
        r"[\ufe0f\U0001F3FB-\U0001F3FF]",
        "",
        text
    )

    # คืน emoji อารมณ์กลับ
    for placeholder, emoji in kept.items():
        text = text.replace(placeholder, emoji)

    # เก็บช่องว่างให้เรียบร้อย
    text = re.sub(r"[ \t]{2,}", " ", text).strip()

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
        "isDuplicate": detect_duplicate(review, previous_reviews),
        "allForeign": detect_all_foreign(clean_encoding_error(text)),
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
        "cleanText": None,
    }

    return result


def main():
    base_dir = Path(__file__).resolve().parent
    input_path = base_dir / "mockdata.json"
    check_path = base_dir / "checkoutput.json"

    with input_path.open("r", encoding="utf-8-sig") as file:
        reviews = json.load(file)

    results = []
    previous_reviews = []
    discarded_count = 0

    for review in reviews:
        # ตรวจข้อความต้นฉบับทุกฟังก์ชัน เพื่อเก็บ flags แม้รีวิวจะถูกทิ้ง
        result = inspect_review(review, previous_reviews)
        results.append(result)
        # เก็บประวัติก่อน continue เพื่อให้ตรวจซ้ำตามลำดับข้อมูลต้นฉบับ
        previous_reviews.append(review)

        discard_reasons = []
        if result["isDuplicate"] is True:
            discard_reasons.append("รีวิวซ้ำ")
        if result["allForeign"] is True:
            discard_reasons.append("ภาษาต่างประเทศล้วน")
        if result["emptyOrEmojiOnly"] is True:
            discard_reasons.append("ข้อความว่างหรือมีแต่อีโมจิ/สัญลักษณ์ตามกฎ")

        if discard_reasons:
            discarded_count += 1
            print(f"คัดทิ้ง ID {review['id']}: {', '.join(discard_reasons)}")
            continue  # ไปรีวิวถัดไป ไม่เข้าลูป Clean

        # เฉพาะรีวิวที่ผ่านจึงเข้า Clean ตามลำดับ โดยทุกขั้นคืน str
        clean_text = clean_review(review["text"])

        # เช่น มีแต่แท็ก HTML เมื่อลบแท็กแล้วอาจไม่เหลือข้อความ
        # flags ใน checkoutput ยังคงเป็นผลตรวจข้อความต้นฉบับ
        if not clean_text.strip():
            discarded_count += 1
            print(f"คัดทิ้ง ID {review['id']}: ข้อความว่างหลัง Clean")
            continue

        result["cleanText"] = clean_text
        print(f"Clean แล้วและเก็บไว้: ID {review['id']}")

    # เก็บทุกรีวิว โดย cleanText อยู่ท้ายสุด; รายการที่คัดทิ้งเป็น null
    with check_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"ผลตรวจ {len(results)} รายการ: {check_path}")
    print(f"เก็บ {len(results) - discarded_count} รายการ / คัดทิ้ง {discarded_count} รายการ")


if __name__ == "__main__":
    main()