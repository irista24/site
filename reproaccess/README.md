# ReproAccess

Abortion-care **access & policy analytics** dashboard for datathon / public-health exploration.

Built with **Python 3.11+**, **Streamlit**, **pandas**, **Plotly**, **GeoPandas**, **SciPy / statsmodels / scikit-learn**, and **Parquet**. Deployable on **Streamlit Community Cloud**. No auth, Postgres, paid APIs, or microservices.

> Observational analytics only. Simulations are **hypothetical**. Associations are **not causal**.

## Quick start

```bash
cd reproaccess
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1) Download / stage public data
python scripts/ingest_data.py

# 2) Clean to analysis tables
python scripts/clean_data.py

# 3) Build geographic metrics
python scripts/build_geographic_metrics.py

# 4) Run the app
streamlit run app.py
```

Open http://localhost:8501

## Project layout

```
reproaccess/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── data/
│   ├── raw/           # downloads + curated KFF extract + optional ANSIRH CSV
│   └── processed/     # parquet/csv analysis tables + data dictionary
├── scripts/
│   ├── ingest_data.py
│   ├── clean_data.py
│   └── build_geographic_metrics.py
├── src/
│   ├── data_loader.py
│   ├── validation.py
│   ├── analysis.py
│   ├── geospatial.py
│   ├── simulations.py
│   ├── visualizations.py
│   └── ui_components.py
├── pages/
│   ├── 1_Overview.py
│   ├── 2_Geographic_Access.py
│   ├── 3_Policy_Analysis.py
│   ├── 4_Scenario_Simulator.py
│   └── 5_Methodology.py
└── tests/
    ├── test_analysis.py
    ├── test_geospatial.py
    └── test_simulations.py
```

## Data sources (real public data only)

| Source | What we use | Notes |
|--------|-------------|-------|
| [Guttmacher Monthly Abortion Provision Study](https://osf.io/k4x7t/) | State monthly abortion estimates | Downloaded from OSF CSV |
| [KFF Abortion Policy / State Health Facts](https://www.kff.org/womens-health-policy/abortion-in-the-u-s-dashboard/) | Gestational limits + waiting periods | Curated extraction of published tables; see KFF CSV workflow below |
| [Census popest age-sex](https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/state/asrh/) | Women ages 15–44 by state (2023) | Civilian estimates file |
| [Census cartographic boundaries](https://www2.census.gov/geo/tiger/GENZ2023/shp/) | State & county 20m shapefiles | Centroids for distance proxy |
| ANSIRH facilities (optional) | Facility lat/lon | **User-supplied CSV only** — never fabricated |

**Integrity rules**
- Never invent facility coordinates, policy values, healthcare outcomes, or national statistics.
- If a source is missing, the UI shows **Data unavailable** + expected file format (no silent synthetic substitution).
- Source URLs, extraction/as-of dates, and a data dictionary are preserved under `data/`.
- Simulation outputs are labeled **HYPOTHETICAL**.

### KFF CSV workflow (if bulk download fails)

KFF indicators are interactive. `scripts/ingest_data.py` writes `data/raw/kff_abortion_policy.csv` from the publicly published State Health Facts tables (gestational limits as of **2026-01-06**, waiting periods as of **2025-12-01**).

To refresh manually:

1. Open [Gestational Limits](https://www.kff.org/state-health-policy-data/state-indicator/gestational-limit-abortions/) and [Waiting Periods](https://www.kff.org/other/state-indicator/mandatory-waiting-periods/).
2. Export or copy the state table.
3. Save as `data/raw/kff_abortion_policy.csv` with columns:

```text
state_name,state_abbr,state_fips,statutory_limit,policy_category,
mandatory_waiting_period,waiting_period_length,in_person_counseling_two_trips,
gestational_source_url,gestational_as_of,waiting_source_url,waiting_as_of,
extraction_date,is_synthetic
```

4. Set `is_synthetic=false` for observed rows.
5. Re-run `clean_data.py` and `build_geographic_metrics.py`.

### Optional ANSIRH facilities (Mode B)

Place `data/raw/ansirh_facilities.csv`:

```text
facility_id,name,state_abbr,latitude,longitude
```

Then re-run `build_geographic_metrics.py`. Missing coordinates are **not** imputed.

## Geographic access metric

Miles from each **county centroid** to the nearest **non-ban state centroid** (KFF `policy_category != total_ban` × Census boundaries).

This is a coarse policy-geography proxy — **not** clinic travel time.

## Pages

1. **Overview** — KPIs, policy map, provision trends, rates  
2. **Geographic Access** — county distance distributions and filters  
3. **Policy Analysis** — category comparisons + optional exploratory regression with limitations  
4. **Scenario Simulator** — Mode A always; Mode B only if facilities exist  
5. **Methodology** — sources, schemas, limitations  

## Tests & smoke check

```bash
cd reproaccess
pytest -q
python -c "from src.data_loader import load_all; d=load_all(); print({k:v.available for k,v in d['statuses'].items()})"
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub (app lives in `reproaccess/`).
2. Go to https://share.streamlit.io → **New app**.
3. Set:
   - **Repository**: your fork/repo  
   - **Branch**: your deploy branch  
   - **Main file path**: `reproaccess/app.py`  
   - **Python version**: 3.11+  
4. Ensure `reproaccess/requirements.txt` is detected (Cloud uses it from the app directory or repo root — if needed, copy/symlink requirements or set advanced Python dependencies to `reproaccess/requirements.txt`).
5. Pre-commit processed data under `reproaccess/data/processed/` (recommended for Cloud) **or** add a setup script that runs ingest/clean/build (downloads require outbound network).
6. Deploy. No secrets required.

## Design notes

Public-health visual language: warm off-white background, navy text, muted teal accents, consistent policy color legend, source/date captions on charts.

## License / attribution

Upstream data remain under their respective licenses and citation requirements (Guttmacher/OSF CC-BY, KFF terms, Census public domain). Cite sources when sharing results.
