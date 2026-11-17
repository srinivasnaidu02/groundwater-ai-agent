# Groundwater AI Agent — Database Schema Documentation

## 1. Relational Model Overview

The database is built using **SQLite** with **SQLAlchemy ORM** and is 100% compliant with PostgreSQL and other ANSI SQL relational database management systems.

```
+----------------+          +-------------------------+
|     states     |1        *|        districts        |
|----------------|----------|-------------------------|
| id (PK)        |          | id (PK)                 |
| name           |          | name                    |
| code           |          | state_id (FK -> states) |
+----------------+          +------------+------------+
                                         | 1
                                         |
                                         | *
+----------------------+    +------------+------------+    +-----------------------+
|   assessment_years   |1  *|  groundwater_resources  |*  1|    source_datasets    |
|----------------------|----|-------------------------|----|-----------------------|
| id (PK)              |    | id (PK)                 |    | id (PK)               |
| year                 |    | state_id (FK)           |    | name                  |
| period_description   |    | district_id (FK)        |    | source_url            |
+----------------------+    | block_id (FK, nullable) |    | download_date         |
                            | assessment_year_id (FK) |    | assessment_period     |
                            | source_dataset_id (FK)  |    | source_agency         |
                            | total_annual_recharge   |    | data_format           |
                            | annual_extractable_gw   |    | unit                  |
                            | total_annual_extraction |    | num_records           |
                            | stage_of_extraction_pct |    +-----------------------+
                            | assessment_category     |
                            | unit                    |
                            +-------------------------+
```

---

## 2. Table Specifications

### 2.1 `states`
Contains all distinct Indian States and Union Territories.
- `id` (INTEGER, PRIMARY KEY)
- `name` (VARCHAR(100), UNIQUE, INDEXED): e.g., 'Bihar', 'Rajasthan'
- `code` (VARCHAR(10), NULLABLE)
- `created_at` (DATETIME)

### 2.2 `districts`
Districts mapped to their respective State.
- `id` (INTEGER, PRIMARY KEY)
- `name` (VARCHAR(150), INDEXED): e.g., 'Patna', 'Gaya', 'Jaipur'
- `state_id` (INTEGER, FOREIGN KEY -> `states.id`)
- `created_at` (DATETIME)

### 2.3 `assessment_years`
Distinct assessment periods documented in official CGWB surveys.
- `id` (INTEGER, PRIMARY KEY)
- `year` (VARCHAR(20), UNIQUE, INDEXED): e.g., '2022'
- `period_description` (VARCHAR(100))
- `created_at` (DATETIME)

### 2.4 `source_datasets`
Maintains full dataset provenance and audit metadata.
- `id` (INTEGER, PRIMARY KEY)
- `name` (VARCHAR(200)): 'CGWB National Compilation on Dynamic Ground Water Resources 2022'
- `source_url` (TEXT)
- `download_date` (DATETIME)
- `assessment_period` (VARCHAR(50))
- `source_agency` (VARCHAR(200)): 'Central Ground Water Board (CGWB), Ministry of Jal Shakti'
- `original_filename` (VARCHAR(200))
- `data_format` (VARCHAR(50)): 'CSV'
- `unit` (VARCHAR(20)): 'Ham (Hectare Meter)'
- `geographic_coverage` (VARCHAR(200))
- `num_records` (INTEGER)
- `is_verified` (BOOLEAN)
- `notes` (TEXT)

### 2.5 `groundwater_resources`
Granular assessment resource metrics per district and assessment year.
- `id` (INTEGER, PRIMARY KEY)
- `state_id` (INTEGER, FOREIGN KEY -> `states.id`)
- `district_id` (INTEGER, FOREIGN KEY -> `districts.id`)
- `block_id` (INTEGER, NULLABLE)
- `assessment_year_id` (INTEGER, FOREIGN KEY -> `assessment_years.id`)
- `source_dataset_id` (INTEGER, FOREIGN KEY -> `source_datasets.id`)
- `monsoon_recharge_rainfall` (FLOAT)
- `monsoon_recharge_other` (FLOAT)
- `non_monsoon_recharge_rainfall` (FLOAT)
- `non_monsoon_recharge_other` (FLOAT)
- `total_annual_recharge` (FLOAT): Sum of monsoon & non-monsoon recharge in Ham
- `total_natural_discharges` (FLOAT)
- `annual_extractable_groundwater` (FLOAT): Extractable groundwater resources in Ham
- `annual_extraction_irrigation` (FLOAT)
- `annual_extraction_industrial` (FLOAT)
- `annual_extraction_domestic` (FLOAT)
- `total_annual_extraction` (FLOAT): Total extraction in Ham
- `gw_allocation_domestic_future` (FLOAT)
- `net_gw_availability_future` (FLOAT)
- `stage_of_extraction_pct` (FLOAT): (Total Extraction / Annual Extractable Resource) * 100
- `assessment_category` (VARCHAR(50)): 'Safe', 'Semi-Critical', 'Critical', or 'Over-Exploited'
- `unit` (VARCHAR(20)): 'Ham'

### 2.6 `query_logs`
Audit table recording all incoming user questions, parsing outputs, and execution times.
- `id` (INTEGER, PRIMARY KEY)
- `question` (TEXT)
- `intent` (VARCHAR(100))
- `entities` (TEXT): JSON dump of extracted parameters
- `function_called` (VARCHAR(100))
- `parameters` (TEXT): JSON dump of passed parameters
- `status` (VARCHAR(50))
- `response_text` (TEXT)
- `execution_time_ms` (FLOAT)
- `created_at` (DATETIME)

### 2.7 `evaluation_results`
Persistent store for automated benchmark test case execution logs.
- `id` (INTEGER, PRIMARY KEY)
- `test_case_id` (VARCHAR(50))
- `input_question` (TEXT)
- `expected_intent` (VARCHAR(100))
- `actual_intent` (VARCHAR(100))
- `intent_correct` (BOOLEAN)
- `expected_function` (VARCHAR(100))
- `actual_function` (VARCHAR(100))
- `function_correct` (BOOLEAN)
- `expected_status` (VARCHAR(50))
- `actual_status` (VARCHAR(50))
- `status_correct` (BOOLEAN)
- `entity_extraction_score` (FLOAT)
- `end_to_end_correct` (BOOLEAN)
- `execution_time_ms` (FLOAT)
- `error_category` (VARCHAR(100))
- `notes` (TEXT)
- `created_at` (DATETIME)

