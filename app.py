from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Bengaluru EV registrations", layout="wide")

CHART_CATS = ["Electric (BOV)", "Pure EV", "Strong Hybrid EV", "Petrol Hybrid (incl. E20)"]
TABLE_ONLY = "Diesel Hybrid"  # small numbers: shown in the table, left out of every chart
PAL_LIGHT = {"Electric (BOV)": "#2F5D9B", "Pure EV": "#0E9F7E",
             "Strong Hybrid EV": "#E3A21A", "Petrol Hybrid (incl. E20)": "#8E5BB5"}
PAL_DARK = {"Electric (BOV)": "#6C9BE0", "Pure EV": "#2FD1A8",
            "Strong Hybrid EV": "#F2BC4B", "Petrol Hybrid (incl. E20)": "#B58BDD"}
IST = timezone(timedelta(hours=5, minutes=30))

DARK_CSS = """<style>
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {background-color:#0E1512 !important;}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {background-color:#16211C !important;}
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label, .stApp li,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] *, [data-testid="stCaptionContainer"] *,
[data-testid="stWidgetLabel"] *, [data-testid="stMarkdownContainer"] *, [data-testid="stToolbar"] *,
[data-testid="stRadio"] label *, [data-testid="stCheckbox"] label *, [data-testid="stToggle"] label *,
[data-testid="stSlider"] * {color:#E7F0EC !important;}
[data-baseweb="select"] > div, [data-baseweb="input"] > div {background-color:#1F2D27 !important; border-color:#33453D !important;}
[data-baseweb="select"] *, [data-baseweb="popover"] li {color:#E7F0EC !important;}
[data-baseweb="popover"], [data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="menu"] {background-color:#1F2D27 !important;}
[data-baseweb="popover"] li:hover {background-color:#2B3D35 !important;}
hr {border-color:#33453D !important;}
</style>"""


@st.cache_data(ttl=3600)  # re-read the files at most once an hour
def load():
    df = pd.read_csv("data/ev_data.csv")
    df["rto_location"] = df["rto_location"].str.strip()
    return df


@st.cache_data(ttl=3600)
def load_updated():
    try:
        return date.fromisoformat(Path("data/last_updated.txt").read_text().strip())
    except Exception:
        return None


df = load()
updated = load_updated()

# The newest year is "in progress" if the data was refreshed during that year.
this_year = (updated or datetime.now(IST).date()).year
all_years = sorted(int(y) for y in df["year"].unique())
partial_year = all_years[-1] if all_years[-1] >= this_year else None

st.title("Bengaluru EV registrations")
st.caption("Source: Vahan dashboard, Ministry of Road Transport and Highways.")
st.caption(f"Last updated: {updated:%d %b %Y}" if updated else "Last updated: not available")
st.caption("Note: Vehicle categories follow VAHAN fuel-type classifications. Electric (BOV) and Pure EV represent "
           "fully electric vehicles; Strong Hybrid EV and Petrol Hybrid (incl. E20) represent hybrid vehicles. "
           "Diesel Hybrid vehicles are excluded due to low numbers."
           + (f" {partial_year} data is year-to-date (YTD)." if partial_year else ""))

# ------------------------------------------------------------------ Sidebar
sb = st.sidebar
sb.header("Filters")
rtos = sorted(df["rto_location"].unique())
chosen = sb.multiselect("RTO", rtos, default=rtos)
cats_all = [c for c in CHART_CATS if c in set(df["vehicle_category"])]
cats_sel = sb.multiselect("Fuel category", cats_all, default=cats_all)
cats_sel = [c for c in CHART_CATS if c in cats_sel]
include_partial = True
if partial_year is not None:
    include_partial = sb.checkbox(f"Include {partial_year} (year to date)", value=True)
avail = [y for y in all_years if include_partial or y != partial_year]
if len(avail) > 1:
    lo, hi = sb.select_slider("Years", options=avail, value=(avail[0], avail[-1]))
else:
    lo = hi = avail[0]
dark = sb.toggle("Dark mode", value=False)
sb.caption("These filters apply to every chart on the page.")

# Colours for the chosen mode
TXT = "#E7F0EC" if dark else "#12201B"
GRID = "#33453D" if dark else "#D6E0DB"
BG = "#0E1512" if dark else "#FFFFFF"
PAL = PAL_DARK if dark else PAL_LIGHT
if dark:
    st.markdown(DARK_CSS, unsafe_allow_html=True)


