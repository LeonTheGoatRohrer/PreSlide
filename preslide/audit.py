"""Conservative audit. Source quality fields are never used as ML predictors."""
import hashlib
import json
import math
import re
from collections import Counter
from datetime import date, datetime, timezone

from .sources import ROOT, LAYERS

POSITION_CLASSES = {
    "Lage sehr genau / sehr sicher (0-5m)": (0, 5),
    "Lage genau (5-20m)": (5, 20),
    "Lage relativ genau (20-100m)": (20, 100),
    "Lage ungenau (100-1000m)": (100, 1000),
    "Lage sehr ungenau (>1000m)": (1000, None),
    "50-2000m": (50, 2000),
    "50 - 2000m": (50, 2000),
}
MONTHS = {m: i for i, m in enumerate([
    "januar", "februar", "maerz", "april", "mai", "juni", "juli", "august",
    "september", "oktober", "november", "dezember"], 1)}
MONTHS.update({"jaenner": 1, "jänner": 1, "märz": 3})


def iso_day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def position_bounds(value):
    return POSITION_CLASSES.get(value, (None, None))


def position_passes(value, maximum):
    lower, upper = position_bounds(value)
    return lower is not None and upper is not None and upper <= maximum


def plausible_coordinates(geometry):
    """Bounding-box plausibility only; not proof of membership of Austria."""
    if not geometry:
        return False
    x, y = geometry.get("x"), geometry.get("y")
    return (isinstance(x, (int, float)) and isinstance(y, (int, float))
            and math.isfinite(x) and math.isfinite(y)
            and 9.4 <= x <= 17.2 and 46.3 <= y <= 49.1)


def date_quality(attributes):
    """Require a structured day corroborated by a single-day source narrative.

    An ISO date can encode the end of an uncertain interval. In particular,
    '12. oder 13. Juni' must not become an exact 13 June event. This conservative
    whitelist intentionally leaves some true exact dates for manual review.
    """
    day = iso_day(attributes.get("Ereignisdatum_validFrom"))
    narrative = (attributes.get("processTimeOrPeriodInfo") or "").strip().lower()
    if not day:
        raw = attributes.get("Ereignisdatum") or ""
        if re.fullmatch(r"\d{4}-\d{2}-00", raw) and raw[5:7] != "00":
            return "month_only"
        if re.fullmatch(r"\d{4}-00-00", raw):
            return "year_only"
        return "missing_or_invalid_day"
    explicit = [attributes.get(k) for k in ("EREIGNIS_J", "EREIGNIS_M", "EREIGNIS_T")]
    if any(actual is not None and actual != expected for actual, expected in zip(explicit, [day.year, day.month, day.day])):
        return "conflicting_date_fields"
    if not narrative:
        return "structured_day_unverified"
    # First consume exactly one day, then restrict the remainder to time-of-day.
    match = re.match(r"^(\d{1,2})\.\s*([a-zäöü]+)\s+(\d{4})(.*)$", narrative)
    if match and match[2] in MONTHS:
        try:
            parsed = date(int(match[3]), MONTHS[match[2]], int(match[1]))
        except ValueError:
            return "invalid_narrative_day"
        tail = match[4].strip()
    else:
        match = re.match(r"^(\d{4}-\d{2}-\d{2})(.*)$", narrative)
        if not match or iso_day(match[1]) is None:
            return "ambiguous_or_unparsed_narrative"
        parsed, tail = iso_day(match[1]), match[2].strip()
    if parsed != day:
        return "conflicting_date_fields"
    if not tail:
        return "reported_single_day"
    # Approximate hour within an identified day is acceptable; uncertain day is not.
    if not (tail.startswith("(") and tail.endswith(")")):
        return "ambiguous_or_unparsed_narrative"
    inner = tail[1:-1].strip()
    if re.search(r"\d{4}|\d{1,2}\.|/|folg|vortag|nacht|wahrsch|vermut|unbekannt|unsicher|\bbis\b|\bzwischen\b", inner):
        return "ambiguous_or_unparsed_narrative"
    tokens = re.sub(r"\d{1,2}:\d{2}|\d{1,2}|[.,;:\-]", " ", inner).split()
    allowed = {"gegen", "um", "uhr", "ca", "etwa", "nach", "vor", "kurz", "bis",
               "zwischen", "und", "morgen", "morgens", "frueh", "früh", "vormittag",
               "vormittags", "mittag", "mittags", "nachmittag", "nachmittags", "abend",
               "abends", "am", "fruehen", "frühen", "spaeten", "späten"}
    return "reported_single_day" if tokens and set(tokens) <= allowed else "ambiguous_or_unparsed_narrative"


