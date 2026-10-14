import json, random, sys, uuid, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from et.values import Sampler, ASCII
from et.normalize import transliterate

S = Sampler(str(ROOT / "lexicon/lexicon.json"), split="heldout", seed=2026)
R = random.Random(2026)
S.rng = R
COMPANIES = ["Telia Eesti AS", "Bolt Technology OÜ", "Swedbank AS", "Elering AS", "Tallinna Vesi AS", "Nortal AS", "Pipedrive OÜ",
             "Wise Payments Ltd", "Eesti Energia AS", "Cleveron AS", "Veriff OÜ", "Starship Technologies", "Rimi Eesti Food AS", "LHV Pank AS",
             "Fortumo OÜ", "Helmes AS", "Omniva", "Maksu- ja Tolliamet", "Töötukassa", "Riigi Infosüsteemi Amet", "Kühne+Nagel Eesti"]
PRODUCTS = ["Smart-ID", "Mobiil-ID", "X-tee", "eesti.ee", "Jira Cloud", "Confluence", "PostgreSQL", "Kafka", "Kubernetes", "Grafana",
            "SAP S/4HANA", "Merit Aktiva", "Directo", "Salesforce", "Keycloak", "Bürokratt", "e-Residency", "TARA"]
IDENTS = ["customerId", "user_service", "PaymentGateway", "fetchInvoiceById", "MAX_RETRY", "isikukoodValidator", "AddressMapper",
          "kliendi_tabel", "OrderStatus.PENDING", "tallinn-prod-01", "ee-north-1", "auth.token.ttl"]
OCR = str.maketrans({"o": "0", "l": "1", "e": "c", "a": "o", "i": "l", "m": "rn", "@": "G", "5": "S"})

class Doc:
    def __init__(self, fmt, noise=0.0):
        self.fmt, self.parts, self.spans, self.neg, self.noise = fmt, [], [], [], noise
        self.n = 0
    def _add(self, s):
        if self.noise and R.random() < 0.5:
            s = "".join(c.translate(OCR) if R.random() < self.noise else c for c in s)
        self.parts.append(s); a = self.n; self.n += len(s); return a, s
    def t(self, *xs):
        for x in xs: self._add(str(x))
        return self
    def p(self, label, v):
        a, s = self._add(str(v)); self.spans.append({"start": a, "end": a + len(s), "label": label, "value": s}); return self
    def x(self, kind, v):
        a, s = self._add(str(v)); self.neg.append({"start": a, "end": a + len(s), "kind": kind, "value": s}); return self
    def out(self, uid):
        return {"uid": uid, "format": self.fmt, "text": "".join(self.parts), "spans": self.spans, "negatives": self.neg}

class P:
    def __init__(self, script=None):
        self.p = S.person(script=script)
        self.g, self.s = self.p.given, self.p.surname
        self.ik = S.isikukood(self.p); self.mail = S.email(self.p); self.tel = S.phone(); self.iban = S.iban()
        st, full, abbr = S.street(); self.street = f"{st} {R.choice([full, abbr])}"
        self.house = S.building(); self.apt = S.apartment() if R.random() < 0.5 else None
        self.city, zp = S.city(); self.zip = S.zip(zp); self.plate = S.plate(); self.idc = S.id_doc()
        self.pas = S.passport(); self.dl = S.drivers_license()

def name(d, pp, order="gs"):
    if order == "gs": d.p("GIVEN_NAME", pp.g).t(" ").p("SURNAME", pp.s)
    else: d.p("SURNAME", pp.s).t(", ").p("GIVEN_NAME", pp.g)
    return d
def addr(d, pp):
    d.p("STREET_NAME", pp.street).t(" ").p("BUILDING_NUMBER", pp.house)
    if pp.apt: d.t("-").p("SECONDARY_ADDRESS", pp.apt)
    return d.t(", ").p("CITY", pp.city).t(" ").p("ZIP_CODE", pp.zip)
