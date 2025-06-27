import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
import cartopy.crs as ccrs
import cartopy.feature as cfeature

st.set_page_config(layout="wide")

# Title and logo
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image("logo.png", width=300)
with col_title:
    st.title("☀️ Helideck Solar Collector Analysis")

# Sidebar inputs
st.sidebar.header("Input Parameters")
helideck_area = st.sidebar.slider("Helideck Area (m²)", 10, 100, 50)
collector_efficiency = st.sidebar.slider("Collector Efficiency (%)", 10, 100, 60) / 100
pool_temp = st.sidebar.slider("Desired Pool Temp (°C)", 20, 35, 28)
pool_area = st.sidebar.slider("Pool Area (m²)", 10, 100, 50)
pool_depth = st.sidebar.slider("Pool Depth (m)", 0.5, 3.0, 1.5)
wind_day = st.sidebar.slider("Day Wind Speed (m/s)", 0.0, 10.0, 3.0)
wind_night = st.sidebar.slider("Night Wind Speed (m/s)", 0.0, 10.0, 1.0)
night_hours = st.sidebar.slider("Night Cover Hours", 0, 24, 10)

month = st.sidebar.selectbox("Select Month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])

show_large = st.sidebar.checkbox("Show large savings map only")

# Load data
@st.cache_data
def load_data():
    return pd.read_csv("climate_data_sea.csv")

df = load_data()
lat = df["lat"].values
lon = df["lon"].values

# Interpolation grid
lon_grid = np.linspace(min(lon), max(lon), 200)
lat_grid = np.linspace(min(lat), max(lat), 150)
lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)

# Loss factors
seconds_per_hour = 3600
pool_volume = pool_area * pool_depth
hours_day = 24 - night_hours

day_loss = (2.8 + 3.0 * wind_day) + 5.0 + 25
night_loss = (2.8 + 3.0 * wind_night) + 5.0 + 5

# Single-month visualizations
value_column = f"ghi_{month}"
tmin = df[f"tmin_{month}"].values
tmax = df[f"tmax_{month}"].values
tavg = df.get(f"tavg_{month}", (tmin + tmax) / 2).values

T_day = (tavg + tmax) / 2
T_night = (tavg + tmin) / 2

ghi = df[value_column].values

Q_day = (day_loss * np.clip(pool_temp - T_day, 0, None) * pool_area * hours_day * seconds_per_hour) / 3600000
Q_night = (night_loss * np.clip(pool_temp - T_night, 0, None) * pool_area * night_hours * seconds_per_hour) / 3600000
total_loss = Q_day + Q_night

helideck_gain = ghi * helideck_area * collector_efficiency
pool_solar_gain = ghi * pool_area * 0.85
net_pool_heating = np.clip(total_loss - pool_solar_gain, 0, None)
net_saving = np.minimum(helideck_gain, net_pool_heating)

# Plotting function
def plot_map(data, title, cmap, vmin=None, vmax=None, large=False):
    figsize = (12, 7) if large else (8, 5)
    grid = griddata((lon, lat), data, (lon_mesh, lat_mesh), method='linear')
    fig, ax = plt.subplots(figsize=figsize, subplot_kw={'projection': ccrs.PlateCarree()})
    cf = ax.contourf(lon_mesh, lat_mesh, grid, levels=100, cmap=cmap, vmin=vmin, vmax=vmax)
    cs = ax.contour(lon_mesh, lat_mesh, grid, levels=10, colors='black', linewidths=0.3)
    ax.clabel(cs, inline=True, fontsize=8, fmt="%.0f")
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.set_title(title, fontsize=14 if large else 12)
    fig.colorbar(cf, ax=ax, orientation='vertical', shrink=0.7, label=title)
    return fig

if show_large:
    st.pyplot(plot_map(net_saving, "Daily Saving (kWh)", "YlGnBu", large=True))
else:
    col1, col2 = st.columns(2)
    with col1:
        st.pyplot(plot_map(net_saving, "Daily Saving (kWh)", "YlGnBu"))
        st.pyplot(plot_map(ghi, "GHI (kWh/m²/day)", "Oranges"))
    with col2:
        st.pyplot(plot_map(net_pool_heating, f"Energy Required (kWh) @ {pool_temp}°C", "Reds"))
        st.pyplot(plot_map(T_day, "Daytime Temperature (°C)", "coolwarm"))
