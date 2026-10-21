import json
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

BASE_DIR = Path(__file__).resolve().parent

def get_data_file(filename: str) -> Path:
    """Resolve file path from data folder, script directory, or CWD."""
    candidates = [
        BASE_DIR / "data" / filename,
        BASE_DIR / filename,
        Path("data") / filename,
        Path(filename),
    ]
    for p in candidates:
        if p.exists():
            return p
    return BASE_DIR / "data" / filename

# --- 1. Page Configuration ---
st.set_page_config(page_title="ED Operations Dashboard", page_icon="🚑", layout="wide")

st.title("🚑 Emergency Department (ED) Analytics")
st.markdown("""
High acuity (CTAS 1–2) represents urgent, life-threatening cases, while low acuity (CTAS 3–5) reflects less critical conditions.

The dominance of low acuity visits suggests that emergency departments handle a high volume of non-urgent cases, which may contribute to system congestion and longer wait times.
""")
st.markdown("---")


# --- 2. Data Loading & Cleaning ---
@st.cache_data
def load_data():
    try:
        # Load prepared ED consolidated dataset
        eda_file = get_data_file('ed_consolidated_dataset.xlsx')
        df_prov = pd.read_excel(eda_file, sheet_name='Provincial Total')
        df_site = pd.read_excel(eda_file, sheet_name='Site Breakdown')
        df_zone = pd.read_excel(eda_file, sheet_name='Zone Total')
        
        # Load pure pure CTAS metrics isolated from the baseline data mapping
        data_file = get_data_file('Data.xlsx')
        df_ctas_zone = pd.read_excel(data_file, sheet_name='ED Total')
        df_ctas_site = pd.read_excel(data_file, sheet_name='ED By Select Sites')
        
        # Format timestamps gracefully into monthly aggregation blocks
        for df in [df_prov, df_site, df_zone, df_ctas_zone, df_ctas_site]:
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df['Month'] = df['Date'].dt.to_period('M').astype(str)
                
        return df_prov, df_site, df_zone, df_ctas_zone, df_ctas_site
    except Exception as e:
        st.error(f"Error loading the data file: {e}")
        return [pd.DataFrame()] * 5

df_prov, df_site, df_zone, df_ctas_zone, df_ctas_site = load_data()


# --- 3. Sidebar Filters ---
st.sidebar.header("Filter Options")

# Ensure safety on empty datasets
if not df_zone.empty:
    zones = ["All"] + sorted(df_zone['Zone'].dropna().unique().tolist())
    sel_zone = st.sidebar.selectbox("Select Zone", zones)
    
    if sel_zone != "All":
        av_sites = ["All"] + sorted(df_site[df_site['Zone'] == sel_zone]['Site'].dropna().unique().tolist())
    else:
        av_sites = ["All"] + sorted(df_site['Site'].dropna().unique().tolist())
        
    sel_site = st.sidebar.selectbox("Select Site", av_sites)
else:
    sel_zone = "All"
    sel_site = "All"


# --- 4. Filtering Scopes ---
df_site_filtered = df_site.copy()
df_zone_filtered = df_zone.copy()

if sel_zone != "All":
    df_site_filtered = df_site_filtered[df_site_filtered['Zone'] == sel_zone]
    df_zone_filtered = df_zone_filtered[df_zone_filtered['Zone'] == sel_zone]

if sel_site != "All":
    df_site_filtered = df_site_filtered[df_site_filtered['Site'] == sel_site]


# --- 5. Requirement 8: Map of ED Sites ---
st.subheader("📍 ED Locations & Visit Densities")

# Exact coordinates lookup representing major known ED centers in NS
coord_lookup = {
    'Dartmouth General Hospital': (44.654, -63.549),
    'Cobequid': (44.757, -63.663),
    'Aberdeen': (45.578, -62.646),
    'Cape Breton': (46.120, -60.169),
    'Halifax Infirmary': (44.645, -63.585),
    'Colchester East Hants': (45.353, -63.298),
    'Yarmouth': (43.837, -66.115),
    'South Shore Regional': (44.380, -64.531)
}

