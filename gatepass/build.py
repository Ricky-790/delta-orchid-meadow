import json
from pathlib import Path

import jsonschema


def _evidence_ok(refs, index):
    if not refs:
        return False
    if any(ref not in index for ref in refs):
        return False
    return not all(index[ref]["is_deflection"] for ref in refs)


def build_output(draft, findings, quotes, provenance_note):
    """Merge the draft with code-computed findings. The LLM proposes, code verifies."""
    index = {q["ref"]: q for q in quotes}
    rejected = 0

    conflicts = []
    for item in draft.get("conflicts", []):
        if len(item.get("between", [])) != 2 or not _evidence_ok(item.get("evidence", []), index):
            rejected += 1
            continue
        conflicts.append(
            {
                "between": item["between"],
                "about": item["about"],
                "resolution": item["resolution"],
            }
        )

    requirements = []
    for item in draft.get("requirements", []):
        if not _evidence_ok(item.get("evidence", []), index):
            rejected += 1
            continue
        if item["status"] == "confirmed" and item["source_persona"] == "assumed":
            rejected += 1
            continue
        if item["status"] == "conflicting" and not any(
            item["source_persona"] in conflict["between"] for conflict in conflicts
        ):
            rejected += 1
            continue
        requirements.append(
            {
                "text": item["text"],
                "source_persona": item["source_persona"],
                "status": item["status"],
            }
        )
    for i, requirement in enumerate(requirements, 1):
        requirement["id"] = f"R{i}"
        # keep key order stable: id first
        requirements[i - 1] = {
            "id": requirement["id"],
            "text": requirement["text"],
            "source_persona": requirement["source_persona"],
            "status": requirement["status"],
        }

    constraints = []
    for item in draft.get("constraints", []):
        if not _evidence_ok(item.get("evidence", []), index):
            rejected += 1
            continue
        constraints.append(item["text"])

    budget = draft.get("budget_inr")
    if budget is not None and not _evidence_ok(draft.get("budget_evidence", []), index):
        budget = None
        rejected += 1

    output = {
        "requirements": requirements,
        "conflicts": conflicts,
        "constraints": constraints,
        "budget_inr": budget,
        "register_findings": list(findings) + [provenance_note],
        "plan": draft.get("plan", []),
        "open_questions": draft.get("open_questions", []),
    }
    return output, rejected


def validate_and_write(output, schema, out_path, root):
    jsonschema.validate(output, schema)
    path = root / out_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
