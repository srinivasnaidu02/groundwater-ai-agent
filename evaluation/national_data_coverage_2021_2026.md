# National Groundwater Data Coverage Report (2021–2026)

**Generated:** 2026-11-15  
**System:** Groundwater AI & IN-GRES Pipeline  
**Authoritative Sources:** Central Ground Water Board (CGWB), Ministry of Jal Shakti, IN-GRES (IIT Hyderabad), OpenCity Data Archives  

---

## 1. Executive Summary

This report establishes the authentic, verified district-wise groundwater data coverage across India for all target assessment cycles between 2021 and 2026 (plus reference cycles 2020 and 2022). In strict accordance with data governance policies:
- **No missing years have been fabricated or synthetically extrapolated.**
- **No percentage inflation or previous-year copying has been applied.**
- **Every record strictly retains its verification status (`VERIFIED`, `UNVERIFIED`, or `REJECTED`), source agency, publication identifier, and assessment unit granularity.**

---

## 2. Assessment Year Coverage Matrix (2021–2026)

| Target Year | Official Assessment Conducted? | Official Source Publication | District Records | Verified Records | States & UTs Covered | Primary Granularity | Available Parameters |
|:---:|:---:|:---|:---:|:---:|:---:|:---|:---|
| **2021** | ❌ No | None (CGWB transitioned assessment cycles; no national compilation published) | 0 | 0 | 0 | N/A | None (Officially unavailable) |
| **2022** | ✅ Yes | CGWB National Compilation on Dynamic Ground Water Resources of India, 2022 (Nov 2022) | 590 | 142 | 31 | District & State | Recharge, Extractable, Extraction (Irrigation, Domestic, Industrial), Stage %, Category |
| **2023** | ✅ Yes | CGWB National Compilation 2023 (released Dec 2023) | 0 (District Volumetric) / 1,082 (Sub-district) | 0 (District) / 1,082 (Categorisation) | 12 States (Major Cities & Taluks) | Assessment Unit / Taluk / Block | Categorisation (Safe, Semi-critical, Critical, Over-exploited) |
| **2024** | ✅ Yes | CGWB National Compilation on Dynamic Ground Water Resources of India, 2024 | 185 | 0 | 7 (DL, GA, GJ, KA, MH, TN, TG) | District & Major Cities | Recharge, Extractable, Extraction, Stage % |
| **2025** | ✅ Yes | CGWB Publication 1741 & State Technical Reports (e.g. Telangana Pub 2123, Bihar PDF 711d8d) | 186 | 72 | 8 (DL, GA, GJ, KA, MH, TN, TG, BR) | District | Recharge, Extractable, Extraction (Sectoral), Stage % |
| **2026** | ❌ No | None (Current / Future assessment cycle; not finalized or published by CGWB) | 0 | 0 | 0 | N/A | None (Officially unavailable) |

---

## 3. Detailed Breakdown by Target Cycle

### Target Cycle 2021
- **Status:** **NO OFFICIAL ASSESSMENT PUBLISHED**
- **Findings:** CGWB historically conducted dynamic groundwater resource assessments periodically (e.g. 2004, 2009, 2011, 2013, 2017, 2020) before moving towards annual assessments under GEC-2015. There is no official "National Compilation on Dynamic Ground Water Resources of India 2021" published by the Ministry of Jal Shakti.
- **System Policy:** When users request 2021 assessment data, the system transparently reports:  
  `"Verified data for this location, parameter and assessment year is not currently available in the database."`

### Target Cycle 2022 (Benchmark National Compilation)
- **Status:** **FULLY INGESTED AND BENCHMARKED**
- **Source Document:** *National Compilation on Dynamic Ground Water Resources of India, 2022*, Central Ground Water Board, Department of Water Resources, River Development & Ganga Rejuvenation, Ministry of Jal Shakti, Government of India.
- **Coverage:**
  - **States/UTs:** 31 States and Union Territories.
  - **Total District Records:** 590.
  - **Individually Verified Records:** 142 records directly audited against primary CGWB benchmarks (e.g., Patna total extraction: 174,600 Ham; stage: 52.2%; category: Safe).
  - **Re-published OpenCity Records:** 448 district records.