if not df_site_filtered.empty:
    # We strip 'Other Sites' from spatial mapping as it is an abstract calculation
    map_data = df_site_filtered[df_site_filtered['Site'] != 'Other Sites'].copy()
    
    if not map_data.empty:
        # Group cumulative statistics
        df_map_agg = map_data.groupby(['Site', 'Zone'])['ED_Visits'].sum().reset_index()
        
        # Merge coords natively
        df_map_agg['Latitude'] = df_map_agg['Site'].map(lambda x: coord_lookup.get(x, (None, None))[0])
        df_map_agg['Longitude'] = df_map_agg['Site'].map(lambda x: coord_lookup.get(x, (None, None))[1])
        df_map_agg = df_map_agg.dropna(subset=['Latitude'])

        # Build CTAS distribution lookup explicitly for hover tracking
        # We process levels 1 through 5 independently
        ctas_1 = df_ctas_site[df_ctas_site['CTAS'] == 1].groupby('Site')['ED_Visits'].sum().to_dict()
        ctas_2 = df_ctas_site[df_ctas_site['CTAS'] == 2].groupby('Site')['ED_Visits'].sum().to_dict()
        ctas_3 = df_ctas_site[df_ctas_site['CTAS'] == 3].groupby('Site')['ED_Visits'].sum().to_dict()
        ctas_4 = df_ctas_site[df_ctas_site['CTAS'] == 4].groupby('Site')['ED_Visits'].sum().to_dict()
        ctas_5 = df_ctas_site[df_ctas_site['CTAS'] == 5].groupby('Site')['ED_Visits'].sum().to_dict()
        
        df_map_agg['CTAS_1'] = df_map_agg['Site'].map(ctas_1).fillna(0)
        df_map_agg['CTAS_2'] = df_map_agg['Site'].map(ctas_2).fillna(0)
        df_map_agg['CTAS_3'] = df_map_agg['Site'].map(ctas_3).fillna(0)
        df_map_agg['CTAS_4'] = df_map_agg['Site'].map(ctas_4).fillna(0)
        df_map_agg['CTAS_5'] = df_map_agg['Site'].map(ctas_5).fillna(0)
        
        with open(get_data_file('ns_zones.geojson')) as f:
            ns_geojson = json.load(f)
            
        for feature in ns_geojson['features']:
            zone_raw = feature['properties']['zone']
            if "-" in zone_raw:
                cleaned = zone_raw.split("-")[1].strip()
                feature['id'] = cleaned

        # Aggregated zone heat map
        df_choro = df_zone_filtered.groupby('Zone')['Total_Visits'].sum().reset_index()
        
        fig_map = px.choropleth_mapbox(
            df_choro,
            geojson=ns_geojson,
            locations='Zone',
            color='Total_Visits',
            color_continuous_scale="YlOrRd",
            range_color=[0, df_choro['Total_Visits'].max()],  # Prevents Northern/Eastern from turning invisible pale yellow
            opacity=0.6, # Bumped from 0.4 so colors don't wash out against white basemap
            zoom=6,
            center={"lat": 44.9, "lon": -63.5},
            mapbox_style="open-street-map",
            title="ED Sites Geographic Scope & Regional Heatmap",
            labels={'Total_Visits': 'Zone Activity'}
        )
        fig_map.update_traces(
            hovertemplate="<b>🗺️ Zone: %{location}</b><br>🏥 Total Visits: %{z:,.0f}<extra></extra>"
        )
        
        hover_cols = ["Site", "Zone", "ED_Visits", "CTAS_1", "CTAS_2", "CTAS_3", "CTAS_4", "CTAS_5"]
        
        fig_scatter = px.scatter_mapbox(
            df_map_agg,
            lat="Latitude",
            lon="Longitude",
            color="Site",  # Differentiate purely by color, not size
            custom_data=hover_cols,
        )
        
        hovertemplate_scatter = (
            "<span style='font-size: 16px;'><b>🏥 %{customdata[0]}</b></span><br><br>"
            "📍 Zone: %{customdata[1]}<br>"
            "📊 Total ED Visits: %{customdata[2]:,.0f}<br><br>"
            "<b>⚕️ Acuity Distribution:</b><br>"
            "• CTAS Level 1: %{customdata[3]:,.0f}<br>"
            "• CTAS Level 2: %{customdata[4]:,.0f}<br>"
            "• CTAS Level 3: %{customdata[5]:,.0f}<br>"
            "• CTAS Level 4: %{customdata[6]:,.0f}<br>"
            "• CTAS Level 5: %{customdata[7]:,.0f}<br>"
            "<extra></extra>"
        )
        
        fig_scatter.update_traces(
            hovertemplate=hovertemplate_scatter,
            marker=dict(size=14, opacity=0.9)
        )
        
        for trace in fig_scatter.data:
            fig_map.add_trace(trace)
        
        fig_map.update_layout(
            margin={"r":0, "t":40, "l":0, "b":0},
            coloraxis_colorbar=dict(
                x=0.01,
                xanchor="left",
                y=0.5
            )
        )
        st.plotly_chart(fig_map, width='stretch', config={'scrollZoom': True})
    else:
        st.info("The selected filters result strictly in abstract 'Other Sites', which don't map to a single geographic coordinate.")