def load_inventory(name):
    path = ROOT / "data/raw" / f"{name}.json"
    content = path.read_bytes()
    data = json.loads(content)
    features = data["features"]
    identifiers = [f["attributes"]["OBJECTID"] for f in features]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate source IDs")
    if data["spatialReference"]["wkid"] != 4326:
        raise ValueError("Expected WGS84, longitude/latitude")
    return features, hashlib.sha256(content).hexdigest()


def counts(values):
    return dict(sorted(Counter("unknown" if v is None else str(v) for v in values).items()))


def source_summary(features, position_field, process_field, date_field):
    attrs = [f["attributes"] for f in features]
    positions = [a.get(position_field) for a in attrs]
    days = [iso_day(a.get(date_field)) for a in attrs]
    return {
        "raw_records": len(features), "process_distribution": counts(a.get(process_field) for a in attrs),
        "position_accuracy_original": counts(positions),
        "position_upper_bound_cumulative": {str(n): sum(position_passes(v, n) for v in positions)
                                             for n in (25, 50, 100, 250, 500)},
        "position_lower_bound_above_500": sum((position_bounds(v)[0] or 0) > 500 for v in positions),
        "position_upper_bound_above_500": sum(position_bounds(v)[1] is not None and position_bounds(v)[1] > 500 for v in positions),
        "position_unknown": sum(position_bounds(v)[0] is None for v in positions),
        "position_open_ended": sum(position_bounds(v)[0] is not None and position_bounds(v)[1] is None for v in positions),
        "dated_2018_onwards_all_processes": sum(d is not None and d >= date(2018, 1, 1) for d in days),
        "missing_or_invalid_structured_day": sum(d is None for d in days),
        "coordinate_bounds_plausible": sum(plausible_coordinates(f.get("geometry")) for f in features),
        "state_distribution": counts(a.get("Bundesland") for a in attrs),
        "missing_fields": {k: sum(a.get(k) in (None, "") for a in attrs)
                           for k in (position_field, process_field, date_field, "Bundesland")},
    }


def classify(feature, config, start_date):
    a = feature["attributes"]
    day = iso_day(a.get("Ereignisdatum_validFrom"))
    checks = {
        "accepted_process": a.get("Prozessgruppe") in config["accepted_process_groups"] and a.get("Prozessuntergruppe") in config["accepted_process_subgroups"],
        "in_period": day is not None and iso_day(start_date) <= day <= iso_day(config["end_date"]),
        "single_reported_day": date_quality(a) == "reported_single_day",
        "coordinates_plausible": plausible_coordinates(feature.get("geometry")),
        "position_quality": position_passes(a.get("QUAL_LAGE"), config["max_position_error_m"]),
        "process_confidence": a.get("QUAL_PROZ") in config["accepted_process_quality"],
        "certain_mass_movement": a.get("QUAL_MB") == "Objekt ist sicher eine Massenbewegung",
    }
    return checks


