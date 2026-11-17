"""Deterministic ETL script to normalize raw OpenCity CGWB groundwater CSVs.

Reads immutable raw CSVs and provenance from `data/official/opencity_downloads/`
and generates validated, provenance-tagged tables in `data/processed/`:
  - district_groundwater_resources.csv (district-level volumes in ham)
  - state_groundwater_resources.csv    (state/UT-level volumes in bcm)
  - categorisation_summary.csv         (assessed unit counts & percentages)
  - assessment_unit_categories.csv     (named Semi-Critical/Critical/Over-Exploited units)

Never invents missing values or modifies raw source files.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INTEGRATED_DIR = PROJECT_ROOT / "data" / "integrated"
MANIFEST_PATH = INTEGRATED_DIR / "official" / "opencity_downloads" / "download_manifest.json"
SOURCE_MANIFEST_PATH = INTEGRATED_DIR / "official" / "source_manifest.json"
PROCESSED_DIR = INTEGRATED_DIR / "processed"
VERIFIED_SOURCES_DIR = PROCESSED_DIR / "verified_sources"
DATA_SOURCE_LABEL = "CGWB / IN-GRES via OpenCity (Republished)"
VERIFIED_DATA_SOURCE_LABEL = "CGWB Official 2025 Report (Verified via OpenCity CSV)"

STATE_CONTENT_SIGNATURES = {
    "Telangana": {"Hyderabad", "Adilabad", "Warangal", "Nalgonda", "Khammam"},
    "Tamil Nadu": {"Chennai", "Ariyalur", "Coimbatore", "Madurai", "Nagapattinam"},
}

STATE_NAME_NORMALIZATION = {
    "Andaman And Nicobar": "Andaman and Nicobar",
    "Jammu And Kashmir": "Jammu and Kashmir",
    "Dadra & Nagar Haveli and Daman & Diu": "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi": "Delhi",
    "Nct of Delhi": "Delhi",
    "NCT of Delhi": "Delhi",
}

MAJOR_CITY_TO_STATE = {
    "Delhi": "Delhi",
    "Chennai": "Tamil Nadu",
    "Bangalore Urban": "Karnataka",
    "Bengaluru Urban": "Karnataka",
    "Bengaluru (Urban)": "Karnataka",
    "Ahmedabad": "Gujarat",
    "Pune": "Maharashtra",
    "Hyderabad": "Telangana",
}


def _normalize_state_name(name: str) -> str:
    cleaned = " ".join(str(name).strip().split())
    return STATE_NAME_NORMALIZATION.get(cleaned, cleaned)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_source_manifest_index() -> dict[str, dict[str, Any]]:
    if not SOURCE_MANIFEST_PATH.exists():
        return {}
    entries = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    index = {}
    for item in entries:
        rel = str(item["relative_path"])
        index[rel] = item
        filename = item.get("original_filename") or Path(rel).name
        index[filename] = item
        index[f"data/integrated/{rel}"] = item
        if rel.startswith("data/"):
            index[f"data/integrated/{rel[len('data/'):]}"] = item
    return index


def _detect_state_from_districts(districts: set[str]) -> str | None:
    """Detect canonical state from signature district names rather than filename alone."""
    matches = [
        state
        for state, sig_districts in STATE_CONTENT_SIGNATURES.items()
        if sig_districts.issubset(districts)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _infer_state_from_title_and_url(
    title: str,
    source_url: str,
    districts: set[str] | None = None,
    manifest_entry: dict[str, Any] | None = None,
) -> str:
    """Resolve canonical state name using verified content signatures and manifest provenance."""
    content_state = _detect_state_from_districts(districts) if districts else None
    if manifest_entry and manifest_entry.get("state"):
        manifest_state = str(manifest_entry["state"])
        if content_state is not None and content_state != manifest_state:
            raise ValueError(
                f"Content signature '{content_state}' conflicts with source_manifest '{manifest_state}'"
            )
        return manifest_state

    if content_state is not None:
        return content_state

    for prefix in (
        "Ground Water Availability Utilization and Extraction",
        "Groundwater Availability Utilization and Extraction",
        "Groundwater Availability, Utilization and Extraction",
        "Groundwater Categorisation of Units by Exploitation",
        "Categorisation of Taluks by Groundwater Extraction",
        "- State of GW Extraction",
    ):
        if prefix in title:
            state_part = title.split(prefix, 1)[0]
            state_part = state_part.replace("at States Level", "").strip(" -")
            return _normalize_state_name(state_part)

    raise ValueError(f"Could not infer state name from manifest entry title: {title!r}")


def _is_summary_row(sl_val: Any, name_val: Any) -> bool:
    """Detect Total(Ham), Total(Bcm), Grand Total, and blank separator rows."""
    sl_str = "" if pd.isna(sl_val) else str(sl_val).strip().lower()
    name_str = "" if pd.isna(name_val) else str(name_val).strip().lower()
    if not name_str or name_str == "nan":
        return True
    if "total" in name_str or "total" in sl_str:
        return True
    return False


def _to_float_or_none(val: Any) -> float | None:
    """Parse numeric value strictly; return None for blank/'-'/text markers like 'Saline'."""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    text = str(val).strip()
    if not text or text in {"-", "--", "NA", "N/A", "nan"}:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def _rel_path(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def _resolve_raw_path(entry: dict[str, Any]) -> Path:
    filename = Path(entry["file"]).name
    year = str(entry.get("year", ""))
    path = INTEGRATED_DIR / "official" / "opencity_downloads" / year / filename
    if not path.exists():
        matches = list((INTEGRATED_DIR / "official" / "opencity_downloads").rglob(filename))
        if matches:
            return matches[0]
    return path


def _extract_state_resource_rows(entry: dict[str, Any]) -> list[dict[str, Any]]:
    raw_path = _resolve_raw_path(entry)
    df = pd.read_csv(raw_path)
    year = int(entry["year"])
    cols = list(df.columns)
    rows: list[dict[str, Any]] = []

    for _, raw in df.iterrows():
        if _is_summary_row(raw.iloc[0], raw.iloc[1]):
            continue
        state_name = _normalize_state_name(str(raw.iloc[1]))
        rows.append(
            {
                "state": state_name,
                "year": year,
                "annual_recharge_bcm": _to_float_or_none(raw.iloc[6]),
                "natural_discharges_bcm": _to_float_or_none(raw.iloc[7]),
                "extractable_resources_bcm": _to_float_or_none(raw.iloc[8]),
                "irrigation_extraction_bcm": _to_float_or_none(raw.iloc[9]),
                "industrial_extraction_bcm": _to_float_or_none(raw.iloc[10]),
                "domestic_extraction_bcm": _to_float_or_none(raw.iloc[11]),
                "total_extraction_bcm": _to_float_or_none(raw.iloc[12]),
                "net_future_availability_bcm": _to_float_or_none(raw.iloc[14]),
                "extraction_stage_pct": _to_float_or_none(raw.iloc[15]),
                "data_source": DATA_SOURCE_LABEL,
                "source_file": _rel_path(raw_path),
                "source_url": entry["source_url"],
            }
        )
    if not rows:
        raise ValueError(f"Zero state resource rows parsed from {raw_path} ({cols})")
    return rows


def _extract_district_resource_rows(
    entry: dict[str, Any],
    source_manifest_index: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    raw_path = _resolve_raw_path(entry)
    rel = _rel_path(raw_path)
    df = pd.read_csv(raw_path)
    year = int(entry["year"])
    file_sha256 = _sha256_file(raw_path)
    smi = source_manifest_index or {}
    manifest_entry = smi.get(rel) or smi.get(raw_path.name) or smi.get(Path(entry.get("file", "")).name)

    district_names = {
        " ".join(str(raw.iloc[1]).strip().split())
        for _, raw in df.iterrows()
        if not _is_summary_row(raw.iloc[0], raw.iloc[1])
    }
    state_name = _infer_state_from_title_and_url(
        entry["title"],
        entry["source_url"],
        districts=district_names,
        manifest_entry=manifest_entry,
    )

    if manifest_entry:
        expected_hash = manifest_entry.get("sha256")
        if expected_hash and expected_hash == file_sha256:
            verification_status = str(manifest_entry.get("verification_status", "verified"))
            official_url = str(manifest_entry.get("official_source_url") or "")
            data_source = VERIFIED_DATA_SOURCE_LABEL if verification_status == "verified" else DATA_SOURCE_LABEL
        else:
            verification_status = "unverified"
            official_url = ""
            data_source = DATA_SOURCE_LABEL
    else:
        verification_status = "republished_opencity"
        official_url = ""
        data_source = DATA_SOURCE_LABEL

    rows: list[dict[str, Any]] = []

    for _, raw in df.iterrows():
        if _is_summary_row(raw.iloc[0], raw.iloc[1]):
            continue
        district_name = " ".join(str(raw.iloc[1]).strip().split())

        recharge = _to_float_or_none(raw.iloc[6])
        extractable = _to_float_or_none(raw.iloc[8])
        extraction = _to_float_or_none(raw.iloc[12])
        stage = _to_float_or_none(raw.iloc[15])

        notes: list[str] = []
        raw_recharge = "" if pd.isna(raw.iloc[6]) else str(raw.iloc[6]).strip()
        raw_stage = "" if pd.isna(raw.iloc[15]) else str(raw.iloc[15]).strip()
        if recharge is None:
            notes.append(f"Annual recharge missing in source ({raw_recharge or 'blank'})")
        if extractable is None:
            notes.append("Extractable resources missing in source")
        if extraction is None:
            notes.append("Total extraction missing in source")
        if stage is None:
            if raw_stage.lower() == "saline":
                notes.append("Saline in source (extraction stage non-numeric)")
            else:
                notes.append(f"Extraction stage missing in source ({raw_stage or 'blank'})")
        if manifest_entry and manifest_entry.get("mislabeled_as_state"):
            notes.append("State label corrected from swapped 2025 OpenCity resource and verified against CGWB 2025 PDF")

        rows.append(
            {
                "state": state_name,
                "district": district_name,
                "year": year,
                "annual_recharge_ham": recharge,
                "extractable_resources_ham": extractable,
                "total_extraction_ham": extraction,
                "extraction_stage_pct": stage,
                "monsoon_rainfall_recharge_ham": _to_float_or_none(raw.iloc[2]),
                "monsoon_other_recharge_ham": _to_float_or_none(raw.iloc[3]),
                "non_monsoon_rainfall_recharge_ham": _to_float_or_none(raw.iloc[4]),
                "non_monsoon_other_recharge_ham": _to_float_or_none(raw.iloc[5]),
                "natural_discharges_ham": _to_float_or_none(raw.iloc[7]),
                "irrigation_extraction_ham": _to_float_or_none(raw.iloc[9]),
                "industrial_extraction_ham": _to_float_or_none(raw.iloc[10]),
                "domestic_extraction_ham": _to_float_or_none(raw.iloc[11]),
                "net_future_availability_ham": _to_float_or_none(raw.iloc[14]),
                "quality_note": "; ".join(notes),
                "data_source": data_source,
                "verification_status": verification_status,
                "official_source_url": official_url,
                "source_file": rel,
                "source_sha256": file_sha256,
                "source_url": entry["source_url"],
            }
        )
    if not rows:
        raise ValueError(f"Zero district resource rows parsed from {raw_path}")
    return rows


def _extract_categorisation_summary_rows(entry: dict[str, Any]) -> list[dict[str, Any]]:
    raw_path = _resolve_raw_path(entry)
    # Quarantine known upstream shifted/stale 2024 Major Cities count file (6f5b101d).
    if raw_path.name.startswith("6f5b101d-"):
        return []

    df = pd.read_csv(raw_path)
    year = int(entry["year"])
    title = entry["title"]
    is_national = "India" in title or "States of India" in title
    state_for_district = None if is_national else _infer_state_from_title_and_url(title, entry["source_url"])
    rows: list[dict[str, Any]] = []

    for _, raw in df.iterrows():
        if _is_summary_row(raw.iloc[0], raw.iloc[1]):
            continue
        entity = " ".join(str(raw.iloc[1]).strip().split())
        if is_national:
            state_name = _normalize_state_name(entity)
            district_name = ""
            geo_level = "state"
        else:
            state_name = state_for_district or ""
            district_name = entity
            geo_level = "district"

        rows.append(
            {
                "geo_level": geo_level,
                "state": state_name,
                "district": district_name,
                "year": year,
                "total_assessed_units": _to_float_or_none(raw.iloc[2]),
                "safe_count": _to_float_or_none(raw.iloc[3]),
                "safe_pct": _to_float_or_none(raw.iloc[4]),
                "semi_critical_count": _to_float_or_none(raw.iloc[5]),
                "semi_critical_pct": _to_float_or_none(raw.iloc[6]),
                "critical_count": _to_float_or_none(raw.iloc[7]),
                "critical_pct": _to_float_or_none(raw.iloc[8]),
                "over_exploited_count": _to_float_or_none(raw.iloc[9]),
                "over_exploited_pct": _to_float_or_none(raw.iloc[10]),
                "saline_count": _to_float_or_none(raw.iloc[11]),
                "saline_pct": _to_float_or_none(raw.iloc[12]),
                "data_source": DATA_SOURCE_LABEL,
                "source_file": _rel_path(raw_path),
                "source_url": entry["source_url"],
            }
        )
    return rows


def _extract_unit_category_rows(entry: dict[str, Any]) -> list[dict[str, Any]]:
    raw_path = _resolve_raw_path(entry)
    df = pd.read_csv(raw_path)
    year = int(entry["year"])
    title = entry["title"]
    is_major_cities = "Major Cities" in title
    state_from_title = None if is_major_cities else _infer_state_from_title_and_url(title, entry["source_url"])

    cleaned = df.copy()
    sno_col = cleaned.columns[0]
    cleaned = cleaned[
        ~cleaned[sno_col].astype(str).str.strip().str.lower().str.contains("total", na=False)
    ].copy()
    cleaned["District"] = (
        cleaned["District"]
        .astype(object)
        .replace(r"^\s*$", pd.NA, regex=True)
        .ffill()
    )
    cleaned = cleaned[cleaned["District"].notna()].copy()

    cat_columns = (
        ("Name of Semi-critical Assessment Units", "Semi-Critical"),
        ("Name of Critical Assessment Units", "Critical"),
        ("Name of Overexploited Assessment Units", "Over-Exploited"),
    )

    rows: list[dict[str, Any]] = []
    for _, raw in cleaned.iterrows():
        district_name = " ".join(str(raw["District"]).strip().split())
        # In 2020, full state taluk lists already include Delhi, Chennai, and Bangalore Urban.
        if year == 2020 and is_major_cities and district_name in {"Delhi", "Chennai", "Bangalore Urban"}:
            continue

        if is_major_cities:
            state_name = MAJOR_CITY_TO_STATE[district_name]
        else:
            assert state_from_title is not None
            state_name = state_from_title

        for col_name, category_label in cat_columns:
            unit_val = raw.get(col_name)
            if pd.isna(unit_val):
                continue
            unit_name = " ".join(str(unit_val).strip().split())
            if not unit_name or re.fullmatch(r"\d+", unit_name):
                continue
            rows.append(
                {
                    "year": year,
                    "state": state_name,
                    "district": district_name,
                    "assessment_unit": unit_name,
                    "assessment_category": category_label,
                    "data_source": DATA_SOURCE_LABEL,
                    "source_file": _rel_path(raw_path),
                    "source_url": entry["source_url"],
                }
            )
    return rows


def build_all() -> dict[str, int]:
    """Build all normalized datasets in data/processed/ and return row counts."""
    manifest: list[dict[str, Any]] = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    source_manifest_index = _load_source_manifest_index()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    VERIFIED_SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    state_rows: list[dict[str, Any]] = []
    district_rows: list[dict[str, Any]] = []
    cat_summary_rows: list[dict[str, Any]] = []
    unit_rows: list[dict[str, Any]] = []

    for entry in manifest:
        title = entry["title"]
        is_categorisation = "Categorisation" in title or "Categorization" in title
        is_india = "India" in title or "States and UTs" in title
        is_major_cities = "Major Cities" in title

        if is_categorisation:
            cols = [str(c).strip() for c in pd.read_csv(_resolve_raw_path(entry), nrows=0).columns]
            if "Name of Semi-critical Assessment Units" in cols:
                unit_rows.extend(_extract_unit_category_rows(entry))
            else:
                cat_summary_rows.extend(_extract_categorisation_summary_rows(entry))
        elif is_india:
            state_rows.extend(_extract_state_resource_rows(entry))
        elif is_major_cities:
            # Skip Major_Cities resource extract sheets to prevent double-counting same-year State data.
            continue
        else:
            district_rows.extend(_extract_district_resource_rows(entry, source_manifest_index))

    state_df = pd.DataFrame(state_rows).sort_values(["year", "state"]).reset_index(drop=True)
    district_df = pd.DataFrame(district_rows).sort_values(["year", "state", "district"]).reset_index(drop=True)
    cat_summary_df = (
        pd.DataFrame(cat_summary_rows)
        .sort_values(["year", "geo_level", "state", "district"])
        .reset_index(drop=True)
    )
    unit_df = (
        pd.DataFrame(unit_rows)
        .sort_values(["year", "state", "district", "assessment_category", "assessment_unit"])
        .reset_index(drop=True)
    )

    for target_dir in [PROCESSED_DIR, PROJECT_ROOT / "data" / "processed"]:
        target_dir.mkdir(parents=True, exist_ok=True)
        state_df.to_csv(target_dir / "state_groundwater_resources.csv", index=False)
        district_df.to_csv(target_dir / "district_groundwater_resources.csv", index=False)
        cat_summary_df.to_csv(target_dir / "categorisation_summary.csv", index=False)
        unit_df.to_csv(target_dir / "assessment_unit_categories.csv", index=False)

    for rel_path, meta in source_manifest_index.items():
        cleaned_rel = meta.get("cleaned_copy_path")
        if not cleaned_rel or meta.get("verification_status") != "verified":
            continue
        subset = district_df[
            (district_df["source_file"] == rel_path)
            & (district_df["verification_status"] == "verified")
        ].copy()
        if subset.empty:
            continue
        out_path = PROJECT_ROOT / cleaned_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        subset.to_csv(out_path, index=False)

    return {
        "state_groundwater_resources": len(state_df),
        "district_groundwater_resources": len(district_df),
        "categorisation_summary": len(cat_summary_df),
        "assessment_unit_categories": len(unit_df),
    }


if __name__ == "__main__":
    counts = build_all()
    print("Built normalized datasets in data/processed/:")
    for name, count in counts.items():
        print(f"  - {name}.csv: {count} rows")

