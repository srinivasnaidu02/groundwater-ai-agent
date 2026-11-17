# Cross-Project Data Reconciliation Report
**Integration of INGRES-Agent Pipeline & Datasets into Groundwater AI**

- **Date:** 2026-11-15
- **Destination Application:** Groundwater AI (`e:\LLM project\groundwater-ai-agent`)
- **Source Pipeline Reference:** INGRES-Agent (`ingres_agent` repository & OpenCity archives)
- **Status:** Complete & Approved for Migration

---

## 1. Executive Summary & Purpose

The Groundwater AI system previously operated with an SQLite database holding 353 records across 2020–2026, including benchmark 2022 records, synthetic projections (2020, 2024, 2026), and a critical discrepancy in Patna 2025 where the database held 189,300 Ham while the raw CSV recorded 59,747.83 Ham.

The **INGRES-Agent** project was introduced as an authoritative data extraction, validation, and provenance foundation. It provides:
1. Complete OpenCity CKAN archives and download manifests (`download_manifest.json`) across 2020, 2022, 2023, 2024, and 2025 with cryptographic SHA-256 checksums.
2. Primary Central Ground Water Board (CGWB) PDF verifications for 2025 Telangana (33 districts) and 2025 Tamil Nadu (38 districts).
3. Explicit resolution of an upstream OpenCity metadata inversion where resource titles and filenames were swapped.
4. Cleaned multi-tier datasets:
   - `district_groundwater_resources.csv` (1,112 district volumetric records in Ham)
   - `state_groundwater_resources.csv` (146 state/UT volumetric totals in Bcm)
   - `assessment_unit_categories.csv` (1,082 sub-district assessment unit categorizations)
   - `categorisation_summary.csv` (152 category count distributions)

This Reconciliation Report audits all overlapping, conflicting, missing, synthetic, and verified records prior to executing database schema migrations and data ingestion into the canonical SQLite database.

---

## 2. Dataset Inventory & Structural Comparison

| Feature / Metric | Groundwater AI (Original DB) | INGRES-Agent (Integrated Source) | Unified Target DB |
|---|---|---|---|
| **Database Path** | Dual (`data/database/groundwater.db` + `backend/...`) | CSV / Python Pipeline | Single Canonical (`data/database/groundwater.db`) |
| **District Volumetric Records** | 353 rows (143 verified, 2 rejected, 208 synthetic) | 1,112 rows (2020: 198; 2022: 544; 2024: 185; 2025: 185) | Primary verified + 1,112 ingested records |
| **State Resource Totals (Bcm)** | None (only district level) | 146 rows (38 states/UTs across 4 cycles) | `StateGroundwaterResource` table |
| **Sub-District Unit Categories** | None (only district level) | 1,082 units (blocks/taluks/mandals) | `AssessmentUnitCategory` table |
| **Verification Granularity** | Global `is_verified` boolean | 4-state: `VERIFIED`, `UNVERIFIED` (`republished_opencity`), `REJECTED`, `SYNTHETIC` | 4-state enum with PDF citation metadata |
| **Checksum Tracking** | File level in `source_datasets` | SHA-256 tracked per file and record | Retained in `GroundwaterResource` & `SourceDocument` |

---

## 3. Deep-Dive on Known Discrepancies & Provenance

### 3.1 The Patna 2025 Discrepancy
- **Original Database Record:**
  - Total Extraction: `189,300 Ham`
  - Irrigation: `154,200 Ham`
  - Domestic: `26,300 Ham`
  - Industrial: `8,800 Ham`
  - *Provenance:* Uncontrolled test script seed where a synthetic scaling factor (~3.17x) was incorrectly applied or an erroneous legacy CSV import was committed.
- **Source CSV (`data/raw/groundwater_2025_all_states.csv` & OpenCity):**
  - Total Extraction: `59,747.83 Ham`
  - Irrigation: `41,223.39 Ham`
  - Domestic: `17,061.84 Ham`
  - Industrial: `1,462.64 Ham`
  - Component Sum: $41,223.39 + 17,061.84 + 1,462.64 = 59,747.87\text{ Ham}$ (0.04 Ham rounding precision delta).
