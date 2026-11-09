"""Derived quantities from the main Bayesian model (draws_main.npz) and the reconciliation with Railway Board data.

outputs/derived_national.csv     elasticity (pooled mean of state elasticities), deaths not occurring in 2020-21 because of
                                 the fall in passenger traffic (fitted deaths at 2019 traffic minus fitted deaths), share of
                                 deaths persisting when traffic fell
outputs/imputed_unreported.csv   posterior predictive deaths for unreported state-years (Karnataka 2014, 2018-24; Odisha 2022-23)
                                 and corrected national totals
outputs/state_rates_2024.csv     2024 deaths, rate per 100 000 population and per 100 route-km (observed; model-fitted with
                                 95% CrI), posterior rank by fitted rate per route-km
outputs/reconciliation.csv       NCRB (calendar year) vs Railway Board Statement 41(F) fatalities (financial year), national
                                 and by zone against the states each zone mainly serves; consequential-accident deaths
"""
import pathlib, json
import numpy as np, pandas as pd

P = pathlib.Path(__file__).resolve().parents[1]; O = P / "outputs"; D = P / "data"
z = np.load(O / "draws_main.npz")                                                   # plain arrays (unit names stored as str): no pickle
panel = pd.read_csv(D / "model_panel.csv")
U = list(z["units"]); yrs = z["years"]; row_unit = z["unit_of_row"]
mu = z["mu"].astype(float); th = z["theta"]; ND = mu.shape[0]
q = lambda v, ax=0: np.percentile(v, [50, 2.5, 97.5], axis=ax)
f3 = lambda v: [round(float(x), 3) for x in q(v)]
rows = []
w = panel.groupby("unit", sort=False).railway_total_died.sum().reindex(U).values      # weights = deaths over the period
rows.append(dict(quantity="elasticity, mean of state elasticities", values=f3(th.mean(1))))
rows.append(dict(quantity="elasticity, death-weighted mean of state elasticities", values=f3((th * w).sum(1) / w.sum())))
rows.append(dict(quantity="elasticity, national (Theta)", values=f3(z["Theta"])))
pk = panel.groupby("year").pkm_bn.first()
x = np.log(panel.pkm_bn.values / pk[2019])
for yr in (2020, 2021):
    m = yrs == yr
    mu_cf = mu[:, m] * np.exp(-th[:, [U.index(u) for u in row_unit[m]]] * x[m][None, :])   # same model, 2019 traffic
    gap = (mu_cf - mu[:, m]).sum(1)
    rows.append(dict(quantity=f"{yr}: fitted deaths", values=[round(float(v)) for v in q(mu[:, m].sum(1))]))
    rows.append(dict(quantity=f"{yr}: fitted deaths at 2019 passenger traffic", values=[round(float(v)) for v in q(mu_cf.sum(1))]))
    rows.append(dict(quantity=f"{yr}: deaths not occurring because of lower passenger traffic", values=[round(float(v)) for v in q(gap)]))
    rows.append(dict(quantity=f"{yr}: passenger-km relative to 2019 (%)", values=[round(100 * (pk[yr] / pk[2019] - 1), 1)] * 3))
    rows.append(dict(quantity=f"{yr}: % of deaths persisting relative to 2019-traffic expectation", values=f3(100 * mu[:, m].sum(1) / mu_cf.sum(1))))
pd.DataFrame(rows).to_csv(O / "derived_national.csv", index=False)

# imputation of unreported state-years
obs = z["observed"]; yp = z["ypred"]
imp = []
for i in np.where(np.isnan(obs))[0]:
    m, l, h = q(yp[:, i]); imp.append(dict(unit=row_unit[i], year=int(yrs[i]), imputed_median=int(m), lo=int(l), hi=int(h)))
imp = pd.DataFrame(imp)
nat = pd.read_csv(D / "national_series.csv").set_index("year")
corr = []
for yr in sorted(set(imp.year)):
    ii = np.where(np.isnan(obs) & (yrs == yr))[0]
    tot = nat.loc[yr, "railway_deaths"] + yp[:, ii].sum(1)
    m, l, h = q(tot); corr.append(dict(unit="ALL INDIA corrected (printed + imputed)", year=yr, imputed_median=int(m), lo=int(l), hi=int(h)))
imp = pd.concat([imp, pd.DataFrame(corr)], ignore_index=True)
imp.to_csv(O / "imputed_unreported.csv", index=False)

