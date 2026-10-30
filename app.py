from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Bengaluru EV registrations", layout="wide")

CATS = ["Electric (BOV)", "Pure EV", "Strong Hybrid EV", "Petrol Hybrid (incl. E20)"]
COLORS = {"Electric (BOV)": "#2F5D9B", "Pure EV": "#0E9F7E",
          "Strong Hybrid EV": "#E3A21A", "Petrol Hybrid (incl. E20)": "#8E5BB5"}
IST = timezone(timedelta(hours=5, minutes=30))


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


def style(fig, height=420):
    """Shared look: legend and axis text at 17 pt, bigger hover text."""
    fig.update_layout(
        height=height,
        margin=dict(t=20, b=10, l=10, r=10),
        font=dict(size=14),
        hoverlabel=dict(font_size=14),
        legend=dict(title_text="", orientation="h", yanchor="top", y=-0.15,
                    font=dict(size=17), itemsizing="constant", itemwidth=60),
    )
    fig.update_xaxes(tickfont=dict(size=17), title_font=dict(size=17), automargin=True)
    fig.update_yaxes(tickfont=dict(size=17), title_font=dict(size=17), automargin=True)
    return fig


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
cats_all = [c for c in CATS if c in set(df["vehicle_category"])]
cats_sel = sb.multiselect("Fuel category", cats_all, default=cats_all)
cats_sel = [c for c in CATS if c in cats_sel]
include_partial = True
if partial_year is not None:
    include_partial = sb.checkbox(f"Include {partial_year} (year to date)", value=True)
avail = [y for y in all_years if include_partial or y != partial_year]
if len(avail) > 1:
    lo, hi = sb.select_slider("Years", options=avail, value=(avail[0], avail[-1]))
else:
    lo = hi = avail[0]
sb.caption("These filters apply to every chart on the page.")

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
wide = (cat_year.pivot(index="year", columns="vehicle_category", values="registrations")
        .reindex(index=years, columns=cats_sel).fillna(0))
if metric == "Cumulative registrations":
    wide = wide.cumsum()
long = wide.reset_index().melt(id_vars="year", var_name="vehicle_category", value_name="value")
long["Year"] = long["year"].map(label)

chart_col, table_col = st.columns(2)
with chart_col:
    fig = px.line(long, x="Year", y="value", color="vehicle_category", markers=True,
                  color_discrete_map=COLORS, category_orders={"vehicle_category": cats_sel, "Year": year_labels})
    fig.update_traces(line=dict(width=3), marker=dict(size=9),
                      hovertemplate="%{fullData.name}<br>%{x}: %{y:,.0f}<extra></extra>")
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title=metric, tickformat=",d")
    st.plotly_chart(style(fig, height=460), use_container_width=True)
with table_col:
    tbl = wide.T  # one row per category, one column per year
    tbl.columns = year_labels
    tbl.index.name = None
    st.dataframe(tbl.style.format("{:,.0f}"), use_container_width=True)
    st.caption("Exact figures behind the chart.")
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
             color_discrete_map=COLORS, custom_data=["registrations", "share", "total"],
             category_orders={"rto_location": order, "vehicle_category": cats_sel})
fig.update_traces(hovertemplate=(
    "<b>%{y}</b><br>%{fullData.name}<br>Registrations: %{customdata[0]:,}"
    "<br>Share of this RTO: %{customdata[1]:.1f}%<br>RTO total: %{customdata[2]:,}<extra></extra>"))
fig.update_yaxes(autorange="reversed", title=None)  # largest RTO at the top
if mode == "Total registrations":
    fig.update_xaxes(title="Registrations" + ("" if pick_year != "All years" else ", all years in range"), tickformat=",d")
else:
    fig.update_xaxes(title="Share of the RTO's registrations", range=[0, 100], ticksuffix="%")
st.plotly_chart(style(fig, height=560), use_container_width=True)
if any("(KA43)" in r or "(KA52)" in r for r in rtos):
    st.caption("Note: KA-43 Devanahalli and KA-52 Nelamangala belong to Bengaluru Rural district, whereas the "
               "remaining 10 RTOs in the dashboard belong to Bengaluru Urban district.")
st.caption("RTOs are ordered by total registrations for the period shown, highest first.")

# ------------------------------------------------------------ 3 and 4
left, right = st.columns(2)
with left:
    st.subheader("Total EV registrations by year")
    totals = cat_year.groupby("Year", sort=False)["registrations"].sum().reindex(year_labels)
    fig = px.bar(cat_year, x="Year", y="registrations", color="vehicle_category",
                 color_discrete_map=COLORS, category_orders={"vehicle_category": cats_sel, "Year": year_labels})
    fig.update_traces(hovertemplate="%{fullData.name}<br>%{x}: %{y:,.0f}<extra></extra>", selector=dict(type="bar"))
    fig.add_trace(go.Scatter(x=totals.index, y=totals.values, mode="text",
                             text=[f"<b>{v:,.0f}</b>" for v in totals.values],
                             textposition="top center", textfont=dict(size=15),
                             showlegend=False, hoverinfo="skip"))
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title="Registrations", tickformat=",d", range=[0, float(totals.max()) * 1.15])
    st.plotly_chart(style(fig), use_container_width=True)
with right:
    head, pick = st.columns([5, 3])
    head.subheader("EV Category share by Year")
    year = pick.selectbox("Year", years, index=len(years) - 1, label_visibility="collapsed",
                          format_func=lambda y: f"{y} (year to date)" if partial and y == latest else str(y))
    mix = cat_year[cat_year["year"] == year]
    fig = px.pie(mix, names="vehicle_category", values="registrations", hole=0.5,
                 color="vehicle_category", color_discrete_map=COLORS,
                 category_orders={"vehicle_category": cats_sel})
    fig.update_traces(sort=False, textinfo="percent", textfont_size=16,
                      hovertemplate="%{label}<br>Registrations: %{value:,}<br>Share: %{percent}<extra></extra>")
    st.plotly_chart(style(fig), use_container_width=True)

# -------------------------------------------------------------------- Notes
st.divider()
st.caption("**Fuel types with low or no registrations are not included:** diesel hybrid, plug-in hybrid EV, "
           "petrol/CNG hybrid combinations, and hydrogen / fuel cell.")
st.caption("**Petrol Hybrid (incl. E20)** adds together Vahan's Petrol/Hybrid and Petrol(E20)/Hybrid labels, "
           "because vehicles moved from one label to the other over time.")