def date(): return S.date_text()
def iso(): return (datetime.datetime(2026, 1, 1) + datetime.timedelta(minutes=R.randint(0, 400000))).isoformat()
def neg(d, kind=None):
    kind = kind or R.choice(["company", "product", "ident", "date", "uuid", "version", "time", "ticket", "amount", "regcode", "order", "hash"])
    v = {"company": lambda: R.choice(COMPANIES), "product": lambda: R.choice(PRODUCTS), "ident": lambda: R.choice(IDENTS),
         "date": date, "uuid": lambda: str(uuid.UUID(int=R.getrandbits(128))), "version": lambda: f"v{R.randint(1,5)}.{R.randint(0,20)}.{R.randint(0,9)}",
         "time": lambda: R.choice([f"kella {R.randint(8,18)}", f"kell {R.randint(8,18)}:{R.choice(['00','15','30'])}", f"{R.randint(8,18)}:{R.choice(['00','30'])}"]),
         "ticket": lambda: f"{R.choice(['PAY','CRM','OPS','HR','INFRA'])}-{R.randint(10,9999)}", "amount": lambda: f"{S.amount()} EUR",
         "regcode": lambda: f"{R.choice('19')}{R.randint(0,9999999):07d}", "order": lambda: f"#{R.randint(100000,999999)}",
         "hash": lambda: "%07x" % R.getrandbits(28)}[kind]()
    return d.x(kind, v)

def openapi_yaml():
    d, pp = Doc("openapi_yaml"), P()
    d.t("openapi: 3.0.3\ninfo:\n  title: ").x("product", R.choice(PRODUCTS)).t(" Customer API\n  version: ").x("version", f"{R.randint(1,4)}.{R.randint(0,9)}.0")
    d.t("\n  contact:\n    name: ").p("GIVEN_NAME", pp.g).t(" ").p("SURNAME", pp.s).t("\n    email: ").p("EMAIL", pp.mail)
    d.t("\npaths:\n  /customers/{customerId}:\n    get:\n      operationId: ").x("ident", "getCustomerById").t("\n      responses:\n        '200':\n          content:\n            application/json:\n              example:\n")
    q = P()
    d.t("                id: ").x("uuid", str(uuid.UUID(int=R.getrandbits(128)))).t("\n                firstName: ").p("GIVEN_NAME", q.g).t("\n                lastName: ").p("SURNAME", q.s)
    d.t("\n                personalCode: \"").p("ISIKUKOOD", q.ik).t("\"\n                phone: \"").p("PHONE", q.tel).t("\"\n                iban: ").p("BANK_ACCOUNT", q.iban.replace(" ", ""))
    d.t("\n                address:\n                  street: ").p("STREET_NAME", q.street).t("\n                  house: \"").p("BUILDING_NUMBER", q.house).t("\"\n                  city: ").p("CITY", q.city).t("\n                  postalCode: \"").p("ZIP_CODE", q.zip)
    d.t("\"\n                createdAt: ").x("date", iso()).t("\n")
    return d

def openapi_json():
    d = Doc("openapi_json")
    d.t('{\n  "openapi": "3.1.0",\n  "info": {"title": "').x("company", R.choice(COMPANIES)).t(' billing", "version": "').x("version", f"{R.randint(1,3)}.{R.randint(0,30)}.{R.randint(0,9)}").t('"},\n  "components": {"examples": {\n')
    for i in range(R.randint(1, 3)):
        q = P()
        d.t(f'    "payer{i}": {{"value": {{"name": "').p("GIVEN_NAME", q.g).t(" ").p("SURNAME", q.s).t('", "email": "').p("EMAIL", q.mail)
        d.t('", "idCode": "').p("ISIKUKOOD", q.ik).t('", "account": "').p("BANK_ACCOUNT", q.iban).t('", "invoiceNo": "').x("order", f"INV-{R.randint(2024,2026)}-{R.randint(1000,9999)}")
        d.t('", "amount": ').x("amount", f"{R.randint(10,9000)}.{R.randint(10,99)}").t(', "ip": "').p("IP_ADDRESS", f"{R.randint(11,223)}.{R.randint(0,255)}.{R.randint(0,255)}.{R.randint(1,254)}").t('"}},\n')
    d.t('    "end": {}\n  }}\n}\n')
    return d

def meeting_notes():
    d = Doc("meeting_notes"); ps = [P() for _ in range(R.randint(2, 4))]
    d.t("Koosoleku protokoll – ").x("company", R.choice(COMPANIES)).t("\nKuupäev: ").x("date", date()).t(", algus ").x("time", f"kell {R.randint(9,16)}:00").t("\nOsalejad: ")
    for i, q in enumerate(ps): name(d, q).t(", " if i < len(ps) - 1 else "\n")
    d.t("\n1. ").x("product", R.choice(PRODUCTS)).t(" migratsioon – vastutaja ").p("GIVEN_NAME", ps[0].g).t(". Tähtaeg ").x("date", date()).t(".\n")
    d.t("2. Tiket ").x("ticket", f"OPS-{R.randint(100,999)}").t(" on endiselt lahti, ").p("SURNAME", ps[1].s).t(" uurib logisid.\n")
    d.t("3. Järgmine kohtumine ").x("time", f"kella {R.randint(10,17)}").t(" teisipäeval. Küsimused: ").p("EMAIL", ps[-1].mail).t(" või ").p("PHONE", ps[-1].tel).t(".\n")
    return d

