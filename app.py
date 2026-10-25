import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Bengaluru EV registrations", layout="wide")

CATS = ["Electric (BOV)", "Pure EV", "Strong Hybrid EV"]
COLORS = {"Electric (BOV)": "#2F5D9B", "Pure EV": "#0E9F7E", "Strong Hybrid EV": "#E3A21A"}


@st.cache_data(ttl=3600)  # re-read the CSV at most once an hour
def load():
    df = pd.read_csv("data/ev_data.csv")
    df["rto_location"] = df["rto_location"].str.strip()
    return df


df = load()
st.title("Bengaluru EV registrations")
st.caption("Source: Vahan dashboard, Ministry of Road Transport and Highways.")

# Sidebar filter
rtos = sorted(df["rto_location"].unique())
chosen = st.sidebar.multiselect("RTO", rtos, default=rtos)
d = df[df["rto_location"].isin(chosen)]
if d.empty:
    st.warning("Select at least one RTO.")
    st.stop()

# Totals per year, and growth
by_year = d.groupby("year", as_index=False)["registrations"].sum()
by_year["yoy"] = by_year["registrations"].pct_change() * 100
years = by_year["year"].tolist()
latest = years[-1]
cur = d[d["year"] == latest]
pure_share = cur.loc[cur["vehicle_category"] == "Pure EV", "registrations"].sum() / max(cur["registrations"].sum(), 1)

# Headline numbers
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Registrations in {latest}", f"{by_year['registrations'].iloc[-1]:,}")
yoy_last = by_year["yoy"].iloc[-1]
c2.metric("Change vs previous year", "n/a" if pd.isna(yoy_last) else f"{yoy_last:+.1f}%")
c3.metric(f"Pure EV share in {latest}", f"{pure_share:.0%}")
c4.metric("Total, all years", f"{by_year['registrations'].sum():,}")

cat_year = d.groupby(["year", "vehicle_category"], as_index=False)["registrations"].sum()

left, right = st.columns(2)
with left:
    st.subheader("Total EV registrations")
    fig = px.bar(cat_year, x="year", y="registrations", color="vehicle_category",
                 color_discrete_map=COLORS, category_orders={"vehicle_category": CATS})
    fig.update_xaxes(type="category")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Registration trend")
    fig = px.line(cat_year, x="year", y="registrations", color="vehicle_category",
                  markers=True, color_discrete_map=COLORS, category_orders={"vehicle_category": CATS})
    fig.update_xaxes(type="category")
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Year-on-year growth (%)")
    fig = px.line(by_year.dropna(subset=["yoy"]), x="year", y="yoy", markers=True)
    fig.update_xaxes(type="category")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("The latest year may be incomplete, which makes its growth rate look worse than it is.")
with right:
    st.subheader("Category mix")
    year = st.selectbox("Year", years, index=len(years) - 1)
    mix = cat_year[cat_year["year"] == year]
    fig = px.pie(mix, names="vehicle_category", values="registrations", hole=0.5,
                 color="vehicle_category", color_discrete_map=COLORS)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Registrations by RTO")
rto = d.groupby(["rto_location", "vehicle_category"], as_index=False)["registrations"].sum()
order = rto.groupby("rto_location")["registrations"].sum().sort_values().index.tolist()
fig = px.bar(rto, y="rto_location", x="registrations", color="vehicle_category", orientation="h",
             color_discrete_map=COLORS, category_orders={"rto_location": order, "vehicle_category": CATS})
st.plotly_chart(fig, use_container_width=True)

st.caption("Electric (BOV) and Pure EV are separate Vahan fuel labels. Registrations appear to shift "
           "from one to the other from 2024, so compare combined totals rather than each alone.")
