# Verification Report: 2025 Telangana & Tamil Nadu Groundwater CSV Sources

**Date:** 2026-11-12  
**Project:** `~/Desktop/ingres_agent`  
**Overall Verdict:** **VERIFIED** (Upstream OpenCity title/resource-ID swap confirmed and remediated without modifying raw source files)

---

## 1. Actual Contents of Inspected 2025 CSV Files

Two 2025 district groundwater assessment CSVs exist under `data/official/opencity_downloads/2025/`, recorded in `data/official/opencity_downloads/download_manifest.json`:

1. **`data/official/opencity_downloads/2025/8000309b-59d7-4b5e-aeb1-befaaab9c0f8_Tamil_Nadu_-_State_of_GW_Extraction.csv`**
   - **Remote OpenCity download filename:** `tg_gw_2025.csv`
   - **OpenCity resource title:** `"Tamil Nadu - State of GW Extraction"`
   - **Dimensions:** `35` rows × `16` columns (`33` districts from `Adilabad` to `Yadadri Bhuvanagiri`, plus `Total(Ham)` and `Total(Bcm)`)
   - **Actual state identity:** **Telangana** (`2025` assessment)
   - **Units:** Hectare-metres (`ham`) on all `33` district rows and `Total(Ham)`; billion cubic metres (`bcm`) on `Total(Bcm)` (`21.93 bcm` annual recharge, `19.84 bcm` extractable resources, `9.26 bcm` total extraction, `46.69%` stage).

2. **`data/official/opencity_downloads/2025/d8c4c53b-5c73-459c-b137-11c51e8fe8e0_Telangana_-_State_of_GW_Extraction.csv`**
   - **Remote OpenCity download filename:** `tn_gw_2025.csv`
   - **OpenCity resource title:** `"Telangana - State of GW Extraction"`
   - **Dimensions:** `40` rows × `16` columns (`38` districts from `Ariyalur` to `Virudhunagar`, plus `Total(Ham)` and `Total(Bcm)`)
   - **Actual state identity:** **Tamil Nadu** (`2025` assessment; no `Hyderabad` row present; `Nagapattinam` contains `'-'` for annual recharge)
   - **Units:** `ham` on all `38` district rows and `Total(Ham)`; `bcm` on `Total(Bcm)` (`22.61 bcm` annual recharge, `20.46 bcm` extractable resources, `15.04 bcm` total extraction, `73.50%` stage).

Both CSVs share identical 16-column headers:
`Sl. No`, `Name of District`, `Monsoon season recharge from rainfall (bcm)`, `Monsoon season recharge from other sources`, `Non-monsoon season recharge from rainfall`, `Non-monsoon season recharge from other sources`, `Total annual groundwater recharge`, `Total Natural Discharges`, `Annual Extractable Groundwater Resource`, `Irrigation - Annual extraction`, `Industrial - Annual extraction`, `Domestic - Annual Extraction`, `Total Annual Extraction`, `Annual GW Allocation for domestic use (2030)`, `Net GW availability for future`, `Stage of GW extraction (%)`.

---

## 2. Hyderabad District Row Details (2025, `ham`)

Found at row index `3` (`Sl. No = 4.0`, `Name of District = Hyderabad`) inside `8000309b-59d7-4b5e-aeb1-befaaab9c0f8_Tamil_Nadu_-_State_of_GW_Extraction.csv` (remote `tg_gw_2025.csv`):

| Metric | Value | Unit | Target Comparison |
| --- | ---: | --- | --- |
| Monsoon season recharge from rainfall | `1023.17` | `ham` | — |
| Monsoon season recharge from other sources | `1833.28` | `ham` | — |
| Non-monsoon season recharge from rainfall | `244.04` | `ham` | — |
| Non-monsoon season recharge from other sources | `3682.02` | `ham` | — |
| **Total annual groundwater recharge** | **`6782.51`** | **`ham`** | Matches `6782.51 ham` exactly |
| Total Natural Discharges | `616.97` | `ham` | — |
| **Annual Extractable Groundwater Resource** | **`6165.55`** | **`ham`** | Matches `6165.55 ham` exactly |
| Irrigation - Annual extraction | `0.00` | `ham` | — |
| Industrial - Annual extraction | `415.80` | `ham` | — |
| Domestic - Annual Extraction | `5646.03` | `ham` | — |
| **Total Annual Extraction** | **`6061.83`** | **`ham`** | Matches `6061.83 ham` exactly |
| Annual GW Allocation for domestic use | `5962.35` | `ham` | — |
| Net GW availability for future | `1057.75` | `ham` | — |
| **Stage of GW extraction** | **`98.32`** | **`%`** | Matches `98.32%` exactly |

