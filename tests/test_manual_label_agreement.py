"""The agreement script that compares manual labels with automatic verdicts."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "agreement", Path(__file__).resolve().parent.parent / "scripts" / "manual_label_agreement.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(auto, mine, source="judge"):
    return {"auto_violation": str(auto), "my_label": mine, "auto_source": source}


def test_counts_agreement_and_both_error_types():
    rows = [row(True, "yes"), row(True, "no"), row(False, "Yes"), row(False, "0"), row(True, "")]
    s = module.agreement(rows)["judge"]
    assert s == {"labelled": 4, "agree": 2, "auto_fp": 1, "auto_fn": 1}


def test_unlabelled_rows_are_skipped_and_sources_kept_apart():
    stats = module.agreement([row(True, "", "judge"), row(False, "no", "exact detector")])
    assert "judge" not in stats
    assert stats["exact detector"]["labelled"] == 1 and stats["all"]["labelled"] == 1
