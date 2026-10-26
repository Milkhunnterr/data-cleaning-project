"""Contextual POS and Thai WordNet agreement, with lazy resource loading."""
from dataclasses import dataclass

ENGINE = "perceptron"
CORPUS = "orchid_ud"
MODES = ("baseline", "noun_verb", "remove_adj_adv_conj", "noun_verb_adj")
ALLOW = {"noun_verb": frozenset({"NOUN", "VERB"}), "noun_verb_adj": frozenset({"NOUN", "VERB", "ADJ"})}
REMOVE = frozenset({"ADJ", "ADV", "CCONJ", "SCONJ"})
MAPPING = {"n": "NOUN", "v": "VERB", "a": "ADJ", "s": "ADJ", "r": "ADV"}
KNOWN = frozenset("ADJ ADP ADV AUX CCONJ DET INTJ NOUN NUM PART PRON PROPN PUNCT SCONJ SYM VERB".split())
CONFIRMED, CONFLICT, POS_ONLY, UNKNOWN = "ยืนยันร่วมกัน", "ขัดแย้ง/เทียบป้ายไม่ได้", "มีเฉพาะผล POS", "ไม่ทราบชนิดคำ"


class WordNetLexicon:
    """Cache lexical possibilities, never context-dependent POS predictions."""
    def __init__(self, reader=None):
        try:
            if reader is None:
                from nltk.corpus import wordnet
                reader = wordnet
                reader.ensure_loaded()
                if not any(reader.all_lemma_names(lang="tha")):
                    raise ValueError("Thai WordNet has no lemmas")
            self.reader = reader
            self.cache = {}
        except (ImportError, LookupError, OSError) as exc:
            raise ValueError("โหลด Thai WordNet ไม่ได้; รัน python -m nltk.downloader wordnet omw-1.4") from exc

    def lookup(self, token):
        if token not in self.cache:
            try:
                synsets = self.reader.synsets(token, lang="tha")
                self.cache[token] = (bool(synsets), frozenset(MAPPING[s.pos()] for s in synsets if s.pos() in MAPPING))
            except (ImportError, LookupError, OSError) as exc:
                raise ValueError("โหลดทรัพยากร Thai WordNet ไม่ได้ ไม่ใช่กรณีไม่พบคำ") from exc
        return self.cache[token]


@dataclass(frozen=True)
class Evidence:
    pos: object
    wordnet: frozenset
    status: str
    reason: str


def decide(tag, lexical):
    found, kinds = lexical
    if not isinstance(tag, str) or tag not in KNOWN:
        return Evidence(tag, kinds, UNKNOWN, "POS ไม่ทราบชนิดหรือป้ายผิดรูปแบบ")
    if not found:
        return Evidence(tag, kinds, POS_ONLY, "WordNet ไม่พบคำ ไม่ได้แปลว่าคำผิดหรือไม่มีความหมาย")
    if tag not in kinds:
        return Evidence(tag, kinds, CONFLICT, "WordNet ไม่สนับสนุนป้าย POS นี้; ไม่เทียบ PROPN เป็น NOUN")
    return Evidence(tag, kinds, CONFIRMED, "POS อยู่ในชุดชนิดคำจากทุก synset; ไม่รับประกันความถูกต้อง")


def keep_pos(mode, tag):
    """Mode policy only: callers must also require joint confirmation."""
    if mode == "baseline":
        return True
    if mode == "remove_adj_adv_conj":
        return isinstance(tag, str) and tag in MAPPING.values() and tag not in REMOVE
    if mode in ALLOW:
        return isinstance(tag, str) and tag in ALLOW[mode]
    raise ValueError(f"Unknown POS mode: {mode}")


def accepts(mode, evidence):
    return mode == "baseline" or (evidence.status == CONFIRMED and keep_pos(mode, evidence.pos))


def pos_tag(*args, **kwargs):
    from pythainlp.tag import pos_tag as implementation
    return implementation(*args, **kwargs)


def tag_tokens(tokens):
    tagged = pos_tag(list(tokens), engine=ENGINE, corpus=CORPUS)
    if not isinstance(tagged, (list, tuple)) or len(tagged) != len(tokens):
        raise ValueError("POS alignment mismatch: token count")
    tags = []
    for token, item in zip(tokens, tagged):
        if not isinstance(item, (list, tuple)) or not item or item[0] != token:
            raise ValueError("POS alignment mismatch: token text/order")
        tags.append(item[1] if len(item) == 2 else None)
    return tags