def filter_period(features, config, start_date):
    cumulative = Counter()
    excluded = Counter()
    accepted = []
    decisions = []
    for f in features:
        checks = classify(f, config, start_date)
        good = True
        for key, passed in checks.items():
            good = good and passed
            cumulative[key] += int(good)
        failures = [k for k, v in checks.items() if not v]
        excluded.update(failures)
        decisions.append({"event_id": f["attributes"]["nameOfEvent"],
                          "object_id": f["attributes"]["OBJECTID"],
                          "date_quality": date_quality(f["attributes"]), "failures": failures})
        if not failures:
            accepted.append(f)
    # Same coordinate and date cannot supply independent positive observations.
    unique = {}
    for f in accepted:
        g = f["geometry"]
        key = (g["x"], g["y"], f["attributes"]["Ereignisdatum_validFrom"])
        unique.setdefault(key, f)
    final = list(unique.values())
    return {"start_date": start_date, "cumulative_filter_counts": dict(cumulative),
            "overlapping_exclusion_counts": dict(excluded), "quality_candidates_before_exact_deduplication": len(accepted),
            "exact_location_date_duplicates_removed": len(accepted)-len(final),
            "quality_candidates": len(final)}, final, decisions


def run_audit(config_path=None):
    config_path = config_path or ROOT / "config/audit.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    general, general_hash = load_inventory("geosphere_mass_movements")
    detail, detail_hash = load_inventory("geosphere_natural_hazards")
    inspire, inspire_hash = load_inventory("geosphere_inspire_media")
    primary, candidates, decisions = filter_period(detail, config, config["primary_start_date"])
    fallback, _, _ = filter_period(detail, config, config["fallback_start_date"])
    if len(candidates) < config["minimum_desired_positives"]:
        selected_period, candidates, decisions = filter_period(detail, config, config["fallback_start_date"])
    else:
        selected_period = primary
    candidate_ids = {x["attributes"]["nameOfEvent"] for x in candidates}
    inspire_ids = {x["attributes"]["nameOfEvent"] for x in inspire}
    (ROOT / "data/interim").mkdir(parents=True, exist_ok=True)
    normalized = []
    for f in candidates:
        a, g = f["attributes"], f["geometry"]
        normalized.append({
            "event_id": a["nameOfEvent"], "original_source_id": a["OBJECTID"],
            "source": "GeoSphere Austria / Naturgefahren (Test)",
            "source_url": LAYERS["geosphere_natural_hazards"],
            "process_type_original": a["Prozessuntergruppe"],
            "process_group_original": a["Prozessgruppe"],
            "process_type_normalized": "slope_slide_or_slope_flow",
            "event_date": a["Ereignisdatum_validFrom"], "date_quality": date_quality(a),
            "date_text_original": a.get("processTimeOrPeriodInfo"),
            "longitude": g["x"], "latitude": g["y"], "state": a.get("Bundesland"),
            "position_accuracy_original": a["QUAL_LAGE"],
            "position_accuracy_lower_m": position_bounds(a["QUAL_LAGE"])[0],
            "position_accuracy_upper_m": position_bounds(a["QUAL_LAGE"])[1],
            "process_quality_original": a.get("QUAL_PROZ"),
            "source_status": "license_unconfirmed_test_service",
            "sample_type": "UNKNOWN", "training_approved": False,
        })
    for name, data in [("quality_candidates_pending_source_clearance.json", normalized),
                       ("event_exclusion_decisions.json", decisions)]:
        (ROOT / "data/interim" / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    wlv = json.loads((ROOT / "data/raw/wlv_slides.json").read_text(encoding="utf-8"))["features"]
    wlv_days = [iso_day(f["properties"].get("validfrom", "")[:10]) for f in wlv]
    general_accepted = [f for f in general if f["attributes"].get("processGroupWeb_DE") == "Gleit- oder Fliessprozess"]
    general_periods = {}
    for year in (2018, 2015):
        dated = [f for f in general_accepted if (d := iso_day(f["attributes"].get("Ereignisdatum_validFrom"))) is not None and date(year, 1, 1) <= d <= iso_day(config["end_date"])]
        general_periods[str(year)] = {"accepted_group_with_structured_day": len(dated),
            "position_upper_bound_at_most_250m": sum(position_passes(f['attributes'].get('positionalAccuracy'), 250) for f in dated)}
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "status": "AUDIT_ACCEPTED_LOCAL_RESEARCH_AUTHORIZED",
        "config": config, "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "source_sha256": {"general": general_hash, "detail": detail_hash, "inspire": inspire_hash},
        "general_inventory": source_summary(general, "positionalAccuracy", "processGroupWeb_DE", "Ereignisdatum_validFrom"),
        "general_candidate_counts_by_start_year": general_periods,
        "detail_inventory": source_summary(detail, "QUAL_LAGE", "Prozessgruppe", "Ereignisdatum_validFrom"),
        "detail_date_quality": counts(date_quality(f["attributes"]) for f in detail),
        "primary_period": primary, "fallback_period": fallback,
        "selected_start_date": selected_period["start_date"],
        "period_expanded": selected_period["start_date"] != config["primary_start_date"],
        "candidate_year_distribution": counts(x["event_date"][:4] for x in normalized),
        "candidate_state_distribution": counts(x["state"] for x in normalized),
        "candidate_process_distribution": counts(x["process_type_original"] for x in normalized),
        "candidate_position_distribution": counts(x["position_accuracy_upper_m"] for x in normalized),
        "candidate_unique_reported_dates": len({x["event_date"] for x in normalized}),
        "candidate_largest_same_date_clusters": Counter(x["event_date"] for x in normalized).most_common(10),
        "candidate_date_range": [min((x["event_date"] for x in normalized), default=None), max((x["event_date"] for x in normalized), default=None)],
        "licensed_inspire_media": {"raw_records": len(inspire), "has_individual_accuracy_field": False,
            "candidate_id_overlap": len(candidate_ids & inspire_ids),
            "note": "CC BY 4.0 applies to this source; not automatically to additional test-service fields."},
        "wlv": {"raw_slide_records": len(wlv),
            "dated_2018_onwards": sum(d is not None and date(2018, 1, 1) <= d <= iso_day(config["end_date"]) for d in wlv_days),
            "dated_2015_onwards": sum(d is not None and date(2015, 1, 1) <= d <= iso_day(config["end_date"]) for d in wlv_days),
            "individual_accuracy_field": False, "date_precision_field": False,
            "future_dated_records": sum(d is not None and d > iso_day(config["end_date"]) for d in wlv_days),
            "note": "ISO timestamps alone do not establish exact day precision; no spatial accuracy inferred."},
        "training_approved_positives": 0, "controls_generated": 0,
        "terrain_status": "see_PROJECT_STATE_and_experiment_reports",
        "weather_status": "see_PROJECT_STATE_and_experiment_reports", "model_metrics": None,
        "source_uncertainty": "Naturgefahren Test: specific license unidentified and quality semantics not provider-confirmed. User authorized local non-commercial research on 2026-10-14. No raw redistribution. Clarification is not a prerequisite.",
    }
    out = ROOT / "reports/dataset_report"
    out.mkdir(parents=True, exist_ok=True)
    (out / "initial_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# PreSlide — Austrian Landslide Data Audit", "", f"Generated: {report['generated_at']}",
        "", "## Decision", "", "**Audit accepted; local non-commercial research authorized by the user.** The detailed source is labelled `Naturgefahren Test`; its specific reuse license remains unidentified. Provider clarification is not a prerequisite. Do not redistribute raw data. This report covers the audit stage; current experiment results are separate.",
        "", "## Verified source counts", "", "| Source | Records | Finding |", "|---|---:|---|",
        f"| GeoSphere standard mass-movement service | {len(general)} | All positions declared 50–2000 m; none demonstrated ≤250 m |",
        f"| GeoSphere INSPIRE Media | {len(inspire)} | CC BY 4.0; individual accuracy not exposed |",
        f"| GeoSphere Naturgefahren (Test) | {len(detail)} | Individual 0–5 / 5–20 / 20–100 / 100–1000 / >1000 m classes |",
        f"| WLV, Rutschung category | {len(wlv)} | {report['wlv']['dated_2018_onwards']} dated 2018+; accuracy and date precision absent |",
        "", "## Standard service: process and period audit", "",
        f"Gleit-/Fliessprozess records (all years): {len(general_accepted)}.",
        f"2018+ with valid structured day: {general_periods['2018']['accepted_group_with_structured_day']}; 2015+: {general_periods['2015']['accepted_group_with_structured_day']}.",
        "Both periods yield zero records with a demonstrated positional upper bound ≤250 m. The lower bound 50 m is not an individual accuracy estimate.",
        "", "## Detailed source: sequential quality filter", "", "| Step | 2018+ | 2015+ sensitivity |", "|---|---:|---:|"]
    for key, value in primary["cumulative_filter_counts"].items():
        lines.append(f"| {key} | {value} | {fallback['cumulative_filter_counts'][key]} |")
    lines += [f"| Exact coordinate/date deduplicated candidates | {primary['quality_candidates']} | {fallback['quality_candidates']} |",
        "", f"Selected start: {report['selected_start_date']}; expanded: {report['period_expanded']}. Candidate date range: {report['candidate_date_range']}.",
        "", "The 100 m threshold is chosen at an actual category boundary. A 250 m threshold cannot distinguish the 100–1000 m class and therefore admits no additional confirmed records. These are source-reported bounds, not independently surveyed error estimates.",
        "", "Structured dates are checked against the narrative. For example, `12. oder 13. Juni 2018` is excluded even when the structured field says `2018-06-13`. Unparsed narratives remain excluded. Single-day reporting does not guarantee independently verified timing.",
        "", f"Candidates occupy {report['candidate_unique_reported_dates']} distinct dates; largest same-date clusters: {report['candidate_largest_same_date_clusters'][:5]}. These are not independent storms. Future evaluation must group storm/spatial clusters as well as each positive/control group.",
        "", "## Candidate distributions (before terrain/weather validation)", ""]
    for title, key in [("By year", "candidate_year_distribution"), ("By state", "candidate_state_distribution"), ("By process", "candidate_process_distribution"), ("By positional upper bound (m)", "candidate_position_distribution")]:
        lines += [f"### {title}", "", "| Category | Count |", "|---|---:|"]
        lines += [f"| {k} | {v} |" for k, v in report[key].items()]
        lines.append("")
    lines += ["## Position uncertainty across all records", "", "Cumulative counts with a demonstrated source-reported upper bound. An interval crossing a threshold is not counted as passing it.", "",
              "| Maximum upper bound (m) | Standard service | Detailed service |", "|---|---:|---:|"]
    for n in (25, 50, 100, 250, 500):
        lines.append(f"| ≤{n} | {report['general_inventory']['position_upper_bound_cumulative'][str(n)]} | {report['detail_inventory']['position_upper_bound_cumulative'][str(n)]} |")
    lines += ["", "Detailed original categories:", "", "| Reported class | Count |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in report["detail_inventory"]["position_accuracy_original"].items()]
    lines.append("")
    lines += ["## Reproducibility and limits", "",
        "Run `python -m preslide audit`. Raw responses, retrieval timestamps, URLs and SHA-256 hashes are cached under `data/raw/http/`. Configuration is `config/audit.json`; all record-level exclusion reasons are in `data/interim/event_exclusion_decisions.json`. Counts above are computed from downloaded records.",
        "", "The sources overlap and must not be summed. Candidate locations pass an Austrian bounding-box plausibility check; precise country-boundary and slope verification remain outstanding. Exact duplicates are removed; spatial/storm clustering remains to be done before evaluation.",
        "", "No individual accuracy is invented for INSPIRE or WLV. No ISO timestamp is automatically treated as evidence of exact timing. Unknown quality is separate from confirmed poor quality. Meteorological completeness is not yet evaluated.",
        "", "The audit snapshot retains historical UNKNOWN/training_approved=false flags. The separately authorized experiment validates terrain, matching and weather before assigning research labels. See PROJECT_STATE.md and RESULTS.md for current implementation and scores.",
        "", "## Required next step", "",
        "Continue the authorized scientific experiment: verify a small real-data run, then scale with leakage-safe evaluation. Optional clarification remains documented but is not a gate. No raw competition redistribution is authorized.",
        "", "Source endpoints and licensing evidence: see DATA_SOURCES.md.", ""]
    (out / "initial_audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "primary_quality_candidates": primary["quality_candidates"],
                      "fallback_quality_candidates": fallback["quality_candidates"], "training_approved": 0}, indent=2))
    return report