- **Authoritative Source Verification:**
  - Primary CGWB Assessment Report PDF `711d8d476bbf498cd90f8038e7371227.pdf` confirms Total Extraction = **`59,747.83 Ham`**.
  - Compared to Patna 2022 extraction (`58,243.08 Ham`), this reflects a realistic 3-year growth of **+2.58%**, whereas the erroneous `189,300 Ham` implied an absurd +225% jump.
- **Resolution:** The database record is updated to the authentic value of **`59,747.83 Ham`** with status `VERIFIED` and evidence referencing CGWB Bihar 2025 documentation.

### 3.2 Patna 2022 Value Calibration
- In the initial Groundwater AI schema, Patna 2022 was stored as `174,600 Ham` (rounded benchmark from an earlier summary table).
- The OpenCity official download (`2022/bce2b67f-...`) and CGWB 2022 National Compilation table record:
  - Total Extraction: `58,243.08 Ham`
  - Irrigation Extraction: `40,183.18 Ham`
  - Domestic Extraction: `16,631.54 Ham`
  - Industrial Extraction: `1,428.36 Ham`
- **Resolution:** Maintain precise decimal records alongside the primary benchmark record. For factual inquiries, precise CGWB decimals are preferred.

### 3.3 Upstream OpenCity Resource Inversion (Tamil Nadu vs. Telangana 2025)
- **Discrepancy:**
  - OpenCity Resource `8000309b-59d7-4b5e-aeb1-befaaab9c0f8` titled `"Tamil Nadu - State of GW Extraction"` actually contains 33 districts belonging to **Telangana** (Adilabad to Yadadri Bhuvanagiri, remote filename `tg_gw_2025.csv`).
  - OpenCity Resource `d8c4c53b-5c73-459c-b137-11c51e8fe8e0` titled `"Telangana - State of GW Extraction"` actually contains 38 districts belonging to **Tamil Nadu** (Ariyalur to Virudhunagar, remote filename `tn_gw_2025.csv`).
- **Primary Source Audit:**
  - CGWB National Compilation 2025 (Publication `1741`, PDF download `/download/1741`):
    - p. 196: Tamil Nadu 38 districts matches `d8c4c53b` cell-for-cell.
    - p. 197: Telangana 33 districts matches `8000309b` cell-for-cell (e.g. Hyderabad: Total Recharge `6,782.51 Ham`, Extraction `6,061.83 Ham`, Stage `98.32%`).
  - CGWB Telangana Assessment 2025 (Publication `2123`, PDF download `/download/2123`):
    - Annexure II, p. 68: Row 4 Hyderabad matches `8000309b` cell-for-cell.
- **Resolution:** Content-based district signature detection (`STATE_CONTENT_SIGNATURES`) automatically maps `8000309b` to Telangana and `d8c4c53b` to Tamil Nadu with `VERIFIED` status.

---

## 4. Assessment Year Coverage Truth Table

| Assessment Year | Official Status | National District Volumetric | Sub-District Unit Categories | State Bcm Summaries | Status in Unified DB |
|---|---|---|---|---|---|
| **2020** | Published | 198 districts across 8 States/UTs | 860 assessment units | 38 States/UTs | `UNVERIFIED` (republished_opencity) |
| **2021** | **No Publication** | None (CGWB did not compile 2021) | None | None | **Blocked** (Returns "Verified data not available") |
| **2022** | Published (National) | 544 districts across 18 States/UTs + 142 GW-AI benchmark | None | 38 States/UTs | `VERIFIED` for benchmark, `UNVERIFIED` for OpenCity |
| **2023** | Special City Focus | None (no district volumetric release) | 77 units (Major Cities taluks) | None | Category queries supported; volumetric blocked |
| **2024** | Published | 185 districts across 7 States/UTs | 74 assessment units | 38 States/UTs | `UNVERIFIED` (republished_opencity) |
| **2025** | Published | 185 districts across 7 States/UTs (72 districts verified) | 71 assessment units | 38 States/UTs | **72 `VERIFIED`** (Telangana 33, Tamil Nadu 38, Patna 1); 113 `UNVERIFIED` |
| **2026** | Future Year | None (Projections only) | None | None | `SYNTHETIC` (Blocked from factual queries) |

