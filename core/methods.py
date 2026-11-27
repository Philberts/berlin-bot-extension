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
    if col not in gdf.columns:
        return []
    values = _split_values(gdf[col]).explode().dropna()
    return values.value_counts().head(n).index.tolist()


def filter_category(gdf, col, category):
    """Keeps objects that have <category> among their values (cuisine=italian;pizza counts for both)"""
    if category == "All" or col not in gdf.columns:
        return gdf
    return gdf[_split_values(gdf[col]).apply(lambda values: category in values)]


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
    n = len(gdf_points)

    def share(k, total):
        return "{} of {} ({:.1f} %)".format(k, total, 100 * k / total) if total else "no data"

    rows = [("Number of objects", str(n)),
            ("Objects without name", share(int(gdf_points["name"].isna().sum()), n))]
    if subcat and subcat in gdf_points.columns:
        rows.append(("Objects without " + subcat, share(int(gdf_points[subcat].isna().sum()), n)))

    # near-duplicates: pairs with the same name within the threshold (metres -> metric CRS)
    named = gdf_points.loc[gdf_points["name"].notna(), ["name", "geometry"]].to_crs(CFG["crs_metric"])
    pairs = gpd.sjoin(named, named, predicate="dwithin", distance=CFG["dup_distance_m"])
    pairs = pairs[(pairs.index < pairs["index_right"])           # every pair once, no self matches
                  & (pairs["name_left"] == pairs["name_right"])]
    rows.append(("Near-duplicates (pairs with same name, within {} m)".format(CFG["dup_distance_m"]),
                 str(len(pairs))))

    rows.append(("Points outside all PLZ areas", str(int(gdf_points["PLZ"].isna().sum()))))
    plausible = (gdf_points.geometry.y.between(*CFG["berlin_lat"])
                 & gdf_points.geometry.x.between(*CFG["berlin_lon"]))
    rows.append(("Implausible coordinates", str(int((~plausible).sum()))))

    # addr:postcode (text) against the PLZ of the spatial join (number); only comparable if both exist
    has_pc = gdf_points["addr:postcode"].notna()
    rows.append(("Objects with addr:postcode", share(int(has_pc.sum()), n)))
    both = gdf_points[has_pc & gdf_points["PLZ"].notna()]
    same = pd.to_numeric(both["addr:postcode"], errors="coerce") == both["PLZ"]
    rows.append(("addr:postcode equals PLZ of spatial join", share(int(same.sum()), len(both))))

    empty = ~gdf_areas["PLZ"].isin(gdf_points["PLZ"])
    rows.append(("PLZ areas without any object", share(int(empty.sum()), len(gdf_areas))))
    return pd.DataFrame(rows, columns=["Check", "Result"])


