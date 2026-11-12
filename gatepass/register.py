import datetime
import re
from collections import Counter

# Detects value-like columns generically; nothing site-specific below.
_VALUE_COL = re.compile(r"value|amount|weight|eway|e-way|e_way", re.I)


def _hm(text):
    hours, minutes = text.split(":")
    return int(hours) * 60 + int(minutes)


def _fmt(total_minutes):
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def analyse(reg, cmap, night_start):
    """Turn the gate register into findings. Pure code, no model."""
    rows = reg["rows"]
    type_col, type_vals = cmap["type"], cmap["type_values"]
    invoice = [r for r in rows if r.get(type_col) == type_vals["invoice"]]
    chit = [r for r in rows if r.get(type_col) == type_vals["chit"]]
    dates = sorted({r[cmap["date"]] for r in rows})
    findings = []

    findings.append(
        f"{len(rows)} movements logged {dates[0]} to {dates[-1]}: "
        f"{len(invoice)} on invoices, {len(chit)} on handwritten chits "
        f"({len(chit) * 100 // len(rows)}%)."
    )

    def span(group):
        ins = [_hm(r[cmap["in_time"]]) for r in group]
        outs = [_hm(r[cmap["out_time"]]) for r in group]
        return _fmt(min(ins)), _fmt(max(outs)), sum(o - i for i, o in zip(ins, outs)) / len(ins)

    inv_lo, inv_hi, inv_dwell = span(invoice)
    chit_lo, chit_hi, chit_dwell = span(chit)
    findings.append(
        f"Invoice movements arrive between {inv_lo} and {inv_hi} "
        f"(average dwell {inv_dwell:.0f} min); chit movements arrive between "
        f"{chit_lo} and {chit_hi} (average dwell {chit_dwell:.0f} min)."
    )

    night = [r for r in chit if int(r[cmap["in_time"]].split(":")[0]) >= night_start]
    guards = Counter(r.get(cmap["guard"]) or "unknown" for r in night)
    split = ", ".join(f"{count} by {guard}" for guard, count in guards.most_common())
    findings.append(
        f"All {len(night)} chit movements start at or after {_fmt(night_start * 60)}: {split}."
    )

    first = datetime.date.fromisoformat(dates[0])
    last = datetime.date.fromisoformat(dates[-1])
    all_days = [first + datetime.timedelta(days=i) for i in range((last - first).days + 1)]
    empty = [d for d in all_days if d.isoformat() not in set(dates)]
    empty_sundays = [d for d in empty if d.weekday() == 6]
    empty_weekdays = [d for d in empty if d.weekday() != 6]
    sunday_rows = [d for d in dates if datetime.date.fromisoformat(d).weekday() == 6]
    if empty_sundays and not sunday_rows:
        findings.append(
            f"No row falls on a Sunday: all {len(empty_sundays)} Sundays in the period "
            f"are empty, and {len(empty_weekdays)} weekdays are also dark."
        )
    else:
        findings.append(
            f"Rows exist on {len(sunday_rows)} Sundays; {len(empty_weekdays)} weekdays "
            f"are dark."
        )

    counts = Counter(r[cmap["invoice_no"]] for r in rows if r.get(cmap["invoice_no"]))
    for number, times in counts.items():
        if times > 1:
            where = "; ".join(
                f"row {r[cmap['sl']]} on {r[cmap['date']]} ({r.get(type_col)})"
                for r in rows
                if r.get(cmap["invoice_no"]) == number
            )
            findings.append(f"Invoice {number} appears {times} times: {where}.")

    chit_with_invoice = [r for r in chit if r.get(cmap["invoice_no"])]
    findings.append(
        f"{len(chit_with_invoice)} of {len(chit)} chit rows carry an invoice number; "
        f"the rest have none to link to."
    )

    vehicles = Counter(r[cmap["vehicle"]] for r in rows)
    unique = sum(1 for v in vehicles.values() if v == 1)
    findings.append(
        f"{unique} of {len(vehicles)} vehicle numbers appear only once; not one "
        f"vehicle returns twice in {len(rows)} movements."
    )

    if not any(_VALUE_COL.search(c) for c in reg["columns"]):
        findings.append(
            "The register has no value, weight, or e-way bill columns, so "
            "invoice-value rules cannot be checked from this data."
        )

    per_day = Counter(r[cmap["date"]] for r in rows)
    day_counts = sorted(per_day.values())
    findings.append(
        f"Trucks per active day: min {day_counts[0]}, max {day_counts[-1]}, "
        f"mean {sum(day_counts) / len(day_counts):.1f} over {len(per_day)} active days."
    )

    if reg.get("source"):
        findings.append(f"Source note: {reg['source']}.")
    return findings
