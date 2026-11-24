import os
import html
import json

import numpy                         as np
import pandas                        as pd
import geopandas                     as gpd
import folium
from folium.plugins                  import HeatMap, MarkerCluster
from branca.colormap                 import LinearColormap
import streamlit                     as st
from streamlit_folium                import st_folium

import core.HelperTools              as ht
import core.chat                     as chat
from config                          import pdict as CFG      # only for CRS and thresholds


# =============================================================================
# 1) Loading
# =============================================================================
@st.cache_data
def load_areas(file, key):
    """Polygons (PLZ or Bezirk) from WKT csv -> GeoDataFrame (one row per area, EPSG:4326)"""
    df  = pd.read_csv("datasets/" + file, sep=";")
    gdf = gpd.GeoDataFrame(df[[key]], geometry=gpd.GeoSeries.from_wkt(df["geometry"]), crs=CFG["crs_geo"])
    return gdf.dissolve(by=key).reset_index()[[key, "geometry"]]


@st.cache_data
def load_osm_points(file):
    """OSM csv (written by download_osm.py) -> GeoDataFrame of Points (EPSG:4326)"""
    df = pd.read_csv("datasets/" + file, sep=";", dtype={"addr:postcode": str})
    df = df.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    # x = longitude, y = latitude
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs=CFG["crs_geo"])


@ht.timer
def preprop_resid(dfr):
    """Preprocessing plz_einwohner.csv: only PLZ and residents, only Berlin range"""
    d = dfr.loc[:, ["plz", "einwohner"]].rename(columns={"plz": "PLZ", "einwohner": "Einwohner"})
    return d[(d["PLZ"] > 10000) & (d["PLZ"] < 14200)].reset_index(drop=True)


# =============================================================================
# 2) Spatial join and category filter
# =============================================================================
def assign_area(gdf_points, gdf_areas, key):
    """Spatial join: adds column <key> (PLZ / Bezirk) to every point. NaN = outside of all areas.
    Points exactly on a border can match twice -> only the first match is kept."""
    joined = gpd.sjoin(gdf_points, gdf_areas[[key, "geometry"]], how="left", predicate="within")
    joined = joined[~joined.index.duplicated(keep="first")]
    return joined.drop(columns="index_right")


def _split_values(series):
    """'italian;pizza' -> ['italian', 'pizza'] (empty list if missing)"""
    return series.fillna("").astype(str).str.split(";").apply(lambda v: [x.strip() for x in v if x.strip()])


def category_options(gdf, col, n=10):
    """The n most frequent values of a (multi-valued) attribute, for the dependent menu"""
    # TODO: use _split_values, explode, value_counts. Return [] if the column does not exist.
    raise NotImplementedError


def filter_category(gdf, col, category):
    """Keeps objects that have <category> among their values (cuisine=italian;pizza counts for both)"""
    # TODO: "All" -> return gdf unchanged
    raise NotImplementedError


# =============================================================================
# 3) Indicators
# =============================================================================
def residents_by_area(df_res, gdf_plz, gdf_dis, key):
    """Residents per PLZ or per Bezirk (columns <key>, Einwohner)."""
    res = gdf_plz.merge(df_res, on="PLZ", how="left")
    if key == "PLZ":
        return res[["PLZ", "Einwohner"]]

    # Approximation: each PLZ counts completely towards the Bezirk that contains (or is closest to) its
    # centroid, although some PLZ areas cross Bezirk borders.
    centres = res[["PLZ", "Einwohner", "geometry"]].to_crs(CFG["crs_metric"])
    centres["geometry"] = centres.geometry.centroid
    joined = gpd.sjoin_nearest(centres, gdf_dis[["Bezirk", "geometry"]].to_crs(CFG["crs_metric"]))
    joined = joined[~joined.index.duplicated(keep="first")]      # same distance to two districts
    return joined.groupby("Bezirk", as_index=False)["Einwohner"].sum()


def aggregate(gdf_points, gdf_areas, key, indicator, residents):
    """One row per area (also areas without objects = 0) with columns count, area_km2, Einwohner, value"""
    counts = gdf_points.groupby(key).size().rename("count").reset_index()     # NaN = outside, not counted
    agg = gdf_areas.merge(counts, on=key, how="left").merge(residents, on=key, how="left")
    agg["count"]    = agg["count"].fillna(0).astype(int)
    agg["area_km2"] = agg.geometry.to_crs(CFG["crs_metric"]).area / 1e6

    if indicator == "Number":
        agg["value"] = agg["count"].astype(float)
    elif indicator == "Number per km2":
        agg["value"] = agg["count"] / agg["area_km2"]
    elif indicator == "Number per 10,000 residents":
        enough = agg["Einwohner"] >= CFG["min_residents"]        # False also if Einwohner is missing
        agg["value"] = (agg["count"] / agg["Einwohner"].where(enough) * 10000)
    else:
        raise ValueError("Unknown indicator: " + str(indicator))
    return agg


