import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))

from et.deterministic import detect
from et.normalize import fold, model_view, premask_view, transliterate
from et.synth import Generator
from et.validators import is_valid_iban, is_valid_isikukood
from et.values import Sampler

LEX = str(ROOT / "lexicon/lexicon.json")


def test_parity_fixture_matches_python():
    for case in json.load(open(ROOT / "fixtures/parity.json")):
        spans = [[s.start, s.end, s.label] for s in detect(case["text"])]
        assert spans == case["spans"]
        assert premask_view(case["text"], [tuple(s) for s in spans]) == case["masked"]


def test_generated_identifiers_validate():
    s = Sampler(LEX, seed=3)
    for _ in range(500):
        p = s.person()
        assert is_valid_isikukood(s.isikukood(p))
        assert not is_valid_isikukood(s.isikukood(p, valid=False))
        assert is_valid_iban(s.iban())


def test_transliteration_follows_estonian_rules():
    assert transliterate("Елена Смирнова") == "Jelena Smirnova"
    assert transliterate("Юлия Щербакова") == "Julija Štšerbakova"
    assert fold("Жанна Мägi") == "zanna magi"


def test_model_view_maps_back_to_raw():
    raw = "Jüri Mägi, isikukood 38001085718."
    view, starts, ends = model_view(raw, [(s.start, s.end, s.label) for s in detect(raw)])
    assert "[isikukood]" in view
    i = view.index("magi")
    assert raw[starts[i]:ends[i + 3]] == "Mägi"


def test_synthetic_spans_are_consistent():
    g = Generator(LEX, seed=11)
    for _ in range(300):
        r = g.row()
        last = -1
        for sp in r.spans:
            assert 0 <= sp["start"] < sp["end"] <= len(r.text)
            assert sp["start"] >= last
            assert r.text[sp["start"]:sp["end"]].strip()
            last = sp["end"]