def messy_notes():
    d = Doc("messy_notes"); q, w = P(), P(script="cyrillic")
    d.t(R.choice(["todo ", "NB!! ", "note to self "])).t("helista ").p("GIVEN_NAME", q.g.lower()).t(" ").p("SURNAME", q.s.lower()).t(" tel ").p("PHONE", q.tel).t(" ta ytles et ")
    d.x("product", R.choice(PRODUCTS)).t(" ei tooota jalle\n")
    d.t("pozvonit' ").p("GIVEN_NAME", w.g).t(" ").p("SURNAME", w.s).t(" насчет договора ").x("order", f"#{R.randint(1000,9999)}").t(" asap\n")
    d.t("ik ").p("ISIKUKOOD", q.ik).t(" konto ").p("BANK_ACCOUNT", q.iban).t(" maksa ").x("amount", f"{R.randint(50,900)}eur").t(" enne ").x("date", date()).t("\n")
    d.t("aadress ").p("STREET_NAME", q.street.lower()).t(" ").p("BUILDING_NUMBER", q.house).t(" ").p("CITY", q.city.lower()).t(" auto ").p("GOVERNMENT_ID", q.plate).t(" meeting ").x("time", f"kella {R.randint(9,18)}").t(" lol\n")
    return d

def confluence():
    d = Doc("confluence_xml"); q = P()
    d.t('<ac:structured-macro ac:name="info" ac:schema-version="1"><ac:rich-text-body><p>Owner: <ac:link><ri:user ri:username="').p("EMAIL", q.mail).t('" /></ac:link></p></ac:rich-text-body></ac:structured-macro>\n')
    d.t('<table class="wrapped confluenceTable"><colgroup><col /><col /></colgroup><tbody><tr><th class="confluenceTh"><span style="color: rgb(23,43,77);">Nimi</span></th><td class="confluenceTd"><span>').p("GIVEN_NAME", q.g).t("&nbsp;").p("SURNAME", q.s)
    d.t('</span></td></tr><tr><th class="confluenceTh">Telefon</th><td class="confluenceTd"><a href="tel:').p("PHONE", q.tel.replace(" ", "")).t('">').p("PHONE", q.tel).t('</a></td></tr>')
    d.t('<tr><th>Asukoht</th><td><p>').p("STREET_NAME", q.street).t(" ").p("BUILDING_NUMBER", q.house).t(", ").p("CITY", q.city).t('</p></td></tr><tr><th>Süsteem</th><td><ac:structured-macro ac:name="jira"><ac:parameter ac:name="key">').x("ticket", f"INFRA-{R.randint(10,999)}").t('</ac:parameter></ac:structured-macro> ').x("product", R.choice(PRODUCTS))
    d.t('</td></tr><tr><th>Uuendatud</th><td><time datetime="').x("date", f"2026-{R.randint(1,12):02d}-{R.randint(1,28):02d}").t('" /></td></tr></tbody></table>\n<p><ac:emoticon ac:name="warning" /> page id ').x("order", str(R.randint(10**8, 10**9))).t("</p>\n")
    return d

def jira():
    d = Doc("jira"); r, a, c = P(), P(), P()
    d.x("ticket", f"CRM-{R.randint(100,9999)}").t(": Klient ei saa ").x("product", R.choice(PRODUCTS)).t("-ga sisse logida\nReporter: ").p("GIVEN_NAME", r.g).t(" ").p("SURNAME", r.s).t("\nAssignee: ").p("GIVEN_NAME", a.g).t(" ").p("SURNAME", a.s)
    d.t("\nPriority: High   Fix Version: ").x("version", f"{R.randint(1,9)}.{R.randint(0,9)}").t("\n\nKirjeldus:\nKlient ").p("GIVEN_NAME", c.g).t(" ").p("SURNAME", c.s).t(" (isikukood ").p("ISIKUKOOD", c.ik).t(") helistas ").x("date", date()).t(" numbrilt ").p("PHONE", c.tel).t(".\n")
    d.t("Steps: 1) ava /login 2) sisesta ").p("EMAIL", c.mail).t(" 3) error 500\n\n{code}\nuserId=").x("uuid", str(uuid.UUID(int=R.getrandbits(128)))).t(" traceId=").x("hash", "%016x" % R.getrandbits(64)).t("\n{code}\n")
    d.t("\nKommentaar (").p("GIVEN_NAME", a.g).t("): reprodutseeritud, vt ").x("ticket", f"CRM-{R.randint(100,9999)}").t(".\n")
    return d