# =============================================================================
# 4) Data quality
# =============================================================================
def quality_report(gdf_points, gdf_areas, subcat=None):
    """Automatic checks of one OSM file. Expects column 'PLZ' (from assign_area). Returns DataFrame."""
    # TODO (see Task 5): number of objects, share without name, share without <subcat>,
    #      near-duplicates (same name, closer than CFG["dup_distance_m"] metres - compute in CFG["crs_metric"]),
    #      points outside Berlin (PLZ is NaN), implausible coordinates (CFG["berlin_lat"], CFG["berlin_lon"]),
    #      share of objects with addr:postcode and how often it equals the PLZ of the spatial join,
    #      number of PLZ areas without any object.
    #      Return a DataFrame with the columns "Check" and "Result".
    raise NotImplementedError


# =============================================================================
# 5) Map
# =============================================================================
def make_map(gdf_points, gdf_agg, maptype, key="PLZ", colors=("yellow", "red"), caption="Value"):
    """Folium map: choropleth (areas), heatmap or marker clusters (single points)"""
    m = folium.Map(location=[52.52, 13.40], zoom_start=10, tiles="OpenStreetMap")

    if maptype == "Choropleth":
        # TODO: LinearColormap(colors, vmin, vmax) from the column "value"; areas with value NaN -> grey.
        #       ONE folium.GeoJson layer (gdf_agg.to_json()) with style_function and tooltip. Add the legend.
        pass
    elif maptype == "Heatmap":
        # TODO: HeatMap([[lat, lon], ...])        <- Folium wants [lat, lon]
        pass
    else:   # Point map (clusters)
        # TODO: MarkerCluster with one marker per point, name as tooltip
        pass
    return m


# =============================================================================
# 6) Streamlit app
# =============================================================================
@st.cache_data(show_spinner="Loading data and assigning areas ...")
def prepare_source(label, pdict):
    """Loads one OSM source, assigns PLZ and Bezirk (spatial join) and runs the quality check"""
    cfg = pdict["sources"][label]
    plz = load_areas(pdict["file_plz"], "PLZ")
    dis = load_areas(pdict["file_dis"], "Bezirk")
    pts = load_osm_points(cfg["file"])
    pts = assign_area(pts, plz, "PLZ")
    pts = assign_area(pts, dis, "Bezirk")
    return pts, plz, dis, quality_report(pts, plz, cfg["subcat"])


def _download_date(pdict, label):
    path = "datasets/" + pdict["file_info"]
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f).get(label, "unknown")
    return "unknown"


@ht.timer
def make_streamlit_app(pdict, df_residents):
    """Makes Streamlit App: OSM data of Berlin, controlled by pull-down menus"""
    st.set_page_config(page_title="OpenStreetMap Berlin", layout="wide")
    st.title("OpenStreetMap Berlin: Places and Supply")

    # ---- Menu 1: data source ------------------------------------------------
    src = st.sidebar.selectbox("Data source", list(pdict["sources"].keys()))
    cfg = pdict["sources"][src]
    if not os.path.exists("datasets/" + cfg["file"]):
        st.error("File datasets/" + cfg["file"] + " not found. Run:  python download_osm.py \"" + src + "\"")
        return
    pts, plz, dis, quality = prepare_source(src, pdict)

    # ---- Menu 2: category filter (depends on menu 1) ------------------------
    # TODO: options = ["All"] + category_options(...); use key="cat_" + src so the menu resets with the source
    cat = "All"

    # ---- Menus 3-5 ----------------------------------------------------------
    area_label = st.sidebar.selectbox("Area unit", list(pdict["areas"].keys()))
    ind        = st.sidebar.selectbox("Indicator", pdict["indicators"])
    mtype      = st.sidebar.selectbox("Map type", pdict["maptypes"])
    # optional menu 6: colour scale (only for the choropleth)

    # TODO: key (PLZ / Bezirk) and the matching polygons, filter by category, stop with st.warning if empty,
    #       residents_by_area, aggregate

    # TODO: key figures with st.metric: objects shown, areas without any object, area with the highest value
    # TODO: map with st_folium(m, width=1000, height=600, returned_objects=[])
    # TODO: st.caption with "© OpenStreetMap contributors" and _download_date(pdict, src)
    # TODO: expander "Top 3 areas and data table" with st.dataframe and st.download_button (CSV)
    # TODO: expander "Data quality" showing the quality DataFrame

    # ---- Chat assistant (LLM) - provided, see core/chat.py -------------------
    # Needs the variables src, cat, area_label, ind, mtype, key, pts_f, agg, quality from your code above.
    ctx = chat.build_context(src, cat, area_label, ind, mtype, key, pts_f, agg, quality)
    chat.render_chat(ctx, pdict)