def style(fig, height=420):
    """Shared look: legend and axis text at 17 pt, theme-aware colours."""
    fig.update_layout(
        template="plotly_dark" if dark else "plotly_white",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=height, margin=dict(t=20, b=10, l=10, r=10),
        font=dict(size=14, color=TXT), hoverlabel=dict(font_size=14),
        legend=dict(title_text="", orientation="h", yanchor="top", y=-0.15,
                    font=dict(size=17, color=TXT), itemsizing="constant", itemwidth=60),
    )
    fig.update_xaxes(tickfont=dict(size=17, color=TXT), title_font=dict(size=17, color=TXT),
                     gridcolor=GRID, automargin=True)
    fig.update_yaxes(tickfont=dict(size=17, color=TXT), title_font=dict(size=17, color=TXT),
                     gridcolor=GRID, automargin=True)
    return fig


def show(fig):
    st.plotly_chart(fig, use_container_width=True, theme=None)


d = df[df["rto_location"].isin(chosen) & df["vehicle_category"].isin(cats_sel) & df["year"].between(lo, hi)]
if d.empty:
    st.warning("Nothing to show. Select at least one RTO and one fuel category.")
    st.stop()

years = sorted(int(y) for y in d["year"].unique())
latest = years[-1]
partial = partial_year is not None and latest == partial_year


def label(y):
    return f"{y} (YTD)" if partial and y == latest else str(y)


year_labels = [label(y) for y in years]
cat_year = d.groupby(["year", "vehicle_category"], as_index=False)["registrations"].sum()
cat_year["Year"] = cat_year["year"].map(label)

# Headline numbers
c1, c2 = st.columns(2)
c1.metric(f"Registrations in {latest}" + (" (year to date)" if partial else ""),
          f"{int(d.loc[d['year'] == latest, 'registrations'].sum()):,}")
c2.metric("Total Registrations for years selected", f"{int(d['registrations'].sum()):,}")

# ---------------------------------------------------------------- 1. Trend
st.subheader("Registration trend")
metric = st.radio("Metric", ["Registrations", "Cumulative registrations"], horizontal=True, key="trend_metric")
tbl_cats = cats_sel + [TABLE_ONLY]
d_tbl = df[df["rto_location"].isin(chosen) & df["vehicle_category"].isin(tbl_cats) & df["year"].between(lo, hi)]
wide_t = (d_tbl.pivot_table(index="year", columns="vehicle_category", values="registrations", aggfunc="sum")
          .reindex(index=years, columns=tbl_cats).fillna(0))
if metric == "Cumulative registrations":
    wide_t = wide_t.cumsum()
wide = wide_t[cats_sel]
long = wide.reset_index().melt(id_vars="year", var_name="vehicle_category", value_name="value")
long["Year"] = long["year"].map(label)

chart_col, table_col = st.columns(2)
with chart_col:
    fig = px.line(long, x="Year", y="value", color="vehicle_category", markers=True,
                  color_discrete_map=PAL, category_orders={"vehicle_category": cats_sel, "Year": year_labels})
    fig.update_traces(line=dict(width=3), marker=dict(size=9),
                      hovertemplate="%{fullData.name}<br>%{x}: %{y:,.0f}<extra></extra>")
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title=metric, tickformat=",d")
    show(style(fig, height=460))
with table_col:
    cols = [[f"{v:,.0f}" for v in wide_t[c]] for c in tbl_cats]
    head_bg, cell_bg = ("#1F2D27", "#16211C") if dark else ("#E4ECE8", "#FFFFFF")
    tfig = go.Figure(go.Table(
        columnwidth=[2.8] + [1.2] * len(years),
        header=dict(values=["Category"] + year_labels, fill_color=head_bg, line_color=GRID,
                    font=dict(color=TXT, size=14), align=["left"] + ["right"] * len(years)),
        cells=dict(values=[tbl_cats] + cols, fill_color=cell_bg, line_color=GRID, height=32,
                   font=dict(color=TXT, size=14), align=["left"] + ["right"] * len(years))))
    tfig.update_layout(height=60 + 32 * (len(tbl_cats) + 1), margin=dict(t=10, b=0, l=0, r=0),
                       paper_bgcolor="rgba(0,0,0,0)")
    show(tfig)
    st.caption("Exact figures behind the chart. Diesel Hybrid appears here only.")