# state rates 2024
m24 = yrs == 2024; p24 = panel[panel.year == 2024].set_index("unit")
rk = p24.route_km.reindex(row_unit[m24]).values; pop = p24.population.reindex(row_unit[m24]).values
r_rk = 100 * mu[:, m24] / rk[None, :]; r_pop = 1e5 * mu[:, m24] / pop[None, :]
rank = (-r_rk).argsort(1).argsort(1) + 1
st = pd.DataFrame({"unit": row_unit[m24], "deaths_observed": p24.deaths.reindex(row_unit[m24]).values,
                   "route_km": rk, "population_m": pop / 1e6,
                   "rate_pop_obs": 1e5 * p24.deaths.reindex(row_unit[m24]).values / pop,
                   "rate_rk_obs": 100 * p24.deaths.reindex(row_unit[m24]).values / rk})
for nm, arr in (("fitted_deaths", mu[:, m24]), ("rate_pop", r_pop), ("rate_rk", r_rk)):
    a = q(arr); st[f"{nm}_med"], st[f"{nm}_lo"], st[f"{nm}_hi"] = a[0], a[1], a[2]
st["rank_rk_med"] = np.median(rank, 0); st["rank_rk_lo"] = np.percentile(rank, 2.5, 0); st["rank_rk_hi"] = np.percentile(rank, 97.5, 0)
st["p_top5_rk"] = (rank <= 5).mean(0)
st = st.sort_values("rate_rk_med", ascending=False)
st.to_csv(O / "state_rates_2024.csv", index=False)

# reconciliation
rb = pd.read_csv(D / "rb_statement41f_fatalities.csv")
w = pd.read_csv(D / "railway_state_year_wide.csv"); w = w[w.state_canonical != "ALL INDIA (printed total)"]
ncrb = lambda states, yr: int(w[(w.year == yr) & w.state_panel.isin(states)].railway_total_died.sum())
ZONES = {"Northern": ["Delhi", "Haryana", "Punjab", "Himachal Pradesh", "Jammu & Kashmir incl. Ladakh", "Uttarakhand", "Chandigarh"],
         "South Western": ["Karnataka", "Goa"], "West Central": ["Madhya Pradesh"], "Western": ["Gujarat"],
         "Central": ["Maharashtra"], "Eastern": ["West Bengal"]}
rec = []
for fyr, cyr in (("2022-23", 2022), ("2023-24", 2023), ("2024-25", 2024)):
    t = rb[(rb.fy == fyr) & (rb.zone == "All zones")].iloc[0]
    rec.append(dict(level="national", zone="All zones", fy=fyr, rb_fatalities=int(t.total), rb_trespassers=int(t.trespassers), rb_suicides=int(t.suicides),
                    ncrb_states="All India", ncrb_calendar_year=cyr, ncrb_deaths=int(nat.loc[cyr, "railway_deaths"]),
                    ratio_rb_to_ncrb=round(t.total / nat.loc[cyr, "railway_deaths"], 3), zones_reporting=int(((rb.fy == fyr) & (rb.zone != "All zones") & (rb.total > 0)).sum())))
    for zn, states in ZONES.items():
        r = rb[(rb.fy == fyr) & (rb.zone == zn)]
        v = int(r.total.iloc[0]) if len(r) else 0
        n = ncrb(states, cyr)
        rec.append(dict(level="zone", zone=zn, fy=fyr, rb_fatalities=v, rb_trespassers=int(r.trespassers.iloc[0]) if len(r) else 0,
                        rb_suicides=int(r.suicides.iloc[0]) if len(r) else 0, ncrb_states="; ".join(states), ncrb_calendar_year=cyr,
                        ncrb_deaths=n, ratio_rb_to_ncrb=round(v / n, 3) if n else np.nan, zones_reporting=np.nan))
cons = {"2014-15": 118, "2015-16": 40, "2016-17": 195, "2017-18": 28, "2018-19": 16}      # passengers killed, Year Books 2016-17/2018-19
for fyr, k in cons.items():
    cyr = int(fyr[:4]); n = int(nat.loc[cyr, "railway_deaths"]) if cyr in nat.index else np.nan
    rec.append(dict(level="consequential train accidents (passengers killed)", zone="All zones", fy=fyr, rb_fatalities=k, ncrb_calendar_year=cyr,
                    ncrb_deaths=n, ratio_rb_to_ncrb=round(k / n, 4) if n == n else np.nan))
rec = pd.DataFrame(rec); rec.to_csv(O / "reconciliation.csv", index=False)

pd.set_option("display.width", 220)
print(pd.read_csv(O / "derived_national.csv").to_string(index=False)); print(imp.to_string(index=False))
print(st[["unit", "deaths_observed", "rate_pop_obs", "rate_rk_obs", "rate_rk_med", "rate_rk_lo", "rate_rk_hi", "rank_rk_med", "p_top5_rk"]].round(2).to_string(index=False))
print(rec.drop(columns=["ncrb_states"]).to_string(index=False))
