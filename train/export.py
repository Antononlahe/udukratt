import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from onnxruntime.quantization.matmul_nbits_quantizer import DefaultWeightOnlyQuantConfig, MatMulNBitsQuantizer
from tokenizers import Tokenizer
from transformers import AutoModelForTokenClassification, BertTokenizerFast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from et.encode import encode  # noqa: E402

logging.getLogger("onnxruntime").setLevel(logging.ERROR)


def export_fp32(model, path: Path, opset: int):
    ids = torch.ones(1, 16, dtype=torch.long)
    kwargs = dict(input_names=["input_ids", "attention_mask", "token_type_ids"], output_names=["logits"],
                  dynamic_axes={n: {0: "batch", 1: "seq"} for n in ("input_ids", "attention_mask", "token_type_ids", "logits")},
                  opset_version=opset, do_constant_folding=True)
    try:
        torch.onnx.export(model, (ids, torch.ones_like(ids), torch.zeros_like(ids)), str(path), dynamo=False, **kwargs)
    except TypeError:
        torch.onnx.export(model, (ids, torch.ones_like(ids), torch.zeros_like(ids)), str(path), **kwargs)


def quantize_q4(src: Path, dst: Path, block: int):
    tmp = dst.with_suffix(".matmul4.onnx")
    q = MatMulNBitsQuantizer(onnx.load(str(src)), algo_config=DefaultWeightOnlyQuantConfig(block_size=block, is_symmetric=True, accuracy_level=4))
    q.process()
    q.model.save_model_to_file(str(tmp), False)
    quantize_dynamic(str(tmp), str(dst), op_types_to_quantize=["Gather"], weight_type=QuantType.QUInt8)
    tmp.unlink()


def agreement(fp32: Path, q4: Path, rows, tok, n: int):
    a, b = ort.InferenceSession(str(fp32)), ort.InferenceSession(str(q4))
    same = total = ent = ent_same = 0
    for r in rows[:n]:
        ids = np.array([encode(r, tok)[0]["input_ids"]], dtype=np.int64)
        feed = {"input_ids": ids, "attention_mask": np.ones_like(ids), "token_type_ids": np.zeros_like(ids)}
        pa = a.run(None, feed)[0].argmax(-1)
        pb = b.run(None, feed)[0].argmax(-1)
        same += int((pa == pb).sum())
        total += pa.size
        mask = pa > 0
        ent += int(mask.sum())
        ent_same += int((pa[mask] == pb[mask]).sum())
    return same / max(1, total), ent_same / max(1, ent)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--val")
    ap.add_argument("--block-size", type=int, default=32)
    ap.add_argument("--opset", type=int, default=17)
    ap.add_argument("--check-rows", type=int, default=300)
    a = ap.parse_args()
    src, out = Path(a.model), Path(a.out)
    (out / "onnx").mkdir(parents=True, exist_ok=True)
    model = AutoModelForTokenClassification.from_pretrained(src).eval()
    fp32, q4 = out / "onnx" / "model.onnx", out / "onnx" / "model_q4.onnx"
    export_fp32(model, fp32, a.opset)
    quantize_q4(fp32, q4, a.block_size)
    model.config.save_pretrained(out)
    hf = BertTokenizerFast.from_pretrained(src)
    hf.save_pretrained(out)
    for extra in ("vocab.txt", "rampart_et_train.json"):
        if (src / extra).exists():
            (out / extra).write_bytes((src / extra).read_bytes())
    report = {"fp32_mb": round(fp32.stat().st_size / 2**20, 2), "q4_mb": round(q4.stat().st_size / 2**20, 2)}
    if a.val:
        rows = [json.loads(l) for _, l in zip(range(a.check_rows), open(a.val))]
        tok = Tokenizer.from_file(str(out / "tokenizer.json"))
        report["token_agreement"], report["entity_token_agreement"] = agreement(fp32, q4, rows, tok, a.check_rows)
    json.dump(report, open(out / "export_report.json", "w"), indent=1)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