Note on units & rounding: District table figures are in **`ham`** (whereas `1 bcm = 100,000 ham`). Rounded to 2 decimal places in `bcm` (CGWB Telangana 2025 Chapter 6, p. 52), Hyderabad reads `0.07 bcm` recharge, `0.06 bcm` extractable, `0.06 bcm` extraction, `98.32%` stage, and `0.01 bcm` net availability for future use.

---

## 3. Comparison Against Official Primary Sources

1. **CGWB National Compilation 2025 (`https://cgwb.gov.in/cgwbpnm/public/publication-detail/1741`, PDF download `/download/1741`, 482 pages, Year of Issue: 2025)**
   - **PDF p. 169 (printed p. 14):** National state-wise `bcm` summary matches local state totals (`23 Tamil Nadu`: `22.61 / 20.46 / 15.04 bcm`, `73.50%`; `24 Telangana`: `21.93 / 19.84 / 9.26 bcm`, `46.69%`).
   - **PDF p. 196 (`TAMIL NADU`, `38` districts + `Ham`/`Bcm` totals):** Line-by-line comparison against local `d8c4c53b` (`tn_gw_2025.csv`) yielded **0 unmatched numeric or category cells across all 40 rows** (including `Nagapattinam` showing `-` for Total Annual Recharge in the primary CGWB table itself).
   - **PDF p. 197 (`TELANGANA`, `33` districts + `Ham`/`Bcm` totals):** Line-by-line comparison against local `8000309b` (`tg_gw_2025.csv`) yielded **0 unmatched numeric or category cells across all 35 rows**, confirming Hyderabad's exact figures (`6782.51`, `6165.55`, `6061.83`, `98.32`).

2. **CGWB Telangana State Assessment 2025 (`https://cgwb.gov.in/cgwbpnm/public/publication-detail/2123`, PDF download `/download/2123`, 125 pages, Year of Issue: 2025)**
   - **Chapter 6, printed p. 52 (PDF p. 72, `bcm`):** Row `4 Hyderabad` gives `0.07 | 0.06 | 0.06 | 0.00 | 0.00 | 0.06 | 98.32% | 0.01`, consistent with the exact `ham` figures divided by `100,000` and rounded to two decimal places.
   - **Annexure II, printed p. 68 (PDF p. 88, `ham`):** Row `4 Hyderabad` gives `1023.17 | 1833.28 | 244.04 | 3682.02 | 6782.51 | 616.97 | 6165.55 | 0 | 415.8 | 5646.03 | 6061.83 | 5962.35 | 1057.75 | 98.32` — **exact cell-by-cell match**.

3. **OpenCity Telangana Resource Page (`https://data.opencity.in/dataset/national-compilation-of-dynamic-ground-water-resources-of-india-2025/resource/d8c4c53b-5c73-459c-b137-11c51e8fe8e0`)**
   - Live requests from this environment returned **`HTTP 502 Bad Gateway`** on `2026-11-12` (and OpenCity CKAN API `package_show` timed out), so the live webpage could not be freshly scraped; provenance from the prior local capture in `download_manifest.json` together with cross-checking against both primary CGWB PDFs confirms `d8c4c53b` carries the swapped `"Telangana - State of GW Extraction"` title while serving Tamil Nadu (`tn_gw_2025.csv`).

---

## 4. Filename / Title Swap & Column Header Discrepancies

- **Upstream OpenCity resource swap:**
  - Resource `8000309b-59d7-4b5e-aeb1-befaaab9c0f8` was published on OpenCity under the title `"Tamil Nadu - State of GW Extraction"`, even though its CKAN attachment filename (`tg_gw_2025.csv`) and all 33 district rows belong to **Telangana**.
  - Resource `d8c4c53b-5c73-459c-b137-11c51e8fe8e0` was published on OpenCity under the title `"Telangana - State of GW Extraction"`, even though its CKAN attachment filename (`tn_gw_2025.csv`) and all 38 district rows belong to **Tamil Nadu**.
- **Header discrepancies in the raw OpenCity CSVs:**
  - Column 3 header reads `"Monsoon season recharge from rainfall (bcm)"`, whereas all district values are in **`ham`** (`bcm` applies only to the `Total(Bcm)` footer row).
  - Column 14 header reads `"Annual GW Allocation for domestic use (2030)"`, whereas CGWB National PDF `1741` labels this column `"as on 2035"` and CGWB Telangana PDF `2123` Annexure II labels it `"as on 2025"` (`5962.35 ham` for Hyderabad in all three).

---

