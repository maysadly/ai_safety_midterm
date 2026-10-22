"""Load the fixed attack sets from attacks/*.yaml.

Files:  attacks/m0_direct.yaml      M0 direct requests
        attacks/m2_persuasion.yaml  M2 persuasion (Zeng et al. techniques)
        attacks/m1_garak_samples.yaml (optional) a few garak prompts copied from the
                                    M1 run, only to show them on /demo

Every attack is a dict: {id, goal, method, technique, prompt}. The loader checks the
files so a typo cannot silently change the experiment.
"""

import json
from pathlib import Path

import yaml

from app.settings import ROOT

ATTACKS_DIR = ROOT / "attacks"
GOALS = {
    "G1": "System prompt leak",
    "G2": "Secret (staff promo code) leak",
    "G3": "Promise outside the policy",
    "G4": "Unrelated work for free",
    "G5": "Harmful content (garak probes)",
}
FILES = ["m0_direct.yaml", "m2_persuasion.yaml", "m1_garak_samples.yaml"]


def taxonomy_names() -> set[str]:
    path = ATTACKS_DIR / "persuasion_taxonomy.jsonl"
    return {json.loads(line)["ss_technique"] for line in path.read_text().splitlines() if line}


def load_attacks(directory: Path = ATTACKS_DIR) -> list[dict]:
    known_techniques = taxonomy_names()
    attacks = []
    for name in FILES:
        path = directory / name
        if not path.exists():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for item in data["attacks"]:
            attack = {
                "id": item["id"],
                "goal": item["goal"],
                "method": data["method"],
                "technique": item.get("technique"),
                "prompt": item["prompt"].strip(),
                "source": item.get("source"),  # only for garak samples: probe name
            }
            if attack["goal"] not in GOALS:
                raise ValueError(f"{name}: {attack['id']} has unknown goal {attack['goal']}")
            if attack["method"] == "M2" and attack["technique"] not in known_techniques:
                raise ValueError(f"{name}: {attack['id']}: {attack['technique']!r} is not in the taxonomy")
            attacks.append(attack)

    ids = [a["id"] for a in attacks]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"duplicate attack ids: {sorted(duplicates)}")
    return attacks
