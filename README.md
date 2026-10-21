# Nova Scotia Healthcare Operations & Emergency Department Analytics

**Platform**: Python 3.10+, Streamlit, Plotly, Pandas, GeoJSON  

---

## 📌 Executive Overview

This project provides an interactive data analytics and geospatial visualization suite for healthcare management across Nova Scotia. It addresses provincial hospital capacity bottlenecks, nurse staffing allocations, inpatient net flow dynamics, and Emergency Department (ED) triage acuity under the **Canadian Triage and Acuity Scale (CTAS)**.

The system is delivered through two interactive **Streamlit** dashboards and standalone geospatial visualizations:
1. **Hospital Operations Dashboard (`costdash.py`)**: Tracks provincial hospital locations, bed occupancy baselines, monthly admission/discharge net flows, and nurse staffing compositions.
2. **Emergency Department Analytics Dashboard (`ed_dashboard.py`)**: Provides regional choropleth heatmaps of Nova Scotia Health Authority zones, ED site-level traffic, CTAS triage distributions (Levels 1–5), and high-acuity vs. low-acuity congestion modeling.

---

## 📁 Repository Structure

```text
.
├── README.md                      # Comprehensive project documentation
├── LICENSE                        # MIT License granted to Nova Scotia Health
├── pyproject.toml                 # uv/PEP 517 project dependencies and configuration
├── uv.lock                        # Deterministic dependency lockfile
├── .gitignore                     # Git ignore rules for caches, venvs, and OS files
├── .streamlit/
│   ├── config.toml                # Headless server & browser configuration
│   └── credentials.toml           # Streamlit telemetry configuration
│
├── costdash.py                    # Streamlit app: Hospital operations & inpatient trends
├── ed_dashboard.py                # Streamlit app: Emergency Department & CTAS analytics
├── test_map.html                  # Standalone interactive Plotly HTML map export
│
└── data/                          # Centralized data directory
    ├── Data.xlsx                  # Master workbook (Attributes, Inpatient, ED, Bed Census, Redesign)
    ├── ed_consolidated_dataset.xlsx # Consolidated ED metrics (Provincial, Zone, Site breakdown)
    ├── data4.csv                  # Supplies, drug expenses, and compensation time-series
    ├── data6.csv                  # Actual vs. Ideal nurse staffing benchmarking (2 RN : 1 LPN)
    └── ns_zones.geojson           # Geospatial boundary polygons for Nova Scotia Health zones
```

---

## 🚀 Key Features & Applications

### 1. Hospital Operations Dashboard (`costdash.py`)
* **Interactive Geographic Mapping**: Built using Plotly Mapbox over OpenStreetMap tiles, mapping each facility listed in `Hospital Attributes`.
* **Dynamic Hover Cards**: Displays real-time metrics including total licensed beds, active beds in use, occupancy rates, postal codes, and staffing levels (Registered Nurses, Licensed Practical Nurses, and Administrative personnel).
* **Algorithmic Occupancy Derivation**: Inpatient occupancy is derived dynamically over time:
  $$\text{Net Flow}_t = \text{Admissions}_t - \text{Discharges}_t$$
  $$\text{Occupied Beds}_t = \text{Baseline Beds} + \sum_{\tau=1}^t \text{Net Flow}_\tau$$
* **Occupancy Metric Toggle**: View patient census as raw occupied bed counts or percentage capacity ($\%$).
* **Admission & Flow Trajectories**: Time-series plots visualizing patient movement across institutions.

### 2. Emergency Department Analytics Dashboard (`ed_dashboard.py`)
* **Choropleth Heatmap by Health Zone**: Integrates `ns_zones.geojson` to render shaded polygons for Nova Scotia's health management zones:
  * **Central Zone** (Halifax & surrounding areas)
  * **Eastern Zone** (Cape Breton, Antigonish, Guysborough)
  * **Northern Zone** (Colchester East Hants, Cumberland, Pictou)
  * **Western Zone** (Annapolis Valley, South Shore, South West)
* **ED Facility Scatter Overlay**: Exact coordinates for major emergency care centres (e.g., Halifax Infirmary, Dartmouth General, Cape Breton Regional, Yarmouth Regional, Cobequid, Aberdeen, Colchester East Hants, South Shore Regional).
* **Cascading Filters**: Filter seamlessly by regional zone and operational site, cleanly distinguishing measured sites from calculated aggregate deductions (*"Other Sites"*).
* **CTAS Urgency Modeling**:
  * **Level 1 (Resuscitation)**: Immediately life-threatening.
  * **Level 2 (Emergent)**: Potentially life-threatening conditions.
  * **Level 3 (Urgent)**: Serious conditions requiring prompt care.
  * **Level 4 (Less Urgent)**: Mild to moderate conditions.
  * **Level 5 (Non-Urgent)**: Conditions that could be managed in primary/ambulatory care.
