"""Figures (greyscale, Arial, 600 dpi TIFF).
Figure 1 (A) national passenger-km and police-recorded railway deaths, indexed to 2019 = 100, with the model's fitted deaths
         (median, 95% CrI); (B) railway deaths as counted by each system (log scale).
Figure 2 State rates in 2024: (A) deaths per 100 route-km (model-fitted median, 95% CrI); (B) deaths per 100 000 population.
"""
import pathlib
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from PIL import Image

P = pathlib.Path(__file__).resolve().parents[1]; O = P / "outputs"; D = P / "data"
K, DG, MG, LG = "#000000", "#4d4d4d", "#8c8c8c", "#d0d0d0"
plt.rcParams.update({"font.family": ["Arial", "Liberation Sans", "DejaVu Sans"], "font.size": 8, "axes.linewidth": 0.6})
oup = lambda v: f"{v:,.0f}".replace(",", " ") if v >= 10000 else f"{v:.0f}"
fmt = FuncFormatter(lambda v, _: oup(v))


def save(fig, name):
    for ax in fig.axes:
        for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.savefig(O / f"{name}.png", dpi=600)
    Image.open(O / f"{name}.png").convert("L").save(O / f"{name}.tif", dpi=(600, 600), compression="tiff_lzw")
    plt.close(fig)


ns = pd.read_csv(D / "national_series.csv").set_index("year")
z = np.load(O / "draws_main.npz"); yrs = z["years"]; mu = z["mu"]
fit = np.array([mu[:, yrs == y].sum(1) for y in ns.index]).T                         # draws x years (22 units)
imp = pd.read_csv(O / "imputed_unreported.csv"); corr = imp[imp.unit.str.startswith("ALL INDIA")].set_index("year")
fig, (a, b) = plt.subplots(1, 2, figsize=(7.09, 3.7))
Y = ns.index.values
pk = 100 * ns.passenger_km_bn / ns.loc[2019, "passenger_km_bn"]; dth = 100 * ns.railway_deaths / ns.loc[2019, "railway_deaths"]
f50, f2, f97 = (100 * np.percentile(fit, q, 0) / np.median(fit[:, list(Y).index(2019)]) for q in (50, 2.5, 97.5))
a.fill_between(Y, f2, f97, color=LG, lw=0); a.plot(Y, f50, color=DG, lw=1.0, ls=(0, (3, 1.5)), label="Railway deaths, model fit")
a.plot(Y, dth, "o-", color=K, ms=4, lw=1.2, label="Railway deaths, police-recorded")
a.plot(Y, pk, "s-", color=DG, ms=4, mfc="white", lw=1.0, label="Passenger-km")
a.axvspan(2015.5, 2017.5, color="white", zorder=3); a.text(2016.5, 60, "no data\n2016–17", ha="center", fontsize=7, zorder=4, color=DG)
a.set_ylim(30, 125); a.set_ylabel("Index (2019 = 100)"); a.set_xticks(range(2014, 2025, 2)); a.legend(frameon=False, fontsize=7, loc="upper left", bbox_to_anchor=(0.0, -0.13))
a.text(-0.16, 1.03, "A", transform=a.transAxes, fontsize=10, fontweight="bold")
b.plot(Y, ns.railway_deaths, "o-", color=K, ms=4, lw=1.2, label="Police (NCRB), printed")
b.plot(corr.index, corr.imputed_median, "o", color=K, ms=4, mfc="white", label="Police, with unreported states imputed")
rb = pd.read_csv(D / "rb_statement41f_fatalities.csv"); rb = rb[rb.zone == "All zones"]
b.plot([int(f[:4]) + 0.25 for f in rb.fy], rb.total, "D", color=DG, ms=4.5, label="Railway Board, unusual occurrences")
cons = {2014: 118, 2015: 40, 2016: 195, 2017: 28, 2018: 16}
b.plot([y + 0.25 for y in cons], list(cons.values()), "^", color=MG, ms=4.5, label="Railway Board, train-accident\npassenger deaths")
b.set_yscale("log"); b.set_ylim(10, 60000); b.yaxis.set_major_formatter(fmt); b.set_xticks(range(2014, 2025, 2))
b.set_ylabel("Deaths per year (log scale)"); b.legend(frameon=False, fontsize=7, loc="upper left", bbox_to_anchor=(0.0, -0.13))
b.text(-0.2, 1.03, "B", transform=b.transAxes, fontsize=10, fontweight="bold")
fig.tight_layout(w_pad=2.5); save(fig, "Figure_1")

st = pd.read_csv(O / "state_rates_2024.csv")
SH = {"Jammu & Kashmir + Ladakh (former J&K state)": "Jammu & Kashmir + Ladakh"}
st = st.sort_values("rate_rk_med"); y = np.arange(len(st))
fig, (a, b) = plt.subplots(1, 2, figsize=(7.09, 4.2), sharey=True)
for yi, r in zip(y, st.itertuples()):
    a.plot([r.rate_rk_lo, r.rate_rk_hi], [yi, yi], color=DG, lw=1.0); a.plot(r.rate_rk_med, yi, "o", color=K, ms=3.8)
    b.plot([r.rate_pop_lo, r.rate_pop_hi], [yi, yi], color=DG, lw=1.0); b.plot(r.rate_pop_med, yi, "o", color=K, ms=3.8)
    if r.unit == "Karnataka":
        for ax in (a, b): ax.plot(r.rate_rk_med if ax is a else r.rate_pop_med, yi, "o", mfc="white", mec=K, ms=3.8)
a.set_xscale("log"); a.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
a.set_yticks(y); a.set_yticklabels([SH.get(u, u) for u in st.unit], fontsize=7.2)
a.set_xlabel("Deaths per 100 route-km, 2024"); b.set_xlabel("Deaths per 100 000 population, 2024")
for ax, lab in ((a, "A"), (b, "B")): ax.text(-0.02 if ax is b else -0.5, 1.02, lab, transform=ax.transAxes, fontsize=10, fontweight="bold")
fig.tight_layout(w_pad=1.2); save(fig, "Figure_2")
for f in ("Figure_1", "Figure_2"): print(f, Image.open(O / f"{f}.tif").size)