# --- 6. Requirement 9: Trend Analysis ---
st.markdown("---")
st.subheader("📈 Flow & Trend Analysis")

col1, col2 = st.columns(2)

with col1:
    st.markdown("##### 📌 A) Visit Trends by Zone")
    st.markdown("Tracks global operations volume across regional health zones.")
    if not df_zone_filtered.empty:
        z_agg = df_zone_filtered.groupby(['Month', 'Zone'])['Total_Visits'].sum().reset_index()
        z_agg = z_agg.sort_values(by='Month')
        fig_z = px.line(z_agg, x='Month', y='Total_Visits', color='Zone', markers=True)
        fig_z.update_layout(xaxis_title="Month", yaxis_title="Total Visits", hovermode="x unified", legend_title="Zone")
        st.plotly_chart(fig_z, width='stretch')

with col2:
    st.markdown("##### 📌 B) Visit Trends by Operational Site")
    st.markdown("Evaluating specific clinic traffic. Filter specific sites dynamically.")
    if not df_site_filtered.empty:
        s_agg = df_site_filtered.groupby(['Month', 'Site'])['ED_Visits'].sum().reset_index()
        s_agg = s_agg.sort_values(by='Month')
        fig_s = px.line(s_agg, x='Month', y='ED_Visits', color='Site', markers=True)
        fig_s.update_layout(xaxis_title="Month", yaxis_title="ED Visits", hovermode="x unified", legend_title="Site")
        st.plotly_chart(fig_s, width='stretch')


st.markdown("---")
st.subheader("⚕️ CTAS Analysis (Acuity Scaling)")
st.info("""
**What is CTAS?**  
CTAS is a triage system used in emergency departments to classify patient urgency.  
**Level 1** = Most urgent (life-threatening) • **Level 5** = Least urgent (non-urgent cases)
""")

# Build isolated CTAS context based entirely on active Site/Zone filters
if sel_site == "Other Sites":
    st.warning("⚠️ 'Other Sites' is a mathematical deduction block (Zone Total − Selected Sites). Since CTAS scores are highly distinct parameters, they are not modeled directly for this aggregate.")
