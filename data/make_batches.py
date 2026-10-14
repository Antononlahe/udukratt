import argparse
import itertools
import random
from pathlib import Path

SCENARIOS = {
    "tootus": ("Töötukassa", "registreerimine töötuks, töötuskindlustushüvitis, töötutoetus, koolitused, tööharjutus"),
    "pension": ("Sotsiaalkindlustusamet", "vanaduspension, toitjakaotuspension, ennetähtaegne pension"),
    "pere": ("Sotsiaalkindlustusamet", "lapsetoetus, vanemahüvitis, lasterikka pere toetus, elatisabi"),
    "hooldus": ("valla sotsiaalosakond", "hooldajatoetus, puudega inimese toetus, toimetulekutoetus, koduteenus"),
    "elukoht": ("Rahvastikuregister", "elukoha registreerimine, sünni ja surma registreerimine, nimemuutus"),
    "dokumendid": ("Politsei- ja Piirivalveamet", "ID-kaart, pass, elamisluba, kadunud dokument, digi-ID"),
    "transport": ("Transpordiamet", "juhiluba, sõiduki registreerimine, trahv, tehnoülevaatus"),
    "maksud": ("Maksu- ja Tolliamet", "tuludeklaratsioon, maksuvõlg, FIE, käibemaksukohustus, tagastus"),
    "tervis": ("Tervisekassa", "ravikindlustus, töövõimetusleht, hambaravihüvitis, Euroopa ravikindlustuskaart"),
    "taitur": ("Kohtutäitur", "arestitud konto, võlg, maksegraafik, elatisvõlg"),
    "haridus": ("Haridus- ja Noorteamet", "lasteaiakoht, kooli registreerimine, õppetoetus, diplom"),
    "riigiabi": ("Ettevõtluse ja Innovatsiooni Sihtasutus", "riigiabi ja vähese tähtsusega abi taotlus, toetuse aruanne, tagasinõue"),
}
LANGS = [("et", 0.6), ("ru", 0.22), ("en", 0.08), ("mixed", 0.05), ("et_public", 0.05)]
STYLES = [
    "kiirustades telefonist, typod ja ilma täpitähtedeta", "kõik väiketähtedega, ilma kirjavahemärkideta",
    "dikteeritud kõnest, numbrid sõnadega ja korduvad sõnad", "kopeeritud vormiväljad, mõni väli valesti täidetud",
    "ametlik avaldus pöördumise ja allkirjaga", "pahane kaebus pika taustaloo ja mitme isikuga",
    "eakas inimene, viisakas ja segaduses", "noor, slängiga ja emotikonidega",
    "lähedase või esindaja nimel kirjutatud", "mitu sõnumit järjest, teises parandus eelmisele",
    "keelte segamine lause sees", "väga lühike, üks või kaks rida",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", type=int, default=400)
    ap.add_argument("--per-batch", type=int, default=25)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--outdir", default="batches")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    out = Path(a.outdir)
    (out / "out").mkdir(parents=True, exist_ok=True)
    combos = list(itertools.product(SCENARIOS, [l for l, _ in LANGS]))
    weights = [dict(LANGS)[l] for _, l in combos]
    for i in range(a.batches):
        sid, lang = rng.choices(combos, weights)[0]
        agency, topics = SCENARIOS[sid]
        styles = rng.sample(STYLES, 3)
        (out / f"batch_{i:03d}.md").write_text(
            f"lang: {lang}\nscenario: {sid}\nagency: {agency}\ntopics: {topics}\n"
            f"styles: {' | '.join(styles)}\ncount: {a.per_batch}\n"
            f"output: {out}/out/batch_{i:03d}.jsonl\nspec: data/TEMPLATE_SPEC.md\n"
        )
    print(a.batches, "batches,", a.batches * a.per_batch, "templates requested")


if __name__ == "__main__":
    main()
