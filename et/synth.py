import hashlib
import json
import random
from dataclasses import dataclass, field

from .morph import inflect_phrase, inflect_word
from .normalize import transliterate
from .templates import EN, ET, ET_PUBLIC, MIXED, RELATIONS, RU
from .values import Person, Sampler

DIACRITICS = str.maketrans("õäöüšžÕÄÖÜŠŽ", "oaouszOAOUSZ")
DIGIT_WORDS = ["null", "üks", "kaks", "kolm", "neli", "viis", "kuus", "seitse", "kaheksa", "üheksa"]
KEYBOARD = {c: n for c, n in zip("qwertyuiopasdfghjklzxcvbnm", "wqetryiuopsadgfhjklkxzvcnbm")}

LANG_POOLS = {"et": ET, "et_public": ET_PUBLIC, "ru": RU, "en": EN, "mixed": MIXED}
LANG_WEIGHTS = {"et": 0.58, "et_public": 0.1, "ru": 0.2, "en": 0.07, "mixed": 0.05}

PERSON_SLOTS = {"p1", "p2", "p3"}
PERSON_PARTS = {"", "g", "s", "rev"}
PRIVATE_SLOTS = {"ik1", "ik2", "ik3", "phone", "phone2", "email", "email2", "iban", "card", "doc", "pass", "dl",
                 "kmkr", "plate", "addr", "st", "bld", "apt", "zip", "farm"}
KEEP_SLOTS = {"city", "city2", "cityru", "county", "vald", "village"}
PUBLIC_SLOTS = {"agency", "date", "amount", "age", "rel"}
CASED_SLOTS = PERSON_SLOTS | {"st", "city", "city2", "agency"}


@dataclass
class Piece:
    text: str
    label: str = None
    public: str = None


@dataclass
class Row:
    text: str
    spans: list = field(default_factory=list)
    public: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def template_split(tid: str) -> str:
    return "heldout" if int(hashlib.md5(tid.encode()).hexdigest(), 16) % 7 == 0 else "train"


def load_templates(paths):
    pools = {lang: [(f"{lang}:{i}", t) for i, t in enumerate(ts)] for lang, ts in LANG_POOLS.items()}
    for path in paths or ():
        for line in open(path):
            r = json.loads(line)
            tid = "llm:" + hashlib.sha1(r["text"].encode()).hexdigest()[:10]
            pools.setdefault(r["lang"], []).append((tid, r["text"]))
    return pools


def parse(template: str):
    out, i = [], 0
    while i < len(template):
        j = template.find("{", i)
        if j < 0:
            out.append(("lit", template[i:]))
            break
        if j > i:
            out.append(("lit", template[i:j]))
        k = template.index("}", j)
        slot, _, case = template[j + 1:k].partition(":")
        out.append(("slot", slot, case or "n"))
        i = k + 1
    return out


