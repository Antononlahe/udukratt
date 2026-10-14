from functools import lru_cache

from estnltk.vabamorf.morf import synthesize

CASES = {
    "n": "sg n", "g": "sg g", "p": "sg p", "ill": "sg ill", "in": "sg in", "el": "sg el",
    "all": "sg all", "ad": "sg ad", "abl": "sg abl", "tr": "sg tr", "ter": "sg ter",
    "es": "sg es", "ab": "sg ab", "kom": "sg kom",
}


def _cap(src: str, out: str) -> str:
    if src.isupper() and len(src) > 1:
        return out.upper()
    return out[:1].upper() + out[1:] if src[:1].isupper() else out


@lru_cache(maxsize=200_000)
def _forms(word: str, form: str):
    for lemma, pos in ((word.lower(), "S"), (word, "H")):
        out = synthesize(lemma, form, pos)
        if out:
            return tuple(_cap(word, o) for o in out)
    return ()


def inflect_word(word: str, case: str, pick=lambda xs: xs[0]) -> str:
    if case == "n" or not word:
        return word
    head, sep, tail = word.rpartition("-")
    target = tail if sep else word
    forms = _forms(target, CASES[case])
    if not forms:
        return word
    out = pick(list(forms))
    return f"{head}-{out}" if sep else out


def inflect_phrase(phrase: str, case: str, pick=lambda xs: xs[0]) -> str:
    parts = phrase.split(" ")
    parts[-1] = inflect_word(parts[-1], case, pick)
    return " ".join(parts)
