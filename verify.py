"""Recompute every number reported in the paper from data/ and outputs/; exit 1 on any failure."""
import json, pathlib, sys
import numpy as np, pandas as pd
R = pathlib.Path(__file__).resolve().parent; O = R / "outputs"; D = R / "data"
E = json.loads((R / "results/expected_key_results.json").read_text())
fails, n = [], 0


def check(name, got, want, tol):
    global n; n += 1; ok = abs(got - want) <= tol
    print(f"{'PASS' if ok else 'FAIL'}  {name:62s} got {got:12.4f}  expected {want:12.4f}")
    if not ok: fails.append(name)


def trio(name, arr, want, tol, rnd=None):
    for lab, q, x in zip(("median", "lo", "hi"), (50, 2.5, 97.5), want):
        g = np.percentile(arr, q); check(f"{name} {lab}", round(g, rnd) if rnd is not None else g, x, tol)


ns = pd.read_csv(D / "national_series.csv").set_index("year")
w = pd.read_csv(D / "railway_state_year_wide.csv")
for y, x in E["national_deaths"].items():
    check(f"national railway deaths {y} (printed total)", ns.loc[int(y), "railway_deaths"], x, 0)
    st = w[(w.year == int(y)) & (w.state_canonical != "ALL INDIA (printed total)")].railway_total_died.sum()
    check(f"state rows sum to national total {y}", st, x, 0)
check("total deaths, nine years", ns.railway_deaths.sum(), E["total_deaths_9_years"], 0)
check("2024 share falls / people on track (%)", 100 * ns.loc[2024, "fall_people_on_track_deaths"] / ns.loc[2024, "railway_deaths"], E["fall_share_2024_pct"], 0.051)
check("2024 level-crossing deaths", ns.loc[2024, "railway_crossing_deaths"], E["crossing_deaths_2024"], 0)
for y in ("2019", "2024"): check(f"deaths per billion passenger-km {y}", ns.loc[int(y), "deaths_per_bn_pkm"], E["deaths_per_bn_pkm"][y], 0.051)
panel = pd.read_csv(D / "model_panel.csv"); stt = w[w.state_canonical != "ALL INDIA (printed total)"].groupby("year").railway_total_died.sum()
check("minimum share of deaths in the 22 states (%)", (100 * panel.groupby("year").railway_total_died.sum() / stt).min(), E["share_in_22_states_min_pct"], 0.051)
z = np.load(O / "draws_main.npz")
trio("elasticity (Theta)", z["Theta"], E["elasticity"], 0.0051)
trio("elasticity, suburban states", z["Theta"] + z["gamma"], E["elasticity_suburban"], 0.0051)
check("deaths fall for a 10% traffic fall (%)", np.median(100 * (1 - 0.9 ** z["Theta"])), E["fall_for_10pct_traffic_pct"], 0.051)
trio("risk trend % per year", 100 * np.expm1(z["B"] / 10), E["risk_trend_pct_per_year"], 0.051)
trio("2024 shift %", 100 * np.expm1(z["delta"]), E["shift_2024_pct"], 0.051)
der = pd.read_csv(O / "derived_national.csv").set_index("quantity")
val = lambda k: json.loads(der.loc[k, "values"].replace("np.float64(", "").replace(")", ""))
for k, key in (("2020: % of deaths persisting relative to 2019-traffic expectation", "persist_2020_pct"),):
    for g, x in zip(val(k), E[key]): check(f"{key}", round(g, 1), x, 0.051)
for k, key in (("2020: deaths not occurring because of lower passenger traffic", "not_occurring_2020"), ("2021: deaths not occurring because of lower passenger traffic", "not_occurring_2021")):
    for g, x in zip(val(k), E[key]): check(key, g, x, 0.5)
check("passenger-km change 2020 vs 2019 (%)", val("2020: passenger-km relative to 2019 (%)")[0], E["traffic_change_2020_pct"], 0.051)
dg = json.loads((O / "model_diagnostics.json").read_text())
for k, key in (("incl_crossing", "shift_2024_incl_crossing"), ("drop_misfiled", "shift_2024_drop_misfiled")):
    for g, x in zip(dg[k]["shift_2024_pct"], E[key]): check(f"{key}", g, x, 0.051)
els = [dg[k]["elasticity_non_suburban"][0] for k in dg]
check("lowest elasticity across analyses", round(min(els), 2), E["elasticity_range_sensitivity"][0], 0.0051)
check("highest elasticity across analyses", round(max(els), 2), E["elasticity_range_sensitivity"][1], 0.0051)
for k, d in dg.items():
    check(f"{k}: max R-hat <= 1.011", min(d["max_rhat"], E["mcmc"]["max_rhat"]), d["max_rhat"], 0); check(f"{k}: divergences", d["divergences"], 0, 0)
imp = pd.read_csv(O / "imputed_unreported.csv")
c = imp[(imp.unit.str.startswith("ALL INDIA")) & (imp.year == 2024)].iloc[0]
for g, x in zip((c.imputed_median, c.lo, c.hi), E["corrected_2024"]): check("corrected national total 2024", g, x, 0)
k = imp[(imp.unit == "Karnataka") & (imp.year == 2024)].iloc[0]
for g, x in zip((k.imputed_median, k.lo, k.hi), E["karnataka_imputed_2024"]): check("Karnataka imputed 2024", g, x, 0)
sr = pd.read_csv(O / "state_rates_2024.csv").set_index("unit")
for s, x in E["state_rate_rk_2024"].items():
    xs = x if isinstance(x, list) else [x]
    for g, w_ in zip((sr.loc[s, "rate_rk_med"], sr.loc[s, "rate_rk_lo"], sr.loc[s, "rate_rk_hi"]), xs): check(f"deaths per 100 route-km {s}", round(g), w_, 0.5)
for s, x in E["state_rate_pop_2024"].items():
    xs = x if isinstance(x, list) else [x]
    for g, w_ in zip((sr.loc[s, "rate_pop_med"], sr.loc[s, "rate_pop_lo"], sr.loc[s, "rate_pop_hi"]), xs): check(f"deaths per 100 000 {s}", round(g, 1), w_, 0.051)
for s, x in E["state_deaths_2024"].items(): check(f"police deaths 2024 {s}", sr.loc[s, "deaths_observed"], x, 0)
rec = pd.read_csv(O / "reconciliation.csv")
for fy, (tot, pct) in E["rb41f"].items():
    r = rec[(rec.level == "national") & (rec.fy == fy)].iloc[0]
    check(f"Railway Board 41(F) total {fy}", r.rb_fatalities, tot, 0); check(f"41(F) as % of police {fy}", 100 * r.ratio_rb_to_ncrb, pct, 0.051)
z2 = lambda zone: rec[(rec.level == "zone") & (rec.zone == zone)].set_index("fy")
for (a, b), key in ((("2023-24", "2024-25"), "maharashtra_2023_2024"),):
    for fy, x in zip((a, b), E[key]): check(f"police Maharashtra {fy}", z2("Central").loc[fy, "ncrb_deaths"], x, 0)
for fy, x in zip(("2023-24", "2024-25"), E["west_bengal_2023_2024"]): check(f"police West Bengal {fy}", z2("Eastern").loc[fy, "ncrb_deaths"], x, 0)
for fy, x in zip(("2023-24", "2024-25"), E["swr_2023_24_2024_25"]): check(f"South Western Railway {fy}", z2("South Western").loc[fy, "rb_fatalities"], x, 0)
print(f"\n{n - len(fails)}/{n} checks passed"); sys.exit(1 if fails else 0)
