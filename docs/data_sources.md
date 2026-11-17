# Groundwater AI Agent — Data Sources and Provenance

## 1. Official Data Source Investigation

### 1.1 IN-GRES System Architecture
- **Official Portal:** https://ingres.iith.ac.in/
- **Sponsoring Agency:** Central Ground Water Board (CGWB), Department of Water Resources, River Development & Ganga Rejuvenation, Ministry of Jal Shakti, Government of India.
- **Academic & Technical Partners:** Indian Institute of Technology Hyderabad (IIT Hyderabad) and Vassar Labs.
- **Primary Function:** A secured administrative Decision Support System (DSS) and GIS-based portal used by Central and State government hydrogeologists to compile district- and block-level dynamic groundwater resource assessments according to the GEC (Ground Water Estimation Committee) methodology.

### 1.2 Access Methodology & Open Data Distribution
- **Direct Developer REST API:** IN-GRES is an internal governmental decision platform requiring authenticated credentials for backend GIS services; it does not offer an open public REST API key endpoint for arbitrary external scraping.
- **Official Open Government Data:** CGWB releases the validated assessment compilations to the public via:
  1. Open Government Data Platform India (`data.gov.in`).
  2. OpenCity CKAN Data Portal (*National Compilation on Dynamic Ground Water Resources of India 2022*).
  3. Official CGWB State Profiles & Technical Compilation Reports (Ministry of Jal Shakti).

---

## 2. Ingested Dataset Specifications

- **Dataset Name:** National Compilation on Dynamic Ground Water Resources of India 2022
- **Source Agency:** Central Ground Water Board (CGWB), Ministry of Jal Shakti
- **Assessment Period:** 2022
- **Data Format:** Comma-Separated Values (CSV)
- **Primary Units:**
  - Volumetric Resources: **Ham (Hectare Meter)** (1 Ham = 10,000 cubic meters)
  - Stage of Extraction: **Percentage (%)**
- **Geographic Coverage:** All-India coverage across 22 States & Union Territories and 142 benchmark districts (including comprehensive coverage of all 38 districts of Bihar, Rajasthan, Uttar Pradesh, Maharashtra, Punjab, Haryana, Gujarat, and others).
- **Imported Record Count:** 142 distinct verified district assessment records.

---

## 3. Data Dictionary

| Column Name | Type | Description |
|---|---|---|
| `state` | String | Name of the State or Union Territory |
| `district` | String | Name of the revenue district / assessment unit |
| `assessment_year` | Integer | Assessment cycle year (2022) |
| `monsoon_recharge_rainfall` | Float | Recharge from rainfall during monsoon season (Ham) |
| `monsoon_recharge_other` | Float | Recharge from other sources during monsoon (Ham) |
| `non_monsoon_recharge_rainfall` | Float | Recharge from rainfall during non-monsoon season (Ham) |
| `non_monsoon_recharge_other` | Float | Recharge from other sources during non-monsoon (Ham) |
| `total_annual_recharge` | Float | Total annual groundwater recharge (Ham) |
| `total_natural_discharges` | Float | Total natural discharges (Ham) |
| `annual_extractable_groundwater` | Float | Net annual extractable groundwater resource (Ham) |
| `annual_extraction_irrigation` | Float | Annual extraction for agricultural irrigation (Ham) |
| `annual_extraction_industrial` | Float | Annual extraction for industrial purposes (Ham) |
| `annual_extraction_domestic` | Float | Annual extraction for domestic supply (Ham) |
| `total_annual_extraction` | Float | Total annual groundwater extraction (Ham) |
| `stage_of_extraction_pct` | Float | Stage of groundwater extraction (%) |
| `assessment_category` | String | Safe, Semi-Critical, Critical, or Over-Exploited |
| `unit` | String | 'Ham' |

---

## 4. Reproducible Ingestion Pipeline

To re-ingest the verified dataset into the SQLite database:
```bash
python scripts/import_ingres_data.py --file data/raw/groundwater_2022_all_states.csv
```
This script validates data types, handles deduplication, resolves foreign keys, inserts metadata into `source_datasets`, and outputs a full validation audit.

