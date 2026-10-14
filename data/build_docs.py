import argparse
import datetime
import json
import random
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from et.values import Sampler  # noqa: E402

ORGS = ["Elisa Eesti AS", "Tele2 Eesti AS", "SEB Pank AS", "Coop Pank AS", "Luminor Bank AS", "Alexela AS", "Enefit Green AS",
        "Tallinna Sadam AS", "Ekspress Meedia AS", "Zone Media OÜ", "Admiral Markets AS", "Glia Technologies OÜ", "Katana MRP OÜ",
        "Skeleton Technologies OÜ", "Lightyear OÜ", "Mooncascade OÜ", "Codeborne OÜ", "Proekspert AS", "Transferwise Ltd",
        "Politsei- ja Piirivalveamet", "Sotsiaalkindlustusamet", "Tervisekassa", "Rahvastikuregister", "Äriregister", "Tallinna Linnavalitsus"]
PRODS = ["ID-kaart", "Digilugu", "e-Kool", "Stuudium", "GitLab", "GitHub Actions", "Sentry", "Datadog", "Redis", "RabbitMQ",
         "Elasticsearch", "Terraform", "Docker", "Notion", "Microsoft Teams", "Zoom", "Figma", "Okta", "Auth0", "Stripe", "Montonio",
         "Maksekeskus", "Excel", "Power BI", "Snowflake"]
IDENT = ["accountHolder", "person_id_hash", "BillingService", "resolveAddress", "TIMEOUT_MS", "ee.rik.client", "PersonDto",
         "kliendiregister_v2", "Status.ACTIVE", "prod-tln-02", "eu-central-1", "cache.ttl.seconds", "handleWebhook", "isActive"]
KEYS = {
    "GIVEN_NAME": ["first_name", "firstname", "givenName", "eesnimi", "Eesnimi", "fname", "imya", "given", "forename", "nimi_ees"],
    "SURNAME": ["last_name", "lastname", "familyName", "perekonnanimi", "Perenimi", "lname", "familiya", "surname", "nimi_pere"],
    "FULL": ["name", "fullName", "full_name", "nimi", "Nimi", "kontaktisik", "contact", "holder", "klient", "fio"],
    "ISIKUKOOD": ["isikukood", "personal_code", "idCode", "ik", "personalIdentificationCode", "national_id", "isikukood_ee"],
    "EMAIL": ["email", "e_mail", "epost", "e-post", "mail", "emailAddress", "kontakt_email"],
    "PHONE": ["phone", "tel", "telefon", "mobile", "phoneNumber", "mob", "kontakt_tel"],
    "BANK_ACCOUNT": ["iban", "account", "arveldusarve", "konto", "bankAccount", "payout_iban"],
    "STREET_NAME": ["street", "tanav", "aadress_tanav", "streetName", "address1"],
    "BUILDING_NUMBER": ["house", "maja", "houseNo", "building", "nr"],
    "SECONDARY_ADDRESS": ["apartment", "korter", "flat", "apt"],
    "CITY": ["city", "linn", "asula", "town", "locality"],
    "ZIP_CODE": ["zip", "postcode", "sihtnumber", "postal_code", "indeks"],
    "GOVERNMENT_ID": ["plate", "reg_nr", "car", "idCard", "document_no", "dokument"],
    "PASSPORT": ["passport", "pass", "passNo"],
    "DRIVERS_LICENSE": ["license", "juhiluba", "dl_number"],
    "IP_ADDRESS": ["ip", "client_ip", "remoteAddr"],
}
NEGKEYS = {"uuid": ["id", "uuid", "requestId", "correlation_id"], "hash": ["commit", "sha", "etag", "checksum"],
           "slack": ["slack_user", "owner_id", "assigned_to"], "ref": ["order", "ticket_ref", "tellimus"],
           "page": ["page_id", "pageId", "doc_id"], "reg": ["registrikood", "reg_code", "companyCode"],
           "org": ["company", "ettevote", "employer", "vendor"], "prod": ["product", "toode", "service"],
           "ver": ["version", "apiVersion", "build"], "date": ["created", "updated_at", "kuupaev", "valid_until"],
           "time": ["meeting", "kohtumine", "slot"], "amount": ["summa", "amount", "total"], "status": ["status", "olek", "state"]}