def email_thread():
    d = Doc("email_thread"); a, b = P(), P()
    d.t("From: ").p("GIVEN_NAME", a.g).t(" ").p("SURNAME", a.s).t(" <").p("EMAIL", a.mail).t(">\nTo: ").p("EMAIL", b.mail).t("\nSubject: RE: arve ").x("order", f"{R.randint(2026000,2026999)}").t("\nDate: ").x("date", date()).t("\n\nTere ")
    d.p("GIVEN_NAME", b.g).t("!\n\nSaatsin arve uuesti. Palun tasuge kontole ").p("BANK_ACCOUNT", a.iban).t(" hiljemalt ").x("date", date()).t(".\n\nLugupidamisega\n").p("GIVEN_NAME", a.g).t(" ").p("SURNAME", a.s)
    d.t("\nProjektijuht | ").x("company", R.choice(COMPANIES)).t("\nTel ").p("PHONE", a.tel).t("\n").p("STREET_NAME", a.street).t(" ").p("BUILDING_NUMBER", a.house).t(", ").p("ZIP_CODE", a.zip).t(" ").p("CITY", a.city)
    d.t("\n\n> On ").x("date", date()).t(", ").p("GIVEN_NAME", b.g).t(" ").p("SURNAME", b.s).t(" <").p("EMAIL", b.mail).t("> wrote:\n> Arve ei jõudnud kohale. Minu aadress on ")
    d.p("STREET_NAME", b.street).t(" ").p("BUILDING_NUMBER", b.house).t(", ").p("CITY", b.city).t(".\n> Tel ").p("PHONE", b.tel).t("\n")
    return d

def slack():
    d = Doc("slack_export"); ps = [P() for _ in range(3)]
    d.t("[\n")
    for i in range(R.randint(3, 6)):
        q = R.choice(ps); o = R.choice(ps)
        d.t('  {"type": "message", "user": "U0').x("ident", "%07X" % R.getrandbits(28)).t('", "user_profile": {"real_name": "').p("GIVEN_NAME", q.g).t(" ").p("SURNAME", q.s).t('"}, "ts": "').x("order", f"{R.randint(1700000000,1790000000)}.{R.randint(100000,999999)}").t('", "text": "')
        k = R.randint(0, 3)
        if k == 0: d.t("<@U0").x("ident", "%07X" % R.getrandbits(28)).t("> deploy ").x("version", f"v{R.randint(1,3)}.{R.randint(0,40)}.{R.randint(0,9)}").t(" on valmis :rocket:")
        elif k == 1: d.t("kas keegi teab ").p("GIVEN_NAME", o.g).t(" numbrit? vist ").p("PHONE", o.tel)
        elif k == 2: d.t("standup ").x("time", f"kell {R.randint(9,11)}:{R.choice(['00','30'])}").t(", ").x("ticket", f"PAY-{R.randint(10,999)}").t(" blokeeritud")
        else: d.t("saada lepingu koopia ").p("EMAIL", o.mail).t(" peale pls")
        d.t('"},\n')
    d.t("]\n")
    return d

def csv_table():
    d = Doc("csv_table"); sep = R.choice([",", ";", "\t"])
    d.t(sep.join(["id", "eesnimi", "perenimi", "isikukood", "telefon", "email", "aadress", "linn", "liitunud"]) + "\n")
    for i in range(R.randint(3, 12)):
        q = P()
        d.x("order", str(1000 + i)).t(sep).p("GIVEN_NAME", q.g).t(sep).p("SURNAME", q.s).t(sep).p("ISIKUKOOD", q.ik).t(sep).p("PHONE", q.tel).t(sep).p("EMAIL", q.mail).t(sep + '"').p("STREET_NAME", q.street).t(" ").p("BUILDING_NUMBER", q.house).t('"' + sep).p("CITY", q.city).t(sep).x("date", f"2025-{R.randint(1,12):02d}-{R.randint(1,28):02d}").t("\n")
    return d

