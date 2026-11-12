import sys
from collections import Counter

from . import build, config, interviews, load, register


def main():
    cfg = config.load()
    root = config.ROOT
    quotes = load.load_interviews(root / cfg["interviews_path"])
    reg = load.load_json(root / cfg["register_path"])
    schema = load.load_json(root / cfg["schema_path"])

    findings = register.analyse(reg, cfg["column_map"], cfg["night_start_hour"])
    draft, source = interviews.extract(cfg, quotes, findings, root)

    note = (
        f"Requirements, conflicts and constraints were extracted from "
        f"{len(quotes)} interview quotes in one LLM call ({source}); every "
        f"register number above was computed by code."
    )
    output, rejected = build.build_output(draft, findings, quotes, note)
    build.validate_and_write(output, schema, cfg["output_path"], root)

    statuses = Counter(r["status"] for r in output["requirements"])
    print(f"requirements: {len(output['requirements'])} {dict(statuses)}")
    print(f"conflicts: {len(output['conflicts'])}  constraints: {len(output['constraints'])}")
    print(f"register_findings: {len(findings)}  open_questions: {len(output['open_questions'])}")
    print(f"rejected draft items: {rejected}  llm source: {source}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"gatepass failed: {exc}", file=sys.stderr)
        sys.exit(1)
