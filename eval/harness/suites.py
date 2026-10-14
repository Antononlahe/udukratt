import json
from pathlib import Path
R = Path(str(__import__("pathlib").Path(__file__).resolve().parents[2]))
PRIVATE_OPENPII = {"GIVENNAME", "SURNAME", "EMAIL", "TELEPHONENUM", "SOCIALNUM", "CREDITCARDNUMBER", "IDCARDNUM", "PASSPORTNUM",
                   "DRIVERLICENSENUM", "TAXNUM", "BUILDINGNUM", "STREET", "CITY", "STATE", "ZIPCODE", "IBAN", "SECADDRESS", "URL", "IP"}
def load():
    S = {}
    S["corp_suite"] = [dict(text=d["text"], fmt=d["format"], gold=d["spans"], public=d["negatives"]) for d in map(json.loads, open(R / "work3/corp_suite/corp_suite.jsonl"))]
    for n in ["synth_heldout", "estner_test", "gov_chats", "fairness"]:
        rows = []
        for d in map(json.loads, open(R / f"work3/suites/{n}.jsonl")):
            pm = d["privacy_mask"]
            rows.append(dict(text=d["source_text"], fmt=n, gold=[m for m in pm if m["label"] in PRIVATE_OPENPII], public=[dict(m, kind=m["label"]) for m in pm if m["label"] not in PRIVATE_OPENPII]))
        S[n] = rows
    return S
