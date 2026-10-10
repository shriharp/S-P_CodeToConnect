"""Fine-tune a DistilRoBERTa event classifier on the generated training data.

CPU-first, no GPU. Trains a sequence-classification head over the event
taxonomy on data/event_train.jsonl, then evaluates on the SAME held-out
EVENT_EVAL_CASES used to benchmark keyword/hybrid/zero-shot — so the comparison
is apples-to-apples with no train/test contamination (the generator excludes
eval texts).

Honesty: training data is synthetic/templated. This measures whether fine-tuning
beats the hybrid on our eval fixtures, NOT real-world accuracy. Checkpoint is
saved to backend/models/event_classifier (gitignored, ~270MB).

Run:
    cd backend && .venv/bin/python -m scripts.finetune_event_classifier
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
from torch.utils.data import DataLoader, RandomSampler
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

from app.nlp.event_eval_cases import EVENT_EVAL_CASES

DATA = Path(__file__).resolve().parents[1] / "data" / "event_train.jsonl"
SAVE_DIR = Path(__file__).resolve().parents[1] / "models" / "event_classifier"
BASE = "distilroberta-base"

# Label space = event taxonomy keys + unknown. Fixed order so it's stable.
LABELS = [
    "earnings", "operational_disruption", "merger_or_acquisition",
    "regulatory_or_legal", "credit_event", "product_launch",
    "commercial_agreement", "geopolitical", "macroeconomic", "unknown",
]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
ID2LABEL = {i: l for l, i in LABEL2ID.items()}

EPOCHS = 3
BATCH = 16
LR = 2e-5
MAX_LEN = 128


def load_data():
    rows = [json.loads(l) for l in DATA.read_text().splitlines() if l.strip()]
    return rows


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {device} | torch {torch.__version__}")
    rows = load_data()
    print(f"train rows: {len(rows)}")

    tok = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE, num_labels=len(LABELS), id2label=ID2LABEL, label2id=LABEL2ID
    )
    model.to(device)

    enc = tok(
        [r["text"] for r in rows],
        truncation=True,
        max_length=MAX_LEN,
        padding=True,
        return_tensors="pt",
    )
    labels = torch.tensor([LABEL2ID[r["label"]] for r in rows])
    enc["labels"] = labels

    dataset = torch.utils.data.TensorDataset(
        enc["input_ids"], enc["attention_mask"], enc["labels"]
    )
    loader = DataLoader(dataset, sampler=RandomSampler(dataset), batch_size=BATCH)

    optim = torch.optim.AdamW(model.parameters(), lr=LR)
    total = len(loader) * EPOCHS
    sched = get_linear_schedule_with_warmup(optim, int(total * 0.1), total)

    model.train()
    step = 0
    for ep in range(EPOCHS):
        for b in loader:
            optim.zero_grad()
            out = model(
                input_ids=b[0].to(device),
                attention_mask=b[1].to(device),
                labels=b[2].to(device),
            )
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            sched.step()
            step += 1
            if step % 50 == 0:
                print(f"  epoch {ep+1} step {step}/{total} loss {out.loss.item():.4f}")

    # Evaluate on the SAME held-out eval set used for keyword/hybrid/zero-shot.
    model.eval()
    correct = 0
    for text, gold in EVENT_EVAL_CASES:
        inputs = tok(text, return_tensors="pt", truncation=True, max_length=MAX_LEN).to(device)
        with torch.no_grad():
            logits = model(**inputs).logits[0]
        pred = ID2LABEL[int(torch.argmax(logits))]
        correct += (pred == gold)
    n = len(EVENT_EVAL_CASES)
    print(f"\nfine-tuned accuracy on held-out eval set: {correct}/{n} = {correct/n:.3f}")

    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(SAVE_DIR)
    tok.save_pretrained(SAVE_DIR)
    (SAVE_DIR / "labels.json").write_text(json.dumps(LABELS))
    print(f"saved -> {SAVE_DIR}")


if __name__ == "__main__":
    main()