---

## 5. Assessment Unit Granularity & Domain Entities

To prevent conflation of different administrative and physical units, the unified database isolates data into three distinct tiers:

```
[State Level: StateGroundwaterResource]
  └── Units: Billion Cubic Meters (Bcm)
  └── Coverage: 38 States & UTs (2020, 2022, 2024, 2025)

[District Level: GroundwaterResource]
  └── Units: Hectare Meters (Ham)
  └── Parameters: Monsoon/Non-monsoon recharge, Natural discharge, Irrigation, Domestic, Industrial, Stage (%)
  └── Coverage: 1,112 official OpenCity records + primary verified benchmark districts

[Sub-District Level: AssessmentUnitCategory]
  └── Units: Qualitative Category (Safe, Semi-Critical, Critical, Over-Exploited, Saline)
  └── Entities: Taluks, Mandals, Blocks, Firka, Watersheds
  └── Coverage: 1,082 assessment units (including 2023 Major Cities)
```

---

## 6. Geographic Aliases and Normalization Mapping

To resolve spelling variations across CGWB, OpenCity, and colloquial user inputs:

### State Aliases
- `Andaman & Nicobar`: `Andaman and Nicobar Islands`
- `Jammu & Kashmir`: `Jammu and Kashmir`
- `NCT of Delhi`: `Delhi`
- `Telengana`: `Telangana`
- `Orissa`: `Odisha`
- `Pondicherry`: `Puducherry`

### District Aliases
- `Patna Sadar`: `Patna`
- `Hyderabad District`: `Hyderabad`
- `Yadadri`: `Yadadri Bhuvanagiri`
- `K.V. Rangareddy`: `Ranga Reddy` / `Rangareddy`
- `Medchal-Malkajgiri`: `Medchal Malkajgiri`
- `Jayashankar Bhupalpally`: `Jayashankar`
- `Thiruvallur`: `Tiruvallur`
- `Tirunelveli Kattabo`: `Tirunelveli`
- `Viluppuram`: `Villupuram`
- `Kanchipuram`: `Kancheepuram`

---

## 7. Verification Policy & Safety Rules

1. **Strict Verification Default:**
   - Any query seeking factual groundwater numbers (`total_annual_extraction`, `stage_of_extraction`, `recharge`) will query `WHERE is_verified = 1` or `verification_status = 'VERIFIED'`.
2. **Missing / Unverified Response Contract:**
   - When requested data is missing, from an uncompiled year (e.g. 2021), a future year (e.g. 2026), or unverified, the system must return:
     `"Verified data for this location, parameter and assessment year is not currently available in the database."`
3. **No Synthetic Extrapolations:**
   - Factual groundwater queries will never execute percentage extrapolation or synthesize values.
4. **No Unrestricted LLM SQL:**
   - Queries are routed strictly through validated Python repository functions using SQLAlchemy parameter binding.

---

## 8. Ingestion Execution Plan

1. **Database Schema Migration:**
   - Add tables: `AssessmentUnit`, `AssessmentUnitCategory`, `StateGroundwaterResource`, `SourceDocument`, `ImportAuditLog`.
   - Add columns to `GroundwaterResource`: `sha256_checksum`, `source_document`, `source_url`, `source_agency`, `original_filename`.
2. **Import Script (`scripts/integrate_ingres_pipeline.py`):**
   - Populate `SourceDocument` and `ImportAuditLog` with manifests and SHA-256 hashes.
   - Insert verified Telangana (33) and Tamil Nadu (38) records with `VERIFIED` status and CGWB PDF URLs.
   - Update Patna 2025 to `59,747.83 Ham` with `VERIFIED` status.
   - Ingest 2020, 2022, 2024, 2025 OpenCity district records with `UNVERIFIED` (`republished_opencity`) status.
   - Ingest `state_groundwater_resources.csv` (146 rows) into `StateGroundwaterResource`.
   - Ingest `assessment_unit_categories.csv` (1,082 rows) into `AssessmentUnitCategory`.
3. **Synchronization:**
   - Maintain perfect file sync between `data/database/groundwater.db` and `backend/data/database/groundwater.db`.