if partial:
    st.caption(f"YTD = year to date. {latest} is still in progress.")

# ------------------------------------------------------------------ 2. RTOs
st.subheader("EV Registrations by RTO Jurisdiction")
v1, v2 = st.columns(2)
mode = v1.radio("View", ["Total registrations", "Category share (%)"], horizontal=True, key="rto_mode")
opts = ["All years"] + year_labels
pick_year = v2.selectbox("Year", opts, key="rto_year")
d_rto = d if pick_year == "All years" else d[d["year"] == years[opts.index(pick_year) - 1]]
rto = d_rto.groupby(["rto_location", "vehicle_category"], as_index=False)["registrations"].sum()
rto["total"] = rto.groupby("rto_location")["registrations"].transform("sum")
rto["share"] = (rto["registrations"] / rto["total"].where(rto["total"] > 0) * 100).fillna(0)
order = rto.groupby("rto_location")["registrations"].sum().sort_values(ascending=False).index.tolist()
xcol = "registrations" if mode == "Total registrations" else "share"
fig = px.bar(rto, y="rto_location", x=xcol, color="vehicle_category", orientation="h",
             color_discrete_map=PAL, custom_data=["registrations", "share", "total"],
             category_orders={"rto_location": order, "vehicle_category": cats_sel})
fig.update_traces(hovertemplate=(
    "<b>%{y}</b><br>%{fullData.name}<br>Registrations: %{customdata[0]:,}"
    "<br>Share of this RTO: %{customdata[1]:.1f}%<br>RTO total: %{customdata[2]:,}<extra></extra>"))
fig.update_yaxes(autorange="reversed", title=None)  # largest RTO at the top
if mode == "Total registrations":
    fig.update_xaxes(title="Registrations" + ("" if pick_year != "All years" else ", all years in range"), tickformat=",d")
else:
    fig.update_xaxes(title="Share of the RTO's registrations", range=[0, 100], ticksuffix="%")
show(style(fig, height=520))
st.caption("RTOs are ordered by total registrations for the period shown, highest first.")

# ------------------------------------------------------------ 3 and 4
left, right = st.columns(2)
with left:
    st.subheader("Total EV registrations by year")
    totals = cat_year.groupby("Year", sort=False)["registrations"].sum().reindex(year_labels)
    fig = px.bar(cat_year, x="Year", y="registrations", color="vehicle_category",
                 color_discrete_map=PAL, category_orders={"vehicle_category": cats_sel, "Year": year_labels})
    fig.update_traces(hovertemplate="%{fullData.name}<br>%{x}: %{y:,.0f}<extra></extra>", selector=dict(type="bar"))
    fig.add_trace(go.Scatter(x=totals.index, y=totals.values, mode="text",
                             text=[f"<b>{v:,.0f}</b>" for v in totals.values],
                             textposition="top center", textfont=dict(size=15, color=TXT),
                             showlegend=False, hoverinfo="skip"))
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title="Registrations", tickformat=",d", range=[0, float(totals.max()) * 1.15])
    show(style(fig))
with right:
    head, pick = st.columns([5, 3])
    head.subheader("EV Category share by Year")
    year = pick.selectbox("Year", years, index=len(years) - 1, label_visibility="collapsed",
                          format_func=lambda y: f"{y} (year to date)" if partial and y == latest else str(y))
    mix = cat_year[cat_year["year"] == year]
    fig = px.pie(mix, names="vehicle_category", values="registrations", hole=0.5,
                 color="vehicle_category", color_discrete_map=PAL,
                 category_orders={"vehicle_category": cats_sel})
    fig.update_traces(sort=False, textinfo="percent", textfont_size=16, marker=dict(line=dict(color=BG, width=2)),
                      hovertemplate="%{label}<br>Registrations: %{value:,}<br>Share: %{percent}<extra></extra>")
    show(style(fig))

# -------------------------------------------------------------------- Notes
st.divider()
st.caption("**Fuel types with low or no registrations are not included:** diesel hybrid (shown in the table only), "
           "plug-in hybrid EV, petrol/CNG hybrid combinations, and hydrogen / fuel cell.")
st.caption("**Petrol Hybrid (incl. E20)** adds together Vahan's Petrol/Hybrid and Petrol(E20)/Hybrid labels, "
           "because vehicles moved from one label to the other over time.")
