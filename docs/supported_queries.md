# Groundwater AI Agent — Supported Queries Documentation

## 1. Registered Function Catalog

The Groundwater AI Agent operates on a strictly validated function registry. No arbitrary SQL queries are generated.

| Function Name | Category | Example Natural Language Query | Required Parameters | Optional Parameters | Data Status |
|---|---|---|---|---|---|
| `get_assessment_years()` | Metadata | "What assessment years are available?" | None | None | Available |
| `get_state_list()` | Metadata | "Which states have groundwater data?" | None | None | Available |
| `get_districts_in_state()` | Metadata | "List districts in Bihar with groundwater data" | `state` | None | Available |
| `get_country_summary()` | National | "Show national groundwater statistics for 2022" | `assessment_year` | None | Available |
| `get_state_summary()` | State | "Show groundwater statistics for Bihar" | `state` | `assessment_year` | Available |
| `get_district_summary()` | District | "Show all groundwater data for Patna Bihar" | `state`, `district` | `assessment_year` | Available |
| `get_groundwater_recharge()` | Recharge | "What is the groundwater recharge in Patna?" | `state` | `district`, `assessment_year` | Available |
| `get_extractable_groundwater()` | Extractable Resources | "What is the extractable groundwater in Patna Bihar?" | `state` | `district`, `assessment_year` | Available |
| `get_groundwater_extraction()` | Extraction | "What is the groundwater extraction in Patna?" | `state` | `district`, `assessment_year` | Available |
| `get_stage_of_extraction()` | Stage of Extraction | "What is the stage of groundwater extraction in Patna?" | `state` | `district`, `assessment_year` | Available |
| `get_assessment_category()` | Assessment Category | "What assessment category does Patna belong to?" | `state` | `district`, `assessment_year` | Available |
| `get_overexploited_units()` | Over-Exploited | "Which districts in Bihar are over-exploited?" | `state` | `assessment_year` | Available |
| `compare_locations()` | Comparison | "Compare groundwater extraction in Patna and Gaya" | `state1`, `district1`, `state2`, `district2`, `parameter` | `assessment_year` | Available |
| `get_groundwater_level()` | Water Level | "What is the groundwater level in Patna?" | `state` | `district`, `year` | **Explicitly Unavailable** |

---

## 2. Parameter Validation & Edge Case Handling

### 2.1 Missing Years
- If a user requests a year that does not exist in the connected dataset (such as 2023 or 2010):
  - **Behavior:** The agent explicitly returns `status: "not_found"`.
  - **Response:** *"No verified groundwater extraction record was found for the requested location and assessment period. Note: The available assessment year in this database is 2022."*
  - **Rule:** The agent **never silently substitutes** another year.

### 2.2 Groundwater Level Queries
- IN-GRES and CGWB dynamic groundwater resource estimations measure volumetric resource components (recharge, extraction in Ham). They are **not** borehole water level depth measurements (meters below ground level).
  - **Behavior:** The agent classifies intent as `get_groundwater_level` and dispatches to the registered handler.
  - **Response:** *"Groundwater depth/level measurements are not available in the currently connected CGWB National Compilation dataset. This dataset contains groundwater resource assessment figures (recharge, extraction, extractable resources, stage of extraction). For groundwater level data, please consult India-WRIS or CGWB groundwater monitoring portal."*

### 2.3 Ambiguous Questions
- If a user asks *"Show groundwater in Bihar"*:
  - **Behavior:** The agent detects an ambiguous query missing an operational metric.
  - **Response:** *"Which groundwater parameter would you like to know? Please choose: recharge, extraction, extractable resources, stage of extraction, or assessment category."*

### 2.4 SQL Injection Defense
- Natural language input is never interpolated into raw SQL statements.
- Inputs are passed exclusively as parameterized values into SQLAlchemy ORM filters.
- Passing strings such as `'; DROP TABLE states; --` cleanly returns a `not_found` response without modifying database state.

