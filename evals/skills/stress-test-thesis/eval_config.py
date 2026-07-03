"""Eval spec for /parallax-stress-test-thesis.

DRAFT — spec only, never run live (same status as portfolio-checkup at authoring).
Wired into the structural harness so the skill's output contract is captured and
CI's pure-function grader tests can reference it; live rollouts remain manual and
cost Parallax tokens.

Output family differs from should-i-buy: this skill emits an argument-decomposition
report (Assumption Map, Load-Bearing Vulnerabilities, per-assumption status table,
World Verdict), not a per-stock scorecard. It shares the cross-skill conventions
(§9.2 AI-disclosure, a "not investment advice" disclaimer, ≤250-line orchestrator)
and makes NO buy/sell/hold recommendation — the analogue of should-i-buy's
bottom_line_no_rec is verdict_no_rec here.

The `core.jsonl` tasks are all Pass-1-only (no client_profile). The two-pass
client-conditioning acceptance test (crypto accumulator vs. retiree, design doc
§9.5) is deliberately NOT in core: it requires a paired-run assertion (identical
Pass-1 statuses across two profiles; divergent client ranking; stronger disclaimer
variant on the retiree run) that the single-transcript generic engine can't express.
Keep it as the manual live acceptance test until the harness grows paired-run support.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "graders"))
from eval_spec import EvalSpec  # noqa: E402
from tier1_structural import Check, _section_text, _REC_PATTERNS  # noqa: E402
from judge_criteria import CRITERIA  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[3]

# Always-present sections (Pass-1, no-profile path). Profile-only and ticker-only
# sections are intentionally excluded from required_sections — they appear in
# section_labels so section-text boundaries resolve, but a no-profile / no-ticker
# task must still pass.
_REQUIRED_SECTIONS = [
    "Thesis Restatement",
    "Assumption Map",
    "Pass 1 — Load-Bearing Vulnerabilities",
    "Assumption-by-Assumption",
    "World Verdict",
    "What to Watch",
    "Confidence & Caveats",
]
_SECTION_LABELS = [
    "Thesis Restatement",
    "Client Profile Summary",            # profile-only
    "Assumption Map",
    "Pass 1 — Load-Bearing Vulnerabilities",
    "Assumption-by-Assumption",
    "Position-Level Read",               # ticker-only
    "World Verdict",
    "Pass 2 — Holder-Dependent Assumptions",         # profile-only
    "Pass 2 — Client-Conditioned Vulnerabilities",   # profile-only
    "Suitability-Relevant Flags",        # profile-only
    "Client-Conditioned Verdict",        # profile-only
    "What to Watch",
    "Confidence & Caveats",
]

# Evidence the five-layer decomposition actually ran: the Assumption Map's `layer`
# column should surface the taxonomy vocabulary.
_LAYER_KEYWORDS = ["macro", "sector", "theme", "position", "implicit", "structural", "holder"]


def _c_verdict_no_rec(t, spec) -> Check:
    """No buy/sell/hold directive in the verdict sections — this skill maps risk in
    an argument, it does not recommend. Analogue of should-i-buy's bottom_line_no_rec."""
    text = (
        _section_text(t.final_prose, "World Verdict", spec.section_labels)
        + "\n"
        + _section_text(t.final_prose, "Client-Conditioned Verdict", spec.section_labels)
    )
    hit = next((p for p in _REC_PATTERNS if re.search(p, text, re.I)), None)
    return Check("verdict_no_rec", hit is None, f"rec_token_in_verdict={hit}")


def _c_assumption_map_layered(t, spec) -> Check:
    """The Assumption Map references the layer taxonomy (>=2 distinct layer keywords)
    — a proxy that the argument was decomposed across layers, not flattened."""
    text = _section_text(t.final_prose, "Assumption Map", spec.section_labels).lower()
    hits = sorted({k for k in _LAYER_KEYWORDS if k in text})
    return Check("assumption_map_layered", len(hits) >= 2, f"layer_keywords={hits}")


_NO_HALLUC = next(c for c in CRITERIA if c["id"] == "no_hallucinated_data")  # COPIED

SPEC = EvalSpec(
    name="stress-test-thesis",
    command="/parallax-stress-test-thesis",
    rollout_prefix="stress-test-thesis",
    skill_md_path=_REPO_ROOT / "skills" / "parallax-stress-test-thesis" / "SKILL.md",
    required_sections=_REQUIRED_SECTIONS,
    section_labels=_SECTION_LABELS,
    check_ids=[
        "sections_present",            # GENERIC
        "ai_disclosure_present",       # GENERIC (§9.2 banner, always)
        "disclaimer_present_correct",  # GENERIC ("not investment advice" — no-profile path renders §9.1)
        "verdict_no_rec",              # NEW (analogue of bottom_line_no_rec)
        "assumption_map_layered",      # NEW (five-layer decomposition ran)
        "orchestrator_length",         # GENERIC
    ],
    extra_checks={
        "verdict_no_rec": _c_verdict_no_rec,
        "assumption_map_layered": _c_assumption_map_layered,
    },
    tier2_criteria=[
        _NO_HALLUC,  # COPIED
        {
            "id": "assumptions_falsifiable",
            "statement": "Each row in the Assumption Map states a falsifiable claim — something that could be shown false — not a vague sentiment.",
            "pass_when": "Every claim could in principle be contradicted by data; none are untestable opinions.",
        },
        {
            "id": "status_grounded_no_fabrication",
            "statement": "No layer-1–4 assumption is marked Supported or Contradicted without a live Parallax read behind it; silent or ambiguous data is marked Unconfirmed rather than guessed.",
            "pass_when": "Supported/Contradicted rows cite a signal; Unconfirmed is used where data is silent, not a forced call.",
        },
        {
            "id": "verdict_names_load_bearing",
            "statement": "The World Verdict identifies which assumptions the thesis most depends on and where it most likely fails first.",
            "pass_when": "The verdict points to specific load-bearing assumptions and a failure sequence, not a generic summary.",
        },
        {
            "id": "pushes_back_on_weak_argument",
            "statement": "Where the thesis rests on non-falsifiable or sentiment-based reasoning (e.g., 'it always comes back', social-media sentiment, authority appeals), the report flags these as unsupported or not testable rather than restating them as findings.",
            "pass_when": "Sentiment/authority claims are called out as low-quality or untestable, not validated — the skill does not rubber-stamp a weak thesis.",
        },
    ],
    tasks_path="evals/tasks/stress-test-thesis/core.jsonl",
    orchestrator_max_lines=250,
)