- **Reported Parameters:** Annual Ground Water Recharge, Total Natural Discharges, Annual Extractable Ground Water Resource, Current Annual Ground Water Extraction for Irrigation, Domestic and Industrial uses, Total Extraction, Stage of Ground Water Extraction (%), and Categorization.

### Target Cycle 2023
- **Status:** **SUB-DISTRICT ASSESSMENT UNIT CATEGORISATION INGESTED**
- **Source Document:** *National Compilation on Dynamic Ground Water Resources of India, 2023* (published Dec 2023).
- **Coverage:**
  - OpenCity archive released sub-district taluk-level categorisation records for major metropolitan regions rather than national district-level volumetric tables.
  - **Sub-district Records Ingested:** 1,082 assessment units stored in `assessment_unit_categories` table.
  - **District Volumetric Tables:** None published in open machine-readable CSV format for 2023.

### Target Cycle 2024
- **Status:** **7 STATES INGESTED (UNVERIFIED / RE-PUBLISHED)**
- **Source Document:** *National Compilation on Dynamic Ground Water Resources of India, 2024*, CGWB / OpenCity.
- **Coverage:**
  - **States Covered:** Delhi (11 districts), Goa (2 districts), Gujarat (33 districts), Karnataka (31 districts), Maharashtra (36 districts), Tamil Nadu (38 districts), Telangana (33 districts) + 1 rejected state-total row.
  - **Total District Records:** 185.
  - **Verification Status:** `UNVERIFIED` (re-published from OpenCity CSVs pending page-by-page PDF matching).
  - **Remaining States:** 24 States/UTs (e.g., Punjab, Bihar, Haryana, Uttar Pradesh, Rajasthan) do not have district CSV extracts in the 2024 OpenCity archive.

### Target Cycle 2025
- **Status:** **8 STATES INGESTED (72 VERIFIED, 114 UNVERIFIED)**
- **Source Documents:**
  1. *National Compilation on Dynamic Ground Water Resources of India, 2025* (CGWB Publication 1741, 482 pages).
  2. *Dynamic Ground Water Resources of Telangana State - 2025* (CGWB & Govt of Telangana Publication 2123, Chapter 6 & Annexure II).
  3. *Dynamic Ground Water Resources of Bihar 2025* (Ministry of Jal Shakti PDF `711d8d476bbf498cd90f8038e7371227.pdf`).
- **Verified Records (72 districts):**
  - **Telangana:** 33 districts verified line-by-line (e.g., Hyderabad total extraction 6,782.51 Ham; stage 98.32%).
  - **Tamil Nadu:** 38 districts verified line-by-line against CGWB Publication 1741.
  - **Bihar:** Patna district verified (total extraction: 59,747.83 Ham; irrigation: 41,223.39 Ham; domestic: 17,061.84 Ham; industrial: 1,462.64 Ham; stage: 60.95%).
- **Re-published OpenCity Records (114 districts):**
  - Delhi (11 districts), Goa (2 districts), Gujarat (33 districts), Karnataka (31 districts), Maharashtra (36 districts).

### Target Cycle 2026
- **Status:** **NO OFFICIAL ASSESSMENT PUBLISHED**
- **Findings:** As of the current date, the 2026 assessment has not been conducted or published by CGWB or the Ministry of Jal Shakti.
- **System Policy:** Factual inquiries for 2026 are blocked and correctly inform the user that official records are not yet available.

---

## 4. Geographic Unit Separation Audit

To prevent geographic aggregation errors, separate database entities and tables are strictly maintained:
1. **District-Level Volumetric Assessments:** Stored in `groundwater_resources` with `assessment_unit_level = 'District'`.
2. **Sub-District Assessment Units (Taluks / Blocks / Mandals):** Stored in `assessment_unit_categories` with specific unit types preserved.
3. **State-Level Volumetric Summaries:** Stored in `state_groundwater_resources` in Bcm.
4. **Assessment Unit Aggregations:** Never mixed with district or state totals.

---

## 5. Verification Policy & Access Control

- **Only `is_verified = 1` (`VERIFIED`) records are permitted to answer factual numerical inquiries.**
- **`UNVERIFIED`, `REJECTED`, or `SYNTHETIC` records are strictly barred from factual responses.**
- In strict adherence to academic standards, queries for unverified districts or missing years return:  
  `"Verified data for this location, parameter and assessment year is not currently available in the database."`
- The system automatically discovers available assessment years from database state without relying on hardcoded lists.

