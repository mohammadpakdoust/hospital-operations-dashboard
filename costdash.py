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
st.set_page_config(page_title="Hospital Operations Dashboard", page_icon="🏥", layout="wide")

st.title("🏥 Hospital Operations Dashboard")
st.markdown("""
Welcome to the **Hospital Operations Dashboard**. This application provides insights into 
hospital utilization, patient flow, and geographic distribution across Nova Scotia.
""")
st.markdown("---")


# --- 2. Data Loading & Cleaning ---
@st.cache_data
def load_data():
    try:
        data_path = get_data_file('Data.xlsx')
        # The true headers for 'Hospital Attributes' start on the second row (header=1)
        df_hosp = pd.read_excel(data_path, sheet_name='Hospital Attributes', header=1)
        df_stats = pd.read_excel(data_path, sheet_name='Inpatient Stats')
        
        # Clean hospital attributes to remove any empty tracking rows
        df_hosp = df_hosp.dropna(subset=['Hospital'])
        
        # Ensure Date is recognized as datetime for time-series parsing
        df_stats['Date'] = pd.to_datetime(df_stats['Date'])
        
        # We need trends aggregated by hospital and month. Formatting it nicely for axes.
        df_stats['Month_Year'] = df_stats['Date'].dt.to_period('M').astype(str)
        
        return df_hosp, df_stats
    except Exception as e:
        st.error(f"Error loading the data file: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_hosp, df_stats = load_data()


# --- 3. Sidebar Filters ---
st.sidebar.header("Filter Options")

show_occ_perc = st.sidebar.checkbox("Show Occupancy as Percentage (%)", value=False)

# Generate the list of hospitals securely to avoid Streamlit state bugs dropping options
if not df_hosp.empty:
    # Build list cleanly
    hospital_choices = sorted(df_hosp['Hospital'].dropna().unique().tolist())
    all_hospitals = ["All"] + hospital_choices
    
    selected_hospital = st.sidebar.selectbox(
        "Select Hospital", 
        options=all_hospitals,
        index=all_hospitals.index("All") if "All" in all_hospitals else 0
    )
else:
    selected_hospital = "All"

# --- 4. Filtering Data ---
if selected_hospital != "All":
    filtered_hosp = df_hosp[df_hosp['Hospital'] == selected_hospital].copy()
    filtered_stats = df_stats[df_stats['Hospital'] == selected_hospital].copy()
else:
    filtered_hosp = df_hosp.copy()
    filtered_stats = df_stats.copy()


# --- 5. Requirement 1 & 2: Map with Hover Attributes ---
st.subheader("📍 Hospital Locations & Attributes")

if not filtered_hosp.empty:
    # --- Calculate Current Beds Used & Occupancy ---
    if not filtered_stats.empty:
        # Sum total net flow across all recorded months for each hospital
        stats_agg = filtered_stats.groupby(['Hospital', 'Activity'])['Count'].sum().unstack(fill_value=0).reset_index()
        if 'Admissions' not in stats_agg.columns: stats_agg['Admissions'] = 0
        if 'Discharge' not in stats_agg.columns: stats_agg['Discharge'] = 0
        stats_agg['Total Net Flow'] = stats_agg['Admissions'] - stats_agg['Discharge']
        
        # Merge the cumulative net flow to our static hospital traits
        filtered_hosp = filtered_hosp.merge(stats_agg[['Hospital', 'Total Net Flow']], on='Hospital', how='left')
        filtered_hosp['Total Net Flow'] = filtered_hosp['Total Net Flow'].fillna(0)
        
        # Update baseline to present logic
        filtered_hosp['Beds_In_Use_Current'] = filtered_hosp['Beds_In_Use'] + filtered_hosp['Total Net Flow']
        filtered_hosp['Occupancy_Current'] = filtered_hosp['Beds_In_Use_Current'] / filtered_hosp['Beds']
    else:
        # Fallback to the static baseline if time-series isn't available
        filtered_hosp['Beds_In_Use_Current'] = filtered_hosp['Beds_In_Use']
        filtered_hosp['Occupancy_Current'] = filtered_hosp['Occupancy']

    # Set up custom data for hover
    hover_cols = ["Hospital", "Beds", "Beds_In_Use_Current", "Occupancy_Current", "RN_Nurses", "LPN_Nurses", "Admin_Staff"]
    has_postal = False
    if "Postal Code" in filtered_hosp.columns:
        hover_cols.append("Postal Code")
        has_postal = True
    elif "Postal_Code" in filtered_hosp.columns:
        hover_cols.append("Postal_Code")
        has_postal = True

    # Use color for differentiation, NOT size
    fig_map = px.scatter_mapbox(
        filtered_hosp, 
        lat="Latitude", 
        lon="Longitude", 
        color="Hospital",          # Distinct colors per hospital
        size="Beds_In_Use_Current", # Size markers by current occupied beds
        size_max=35,                # Cap maximum size so large hospitals don't overlap too much
        custom_data=hover_cols,
        zoom=5.5, 
        center={"lat": 45.0, "lon": -63.5},
        mapbox_style="open-street-map",
        title="Nova Scotia Hospitals Map"
    )
    
    # Construct a clean, structured hover tooltip with visual hierarchy
    hovertemplate = (
        "<span style='font-size: 16px;'><b>🏥 %{customdata[0]}</b></span><br><br>"
        "🛏 Total Beds: %{customdata[1]}<br>"
        "📊 Current Beds Used: %{customdata[2]}<br>"
        "📈 Current Occupancy: %{customdata[3]:.0%}<br><br>"
        "<b>👥 Staffing Metrics:</b><br>"
        "• RN: %{customdata[4]}<br>"
        "• LPN: %{customdata[5]}<br>"
        "• Admin: %{customdata[6]}<br>"
    )
    if has_postal:
        hovertemplate += "Postal Code: %{customdata[7]}<br>"
    hovertemplate += "<extra></extra>"  # Hide extra trace info
    
    fig_map.update_traces(
        hovertemplate=hovertemplate,
        marker=dict(opacity=0.8)  # Let plotly handles sizes dynamically via size mapping
    )
    
    fig_map.update_layout(
        margin={"r":0, "t":40, "l":0, "b":0},
        title_font_size=18,
        title_x=0.01,
        legend_title_text="Hospitals"
    )
    
    st.plotly_chart(fig_map, width='stretch', config={'scrollZoom': True})
    
    # Glossary for Staff Acronyms
    st.caption("**Glossary:** **RN**: Registered Nurses | **LPN**: Licensed Practical Nurses | **Admin**: Administrative Staff")
else:
    st.warning("No location data available to display on the map.")


# --- 6. Requirement 3: Trend Activity ---
st.subheader("📈 Trend Activity")

if not filtered_stats.empty:
    # Pivot the data to easily grab 'Admissions' and 'Discharge' as distinct columns per month
    df_pivot = filtered_stats.pivot_table(
        index=['Hospital', 'Month_Year'], 
        columns='Activity', 
        values='Count', 
        aggfunc='sum'
    ).reset_index()
    
    # Fill any missing activities with 0 just in case one hospital lacked discharges or admissions
    if 'Admissions' not in df_pivot:
        df_pivot['Admissions'] = 0
    if 'Discharge' not in df_pivot:
        df_pivot['Discharge'] = 0
        
    # User-defined formula: Net Flow = Admissions - Discharges
    df_pivot['Net Flow'] = df_pivot['Admissions'] - df_pivot['Discharge']
    
    # Explicitly sort the data so charts follow time order sequentially
    df_pivot = df_pivot.sort_values(by=['Hospital', 'Month_Year'])

    # Map baseline beds used to each hospital from the global Hospital Attributes
    baseline_map = df_hosp.set_index('Hospital')['Beds_In_Use'].to_dict()
    
    # For each hospital, calculate cumulative net flow
    df_pivot['Cumulative Net Flow'] = df_pivot.groupby('Hospital')['Net Flow'].cumsum()
    
    # Add baseline to cumulative net flow to derive Occupied Beds
    df_pivot['Baseline Beds'] = df_pivot['Hospital'].map(baseline_map).fillna(0)
    df_pivot['Occupied Beds'] = df_pivot['Baseline Beds'] + df_pivot['Cumulative Net Flow']
    
    # Calculate toggle state conditionally
    total_beds_map = df_hosp.set_index('Hospital')['Beds'].to_dict()
    df_pivot['Total Beds'] = df_pivot['Hospital'].map(total_beds_map).fillna(1)
    
    if show_occ_perc:
        df_pivot['Plot Occupancy'] = (df_pivot['Occupied Beds'] / df_pivot['Total Beds']) * 100
        occ_y_label = 'Occupancy (%)'
    else:
        df_pivot['Plot Occupancy'] = df_pivot['Occupied Beds']
        occ_y_label = 'Occupied Beds'

    st.markdown("##### Admissions Over Time")
    st.markdown("Visualizing the total number of admissions aggregating by month.")
    
    # Pre-sort hospitals descending by overall magnitude so hover tooltip orders elegantly
    order_in = df_pivot.groupby('Hospital')['Admissions'].sum().sort_values(ascending=False).index.tolist()

    # admissions chart
    fig_in = px.line(
        df_pivot,
        x='Month_Year',
        y='Admissions',
        color='Hospital',
        markers=True,
        category_orders={'Hospital': order_in},
        labels={'Month_Year': 'Month', 'Admissions': 'Admissions'},
        color_discrete_sequence=px.colors.qualitative.Plotly
    )
    # clean visual
    fig_in.update_layout(xaxis_title="Month", yaxis_title="Total Admissions", hovermode="x unified")
    st.plotly_chart(fig_in, width='stretch')
    
    st.markdown("##### Hospital Occupancy Over Time")
    st.markdown("Evaluating occupied beds algorithmically derived from historical baseline tracking plus rolling net flow.")
    
    # Pre-sort hospitals descending by overall occupancy so hover aligns correctly
    order_occ = df_pivot.groupby('Hospital')['Plot Occupancy'].mean().sort_values(ascending=False).index.tolist()

    # Occupancy chart
    fig_occ = px.line(
        df_pivot,
        x='Month_Year',
        y='Plot Occupancy',
        color='Hospital',
        markers=True,
        category_orders={'Hospital': order_occ},
        labels={'Month_Year': 'Month', 'Plot Occupancy': occ_y_label},
        color_discrete_sequence=px.colors.qualitative.Plotly
    )
    fig_occ.update_layout(xaxis_title="Month", yaxis_title=occ_y_label, hovermode="x unified")
    st.plotly_chart(fig_occ, width='stretch')

else:
    st.warning("No inpatient time-series data available for the selected hospital.")


# --- 7. Formatting & Raw Data ---
st.markdown("---")

with st.expander("📊 View Raw Data (Expand)"):
    st.write("### Underlying Data used for mapping & hospital traits:")
    st.dataframe(filtered_hosp, width='stretch')
    
    st.write("### Underlying Inpatient Statistics Data:")
    st.dataframe(filtered_stats, width='stretch')