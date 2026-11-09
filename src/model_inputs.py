"""Analysis panel for railway deaths in Indian states, 2014, 2015 and 2018-2024.

Outcome: deaths in railway accidents (NCRB ADSI Table 1A.2 railway column; 2024 = railway accidents + the new
'incidents on railway tracks / in railway premises'), from data/railway_state_year_wide.csv (validated extraction).
Units: states/UTs with >= 150 route-km (Year Book 2024-25); smaller units are excluded (their deaths are reported).
Unreported state-years are set to missing, not zero (rule: printed zero, or under 15% of the state's other years, in a
state with substantial rail traffic): Karnataka 2014 and 2018-2024, Odisha 2022-2023. Himachal Pradesh prints 0 in every
year and is excluded.
Population: Technical Group projections (1 July), from the snakebite project file. Route-km: Year Books 2016-17,
2018-19, 2024-25 (as of 31 March 2017, 2019, 2025), linearly interpolated/extrapolated by year.
Exposure: calendar-year national passenger-km = 0.25 x FY(t-1/t) + 0.75 x FY(t/t+1); 2014 uses FY2014-15.
Writes data/model_panel.csv and data/national_series.csv; prints coverage checks.
"""
import pathlib
import numpy as np, pandas as pd

P = pathlib.Path(__file__).resolve().parents[1]
w = pd.read_csv(P / "data/railway_state_year_wide.csv")
pop = pd.read_csv(P / "data/state_population.csv")
rk = pd.read_csv(P / "data/state_route_km.csv")
pk = pd.read_csv(P / "data/national_passenger_km.csv")

NAME = {"Chhatisgarh": "Chhattisgarh", "Pondicherry": "Puducherry", "Jammu & Kashmir": "Jammu & Kashmir + Ladakh (former J&K state)"}
rk["state"] = rk.state_printed.replace(NAME)
rk["t"] = rk.as_of.str[:4].astype(int) - 0.25                                       # 31 March -> fraction of year
YEARS = [2014, 2015, 2018, 2019, 2020, 2021, 2022, 2023, 2024]


def route_km(state, year):
    d = rk[rk.state == state].sort_values("t")
    if d.empty: return np.nan
    return float(np.interp(year + 0.5, d.t, d.route_km, left=None, right=None)) if len(d) > 1 else float(d.route_km.iloc[0])


# calendar-year passenger-km index
fy = dict(zip(pk.fy, pk.passenger_km_million / 1e3))                                 # billion
cy = {2014: fy["2014-15"]}
for y in YEARS[1:]:
    cy[y] = 0.25 * fy[f"{y - 1}-{str(y)[2:]}"] + 0.75 * fy[f"{y}-{str(y + 1)[2:]}"]
nat = w[w.state_canonical == "ALL INDIA (printed total)"].set_index("year")
ns = pd.DataFrame({"year": YEARS, "passenger_km_bn": [cy[y] for y in YEARS],
                   "railway_deaths": [int(nat.loc[y, "railway_total_died"]) for y in YEARS],
                   "fall_people_on_track_deaths": [int(nat.loc[y, "fall_from_train_people_on_track_died"]) for y in YEARS],
                   "railway_crossing_deaths": [int(nat.loc[y, "railway_crossing_died"]) for y in YEARS]})
ns["deaths_per_bn_pkm"] = ns.railway_deaths / ns.passenger_km_bn
ns.to_csv(P / "data/national_series.csv", index=False)

# state panel (time-consistent units)
st = w[w.state_canonical != "ALL INDIA (printed total)"].copy()
st["unit"] = st.state_panel.replace({"Jammu & Kashmir incl. Ladakh": "Jammu & Kashmir + Ladakh (former J&K state)"})
g = st.groupby(["unit", "year"], as_index=False)[["railway_total_died", "railway_crossing_died", "fall_from_train_people_on_track_died"]].sum()
popu = pop.copy(); popu["unit"] = popu.state
g = g.merge(popu[["unit", "year", "population"]], on=["unit", "year"], how="left")
miss_pop = g[g.population.isna()].unit.unique()
assert set(miss_pop) <= {"Jammu & Kashmir", "Ladakh"}, miss_pop
g["route_km"] = [route_km(u, y) for u, y in zip(g.unit, g.year)]
keep = sorted(rk[(rk.fy == "2024-25") & (rk.route_km >= 150)].state.unique())
keep = [k for k in keep if k != "Himachal Pradesh"]          # prints 0 railway deaths in all nine years: never reports
panel = g[g.unit.isin(keep)].copy()
panel["deaths"] = panel.railway_total_died.astype(float)
panel["deaths_incl_crossing"] = (panel.railway_total_died + panel.railway_crossing_died).astype(float)
panel["note"] = ""
UNREPORTED = (("Karnataka", [2014] + list(range(2018, 2025)), "prints 0 in 2018-2024 and 25 in 2014 vs 891 in 2015; its zone (South Western Railway) reports ~1,300 fatalities a year"),
              ("Odisha", [2022, 2023], "prints 27 in 2022 and 0 in 2023 (footnote: clarification pending) vs 179-446 in other years"))
for u, ys, why in UNREPORTED:
    m = (panel.unit == u) & panel.year.isin(ys)
    panel.loc[m, ["deaths", "deaths_incl_crossing"]] = np.nan; panel.loc[m, "note"] = why
panel["suburban"] = panel.unit.isin(["Maharashtra", "West Bengal", "Tamil Nadu", "Telangana"]).astype(int)   # EMU suburban systems
panel["pkm_bn"] = panel.year.map(cy)
panel = panel.sort_values(["unit", "year"]).reset_index(drop=True)
panel.to_csv(P / "data/model_panel.csv", index=False)

tot = st.groupby("year").railway_total_died.sum()
cov = panel.groupby("year").railway_total_died.sum() / tot
print(ns.round(1).to_string(index=False))
print(f"units {panel.unit.nunique()}: {', '.join(panel.unit.unique())}")
print("share of national railway deaths in modelled units, by year:", (100 * cov).round(1).to_dict())
print("missing outcome rows:", int(panel.deaths.isna().sum()))
assert (tot == nat.loc[tot.index, "railway_total_died"]).all(), "state sum != printed national total"