# =============================================================================
# 5) Map
# =============================================================================
def make_map(gdf_points, gdf_agg, maptype, key="PLZ", colors=("yellow", "red"), caption="Value"):
    """Folium map: choropleth (areas), heatmap or marker clusters (single points)"""
    m = folium.Map(location=[52.52, 13.40], zoom_start=10, tiles="OpenStreetMap")

    if maptype == "Choropleth":
        values = gdf_agg["value"].dropna()
        vmin, vmax = (values.min(), values.max()) if len(values) else (0, 1)
        if vmin == vmax:                                         # a colour scale needs a range
            vmax = vmin + 1
        cmap = LinearColormap(list(colors), vmin=vmin, vmax=vmax, caption=caption)

        def style(feature):
            v = feature["properties"]["value"]                   # NaN becomes None (null) in GeoJSON
            return {"fillColor": "grey" if v is None else cmap(v),
                    "fillOpacity": 0.65, "color": "black", "weight": 0.7}

        shown = gdf_agg[[key, "count", "value", "geometry"]].copy()
        shown["label"] = shown["value"].apply(lambda v: "no value" if pd.isna(v) else "{:,.2f}".format(v))
        folium.GeoJson(shown.to_json(), style_function=style,
                       tooltip=folium.GeoJsonTooltip(fields=[key, "count", "label"],
                                                     aliases=[key, "Objects", caption])).add_to(m)
        cmap.add_to(m)
    elif maptype == "Heatmap":
        coords = np.column_stack([gdf_points.geometry.y, gdf_points.geometry.x])   # [lat, lon]
        HeatMap(coords.tolist(), radius=12, blur=15).add_to(m)
    else:   # Point map (clusters)
        cluster = MarkerCluster().add_to(m)
        for lat, lon, name in zip(gdf_points.geometry.y, gdf_points.geometry.x, gdf_points["name"]):
            label = "(no name)" if pd.isna(name) else html.escape(str(name))    # tooltips render HTML
            folium.Marker([lat, lon], tooltip=label).add_to(cluster)
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
    visible = [k for k, v in pdict["sources"].items() if v.get("show", True)]
    src = st.sidebar.selectbox("Data source", visible)
    cfg = pdict["sources"][src]
    if not os.path.exists("datasets/" + cfg["file"]):
        st.error("File datasets/" + cfg["file"] + " not found. Run:  python download_osm.py \"" + src + "\"")
        return
    pts, plz, dis, quality = prepare_source(src, pdict)

    # ---- Menu 2: category filter (depends on menu 1) ------------------------
    options = ["All"] + category_options(pts, cfg["subcat"], pdict["top_n_category"])
    cat = st.sidebar.selectbox("Category filter (" + cfg["subcat"] + ")", options, key="cat_" + src)

    # ---- Menus 3-5 ----------------------------------------------------------
    area_label = st.sidebar.selectbox("Area unit", list(pdict["areas"].keys()))
    ind        = st.sidebar.selectbox("Indicator", pdict["indicators"])
    mtype      = st.sidebar.selectbox("Map type", pdict["maptypes"])
    colors     = list(pdict["colorscales"].values())[0]
    if mtype == "Choropleth":
        colors = pdict["colorscales"][st.sidebar.selectbox("Colour scale", list(pdict["colorscales"].keys()))]

    # ---- Filter and aggregation ---------------------------------------------
    key   = pdict["areas"][area_label]
    areas = plz if key == "PLZ" else dis
    pts_f = filter_category(pts, cfg["subcat"], cat)
    if pts_f.empty:
        st.warning("No objects for this selection.")
        return
    residents = residents_by_area(df_residents, plz, dis, key)
    agg       = aggregate(pts_f, areas, key, ind, residents)

    # ---- Key figures --------------------------------------------------------
    ranking = agg.dropna(subset=["value"]).sort_values("value", ascending=False)
    c1, c2, c3 = st.columns(3)
    c1.metric("Objects shown", len(pts_f))
    c2.metric("Areas without any object", "{} of {}".format(int((agg["count"] == 0).sum()), len(agg)))
    if len(ranking):
        c3.metric("Highest value: " + ind,
                  "{} ({:,.2f})".format(ranking.iloc[0][key], ranking.iloc[0]["value"]))

    # ---- Map ----------------------------------------------------------------
    m = make_map(pts_f, agg, mtype, key, colors, ind)
    st_folium(m, width=1000, height=600, returned_objects=[])
    st.caption("© OpenStreetMap contributors (ODbL) · downloaded: " + _download_date(pdict, src))

    # ---- Table and quality --------------------------------------------------
    table = agg[[key, "count", "area_km2", "Einwohner", "value"]].sort_values("value", ascending=False)
    with st.expander("Top 3 areas and data table"):
        st.write("Top 3 areas: " + ", ".join("{} ({:,.2f})".format(r[key], r["value"])
                                             for _, r in ranking.head(3).iterrows()))
        st.dataframe(table, hide_index=True, column_config={key: st.column_config.Column(), **{
            c: st.column_config.NumberColumn(format="%.2f") for c in ("area_km2", "value")}})
        st.download_button("Download table (CSV)", table.to_csv(index=False, sep=";").encode("utf-8"),
                           file_name="osm_{}_{}.csv".format(src.lower().replace(" ", "_"), key),
                           mime="text/csv")
    with st.expander("Data quality"):
        st.dataframe(quality, hide_index=True)

    # ---- Chat assistant (LLM) - provided, see core/chat.py -------------------
    # Needs the variables src, cat, area_label, ind, mtype, key, pts_f, agg, quality from your code above.
    ctx = chat.build_context(src, cat, area_label, ind, mtype, key, pts_f, agg, quality)
    chat.render_chat(ctx, pdict)