class Doc:
    def __init__(self, rng):
        self.parts, self.spans, self.n, self.rng = [], [], 0, rng
    def t(self, *xs):
        for x in xs:
            x = str(x); self.parts.append(x); self.n += len(x)
        return self
    def p(self, label, v):
        v = str(v); self.spans.append({"start": self.n, "end": self.n + len(v), "label": label}); return self.t(v)
    def text(self):
        return "".join(self.parts)


class Gen:
    def __init__(self, sampler, rng):
        self.S, self.r = sampler, rng

    def person(self, script=None):
        S, r = self.S, self.r
        p = S.person(script=script)
        st, full, abbr = S.street()
        city, zp = S.city()
        lower = r.random() < 0.08
        f = (lambda x: x.lower()) if lower else (lambda x: x)
        return {"GIVEN_NAME": f(p.given), "SURNAME": f(p.surname), "ISIKUKOOD": S.isikukood(p), "EMAIL": S.email(p), "PHONE": S.phone(),
                "BANK_ACCOUNT": S.iban(), "STREET_NAME": f(f"{st} {r.choice([full, abbr])}"), "BUILDING_NUMBER": S.building(),
                "SECONDARY_ADDRESS": S.apartment(), "CITY": f(city), "ZIP_CODE": S.zip(zp), "GOVERNMENT_ID": r.choice([S.plate(), S.id_doc()]),
                "PASSPORT": S.passport(), "DRIVERS_LICENSE": S.drivers_license(),
                "IP_ADDRESS": f"{r.randint(11, 223)}.{r.randint(0, 255)}.{r.randint(0, 255)}.{r.randint(1, 254)}"}

    def negval(self, kind):
        r = self.r
        return {"uuid": lambda: str(uuid.UUID(int=r.getrandbits(128))), "hash": lambda: "%0*x" % (r.choice([7, 8, 12, 40]), r.getrandbits(160)),
                "slack": lambda: "U0" + "".join(r.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789") for _ in range(r.randint(7, 9))),
                "ref": lambda: f"#{r.randint(100, 99999)}", "page": lambda: str(r.randint(10 ** 6, 10 ** 10)),
                "reg": lambda: f"{r.choice('189')}{r.randint(0, 9999999):07d}", "org": lambda: r.choice(ORGS), "prod": lambda: r.choice(PRODS),
                "ver": lambda: r.choice([f"v{r.randint(0, 9)}.{r.randint(0, 40)}.{r.randint(0, 20)}", f"{r.randint(1, 9)}.{r.randint(0, 40)}.{r.randint(0, 20)}"]),
                "date": lambda: r.choice([(datetime.date(2020, 1, 1) + datetime.timedelta(days=r.randint(0, 2500))).isoformat(), self.S.date_text()]),
                "time": lambda: r.choice([f"kella {r.randint(7, 20)}", f"kell {r.randint(7, 20)}.{r.choice(['00', '15', '30', '45'])}", f"{r.randint(7, 20)}:{r.choice(['00', '30'])}"]),
                "amount": lambda: f"{r.randint(1, 20000)}.{r.randint(0, 99):02d}", "status": lambda: r.choice(["ACTIVE", "pending", "SUSPENDED", "aktiivne", "suletud"])}[kind]()

    def record(self, pp):
        r = self.r
        fields = []
        if r.random() < 0.4:
            fields.append(("FULL", r.choice(KEYS["FULL"])))
        else:
            fields += [("GIVEN_NAME", r.choice(KEYS["GIVEN_NAME"])), ("SURNAME", r.choice(KEYS["SURNAME"]))]
        for lab in r.sample([k for k in KEYS if k not in ("GIVEN_NAME", "SURNAME", "FULL")], r.randint(2, 7)):
            fields.append((lab, r.choice(KEYS[lab])))
        for kind in r.sample(list(NEGKEYS), r.randint(2, 5)):
            fields.append(("NEG:" + kind, r.choice(NEGKEYS[kind])))
        r.shuffle(fields)
        out = []
        for lab, key in fields:
            if lab == "FULL":
                out.append((key, [("GIVEN_NAME", pp["GIVEN_NAME"]), (None, " "), ("SURNAME", pp["SURNAME"])]))
            elif lab.startswith("NEG:"):
                out.append((key, [(None, self.negval(lab[4:]))]))
            else:
                out.append((key, [(lab, pp[lab])]))
        return out

    def val(self, d, segs):
        for lab, v in segs:
            d.p(lab, v) if lab else d.t(v)

    def ser_json(self, d, recs):
        r = self.r; ind = r.choice(["", "  ", "    "]); nl = "\n" if ind else " "
        d.t(r.choice(['{"data": [', '[', '{"items": [', '{"results": [']), nl)
        for i, rec in enumerate(recs):
            d.t(ind, "{")
            for j, (k, segs) in enumerate(rec):
                d.t(nl, ind * 2, f'"{k}": "'); self.val(d, segs); d.t('"', "," if j < len(rec) - 1 else "")
            d.t(nl, ind, "}", "," if i < len(recs) - 1 else "", nl)
        d.t("]}" if r.random() < 0.7 else "]", "\n")

    def ser_yaml(self, d, recs):
        d.t(self.r.choice(["records:\n", "items:\n", "examples:\n  sample:\n    value:\n", "data:\n"]))
        for rec in recs:
            for j, (k, segs) in enumerate(rec):
                d.t("  - " if j == 0 else "    ", k, ": ")
                q = self.r.random() < 0.4
                d.t('"' if q else ""); self.val(d, segs); d.t('"' if q else "", "\n")

    def ser_csv(self, d, recs):
        sep = self.r.choice([",", ";", "|", "\t"]); cols = [k for k, _ in recs[0]]
        d.t(sep.join(cols), "\n")
        for rec in recs:
            m = dict(rec)
            for j, c in enumerate(cols):
                if c in m: self.val(d, m[c])
                d.t(sep if j < len(cols) - 1 else "\n")

    def ser_sql(self, d, recs):
        r = self.r; tbl = r.choice(["kliendid", "users", "persons", "isikud", "contacts", "payees"]); cols = [k for k, _ in recs[0]]
        if r.random() < 0.5:
            d.t(f"CREATE TABLE {tbl} (", ", ".join(f"{c} varchar(255)" for c in cols), ");\n")
        multi = r.random() < 0.5
        if multi: d.t(f"INSERT INTO {tbl} ({', '.join(cols)}) VALUES\n")
        for i, rec in enumerate(recs):
            m = dict(rec)
            d.t("  (" if multi else f"INSERT INTO `{tbl}` VALUES (")
            for j, c in enumerate(cols):
                if c in m: d.t("'"); self.val(d, m[c]); d.t("'")
                else: d.t("NULL")
                if j < len(cols) - 1: d.t(", ")
            d.t(("),\n" if i < len(recs) - 1 else ");\n") if multi else ");\n")

    def ser_html(self, d, recs):
        r = self.r; sp = r.choice(["&nbsp;", " ", "&#160;", "\u00a0"])
        d.t(r.choice(['<table class="confluenceTable"><tbody>', '<div class="panel"><table>', '<ac:layout><ac:layout-section><table data-layout="wide">']), "\n")
        for rec in recs:
            for k, segs in rec:
                d.t(f'<tr><th class="confluenceTh"><strong>{k}</strong></th><td class="confluenceTd"><span style="color: rgb(0,0,0);">')
                for lab, v in segs:
                    d.p(lab, v) if lab else d.t(sp)
                d.t("</span></td></tr>\n")
        d.t("</tbody></table>\n")

    def ser_kv(self, d, recs):
        r = self.r; eq = r.choice(["=", ": ", " = "])
        for rec in recs:
            d.t(r.choice(["", "[", "ts=" + self.negval("date") + " "]))
            for j, (k, segs) in enumerate(rec):
                d.t(k, eq); self.val(d, segs); d.t(" " if j < len(rec) - 1 else "\n")

    def ser_mdtable(self, d, recs):
        cols = [k for k, _ in recs[0]]
        d.t("| ", " | ".join(cols), " |\n|", "---|" * len(cols), "\n")
        for rec in recs:
            m = dict(rec); d.t("|")
            for c in cols:
                d.t(" ")
                if c in m: self.val(d, m[c])
                d.t(" |")
            d.t("\n")

    def structured(self):
        r = self.r
        d = Doc(r)
        if r.random() < 0.5: d.t(r.choice(["# export ", "-- dump ", "<!-- page ", "Report: ", "// fixture "]), self.negval(r.choice(["org", "prod", "date"])), "\n")
        ser = r.choice([self.ser_json, self.ser_yaml, self.ser_csv, self.ser_sql, self.ser_html, self.ser_kv, self.ser_mdtable])
        base = self.record(self.person())
        keys = [k for k, _ in base]
        recs = [base]
        for _ in range(r.randint(0, 5)):
            p2 = self.person(); fresh = self.record(p2); fm = {}
            for lab_key, segs in fresh: fm.setdefault(lab_key, segs)
            rec = []
            for k, segs in base:
                labs = [l for l, _ in segs if l]
                if labs and all(l in p2 for l in labs):
                    rec.append((k, [(l, p2[l]) if l else (None, v) for l, v in segs]))
                elif not labs:
                    kind = next(nk for nk, ks in NEGKEYS.items() if k in ks)
                    rec.append((k, [(None, self.negval(kind))]))
                else:
                    rec.append((k, segs))
            recs.append(rec)
        ser(d, recs)
        return d, ser.__name__

    def prose(self):
        r = self.r; d = Doc(r); a, b = self.person(), self.person(r.choice([None, "cyrillic"]))
        kind = r.choice(["email", "slack", "jira", "note", "minutes", "teams"])
        nm = lambda pp: d.p("GIVEN_NAME", pp["GIVEN_NAME"]).t(" ").p("SURNAME", pp["SURNAME"])
        if kind == "email":
            d.t(r.choice(["Saatja: ", "From: ", "От: "])); nm(a).t(" <").p("EMAIL", a["EMAIL"]).t(">\n", r.choice(["Saaja: ", "To: "])).p("EMAIL", b["EMAIL"]).t("\n")
            d.t(r.choice(["Teema: ", "Subject: "]), r.choice(["Fwd: ", "Re: ", ""]), r.choice(["leping ", "makse ", "ligipääs "]), self.negval("ref"), "\n\n")
            d.t(r.choice(["Hei ", "Tere ", "Hi ", "Здравствуйте, "])).p("GIVEN_NAME", b["GIVEN_NAME"]).t(r.choice([",\n\n", "!\n\n"]))
            d.t(r.choice(["kohtume ", "call on ", "созвон "]), self.negval("time"), ", ", self.negval("prod"), r.choice([" link tuleb kalendrisse.", " ei tööta."]), "\n\n")
            d.t(r.choice(["Parimat\n", "Lugupidamisega\n", "BR,\n", "С уважением,\n", "--\n"])); nm(a).t("\n", r.choice(["Arendusjuht", "CTO", "Raamatupidaja", "Klienditugi"]), ", ", self.negval("org"), "\n")
            d.t(r.choice(["M: ", "Tel: ", "+ "])).p("PHONE", a["PHONE"]).t("\n")
            if r.random() < 0.6: d.p("STREET_NAME", a["STREET_NAME"]).t(" ").p("BUILDING_NUMBER", a["BUILDING_NUMBER"]).t(", ").p("CITY", a["CITY"]).t("\n")
            if r.random() < 0.7:
                d.t("\n", r.choice(["-----Original Message-----\n", "> ", "Kirjutas "])); nm(b).t(r.choice([" kirjutas:\n> ", ":\n> "]))
                d.t(r.choice(["minu uus number on ", "мой телефон "])).p("PHONE", b["PHONE"]).t(r.choice([" ja konto ", " и счёт "])).p("BANK_ACCOUNT", b["BANK_ACCOUNT"]).t("\n")
        elif kind in ("slack", "teams"):
            for _ in range(r.randint(2, 6)):
                who = r.choice([a, b])
                d.t(r.choice(["", "[", "**"])); nm(who).t(r.choice(["  ", "] ", "** "]), self.negval("time"), "\n")
                c = r.randint(0, 4)
                if c == 0: d.t("<@", self.negval("slack"), "> vaata ", self.negval("ref"), " pls\n")
                elif c == 1: d.t("deploy ", self.negval("ver"), " ", self.negval("hash"), " läks läbi :white_check_mark:\n")
                elif c == 2: d.t("kliendi ").p("GIVEN_NAME", b["GIVEN_NAME"]).t(" ik on ").p("ISIKUKOOD", b["ISIKUKOOD"]).t(" kontrolli palun\n")
                elif c == 3: d.t("helistan ").p("SURNAME", a["SURNAME"]).t("-le ", self.negval("time"), ", nr ").p("PHONE", a["PHONE"]).t("\n")
                else: d.t("request ", self.negval("uuid"), " failed in ", self.negval("prod"), "\n")
        elif kind == "jira":
            d.t(r.choice(["PROJ", "SUP", "DEV", "KLT"]), "-", r.randint(1, 9999), " | ", r.choice(["Bug", "Task", "Incident"]), " | ", self.negval("status"), "\n")
            d.t(r.choice(["Reporter", "Teataja", "Created by"]), ": "); nm(a).t("\n", r.choice(["Assignee", "Täitja"]), ": ", "Unassigned\n" if r.random() < 0.3 else "")
            if not d.parts[-1].startswith("Unassigned"): nm(b).t("\n")
            d.t("Labels: ", self.negval("prod"), ", ", self.negval("ver"), "\n\nKlient ").p("SURNAME", b["SURNAME"]).t(" (").p("EMAIL", b["EMAIL"]).t(r.choice([") ei saa arvet alla laadida. ", ") reports 500 on /invoices. "]))
            d.t("Trace: ", self.negval("uuid"), "\nKeskkond: ", self.negval("prod"), " ", self.negval("ver"), "\n")
        elif kind == "note":
            f = lambda s: s.lower()
            d.t(r.choice(["", "!!! ", "mmm "]), "helistada ").p("GIVEN_NAME", f(a["GIVEN_NAME"])).t(" ").p("SURNAME", f(a["SURNAME"])).t(" ").p("PHONE", a["PHONE"]).t(" ", self.negval("time"), " ")
            d.t(r.choice(["re ", "по поводу ", "about "]), self.negval("ref"), " ", r.choice(["ei vasta", "не отвечает", "no reply"]), "\n")
            d.t(r.choice(["saata leping ", "send contract to ", "отправить "])).p("EMAIL", b["EMAIL"]).t(" ", self.negval("prod"), " kaudu\n")
            d.t(r.choice(["aadr ", "адрес ", "addr "])).p("STREET_NAME", f(b["STREET_NAME"])).t(" ").p("BUILDING_NUMBER", b["BUILDING_NUMBER"]).t(r.choice(["-", " kt "])).p("SECONDARY_ADDRESS", b["SECONDARY_ADDRESS"]).t(" ").p("CITY", f(b["CITY"])).t(" ")
            d.t(r.choice(["auto ", "машина "])).p("GOVERNMENT_ID", b["GOVERNMENT_ID"]).t("\n")
        else:
            d.t(r.choice(["Arutelu ", "Sync ", "Retro "]), self.negval("date"), " ", self.negval("time"), "\n", r.choice(["Kohal: ", "Present: ", "Присутствовали: "]))
            ps = [a, b] + [self.person() for _ in range(r.randint(0, 3))]
            for i, pp in enumerate(ps):
                nm(pp).t(", " if i < len(ps) - 1 else "\n")
            d.t("- ", self.negval("prod"), " ", self.negval("ver"), " release: ").p("SURNAME", ps[-1]["SURNAME"]).t("\n- ").p("GIVEN_NAME", a["GIVEN_NAME"]).t(r.choice([" uurib ", " võtab ", " checks "]), self.negval("ref"), "\n")
            d.t("- järgmine kord ", self.negval("time"), ", ", self.negval("org"), " kontoris\n")
        return d, "prose_" + kind


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30000)
    ap.add_argument("--split", default="train")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lexicon", default=str(ROOT / "lexicon/lexicon.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    S = Sampler(a.lexicon, split=a.split, seed=a.seed); S.rng = rng
    g = Gen(S, rng)
    with open(a.out, "w") as fh:
        for i in range(a.n):
            d, kind = g.structured() if rng.random() < 0.6 else g.prose()
            text = d.text()
            fh.write(json.dumps({"id": f"docs:{a.split}:{a.seed}:{i}", "source": "docs", "lang": "et", "text": text, "spans": d.spans,
                                 "public": [], "meta": {"kind": kind}}, ensure_ascii=False) + "\n")
    print(a.n, "rows ->", a.out)


if __name__ == "__main__":
    main()
