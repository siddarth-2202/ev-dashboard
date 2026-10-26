from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Bengaluru EV registrations", layout="wide")

CATS = ["Electric (BOV)", "Pure EV", "Strong Hybrid EV"]
COLORS = {"Electric (BOV)": "#2F5D9B", "Pure EV": "#0E9F7E", "Strong Hybrid EV": "#E3A21A"}
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
    """Shared look: bigger legend text and icons, bigger hover text."""
    fig.update_layout(
        height=height,
        margin=dict(t=20, b=10, l=10, r=10),
        font=dict(size=14),
        hoverlabel=dict(font_size=14),
        legend=dict(
            title_text="",
            orientation="h",
            yanchor="top",
            y=-0.15,
            font=dict(size=17),
            itemsizing="constant",
            itemwidth=60,
        ),
    )
    return fig


df = load()
updated = load_updated()

st.title("Bengaluru EV registrations")
st.caption("Source: Vahan dashboard, Ministry of Road Transport and Highways.")
st.caption(f"Last updated: {updated:%d %b %Y}" if updated else "Last updated: not available")

# Sidebar filter
rtos = sorted(df["rto_location"].unique())
chosen = st.sidebar.multiselect("RTO", rtos, default=rtos)
d = df[df["rto_location"].isin(chosen)]
if d.empty:
    st.warning("Select at least one RTO.")
    st.stop()

years = sorted(d["year"].unique())
latest = years[-1]
# The newest year is "in progress" if the data was refreshed during that year.
this_year = (updated or datetime.now(IST).date()).year
partial = latest >= this_year


def label(y):
    return f"{y} (YTD)" if partial and y == latest else str(y)


cat_year = d.groupby(["year", "vehicle_category"], as_index=False)["registrations"].sum()
cat_year["Year"] = cat_year["year"].map(label)
year_labels = [label(y) for y in years]

# Headline numbers
cur = d[d["year"] == latest]
cur_total = int(cur["registrations"].sum())
pure_share = cur.loc[cur["vehicle_category"] == "Pure EV", "registrations"].sum() / max(cur_total, 1)
c1, c2, c3 = st.columns(3)
c1.metric(f"Registrations in {latest}" + (" (year to date)" if partial else ""), f"{cur_total:,}")
c2.metric(f"Pure EV share in {latest}", f"{pure_share:.0%}")
c3.metric("Total, all years", f"{int(d['registrations'].sum()):,}")

# ---------------------------------------------------------------- 1. Trend
st.subheader("Registration trend")
metric = st.radio(
    "Metric",
    ["Registrations", "Percentage growth", "Cumulative registrations"],
    horizontal=True,
    key="trend_metric",
)
wide = (
    cat_year.pivot(index="year", columns="vehicle_category", values="registrations")
    .reindex(columns=CATS)
    .fillna(0)
)
if metric == "Registrations":
    vals, ytitle, hover, ytick = wide, "Registrations", "%{y:,.0f}", dict(tickformat=",d")
elif metric == "Cumulative registrations":
    vals, ytitle, hover, ytick = wide.cumsum(), "Cumulative registrations", "%{y:,.0f}", dict(tickformat=",d")
else:
    g = wide[wide.index < latest] if partial else wide  # a year in progress would look like a fall
    vals = ((g / g.shift(1) - 1) * 100).replace([np.inf, -np.inf], np.nan).iloc[1:]
    ytitle, hover, ytick = "Growth on previous year (%)", "%{y:+.1f}%", dict(ticksuffix="%")

long = vals.reset_index().melt(id_vars="year", var_name="vehicle_category", value_name="value")
long["Year"] = long["year"].map(label)
if long["value"].notna().sum() == 0:
    st.info("Not enough complete years to show growth for the selected RTOs.")
else:
    fig = px.line(long, x="Year", y="value", color="vehicle_category", markers=True,
                  color_discrete_map=COLORS, category_orders={"vehicle_category": CATS, "Year": year_labels})
    fig.update_traces(line=dict(width=3), marker=dict(size=9),
                      hovertemplate="%{fullData.name}<br>%{x}: " + hover + "<extra></extra>")
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title=ytitle, **ytick)
    st.plotly_chart(style(fig), use_container_width=True)
if metric == "Percentage growth":
    note = "Blank points mean the category had no registrations the year before, so growth cannot be calculated."
    if partial:
        note += f" {latest} is left out because the year is still in progress."
    st.caption(note)
elif partial:
    st.caption(f"YTD = year to date. {latest} is still in progress.")

# ------------------------------------------------------------------ 2. RTOs
st.subheader("EV Registrations by RTO Jurisdiction")
mode = st.radio("View", ["Total registrations", "Category share (%)"], horizontal=True, key="rto_mode")
rto = d.groupby(["rto_location", "vehicle_category"], as_index=False)["registrations"].sum()
rto["total"] = rto.groupby("rto_location")["registrations"].transform("sum")
rto["share"] = (rto["registrations"] / rto["total"].where(rto["total"] > 0) * 100).fillna(0)
order = rto.groupby("rto_location")["registrations"].sum().sort_values(ascending=False).index.tolist()
xcol = "registrations" if mode == "Total registrations" else "share"
fig = px.bar(rto, y="rto_location", x=xcol, color="vehicle_category", orientation="h",
             color_discrete_map=COLORS, custom_data=["registrations", "share", "total"],
             category_orders={"rto_location": order, "vehicle_category": CATS})
fig.update_traces(hovertemplate=(
    "<b>%{y}</b><br>%{fullData.name}<br>Registrations: %{customdata[0]:,}"
    "<br>Share of this RTO: %{customdata[1]:.1f}%<br>RTO total: %{customdata[2]:,}<extra></extra>"))
fig.update_yaxes(autorange="reversed", title=None)  # largest RTO at the top
if mode == "Total registrations":
    fig.update_xaxes(title="Registrations, all years combined", tickformat=",d")
else:
    fig.update_xaxes(title="Share of the RTO's registrations", range=[0, 100], ticksuffix="%")
st.plotly_chart(style(fig, height=520), use_container_width=True)
st.caption("All years combined. RTOs are ordered by total registrations, highest first.")

# ------------------------------------------------------------ 3 and 4
left, right = st.columns(2)
with left:
    st.subheader("Total EV registrations by year")
    totals = cat_year.groupby("Year", sort=False)["registrations"].sum().reindex(year_labels)
    fig = px.bar(cat_year, x="Year", y="registrations", color="vehicle_category",
                 color_discrete_map=COLORS, category_orders={"vehicle_category": CATS, "Year": year_labels})
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
                 color="vehicle_category", color_discrete_map=COLORS)
    fig.update_traces(sort=False, textinfo="percent", textfont_size=16,
                      hovertemplate="%{label}<br>Registrations: %{value:,}<br>Share: %{percent}<extra></extra>")
    st.plotly_chart(style(fig), use_container_width=True)

st.caption("Electric (BOV) and Pure EV are separate Vahan fuel labels. Registrations appear to shift "
           "from one to the other from 2024, so compare combined totals rather than each alone.")