def log_file():
    d = Doc("log_file")
    for i in range(R.randint(8, 25)):
        d.x("date", iso()).t(R.choice([" INFO ", " WARN ", " ERROR ", " DEBUG "])).t(f"[{R.choice(['auth','payments','gateway'])}-{R.randint(1,9)}] ")
        k = R.randint(0, 4); q = P()
        if k == 0: d.t("login ok user=").p("EMAIL", q.mail).t(" ip=").p("IP_ADDRESS", f"{R.randint(11,223)}.{R.randint(0,255)}.{R.randint(0,255)}.{R.randint(1,254)}")
        elif k == 1: d.t("payment failed iban=").p("BANK_ACCOUNT", q.iban.replace(" ", "")).t(" amount=").x("amount", f"{R.randint(1,999)}.{R.randint(10,99)}").t(" orderId=").x("uuid", str(uuid.UUID(int=R.getrandbits(128))))
        elif k == 2: d.t("GET /api/v2/persons/").p("ISIKUKOOD", q.ik).t(" 404 ").x("order", f"{R.randint(3,900)}ms")
        elif k == 3: d.t("SMS sent to ").p("PHONE", q.tel).t(" template=").x("ident", "OTP_LOGIN").t(" provider=").x("company", "Telia Eesti AS")
        else: d.t("worker ").x("ident", "tallinn-prod-0" + str(R.randint(1, 9))).t(" heartbeat build=").x("hash", "%07x" % R.getrandbits(28))
        d.t("\n")
    return d

def stack_trace():
    d, q = Doc("stack_trace"), P()
    d.t("Exception in thread \"main\" ee.").x("ident", R.choice(["registry.PersonValidationException", "billing.IbanMismatchError"])).t(": Invalid record for customer ").p("GIVEN_NAME", q.g).t(" ").p("SURNAME", q.s).t(" (").p("ISIKUKOOD", q.ik).t(")\n")
    for _ in range(R.randint(3, 8)):
        d.t("\tat ee.").x("ident", R.choice(IDENTS)).t(f"({R.choice(['Mapper','Service','Controller'])}.java:{R.randint(20,900)})\n")
    d.t("Caused by: java.lang.IllegalStateException: address ").p("STREET_NAME", q.street).t(" ").p("BUILDING_NUMBER", q.house).t(" not found in ").x("product", "X-tee").t(" response ").x("uuid", str(uuid.UUID(int=R.getrandbits(128)))).t("\n")
    return d

def contract():
    d = Doc("contract"); a, b = P(), P()
    d.t("TÖÖVÕTULEPING nr ").x("order", f"{R.randint(1,99)}/{R.randint(2024,2026)}").t("\n\n").x("company", R.choice(COMPANIES)).t(", registrikood ").x("regcode", f"1{R.randint(0,9999999):07d}").t(", keda esindab juhatuse liige ")
    name(d, a).t(" (edaspidi Tellija), ja\n\n")
    name(d, b).t(", isikukood ").p("ISIKUKOOD", b.ik).t(", elukoht ")
    addr(d, b).t(" (edaspidi Töövõtja),\n\nsõlmisid ").x("date", date()).t(" alljärgneva lepingu.\n\n")
    for k in range(R.randint(3, 8)):
        d.t(f"{k+1}. ").t(R.choice(["Töövõtja kohustub tegema tööd vastavalt lisale 1.", "Tasu makstakse Töövõtja arveldusarvele ", "Leping jõustub allkirjastamisel ja kehtib kuni ", "Pooled lahendavad vaidlused läbirääkimiste teel."]))
        if R.random() < 0.4: d.p("BANK_ACCOUNT", b.iban).t(".")
        elif R.random() < 0.4: d.x("date", date()).t(".")
        d.t(" Tasu on ").x("amount", f"{R.randint(500,9000)} EUR").t(".\n" * R.randint(1, 2))
    d.t("\nTellija: ").p("GIVEN_NAME", a.g).t(" ").p("SURNAME", a.s).t("   /allkirjastatud digitaalselt/\nTöövõtja: ").p("GIVEN_NAME", b.g).t(" ").p("SURNAME", b.s).t("   tel ").p("PHONE", b.tel).t("\n")
    return d

