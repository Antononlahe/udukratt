import re
from dataclasses import dataclass

from .validators import is_valid_iban, is_valid_isikukood, luhn


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    label: str
    score: float = 1.0
    source: str = "heuristic"


DIGIT_RULES = (
    ("CREDIT_CARD", (16, 15, 14), luhn),
    ("ISIKUKOOD", (11,), is_valid_isikukood),
)

DIGIT_RUN = re.compile(r"\d(?:[ .-]?\d)*", re.ASCII)

TEXT_RULES = (
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.ASCII)),
    ("URL", re.compile(r"\bhttps?://[^\s<>\"'\])}]+", re.ASCII)),
    ("URL", re.compile(r"\bwww\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s<>\"'\])}]*)?", re.ASCII)),
    ("IP_ADDRESS", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b", re.ASCII)),
    ("IP_ADDRESS", re.compile(
        r"(?<![:.\w])(?:(?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}|(?:[0-9A-Fa-f]{1,4}:){1,7}:|(?:[0-9A-Fa-f]{1,4}:){1,6}:[0-9A-Fa-f]{1,4}"
        r"|(?:[0-9A-Fa-f]{1,4}:){1,5}(?::[0-9A-Fa-f]{1,4}){1,2}|(?:[0-9A-Fa-f]{1,4}:){1,4}(?::[0-9A-Fa-f]{1,4}){1,3}"
        r"|(?:[0-9A-Fa-f]{1,4}:){1,3}(?::[0-9A-Fa-f]{1,4}){1,4}|(?:[0-9A-Fa-f]{1,4}:){1,2}(?::[0-9A-Fa-f]{1,4}){1,5}"
        r"|[0-9A-Fa-f]{1,4}:(?::[0-9A-Fa-f]{1,4}){1,6}|::(?:[0-9A-Fa-f]{1,4}:){0,6}[0-9A-Fa-f]{1,4})(?![:.\w])",
        re.ASCII,
    )),
    ("IP_ADDRESS", re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b", re.ASCII)),
)

IBAN = re.compile(r"\b[A-Za-z]{2}\d{2}(?: ?[A-Za-z0-9]{4}){2,7}(?: ?[A-Za-z0-9]{1,3})?\b", re.ASCII)


def _digit_groups(match: re.Match):
    groups, cur, idx = [], [], []
    for i, ch in enumerate(match.group(0)):
        if ch.isdigit():
            cur.append(ch)
            idx.append(match.start() + i)
        elif cur:
            groups.append(("".join(cur), idx))
            cur, idx = [], []
    if cur:
        groups.append(("".join(cur), idx))
    return groups


def detect_digits(raw: str):
    spans = []
    for m in DIGIT_RUN.finditer(raw):
        groups = _digit_groups(m)
        taken = set()
        for label, lengths, validate in DIGIT_RULES:
            for i in range(len(groups)):
                total, j = 0, i
                while j < len(groups) and total < max(lengths):
                    total += len(groups[j][0])
                    j += 1
                    if total in lengths and not taken.intersection(range(i, j)):
                        digits = "".join(g[0] for g in groups[i:j])
                        if validate(digits):
                            spans.append(Span(groups[i][1][0], groups[j - 1][1][-1] + 1, label))
                            taken.update(range(i, j))
                            break
    return spans


def detect_iban(raw: str):
    spans = []
    for m in IBAN.finditer(raw):
        text, start = m.group(0), m.start()
        while len(text.replace(" ", "")) >= 15:
            if is_valid_iban(text):
                spans.append(Span(start, start + len(text), "BANK_ACCOUNT"))
                break
            cut = text.rfind(" ")
            if cut < 0:
                break
            text = text[:cut]
    return spans


def detect_text(raw: str):
    return [Span(m.start(), m.end(), label) for label, pat in TEXT_RULES for m in pat.finditer(raw)]


def merge(spans):
    out = []
    for s in sorted(spans, key=lambda s: (s.start, -s.end)):
        if out and s.start < out[-1].end:
            p = out[-1]
            win = max((p, s), key=lambda x: (x.score, x.end - x.start, x.source == "heuristic"))
            contains = (p.start <= s.start and p.end >= s.end) or (s.start <= p.start and s.end >= p.end)
            out[-1] = win if contains else Span(min(p.start, s.start), max(p.end, s.end), win.label, win.score, win.source)
        else:
            out.append(s)
    return out


NEVER = {"UUID", "HASH", "SLACK_ID", "VERSION", "REF"}
NEVER_RULES = (
    ("UUID", re.compile(r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b", re.ASCII)),
    ("SLACK_ID", re.compile(r"\b[UWCT]0[A-Z0-9]{6,10}\b", re.ASCII)),
    ("HASH", re.compile(r"\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*[0-9])[0-9a-f]{7,64}\b", re.ASCII)),
    ("VERSION", re.compile(r"\bv\d+(?:\.\d+){1,3}\b|(?<![\d.])\d{1,2}\.\d{1,3}\.\d{1,3}(?![\d.])", re.ASCII)),
    ("REF", re.compile(r"#\d{2,}\b", re.ASCII)),
)


def detect_never(raw: str, pii):
    spans = [Span(m.start(), m.end(), label, source="never") for label, pat in NEVER_RULES for m in pat.finditer(raw)]
    return merge([s for s in spans if not any(p.start < s.end and s.start < p.end for p in pii)])


def detect(raw: str, never: bool = True):
    pii = merge(detect_digits(raw) + detect_iban(raw) + detect_text(raw))
    return sorted(pii + detect_never(raw, pii), key=lambda s: s.start) if never else pii
