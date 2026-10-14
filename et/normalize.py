import unicodedata

VOWELS = set("аеёиоуыэюяaeiouõäöüy")

BASE = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ж": "ž", "з": "z", "и": "i",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s",
    "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "tš", "ш": "š", "щ": "štš",
    "ъ": "", "ы": "õ", "ь": "", "э": "e", "ю": "ju", "я": "ja",
    "і": "i", "ї": "ji", "є": "je", "ґ": "g", "ў": "u",
}


def _translit_char(text: str, i: int) -> str:
    c = text[i]
    low = c.lower()
    prev = text[i - 1].lower() if i > 0 else " "
    nxt = text[i + 1].lower() if i + 1 < len(text) else " "
    if low == "е":
        out = "je" if (not prev.isalpha() or prev in VOWELS or prev in "ъь") else "e"
    elif low == "ё":
        out = "o" if prev in "жчшщ" else "jo"
    elif low == "й":
        out = "j" if nxt in VOWELS else "i"
    elif low in BASE:
        out = BASE[low]
    else:
        return c
    return out[:1].upper() + out[1:] if c != low and out else out


def transliterate(text: str) -> str:
    return "".join(_translit_char(text, i) for i in range(len(text)))


def fold_char(ch: str) -> str:
    return "".join(d for d in unicodedata.normalize("NFKD", ch.lower()) if unicodedata.category(d) != "Mn").lower()


def fold(text: str, translit: bool = True) -> str:
    return model_view(text, (), translit=translit)[0]


def premask_view(raw: str, sentinel_spans, translit: bool = True):
    out, cursor = [], 0
    for start, end, label in sorted(sentinel_spans, key=lambda s: s[0]):
        if start < cursor:
            continue
        out += [_translit_char(raw, i) if translit else raw[i] for i in range(cursor, start)]
        out.append(f"[{label}]")
        cursor = end
    out += [_translit_char(raw, i) if translit else raw[i] for i in range(cursor, len(raw))]
    return "".join(out)


def model_view(raw: str, sentinel_spans, translit: bool = True):
    spans = sorted(sentinel_spans, key=lambda s: s[0])
    out, starts, ends = [], [], []
    cursor = 0

    def emit(s: str, a: int, b: int):
        for ch in s:
            for f in fold_char(ch):
                out.append(f)
                starts.append(a)
                ends.append(b)

    for start, end, label in spans:
        if start < cursor:
            continue
        for i in range(cursor, start):
            emit(_translit_char(raw, i) if translit else raw[i], i, i + 1)
        emit(f"[{label}]", start, end)
        cursor = end
    for i in range(cursor, len(raw)):
        emit(_translit_char(raw, i) if translit else raw[i], i, i + 1)
    return "".join(out), starts, ends