def invoice():
    d = Doc("invoice"); q = P()
    d.t("ARVE nr ").x("order", f"{R.randint(1000,99999)}").t("\nKuupäev ").x("date", date()).t("   Maksetähtaeg ").x("date", date()).t("\n\nMüüja: ").x("company", R.choice(COMPANIES)).t("\nReg.kood ").x("regcode", f"1{R.randint(0,9999999):07d}").t("  KMKR ").x("regcode", f"EE10{R.randint(0,9999999):07d}")
    d.t("\n\nOstja: ")
    name(d, q).t("\n"); addr(d, q).t("\n\n")
    d.t("Kirjeldus                 Kogus   Hind\n")
    for _ in range(R.randint(2, 6)): d.x("product", R.choice(PRODUCTS)).t(" litsents        1   ").x("amount", f"{R.randint(5,900)},00").t("\n")
    d.t("\nKokku: ").x("amount", f"{R.randint(100,9999)},{R.randint(10,99)} EUR").t("\nMakse kontole ").x("company", "LHV Pank AS").t(" ").p("BANK_ACCOUNT", S.iban()).t(", viitenumber ").x("order", str(R.randint(10**6, 10**8))).t("\n")
    return d

def hr_doc():
    d = Doc("hr_doc"); q = P(script=R.choice([None, "latin"]))
    d.t("TÖÖTAJA ANKEET\n\nPerekonnanimi: ").p("SURNAME", q.s).t("\nEesnimi: ").p("GIVEN_NAME", q.g).t("\nIsikukood: ").p("ISIKUKOOD", q.ik).t("\nIsikutunnistus: ").p("GOVERNMENT_ID", q.idc)
    d.t("\nPass: ").p("PASSPORT", q.pas).t("\nJuhiluba: ").p("DRIVERS_LICENSE", q.dl).t("\nAuto reg. nr: ").p("GOVERNMENT_ID", q.plate).t("\nElukoht: ")
    addr(d, q).t("\nTelefon: ").p("PHONE", q.tel).t("\nE-post: ").p("EMAIL", q.mail).t("\nPalgakonto: ").p("BANK_ACCOUNT", q.iban)
    e = P(); d.t("\nHädaolukorras teavitada: ").p("GIVEN_NAME", e.g).t(" ").p("SURNAME", e.s).t(", ").p("PHONE", e.tel)
    d.t("\nAmet: tarkvaraarendaja, ").x("company", R.choice(COMPANIES)).t("\nTööle asumise kuupäev: ").x("date", date()).t("\n")
    return d

def sql_dump():
    d = Doc("sql_dump")
    d.t("-- PostgreSQL database dump\n-- Dumped by pg_dump version ").x("version", f"16.{R.randint(1,6)}").t("\n\nCREATE TABLE public.customers (id uuid PRIMARY KEY, first_name text, last_name text, id_code char(11), email text, phone text, iban text, created_at timestamptz);\n\n")
    for _ in range(R.randint(3, 15)):
        q = P()
        d.t("INSERT INTO public.customers VALUES ('").x("uuid", str(uuid.UUID(int=R.getrandbits(128)))).t("', '").p("GIVEN_NAME", q.g.replace("'", "''")).t("', '").p("SURNAME", q.s.replace("'", "''")).t("', '").p("ISIKUKOOD", q.ik).t("', '").p("EMAIL", q.mail).t("', '").p("PHONE", q.tel).t("', '").p("BANK_ACCOUNT", q.iban.replace(" ", "")).t("', '").x("date", iso()).t("');\n")
    return d

def config():
    d = Doc("config"); q = P()
    d.t(R.choice(["# application.yml\n", "[default]\n"])).t("spring.datasource.url=jdbc:postgresql://").p("IP_ADDRESS", f"10.{R.randint(0,255)}.{R.randint(0,255)}.{R.randint(1,254)}").t(":5432/").x("ident", "kliendi_tabel")
    d.t("\nservice.version=").x("version", f"{R.randint(1,5)}.{R.randint(0,30)}.{R.randint(0,9)}").t("\nalerts.oncall.email=").p("EMAIL", q.mail).t("\nalerts.oncall.phone=").p("PHONE", q.tel.replace(" ", ""))
    d.t("\n# owner: ").p("GIVEN_NAME", q.g).t(" ").p("SURNAME", q.s).t("\nretry.max=").x("order", str(R.randint(1, 9))).t("\ncron.report=0 0 ").x("time", f"{R.randint(1,23)} * * *").t("\nfeature.").x("ident", "isikukoodValidator").t(".enabled=true\n")
    return d

