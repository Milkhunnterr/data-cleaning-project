"""Occurrence-level POS rules; tagging precedes all feature filtering."""

from pythainlp.tag import pos_tag

ENGINE = "perceptron"
CORPUS = "orchid_ud"
MODES = ("baseline", "noun_verb", "remove_adj_adv_conj", "noun_verb_adj")

# 0: baseline ignores POS.
# 1: PROPN belongs to the noun family; AUX is not VERB.
# 2: exclude both coordinating and subordinating conjunctions.
# 3: include adjectives, including ORCHID VATT -> ADJ.
ALLOW = {
    "noun_verb": frozenset({"NOUN", "PROPN", "VERB"}),
    "noun_verb_adj": frozenset({"NOUN", "PROPN", "VERB", "ADJ"}),
}
REMOVE = frozenset({"ADJ", "ADV", "CCONJ", "SCONJ"})


def keep_pos(mode: str, tag: str | None) -> bool:
    if mode == "baseline":
        return True
    if mode == "remove_adj_adv_conj":
        return tag not in REMOVE
    if mode in ALLOW:
        return tag in ALLOW[mode]
    raise ValueError(f"Unknown POS mode: {mode}")


def tag_tokens(tokens: list[str]) -> list[str]:
    """Tag the whole review, retaining spaces, punctuation and placeholders.

    Fail if PyThaiNLP changes token identity, order or count. Never silently
    zip a shortened/shifted sequence back onto original tokens.
    """
    tagged = pos_tag(list(tokens), engine=ENGINE, corpus=CORPUS)
    if [word for word, _ in tagged] != tokens:
        raise ValueError("POS alignment mismatch: token text/order/count changed")
    return [tag for _, tag in tagged]
