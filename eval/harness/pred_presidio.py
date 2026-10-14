import json, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from suites import load, R
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import (EmailRecognizer, PhoneRecognizer, IbanRecognizer, CreditCardRecognizer,
                                                      IpRecognizer, UrlRecognizer, SpacyRecognizer)
nlp = NlpEngineProvider(nlp_configuration={"nlp_engine_name": "spacy", "models": [{"lang_code": "et", "model_name": "xx_ent_wiki_sm"}]}).create_engine()
reg = RecognizerRegistry(supported_languages=["et"])
for rc in [EmailRecognizer(supported_language="et"), PhoneRecognizer(supported_language="et", supported_regions=("EE", "FI", "RU", "LV", "GB", "US")),
           IbanRecognizer(supported_language="et"), CreditCardRecognizer(supported_language="et"), IpRecognizer(supported_language="et"),
           UrlRecognizer(supported_language="et"), SpacyRecognizer(supported_language="et")]:
    reg.add_recognizer(rc)
eng = AnalyzerEngine(nlp_engine=nlp, registry=reg, supported_languages=["et"])
ENTS = ["PERSON", "LOCATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "IBAN_CODE", "CREDIT_CARD", "IP_ADDRESS", "URL"]
out = {}
for s, docs in load().items():
    out[s] = [[[x.start, x.end, x.entity_type] for x in eng.analyze(d["text"], language="et", entities=ENTS)] for d in docs]
json.dump(out, open(R / "work4/eval/preds_presidio.json", "w"))
print("done")