else:
    if sel_site != "All":
        df_ctas_proc = df_ctas_site[df_ctas_site['Site'] == sel_site].copy()
        scoping_label = f"Site: {sel_site}"
    elif sel_zone != "All":
        df_ctas_proc = df_ctas_zone[df_ctas_zone['Zone'] == sel_zone].copy()
        scoping_label = f"Zone: {sel_zone}"
    else:
        df_ctas_proc = df_ctas_zone.copy()
        scoping_label = "Provincial Overview"

    if not df_ctas_proc.empty:
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown(f"##### C) Acuity Breakdown ({scoping_label})")
            ctas_agg = df_ctas_proc.groupby(['Month', 'CTAS'])['ED_Visits'].sum().reset_index()
            ctas_agg['CTAS'] = ctas_agg['CTAS'].astype(str) # Convert explicitly for discrete coloring
            ctas_agg = ctas_agg.sort_values(by='Month')
            
            fig_ctas = px.line(ctas_agg, x='Month', y='ED_Visits', color='CTAS', markers=True, category_orders={"CTAS": ["1", "2", "3", "4", "5"]})
            fig_ctas.update_layout(xaxis_title="Month", yaxis_title="Volume", hovermode="x unified")
            st.plotly_chart(fig_ctas, width='stretch')
            st.caption("Higher CTAS levels (4–5) represent lower urgency but drive higher overall visit volume. Lower CTAS levels (1–2) are critical, life-threatening interventions but occur less frequently.")
            
        with c2:
            st.markdown(f"##### D) High vs Low Classification ({scoping_label})")
            st.markdown("Grouping: **High Acuity** (CTAS 1–2) vs **Low Acuity** (CTAS 3–5).")
            # Map CTAS into generalized buckets per prompt rules 1-2 (High), 3-5 (Low)
            df_ctas_proc['Acuity'] = df_ctas_proc['CTAS'].apply(lambda c: 'High Acuity (Level 1-2)' if c in [1, 2] else 'Low Acuity (Level 3-5)')
            acuity_agg = df_ctas_proc.groupby(['Month', 'Acuity'])['ED_Visits'].sum().reset_index()
            acuity_agg = acuity_agg.sort_values(by='Month')
            
            fig_acuity = px.line(acuity_agg, x='Month', y='ED_Visits', color='Acuity', markers=True)
            fig_acuity.update_layout(xaxis_title="Month", yaxis_title="Visit Volume", hovermode="x unified")
            st.plotly_chart(fig_acuity, width='stretch')
            st.caption("Comparing these trends helps evaluate capacity: if low acuity dominates, it indicates potential system pressure from non-urgent visits rather than strictly severe emergencies.")

# --- Independent Regional & Site CTAS Triggers ---
st.markdown("---")
st.subheader("Regional & Site CTAS Trends")
c3, c4 = st.columns(2)

with c3:
    st.markdown("##### CTAS Trends by Zone")
    df_cz = df_ctas_zone.copy()
    if sel_zone != "All":
        df_cz = df_cz[df_cz['Zone'] == sel_zone]
        
    if not df_cz.empty:
        cz_agg = df_cz.groupby(['Month', 'CTAS'])['ED_Visits'].sum().reset_index()
        cz_agg['CTAS'] = cz_agg['CTAS'].astype(str)
        cz_agg = cz_agg.sort_values(by='Month')
        fig_cz = px.line(cz_agg, x='Month', y='ED_Visits', color='CTAS', markers=True, category_orders={"CTAS": ["1", "2", "3", "4", "5"]})
        fig_cz.update_layout(xaxis_title="Month", yaxis_title="Visit Volume", hovermode="x unified")
        st.plotly_chart(fig_cz, width='stretch')
    else:
        st.info("No CTAS data available for the selected zone.")

with c4:
    st.markdown("##### CTAS Trends by Site")
    if sel_site == "Other Sites":
        st.warning("⚠️ 'Other Sites' is a mathematical deduction block. CTAS scores cannot be modeled directly for this aggregate.")
    else:
        df_cs = df_ctas_site.copy()
        if sel_site != "All":
            df_cs = df_cs[df_cs['Site'] == sel_site]
            
        if not df_cs.empty:
            cs_agg = df_cs.groupby(['Month', 'CTAS'])['ED_Visits'].sum().reset_index()
            cs_agg['CTAS'] = cs_agg['CTAS'].astype(str)
            cs_agg = cs_agg.sort_values(by='Month')
            fig_cs = px.line(cs_agg, x='Month', y='ED_Visits', color='CTAS', markers=True, category_orders={"CTAS": ["1", "2", "3", "4", "5"]})
            fig_cs.update_layout(xaxis_title="Month", yaxis_title="Visit Volume", hovermode="x unified")
            st.plotly_chart(fig_cs, width='stretch')
        else:
            st.info("No CTAS data available for the selected site.")


# --- 7. Output Structuring & Raw Data ---
st.markdown("---")
with st.expander("📊 View Raw ED Data Context (Expand)"):
    st.markdown("Underlying operational datasets feeding the above metrics.")
    c_raw_1, c_raw_2 = st.columns(2)
    with c_raw_1:
        st.write("**Active Site Breakdown**")
        st.dataframe(df_site_filtered, width='stretch')
    with c_raw_2:
        st.write("**Active Zone Validation Context**")
        st.dataframe(df_zone_filtered, width='stretch')
