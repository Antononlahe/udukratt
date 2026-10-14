import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from et.deterministic import detect  # noqa: E402
from et.normalize import premask_view  # noqa: E402

CASES = [
    "Isikukood 38001085718, tel +372 5555 5555.",
    "IK 380 0108 5718 tel 5123 4567",
    "38001085718 51234567",
    "vale kood 38001085719 ja tellimus 380010857189",
    "arve EE38 2200 2210 2014 5685 ja summa 500 EUR",
    "konto ee382200221020145685.",
    "IBAN DE89 3704 0044 0532 0130 00 palun",
    "kaart 4111 1111 1111 1111, mail jaan.tamm@eesti.ee ip 10.0.0.1",
    "server 2001:db8::1 ja mac 00:1A:2B:3C:4D:5E",
    "vt https://www.eesti.ee/et/toetused ja www.tootukassa.ee",
    "Меня зовут Елена Смирнова, личный код 49403136526.",
    "Сергей Йошкин живёт в Нарве, улица Юрия Щербакова 5",
    "Мägi ja Тамм kirjutasid",
    "summa 1250,50 eurot, § 32 lg 1, asi nr 3-21-1234",
    "Ярослав Ільченко, тел 53 456 789",
    "kood 6 0108 1503 18 ja telefon 5 123 4567",
]


def main():
    out = []
    for text in CASES:
        spans = detect(text)
        out.append({"text": text, "spans": [[s.start, s.end, s.label] for s in spans],
                    "masked": premask_view(text, [(s.start, s.end, s.label) for s in spans])})
    json.dump(out, open(ROOT / "fixtures/parity.json", "w"), ensure_ascii=False, indent=1)
    for c in out:
        print(c["masked"])


if __name__ == "__main__":
    main()
