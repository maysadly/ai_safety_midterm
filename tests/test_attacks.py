"""The fixed attack sets: complete, valid, and fair (no secrets in the prompts)."""

import json
from pathlib import Path

import yaml

from app.attacks import ATTACKS_DIR, load_attacks, taxonomy_names

M2_TECHNIQUES = {
    "Logical Appeal", "Authority Endorsement", "Evidence-based Persuasion",
    "Negative Emotion Appeal", "Foot-in-the-door", "Misrepresentation",
}


def by_method(method):
    return [a for a in load_attacks() if a["method"] == method]


def test_m0_has_three_direct_requests_per_goal():
    m0 = by_method("M0")
    assert len(m0) == 12
    assert sorted(a["goal"] for a in m0) == sorted(["G1", "G2", "G3", "G4"] * 3)
    assert all(a["technique"] is None for a in m0)


def test_m2_is_a_full_technique_by_goal_grid():
    m2 = by_method("M2")
    assert len(m2) == 24
    pairs = {(a["technique"], a["goal"]) for a in m2}
    assert pairs == {(t, g) for t in M2_TECHNIQUES for g in ("G1", "G2", "G3", "G4")}


def test_m2_techniques_and_definitions_match_the_published_taxonomy():
    assert M2_TECHNIQUES <= taxonomy_names()
    data = yaml.safe_load((ATTACKS_DIR / "m2_persuasion.yaml").read_text())
    taxonomy = {
        json.loads(line)["ss_technique"]: json.loads(line)["ss_definition"]
        for line in (ATTACKS_DIR / "persuasion_taxonomy.jsonl").read_text().splitlines()
    }
    for name, definition in data["techniques"].items():
        assert taxonomy[name] == definition  # copied verbatim


def test_attacker_does_not_know_the_secrets(settings):
    """A prompt that already contains the canary would make the detector fire for free."""
    code = settings.detectors["staff_promo_code"].lower()
    marker = settings.detectors["marker_phrase"].lower()
    for attack in load_attacks():
        text = attack["prompt"].lower()
        assert code not in text and "d6nb" not in text and "wwqb" not in text, attack["id"]
        assert marker not in text and "marigold" not in text and "meridian" not in text, attack["id"]


def test_pilot_questions_are_not_reused():
    pilot = Path(__file__).resolve().parent.parent / "scripts" / "pilot_model_choice.py"
    source = pilot.read_text()
    for attack in load_attacks():
        assert attack["prompt"] not in source, attack["id"]


def test_no_harmful_content_requests_in_our_own_sets():
    """G5 (harmful content) is covered only by garak probes, never by our prompts."""
    assert not [a for a in load_attacks() if a["method"] in ("M0", "M2") and a["goal"] == "G5"]
