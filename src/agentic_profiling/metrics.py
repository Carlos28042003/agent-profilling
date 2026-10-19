import re
import string
from collections import Counter

NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def normalize_answer(s: str) -> str:
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def f1_score(prediction: str, truth: str) -> float:
    pred, gold = normalize_answer(prediction), normalize_answer(truth)
    if pred in ("yes", "no", "noanswer") or gold in ("yes", "no", "noanswer"):
        return float(pred == gold)
    p, g = pred.split(), gold.split()
    common = Counter(p) & Counter(g)
    same = sum(common.values())
    if same == 0:
        return 0.0
    precision, recall = same / len(p), same / len(g)
    return 2 * precision * recall / (precision + recall)


def last_number(s: str) -> float | None:
    matches = NUMBER_RE.findall(s.replace("$", ""))
    if not matches:
        return None
    try:
        return float(matches[-1].replace(",", "").rstrip("."))
    except ValueError:
        return None


def grade(answer: str | None, expected: list[str], metric: str = "contains") -> dict:
    if answer is None:
        return {"correct": False, "em": 0.0 if metric == "hotpotqa" else None,
                "f1": 0.0 if metric == "hotpotqa" else None}
    if metric == "hotpotqa":
        em = max(float(normalize_answer(answer) == normalize_answer(e)) for e in expected)
        f1 = max(f1_score(answer, e) for e in expected)
        return {"correct": em == 1.0, "em": em, "f1": f1}
    if metric == "numeric":
        got = last_number(answer)
        ok = got is not None and any(abs(got - float(e.replace(",", ""))) < 1e-6 for e in expected)
        return {"correct": ok, "em": None, "f1": None}
    a = answer.lower().replace(",", "")
    return {"correct": any(e.lower().replace(",", "") in a for e in expected), "em": None, "f1": None}