## 5. Checksums, Manifest, and Cleaned Copies

Raw files under `data/official/opencity_downloads/2025/` remain **byte-for-byte untouched**. Provenance is recorded in `data/official/source_manifest.json`, and content-verified standalone copies were generated in `data/processed/verified_sources/`:

| Role | Relative Path | Size (B) | SHA-256 |
| --- | --- | ---: | --- |
| Original (`tg_gw_2025.csv`, mislabeled Tamil Nadu) | `data/official/opencity_downloads/2025/8000309b-59d7-4b5e-aeb1-befaaab9c0f8_Tamil_Nadu_-_State_of_GW_Extraction.csv` | `5038` | `7d710e88629c6b92e61f88ac84da5bb7beada949d04bc93ea75a0bf6a55fe76c` |
| Original (`tn_gw_2025.csv`, mislabeled Telangana) | `data/official/opencity_downloads/2025/d8c4c53b-5c73-459c-b137-11c51e8fe8e0_Telangana_-_State_of_GW_Extraction.csv` | `5502` | `0594a84db2c0ae373fc3e04354461a73ed87dc3408ea95ad13754fdcca6c9ec2` |
| Cleaned verified Telangana (`33` districts, `ham`) | `data/processed/verified_sources/Telangana_2025_GW_Extraction_verified.csv` | `22539` | `84d172bf97fe0e33930c23a92cf958f7a4ae97958e6307312abf7a8a51535df3` |
| Cleaned verified Tamil Nadu (`38` districts, `ham`) | `data/processed/verified_sources/Tamil_Nadu_2025_GW_Extraction_verified.csv` | `25742` | `7ad96d453d98f3226c9852ae6d84b602b8ac17752c62df698ed4359b2195c186` |

---

## 6. Code Protections & Verification Status Behavior

- **`scripts/build_cleaned_datasets.py`:** Validates canonical state identity using `STATE_CONTENT_SIGNATURES` + `data/official/source_manifest.json` SHA-256 verification before writing `data/processed/district_groundwater_resources.csv` and `data/processed/verified_sources/*.csv`.
- **`database.py`:**
  - Enforces an anti-swap check (`TELANGANA_SIGNATURE_DISTRICTS` vs `TAMIL_NADU_SIGNATURE_DISTRICTS`) inside `load_dataset()`, raising `ValueError` on any swapped TN↔TG dataset.
  - Preserves `verification_status`, `source_file`, `source_url`, and `official_source_url` on returned records and exposes `is_verified` and `verification_status` on `get_district_metrics()` and `get_state_summary()`.
  - Automatically blocks `"unverified"` non-synthetic records (and non-`"verified"` records when `require_verified=True`), returning `status="unverified"` instead of surfacing unverified data.
- **`agent.py`:** Accepts `require_verified: bool = False` in `ask_agent()`, propagates it across single-year, multi-year, and state summary calls, and exposes `is_verified` and `verification_status` in responses.

---

## 7. Automated Test Results & Remaining Limitations

- **Verification runs (post-edit):**
  - `.venv/bin/python -m pytest -v --tb=short`: **`40 passed in 1.61s`** (including `test_verified_2025_telangana_and_tamil_nadu_provenance`, `test_load_dataset_rejects_swapped_tamil_nadu_telangana_records`, `test_unverified_records_blocked_and_require_verified_enforcement`, and `test_agent_2025_hyderabad_verified_and_unverified_guard`).
  - `.venv/bin/python -m pip check`: **`No broken requirements found.`**
- **Exact limitations / remaining uncertainty:**
  1. **Live OpenCity availability:** `https://data.opencity.in/.../resource/d8c4c53b-5c73-459c-b137-11c51e8fe8e0` returned `HTTP 502 Bad Gateway` and the OpenCity CKAN API timed out during live verification on `2026-11-12`; resource-title inspection relied on the prior downloaded `download_manifest.json`, while numeric values were verified directly against the official CGWB 2025 PDFs (`1741` and `2123`).
  2. **TLS bundle difference during fetch:** Standard Python `urllib` with `certifi` failed TLS issuer verification for `cgwb.gov.in`, whereas macOS `/usr/bin/curl` (system trust store + AIA, without `-k`) verified the certificate chain and downloaded both official PDFs with HTTP 200.
  3. **Scope of PDF line-by-line audit:** Line-by-line CGWB PDF verification in this audit covers the **2025 Telangana and Tamil Nadu district resource files** (`verified`); older or other-state CSVs from OpenCity remain tagged `republished_opencity` until individually PDF-verified, and `require_verified=True` allows restricting queries strictly to PDF-verified rows.

