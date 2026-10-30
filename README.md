# Bengaluru EV Registrations Dashboard

An interactive dashboard of electric and hybrid vehicle registrations across Bengaluru RTOs, built from official VAHAN data.

**Live dashboard:** https://ev-registrations-blr.streamlit.app/

## What it shows

- Registration trend by fuel category, as yearly or cumulative figures
- Registrations by RTO, as totals or category share, for all years or any single year
- Total registrations by year, and category share for a chosen year
- Filters for RTO, fuel category and year range, with exact figures in the hover text and a table

## Data

- **Source:** [VAHAN dashboard](https://vahan.parivahan.gov.in/vahan4dashboard/), Ministry of Road Transport and Highways. Data runs from 2021, and the current year is year-to-date (YTD).
- **Vehicle types:** no vehicle-type filter is applied, so figures are expected to cover all vehicle types (two-wheelers, three-wheelers, cars, buses and others), not cars only.
- **What a figure means:** new registrations in that period. It is not the number of EVs on the road.
- **RTOs:** the 10 Bengaluru Urban RTOs (KA-01 to KA-05, KA-41, KA-50, KA-51, KA-53, KA-59). Devanahalli (KA-43) and Nelamangala (KA-52), both Bengaluru Rural, are being added.

### Fuel categories

| Dashboard category | VAHAN fuel type(s) |
|---|---|
| Electric (BOV) | ELECTRIC(BOV) |
| Pure EV | PURE EV |
| Strong Hybrid EV | STRONG HYBRID EV |
| Petrol Hybrid (incl. E20) | PETROL/HYBRID + PETROL(E20)/HYBRID |

Excluded because of low or no numbers: diesel hybrid, plug-in hybrid EV, petrol/CNG hybrid combinations, and hydrogen / fuel cell.

### Read with care

- **Electric (BOV) and Pure EV are separate VAHAN labels.** Registrations appear to have shifted from one to the other from 2024, so compare their combined total.
- **Petrol/Hybrid and Petrol(E20)/Hybrid are added together** for the same reason: vehicles moved between the two labels.
- **The hybrid categories are not fully electric vehicles.**
- VAHAN revises past figures, so numbers can change slightly between updates.

## How it works

1. A public scraper ([RevTpark/vahan-scraper](https://github.com/RevTpark/vahan-scraper), not included in this repo) downloads fuel-wise monthly registrations for each RTO.
2. `build_csv.py` keeps the chosen fuel types, combines labels, runs sanity checks and writes `data/ev_data.csv` and `data/last_updated.txt`.
3. `app.py` (Streamlit) reads those files and draws the dashboard. It redeploys whenever the repo changes.

The refresh runs weekly from the author's computer on a schedule, so it can lag if that computer is off. The "Last updated" date on the dashboard shows when it last worked. A GitHub Actions workflow is included but disabled, because VAHAN did not accept connections from GitHub's servers in testing.

## Run it locally

```
pip install -r requirements.txt
streamlit run app.py
```

## Disclaimer

An independent project, not affiliated with or endorsed by MoRTH or VAHAN. The figures come from a third-party scrape of a public website and may contain errors. Check against the official source before relying on them.

## Feedback

Suggestions are welcome: open an issue on this repo.
