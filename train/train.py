import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import torch
from datasets import Dataset
from tokenizers import Tokenizer
from transformers import (AutoConfig, AutoModelForTokenClassification, BertTokenizerFast,
                          DataCollatorForTokenClassification, Trainer, TrainingArguments)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from et.encode import check_normalizer, encode  # noqa: E402
from et.labels import ENTITY_TYPES, ID2LABEL, LABEL2ID  # noqa: E402

PROBES = ["Jüri Mägi elab Õismäel", "Елена Смирнова, улица Ленина", "ŠOKOLAAD Žürii", "ﬁnants 1½ €", "İstanbul ß"]


def dataset(path, tok, max_len, stride, prefilter, translit):
    def gen():
        with open(path) as fh:
            for line in fh:
                for ch in encode(json.loads(line), tok, max_len, stride, translit, prefilter):
                    ch["length"] = len(ch["input_ids"])
                    yield ch
    return Dataset.from_generator(gen)


def trim_embeddings(model, keep_ids):
    old = model.get_input_embeddings()
    new = torch.nn.Embedding(len(keep_ids), old.embedding_dim, padding_idx=0)
    new.weight.data = old.weight.data[torch.tensor(keep_ids)].clone()
    model.set_input_embeddings(new)
    model.config.vocab_size = len(keep_ids)


def hf_tokenizer(tok_dir: Path):
    return BertTokenizerFast(vocab_file=str(tok_dir / "vocab.txt"), tokenizer_file=str(tok_dir / "tokenizer.json"),
                             do_lower_case=True, strip_accents=True, model_max_length=512)


def metrics(eval_pred):
    preds, labels = eval_pred
    mask = labels != -100
    p, y = preds[mask], labels[mask]
    out = {"token_acc": float((p == y).mean())}
    ent_y, ent_p = y > 0, p > 0
    out["entity_token_recall"] = float((ent_p & ent_y).sum() / max(1, ent_y.sum()))
    out["entity_token_precision"] = float((ent_p & ent_y).sum() / max(1, ent_p.sum()))
    typ = lambda a: (a + 1) // 2
    for i, t in enumerate(ENTITY_TYPES, 1):
        sel = typ(y) == i
        if sel.any():
            out[f"recall_{t}"] = float((typ(p[sel]) == i).mean())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--tokenizer-dir", required=True)
    ap.add_argument("--base", default="nreimers/MiniLM-L6-H384-uncased")
    ap.add_argument("--random-init", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--wd", type=float, default=0.01)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--stride", type=int, default=128)
    ap.add_argument("--no-prefilter", action="store_true")
    ap.add_argument("--no-translit", action="store_true")
    ap.add_argument("--group-by-length", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    tok_dir = Path(a.tokenizer_dir)
    tok = Tokenizer.from_file(str(tok_dir / "tokenizer.json"))
    check_normalizer(tok, PROBES)
    kw = dict(num_labels=len(ID2LABEL), id2label=dict(enumerate(ID2LABEL)), label2id=LABEL2ID)
    if a.random_init:
        cfg = AutoConfig.for_model("bert", hidden_size=384, num_hidden_layers=6, num_attention_heads=12,
                                   intermediate_size=1536, vocab_size=30522, **kw)
        model = AutoModelForTokenClassification.from_config(cfg)
    else:
        model = AutoModelForTokenClassification.from_pretrained(a.base, **kw)
    keep = tok_dir / "keep_ids.json"
    if keep.exists():
        trim_embeddings(model, json.load(open(keep)))
    if model.config.vocab_size != tok.get_vocab_size():
        raise SystemExit(f"vocab mismatch: model {model.config.vocab_size} vs tokenizer {tok.get_vocab_size()}")

    prefilter, translit = not a.no_prefilter, not a.no_translit
    train_ds = dataset(a.train, tok, a.max_len, a.stride, prefilter, translit)
    val_ds = dataset(a.val, tok, a.max_len, a.stride, prefilter, translit)
    hf_tok = hf_tokenizer(tok_dir)
    cuda = torch.cuda.is_available()
    args = TrainingArguments(
        output_dir=a.out, num_train_epochs=a.epochs, per_device_train_batch_size=a.batch,
        per_device_eval_batch_size=a.batch * 2, learning_rate=a.lr, weight_decay=a.wd, optim="adamw_torch",
        eval_strategy="epoch", save_strategy="epoch", load_best_model_at_end=True,
        metric_for_best_model="eval_loss", greater_is_better=False, save_total_limit=3,
        bf16=cuda and torch.cuda.is_bf16_supported(), group_by_length=a.group_by_length,
        logging_steps=200, report_to="none", seed=a.seed, dataloader_num_workers=2 if cuda else 0,
    )
    trainer = Trainer(
        model=model, args=args, train_dataset=train_ds, eval_dataset=val_ds,
        data_collator=DataCollatorForTokenClassification(hf_tok, pad_to_multiple_of=8),
        processing_class=hf_tok, compute_metrics=metrics,
        preprocess_logits_for_metrics=lambda logits, labels: logits.argmax(-1),
    )
    trainer.train()
    best = Path(a.out) / "best"
    trainer.save_model(best)
    hf_tok.save_pretrained(best)
    shutil.copy(tok_dir / "vocab.txt", best / "vocab.txt")
    json.dump({"prefilter": prefilter, "translit": translit, **{k: v for k, v in vars(a).items() if k not in ("train", "val")}},
              open(best / "rampart_et_train.json", "w"), indent=1)
    print(json.dumps(trainer.evaluate(), indent=1))


if __name__ == "__main__":
    main()
