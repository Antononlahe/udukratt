import datetime
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .normalize import transliterate
from .validators import isikukood_check_digit, luhn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from seed import (BANK_CODES, CITIES, CITIES_RU, COUNTIES, EMAIL_DOMAINS, FARM_STEMS, ID_DOC_PREFIXES,  # noqa: E402
                  STREET_TYPES, TALLINN_DISTRICTS, VALDS)

ASCII = str.maketrans("õäöüšžÕÄÖÜŠŽ", "oaousz" + "OAOUSZ")


@dataclass
class Person:
    given: str
    surname: str
    sex: str
    origin: str
    script: str = "latin"
    birth: datetime.date = field(default_factory=lambda: datetime.date(1980, 1, 1))


class Sampler:
    def __init__(self, lexicon_path: str, split: str = "train", seed: int = 0):
        self.lex = json.load(open(lexicon_path))
        self.split = split
        self.rng = random.Random(seed)

    def pool(self, key):
        return self.lex["names"][key][self.split]

    def birth(self) -> datetime.date:
        start = datetime.date(1935, 1, 1).toordinal()
        end = datetime.date(2024, 12, 31).toordinal()
        return datetime.date.fromordinal(self.rng.randint(start, end))

    def person(self, origin=None, script=None, sex=None, surname=None) -> Person:
        r = self.rng
        origin = origin or r.choices(["est", "rus", "ukr", "other"], [0.66, 0.24, 0.04, 0.06])[0]
        sex = sex or r.choice("MF")
        if origin in ("rus", "ukr"):
            script = script or r.choices(["latin", "cyrillic"], [0.7, 0.3])[0]
            g = r.choice(self.pool("given_cyr_m" if sex == "M" else "given_cyr_f"))
            s = surname or r.choice(self.pool("sur_cyr_m" if sex == "M" else "sur_cyr_f"))
            if script == "latin":
                g, s = transliterate(g), transliterate(s) if surname is None else surname
        elif origin == "est":
            g = r.choice(self.pool("given_est"))
            s = surname or r.choice(self.pool("sur_est"))
            script = "latin"
        else:
            g = r.choice(self.pool("given_other"))
            s = surname or r.choice(self.pool("sur_other"))
            script = "latin"
        if r.random() < 0.05 and origin == "est":
            s = f"{s}-{r.choice(self.pool('sur_est'))}"
        if r.random() < 0.04:
            g = f"{g}-{r.choice(self.pool('given_est'))}" if origin == "est" else f"{g} {r.choice(self.pool('given_other'))}"
        return Person(g, s, sex, origin, script, self.birth())

    def isikukood(self, p: Person = None, valid: bool = True) -> str:
        d = p.birth if p else self.birth()
        sex = p.sex if p else self.rng.choice("MF")
        century = (d.year - 1800) // 100
        g = 1 + 2 * century + (1 if sex == "F" else 0)
        first10 = f"{g}{d:%y%m%d}{self.rng.randint(0, 999):03d}"
        check = isikukood_check_digit(first10)
        if not valid:
            check = (check + self.rng.randint(1, 9)) % 10
        return first10 + str(check)

    def phone(self) -> str:
        r = self.rng
        mob = f"5{r.randint(0, 9)}{r.randint(0, 99999):05d}" if r.random() < 0.35 else f"5{r.randint(0, 9)}{r.randint(0, 999999):06d}"
        land = f"{r.choice('34678')}{r.randint(0, 999999):06d}"
        n = mob if r.random() < 0.85 else land
        fmt = r.choices(["plain", "split", "cc", "cc_plain", "00", "dash"], [0.3, 0.25, 0.25, 0.08, 0.04, 0.08])[0]
        split = f"{n[:-4]} {n[-4:]}" if len(n) == 8 else f"{n[:3]} {n[3:]}"
        return {
            "plain": n, "split": split, "cc": f"+372 {split}", "cc_plain": f"+372{n}",
            "00": f"00372{n}", "dash": f"{n[:-4]}-{n[-4:]}",
        }[fmt]

    def iban(self, grouped=None) -> str:
        bank = self.rng.choice(BANK_CODES)
        acct = bank + "".join(str(self.rng.randint(0, 9)) for _ in range(14))
        num = int("".join(str(int(c, 36)) for c in acct + "EE00"))
        s = f"EE{98 - num % 97:02d}{acct}"
        grouped = self.rng.random() < 0.55 if grouped is None else grouped
        return " ".join(s[i:i + 4] for i in range(0, 20, 4)) if grouped else s

    def card(self) -> str:
        body = [self.rng.choice("45")] + [str(self.rng.randint(0, 9)) for _ in range(14)]
        for d in range(10):
            if luhn("".join(body) + str(d)):
                body.append(str(d))
                break
        s = "".join(body)
        return " ".join(s[i:i + 4] for i in range(0, 16, 4)) if self.rng.random() < 0.6 else s

    def id_doc(self) -> str:
        return self.rng.choice(ID_DOC_PREFIXES) + f"{self.rng.randint(0, 9999999):07d}"

    def passport(self) -> str:
        return "K" + f"{self.rng.randint(0, 9999999):07d}"

    def drivers_license(self) -> str:
        return self.rng.choice(["ET", "EE"]) + f"{self.rng.randint(0, 999999):06d}"

    def kmkr(self) -> str:
        return f"EE10{self.rng.randint(0, 9999999):07d}"

    def plate(self) -> str:
        letters = "ABCDEFGHJKLMNOPRSTUVZ"
        return f"{self.rng.randint(0, 999):03d}{self.rng.choice(['', ' '])}{''.join(self.rng.choice(letters) for _ in range(3))}"

    def email(self, p: Person) -> str:
        g = transliterate(p.given).translate(ASCII).lower().replace(" ", ".")
        s = transliterate(p.surname).translate(ASCII).lower().replace(" ", "")
        r = self.rng
        local = r.choice([f"{g}.{s}", f"{g}{s}", f"{g[0]}{s}", f"{g}.{s}{r.randint(1, 99)}", f"{s}{p.birth:%y}", f"{g}{r.randint(1, 999)}"])
        domain = r.choices([d for d, _ in EMAIL_DOMAINS], [w for _, w in EMAIL_DOMAINS])[0]
        return f"{local}@{domain}"

    def street(self):
        stem = self.rng.choice(self.lex["streets"][self.split])
        full, abbr, _ = self.rng.choices(STREET_TYPES, [w for *_, w in STREET_TYPES])[0]
        return stem, full, abbr

    def building(self) -> str:
        n = str(self.rng.choices([self.rng.randint(1, 30), self.rng.randint(31, 180)], [0.8, 0.2])[0])
        r = self.rng.random()
        if r < 0.1:
            n += self.rng.choice("abcdeABC")
        elif r < 0.14:
            n += f"/{self.rng.randint(1, 9)}"
        return n

    def apartment(self) -> str:
        return str(self.rng.randint(1, 120))

    def city(self):
        name = self.rng.choices(list(CITIES), [30, 12, 5, 4, 3, 2] + [1] * (len(CITIES) - 6))[0]
        return name, CITIES[name]

    def zip(self, prefix: str) -> str:
        return (prefix + "".join(str(self.rng.randint(0, 9)) for _ in range(5)))[:5]

    def county(self) -> str:
        return self.rng.choice(COUNTIES)

    def vald(self) -> str:
        return self.rng.choice(VALDS)

    def village(self) -> str:
        return self.rng.choice(self.lex["villages"][self.split])

    def farm(self) -> str:
        return f"{self.rng.choice(FARM_STEMS)}"

    def district(self) -> str:
        return self.rng.choice(TALLINN_DISTRICTS)

    def city_ru(self):
        lat = self.rng.choice(list(CITIES_RU))
        return lat, CITIES_RU[lat]

    def date_text(self, d: datetime.date = None) -> str:
        d = d or datetime.date.fromordinal(self.rng.randint(datetime.date(2019, 1, 1).toordinal(), datetime.date(2026, 12, 31).toordinal()))
        months = ["jaanuar", "veebruar", "märts", "aprill", "mai", "juuni", "juuli", "august", "september", "oktoober", "november", "detsember"]
        return self.rng.choice([f"{d:%d.%m.%Y}", f"{d.day}. {months[d.month - 1]} {d.year}", f"{d:%Y-%m-%d}", f"{d.day}.{d.month}.{d:%y}"])

    def amount(self) -> str:
        v = self.rng.choice([self.rng.randint(20, 900), self.rng.randint(900, 4000), round(self.rng.uniform(10, 2000), 2)])
        return f"{v}".replace(".", ",") if self.rng.random() < 0.7 else f"{v}"