class Generator:
    def __init__(self, lexicon: str, split: str = "train", seed: int = 0, templates=None):
        self.s = Sampler(lexicon, split, seed)
        self.rng = self.s.rng
        self.split = split
        self.pools = load_templates(templates)

    def context(self, lang: str):
        r, s = self.rng, self.s
        script = None if lang == "ru" else "latin"
        p1 = s.person(script=script)
        p2 = s.person(script=script, surname=p1.surname if r.random() < 0.3 else None, origin=p1.origin if r.random() < 0.6 else None)
        p3 = s.person(origin=p1.origin, script=p1.script, surname=p1.surname)
        city, prefix = s.city()
        city2, _ = s.city()
        return {
            "p1": p1, "p2": p2, "p3": p3, "ik1": s.isikukood(p1, r.random() > 0.02), "ik2": s.isikukood(p2), "ik3": s.isikukood(p3),
            "phone": s.phone(), "phone2": s.phone(), "email": s.email(p1), "email2": s.email(p2), "iban": s.iban(),
            "card": s.card(), "doc": s.id_doc(), "pass": s.passport(), "dl": s.drivers_license(), "kmkr": s.kmkr(),
            "plate": s.plate(), "street": s.street(), "bld": s.building(), "apt": s.apartment(), "city": city,
            "city2": city2, "zip": s.zip(prefix), "county": s.county(), "vald": s.vald(), "village": s.village(),
            "farm": s.farm(), "district": s.district(), "cityru": s.city_ru()[1], "date": s.date_text(),
            "amount": s.amount(), "age": str(r.randint(18, 79)), "agency": r.choice(__import__("seed").AGENCIES),
            "rel": r.choice(RELATIONS),
        }

    def person_pieces(self, p: Person, part: str, case: str, lang: str):
        r = self.rng
        g, sn = p.given, p.surname
        if p.script == "cyrillic" and lang != "ru":
            g, sn = transliterate(g), transliterate(sn)
        can_inflect = lang in ("et", "et_public", "mixed") and p.script == "latin"
        if part == "g":
            return [Piece(inflect_word(g, case, r.choice) if can_inflect else g, "GIVEN_NAME")]
        if part == "s":
            return [Piece(inflect_word(sn, case, r.choice) if can_inflect else sn, "SURNAME")]
        if part == "rev":
            style = r.choice(["upper", "comma", "plain"])
            sur = sn.upper() if style == "upper" else sn
            return [Piece(sur, "SURNAME"), Piece(", " if style == "comma" else " "), Piece(g, "GIVEN_NAME")]
        full_s = inflect_word(sn, case, r.choice) if can_inflect else sn
        if r.random() < 0.06:
            return [Piece(sn if case == "n" else full_s, "SURNAME"), Piece(" "), Piece(g, "GIVEN_NAME")]
        return [Piece(g, "GIVEN_NAME"), Piece(" "), Piece(full_s, "SURNAME")]

    def street_pieces(self, ctx, case: str):
        stem, full, abbr = ctx["street"]
        if case != "n":
            return [Piece(inflect_phrase(f"{stem} {full}", case, self.rng.choice), "STREET_NAME")]
        return [Piece(f"{stem} {self.rng.choice([full, abbr, abbr])}", "STREET_NAME")]

    def county_piece(self, ctx):
        c = ctx["county"]
        return Piece(self.rng.choice([f"{c} maakond", f"{c}maa".replace("-Virumaa", "-Virumaa"), f"{c} mk"]), "STATE")

    def apt_pieces(self, apt):
        style = self.rng.choices(["dash", "korter", "krt", "k"], [0.6, 0.2, 0.15, 0.05])[0]
        if style == "dash":
            return [Piece("-"), Piece(apt, "SECONDARY_ADDRESS")]
        return [Piece(", " if self.rng.random() < 0.5 else " "), Piece(f"{style} {apt}", "SECONDARY_ADDRESS")]

    def address_pieces(self, ctx):
        r = self.rng
        fmt = r.choices(["urban", "urban_full", "ads", "rural", "tallinn", "short"], [0.32, 0.18, 0.12, 0.12, 0.12, 0.14])[0]
        st = self.street_pieces(ctx, "n")
        bld = [Piece(ctx["bld"], "BUILDING_NUMBER")]
        apt = self.apt_pieces(ctx["apt"]) if r.random() < 0.55 else []
        city = Piece(ctx["city"], "CITY")
        zp = Piece(ctx["zip"], "ZIP_CODE")
        if fmt == "urban":
            return st + [Piece(" ")] + bld + apt + [Piece(", "), zp, Piece(" "), city]
        if fmt == "urban_full":
            return st + [Piece(" ")] + bld + apt + [Piece(", "), city, Piece(", "), self.county_piece(ctx), Piece(", "), zp]
        if fmt == "ads":
            return [self.county_piece(ctx), Piece(", "), Piece(f"{ctx['city']} linn", "CITY"), Piece(", ")] + st + [Piece(" ")] + bld + apt
        if fmt == "rural":
            return [Piece(f"{ctx['farm']} talu", "STREET_NAME"), Piece(", "), Piece(f"{ctx['village']} küla", "CITY"), Piece(", "),
                    Piece(f"{ctx['vald']} vald", "CITY"), Piece(", "), self.county_piece(ctx)] + ([Piece(", "), zp] if r.random() < 0.6 else [])
        if fmt == "tallinn":
            return [Piece("Tallinn", "CITY"), Piece(", "), Piece(f"{ctx['district']} linnaosa", "CITY"), Piece(", ")] + st + [Piece(" ")] + bld + apt
        return st + [Piece(" ")] + bld + apt + [Piece(", "), city]

    def phone_piece(self, value):
        if self.rng.random() < 0.03:
            return Piece(" ".join(DIGIT_WORDS[int(c)] for c in value if c.isdigit()), "PHONE")
        return Piece(value, "PHONE")

    def slot(self, ctx, name, case, lang):
        r = self.rng
        base, _, part = name.partition(".")
        if base in ("p1", "p2", "p3"):
            return self.person_pieces(ctx[base], part, case, lang)
        simple = {"ik1": "ISIKUKOOD", "ik2": "ISIKUKOOD", "ik3": "ISIKUKOOD", "email": "EMAIL", "email2": "EMAIL",
                  "iban": "BANK_ACCOUNT", "card": "CREDIT_CARD", "doc": "GOVERNMENT_ID", "pass": "PASSPORT",
                  "dl": "DRIVERS_LICENSE", "kmkr": "TAX_ID", "plate": "GOVERNMENT_ID", "bld": "BUILDING_NUMBER",
                  "zip": "ZIP_CODE", "cityru": "CITY", "village": "CITY", "vald": "CITY", "farm": "STREET_NAME"}
        if base in ("phone", "phone2"):
            return [self.phone_piece(ctx[base])]
        if base in simple:
            return [Piece(ctx[base], simple[base])]
        if base == "apt":
            return [Piece(ctx["apt"], "SECONDARY_ADDRESS")]
        if base == "addr":
            return self.address_pieces(ctx)
        if base == "st":
            return self.street_pieces(ctx, case)
        if base in ("city", "city2"):
            return [Piece(inflect_word(ctx[base], case, r.choice) if case != "n" else ctx[base], "CITY")]
        if base == "county":
            return [self.county_piece(ctx)]
        if base == "agency":
            return [Piece(inflect_phrase(ctx["agency"], case, r.choice) if case != "n" else ctx["agency"], public="ORG")]
        if base in ("date", "amount", "age"):
            return [Piece(ctx[base], public=base.upper())]
        if base == "rel":
            return [Piece(ctx["rel"])]
        raise KeyError(name)

    def typo(self, word: str) -> str:
        if len(word) < 4:
            return word
        r = self.rng
        i = r.randrange(1, len(word) - 1)
        op = r.choice(["swap", "drop", "dup", "near"])
        if op == "swap":
            return word[:i] + word[i + 1] + word[i] + word[i + 2:]
        if op == "drop":
            return word[:i] + word[i + 1:]
        if op == "dup":
            return word[:i] + word[i] + word[i:]
        c = word[i].lower()
        return word[:i] + KEYBOARD.get(c, c) + word[i + 1:]

    def noise(self, pieces, lang):
        r = self.rng
        flags = {
            "lower": r.random() < 0.22, "ascii": lang != "ru" and r.random() < 0.15,
            "typos": r.random() < 0.3, "entity_typo": r.random() < 0.05, "spacing": r.random() < 0.1,
        }
        out = []
        for p in pieces:
            t = p.text
            if flags["typos"] and p.label is None and p.public is None:
                t = " ".join(self.typo(w) if r.random() < 0.12 else w for w in t.split(" "))
            if flags["entity_typo"] and p.label in ("GIVEN_NAME", "SURNAME", "STREET_NAME") and r.random() < 0.5:
                t = self.typo(t)
            if flags["lower"]:
                t = t.lower()
            if flags["ascii"]:
                t = t.translate(DIACRITICS)
            if flags["spacing"] and p.label is None:
                t = t.replace(", ", ",") if r.random() < 0.5 else t.replace(" ", "  ", 1)
            out.append(Piece(t, p.label, p.public))
        return out, {k: v for k, v in flags.items() if v}

    def message(self, lang=None):
        r = self.rng
        lang = lang or r.choices(list(LANG_WEIGHTS), list(LANG_WEIGHTS.values()))[0]
        pool = [(i, t) for i, t in self.pools[lang] if template_split(i) == self.split] or self.pools[lang]
        idx, tpl = r.choice(pool)
        ctx = self.context(lang)
        pieces = []
        for tok in parse(tpl):
            if tok[0] == "lit":
                pieces.append(Piece(tok[1]))
            else:
                pieces.extend(self.slot(ctx, tok[1], tok[2], lang))
        return pieces, lang, idx

    def row(self, max_turns=3) -> Row:
        r = self.rng
        n = r.choices([1, 2, 3], [0.7, 0.2, 0.1])[: max_turns][0]
        all_pieces, meta = [], {"templates": [], "noise": {}}
        lang0 = None
        for k in range(n):
            pieces, lang, idx = self.message(lang0 if lang0 and r.random() < 0.7 else None)
            lang0 = lang0 or lang
            pieces, flags = self.noise(pieces, lang)
            meta["templates"].append(idx)
            meta["noise"].update(flags)
            if k:
                all_pieces.append(Piece(r.choice(["\n", " ", "\n\n"])))
            all_pieces.extend(pieces)
        text, spans, public, pos = "", [], [], 0
        for p in all_pieces:
            if p.label and p.text:
                spans.append({"start": pos, "end": pos + len(p.text), "label": p.label})
            if p.public and p.text:
                public.append({"start": pos, "end": pos + len(p.text), "label": p.public})
            text += p.text
            pos += len(p.text)
        meta["lang"] = lang0
        return Row(text, spans, public, meta)