* **High vs. Low Acuity Congestion Analysis**: Contrasts High Acuity (CTAS 1–2) against Low Acuity (CTAS 3–5) visits to determine whether emergency congestion is driven by acute critical surges or volume of low-urgency presentations.

---

## 🛠️ Data Sources & Description

| Dataset / File | Format | Key Contents |
| :--- | :--- | :--- |
| **`data/Data.xlsx`** | Excel | Master workbook with sheets: `Hospital Attributes`, `Inpatient Stats`, `Salary_Table`, `Dollars`, `ED Total`, `ED By Select Sites`, `NSH Beds`, `LTC Beds`, and regional population census. |
| **`data/ed_consolidated_dataset.xlsx`** | Excel | Preprocessed and consolidated tables: `Provincial Total`, `Site Breakdown`, and `Zone Total`. |
| **`data/ns_zones.geojson`** | GeoJSON | Polygons representing official Nova Scotia Health Authority administrative boundaries. |
| **`data/data4.csv`** | CSV | Line-item expenses covering drugs, medical supplies, regular compensation, and overtime by hospital and date. |
| **`data/data6.csv`** | CSV | Best-in-class nurse staffing ratios benchmarking actual RN/LPN expenses against the ideal 2:1 formula. |
| **`test_map.html`** | HTML | Portable, self-contained interactive Plotly web map for offline inspection. |

---

## 💻 Installation & Setup

### Prerequisites
* **Python**: Version `3.10` or higher
* **uv** (recommended) or standard `pip` / `venv`

### Option A: Using `uv` (Recommended)

1. **Clone or navigate to the workspace directory**:
   ```bash
   cd "Assignment files"
   ```

2. **Sync the virtual environment and dependencies**:
   ```bash
   uv sync
   ```

### Option B: Using Standard Python `venv`

1. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate    # On Windows: .venv\Scripts\activate
   ```

2. **Install project dependencies**:
   ```bash
   pip install openpyxl pandas folium matplotlib streamlit streamlit-folium plotly
   ```

---

## 🖥️ Running the Dashboards

### 1. Launch the Emergency Department Dashboard
```bash
uv run streamlit run ed_dashboard.py
```
*(Or with activated virtualenv: `streamlit run ed_dashboard.py`)*

Open your browser at: **`http://localhost:8501`**

### 2. Launch the Hospital Operations Dashboard
```bash
uv run streamlit run costdash.py --server.port 8502
```
*(Or with activated virtualenv: `streamlit run costdash.py --server.port 8502`)*

Open your browser at: **`http://localhost:8502`**

---

## 📊 Core Analytical Concepts

### 1. The Cumulative Net Flow Principle
Hospital bed utilization is not static. Given baseline bed usage $B_0$ on March 31, 2018:
$$B_t = B_0 + \sum_{i=1}^t (A_i - D_i)$$
Where $A_i$ represents total inpatient admissions and $D_i$ represents discharges during interval $i$.

### 2. Staffing Optimization Model
According to best-in-class healthcare staffing benchmarks:
* **Target RN Ratio**: $2.0 \times \text{Beds in Use}$
* **Target LPN Ratio**: $1.0 \times \text{Beds in Use}$
Staffing models evaluate actual full-time equivalents (FTE) and payroll against this standard to identify overtime expenditure anomalies.

### 3. ED Capacity & Low Acuity System Load
Analysis across Nova Scotia emergency centers demonstrates that the majority of patient presentations fall into **CTAS 3, 4, and 5**. Visualizing this pattern provides clinical and managerial evidence that emergency wait times are heavily influenced by alternate-level-of-care (ALC) demand and primary care accessibility shortages rather than solely catastrophic emergencies.

---

## 📦 Dependencies

Defined in [`pyproject.toml`](pyproject.toml):
* **`streamlit`** ($\ge 1.35$): Reactive dashboard application framework
* **`plotly`** ($\ge 6.6.0$): Interactive maps, line trajectories, and choropleths
* **`pandas`** ($\ge 2.0$): Tabular data manipulation and aggregation
* **`openpyxl`** ($\ge 3.1$): Reading multi-tab Excel workbooks
* **`folium`** ($\ge 0.17$) & **`streamlit-folium`** ($\ge 0.22$): Geospatial mapping utilities
* **`matplotlib`** ($\ge 3.8$): Static chart rendering fallback

---

## 📄 License

This project is licensed under the **MIT License** to **Nova Scotia Health (NSH)**. See the [`LICENSE`](LICENSE) file for complete terms and copyright notices.


