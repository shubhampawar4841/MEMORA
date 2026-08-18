"""
Nerva RAG evaluation harness.

Run from the backend/ directory:

    python -m eval.run_eval

Measures:
- retrieval hit@k (dense vector, before rerank)
- rerank hit@k (after rerank)
- citation accuracy (/ask sources)
- answer sufficiency check for expect_insufficient cases
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.retrieval import (  # noqa: E402
    retrieve_for_ask,
    retrieve_vector_only,
)
from app.routers.chat import _run_ask  # noqa: E402


EVAL_DIR = Path(__file__).resolve().parent
DATASET_PATH = EVAL_DIR / "dataset.json"
REPORT_PATH = EVAL_DIR / "last_report.json"


def _source_hit(items: list[dict], needle: str | None) -> bool:
    if not needle:
        return False
    needle_l = needle.lower()
    for item in items:
        meta = item.get("metadata") or {}
        source = (
            item.get("source")
            or meta.get("source")
            or ""
        )
        if needle_l in str(source).lower():
            return True
    return False


def _print_row(cols: list[str], widths: list[int]) -> None:
    parts = [c[:w].ljust(w) for c, w in zip(cols, widths)]
    print(" | ".join(parts))


def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    rows = []

    retrieval_hits = 0
    rerank_hits = 0
    citation_hits = 0
    scored = 0
    insufficient_ok = 0
    insufficient_total = 0

    widths = [18, 8, 8, 8, 10]

    print("\nNerva RAG Eval")
    print("=" * 70)
    _print_row(
        ["id", "retr@k", "rerank", "cite", "notes"],
        widths,
    )
    print("-" * 70)

    for item in dataset:
        qid = item["id"]
        question = item["question"]
        expected = item.get("expected_source_contains")
        expect_insufficient = bool(item.get("expect_insufficient"))

        vector_hits = retrieve_vector_only(question, top_k=10)
        ranked = retrieve_for_ask(question)
        ask = _run_ask(question)

        retr_ok = _source_hit(vector_hits, expected) if expected else None
        rerank_ok = _source_hit(ranked, expected) if expected else None
        cite_ok = _source_hit(ask.get("sources") or [], expected) if expected else None

        note = ""
        if expect_insufficient:
            insufficient_total += 1
            answer = (ask.get("answer") or "").lower()
            ok = "enough information" in answer or "don't have" in answer
            if ok:
                insufficient_ok += 1
            note = "insufficient-ok" if ok else "insufficient-FAIL"
        else:
            scored += 1
            if retr_ok:
                retrieval_hits += 1
            if rerank_ok:
                rerank_hits += 1
            if cite_ok:
                citation_hits += 1
            note = item.get("notes") or ""

        rows.append({
            "id": qid,
            "question": question,
            "expected_source_contains": expected,
            "retrieval_hit": retr_ok,
            "rerank_hit": rerank_ok,
            "citation_hit": cite_ok,
            "expect_insufficient": expect_insufficient,
            "answer_preview": (ask.get("answer") or "")[:180],
            "sources": [
                s.get("source") for s in (ask.get("sources") or [])
            ],
        })

        _print_row(
            [
                qid,
                "-" if retr_ok is None else ("Y" if retr_ok else "N"),
                "-" if rerank_ok is None else ("Y" if rerank_ok else "N"),
                "-" if cite_ok is None else ("Y" if cite_ok else "N"),
                note,
            ],
            widths,
        )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_scored": scored,
        "retrieval_accuracy": (retrieval_hits / scored) if scored else None,
        "rerank_accuracy": (rerank_hits / scored) if scored else None,
        "citation_accuracy": (citation_hits / scored) if scored else None,
        "insufficient_accuracy": (
            (insufficient_ok / insufficient_total)
            if insufficient_total
            else None
        ),
        "rows": rows,
    }

    REPORT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("-" * 70)
    print(
        f"Retrieval accuracy: "
        f"{summary['retrieval_accuracy']:.2%}" if scored else "n/a"
    )
    if scored:
        print(f"Rerank accuracy:    {summary['rerank_accuracy']:.2%}")
        print(f"Citation accuracy:  {summary['citation_accuracy']:.2%}")
    if insufficient_total:
        print(
            f"Insufficient handling: "
            f"{summary['insufficient_accuracy']:.2%}"
        )
    print(f"\nWrote report → {REPORT_PATH}")


if __name__ == "__main__":
    main()