def readme():
    d = Doc("readme_md"); q, c = P(), P()
    d.t("# ").x("ident", R.choice(["iban-validator", "address-mapper", "person-registry-client"])).t("\n\n![build](https://ci.example.ee/badge.svg) ").x("version", f"v{R.randint(0,3)}.{R.randint(0,20)}.{R.randint(0,9)}").t("\n\n## Usage\n\n```python\n")
    d.t("client.lookup(id_code=\"").p("ISIKUKOOD", q.ik).t("\")  # test isik ").p("GIVEN_NAME", q.g).t(" ").p("SURNAME", q.s).t("\n```\n\nIntegreerub teenusega ").x("product", R.choice(PRODUCTS)).t(". Vt ").x("ticket", f"OPS-{R.randint(10,999)}").t(".\n\n## Maintainers\n\n- ").p("GIVEN_NAME", c.g).t(" ").p("SURNAME", c.s).t(" (").p("EMAIL", c.mail).t(")\n")
    return d

def ocr_scan():
    d = Doc("ocr_scan", noise=0.08); q = P()
    d.t("AVALDUS\n\n").x("company", R.choice(["Maksu- ja Tolliamet", "Töötukassa", "Sotsiaalkindlustusamet"])).t("\n\nTaotleja nimi  ").p("GIVEN_NAME", q.g.upper()).t(" ").p("SURNAME", q.s.upper()).t("\nIsikukood  ").p("ISIKUKOOD", q.ik)
    d.t("\nAadress  ").p("STREET_NAME", q.street).t(" ").p("BUILDING_NUMBER", q.house).t(" , ").p("CITY", q.city).t("\nTel. ").p("PHONE", q.tel).t("  E-post ").p("EMAIL", q.mail).t("\nArveldusarve  ").p("BANK_ACCOUNT", q.iban)
    d.t("\n\nPalun maksta toetus ").x("amount", f"{R.randint(50,900)} €").t("\n\n").x("date", date()).t("          allkiri ______\n")
    return d

def chat():
    d = Doc("chat_transcript"); c, a = P(script=R.choice([None, "cyrillic"])), P()
    d.t("[").x("time", f"{R.randint(8,18):02d}:{R.randint(0,59):02d}").t("] Klient: tere, mul on probleem ").x("product", R.choice(PRODUCTS)).t("-ga\n[").x("time", f"{R.randint(8,18):02d}:{R.randint(0,59):02d}").t("] ").p("GIVEN_NAME", a.g).t(" (").x("company", R.choice(COMPANIES)).t("): Tere! Palun teie nimi ja isikukood?\n")
    d.t("[..] Klient: ").p("GIVEN_NAME", c.g).t(" ").p("SURNAME", c.s).t(", ").p("ISIKUKOOD", c.ik).t("\n[..] ").p("GIVEN_NAME", a.g).t(": Aitäh. Kas aadress on endiselt ").p("STREET_NAME", c.street).t(" ").p("BUILDING_NUMBER", c.house).t("?\n")
    d.t("[..] Klient: ei, kolisin, uus on ").p("STREET_NAME", P().street).t(" ").p("BUILDING_NUMBER", S.building()).t(" ").p("CITY", P().city).t(". helistage ").x("time", f"kella {R.randint(12,18)}").t(" peale ").p("PHONE", c.tel).t("\n")
    d.t("[..] ").p("GIVEN_NAME", a.g).t(": Selge, pöördumine nr ").x("ticket", f"CRM-{R.randint(1000,9999)}").t(".\n")
    return d

FMTS = [openapi_yaml, openapi_json, meeting_notes, messy_notes, confluence, jira, email_thread, slack, csv_table, log_file, stack_trace,
        contract, invoice, hr_doc, sql_dump, config, readme, ocr_scan, chat]
docs = []
for f in FMTS:
    for _ in range(22):
        docs.append(f().out(len(docs)))
for x in docs:
    for s in x["spans"] + x["negatives"]:
        assert x["text"][s["start"]:s["end"]] == s["value"]
out = Path(__file__).parent / "corp_suite.jsonl"
with open(out, "w") as fh:
    for x in docs: fh.write(json.dumps(x, ensure_ascii=False) + "\n")
print(len(docs), sum(len(x["spans"]) for x in docs), sum(len(x["negatives"]) for x in docs))
