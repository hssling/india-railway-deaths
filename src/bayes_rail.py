"""Bayesian hierarchical model of railway deaths in 23 Indian states, 2014, 2015, 2018-2024.

  deaths_st ~ NegBin(mu_st, phi)
  log mu_st = log(pop_st / 1e5) + a_s + b_s * tau_t + theta_s * x_t + delta * I(t = 2024) [+ e_st]
     tau_t = (t - 2019) / 10                       secular trend in risk per unit of passenger traffic (per decade)
     x_t   = log(passenger-km_t / passenger-km_2019)   national calendar-year passenger-km (COVID-19 shock identifies)
     theta_s = Theta + gamma * suburban_s + s_th * z_s   elasticity of deaths to passenger traffic, partially pooled;
               suburban_s = state with an EMU suburban system (Maharashtra, West Bengal, Tamil Nadu, Telangana)
     delta = shift in 2024, when NCRB reclassified 'railway accidents' as 'incidents on railway tracks / premises'
  a_s ~ N(A, s_a), b_s ~ N(B, s_b); weakly informative priors (see PRIORS). Missing (unreported) state-years are
  imputed from the posterior predictive (Karnataka 2014 and 2018-2024; Odisha 2022-2023; see model_inputs.py).
Scenarios: main; incl_crossing (railway + railway-crossing deaths, guards against misfiling between the two);
  drop_misfiled (removes 4 state-years with apparent misfiling: Telangana 2014, Bihar 2014, Haryana 2015, Andhra
  Pradesh 2015); extra_noise (adds state-year random effects e_st ~ N(0, s_e)); no_suburban (gamma = 0).
Outputs: outputs/draws_<scenario>.npz, outputs/summary_<scenario>.csv, outputs/model_diagnostics.json
"""
import os, sys, json, pathlib, time
os.environ["XLA_FLAGS"] = "--xla_force_host_platform_device_count=4"
import numpy as np, pandas as pd
import jax, jax.numpy as jnp
import numpyro, numpyro.distributions as dist
from numpyro.infer import MCMC, NUTS
from numpyro.diagnostics import summary
numpyro.set_host_device_count(4)

P = pathlib.Path(__file__).resolve().parents[1]; O = P / "outputs"; O.mkdir(exist_ok=True)
panel = pd.read_csv(P / "data/model_panel.csv")
U = list(dict.fromkeys(panel.unit)); S = len(U); YEARS = sorted(panel.year.unique())
uix = jnp.array([U.index(u) for u in panel.unit])
tau = jnp.array((panel.year.values - 2019) / 10.0)
pk19 = panel.loc[panel.year == 2019, "pkm_bn"].iloc[0]
x = jnp.array(np.log(panel.pkm_bn.values / pk19))
y24 = jnp.array((panel.year.values == 2024).astype(float))
off = jnp.array(np.log(panel.population.values / 1e5))
sub = jnp.array(panel.groupby("unit", sort=False).suburban.first().reindex(U).values.astype(float))
MISFILED = {("Telangana", 2014), ("Bihar", 2014), ("Haryana", 2015), ("Andhra Pradesh", 2015)}


def model(yobs, mask, scn):
    A = numpyro.sample("A", dist.Normal(np.log(2.0), 2.0))
    s_a = numpyro.sample("s_a", dist.HalfNormal(1.0))
    B = numpyro.sample("B", dist.Normal(0.0, 1.0))
    s_b = numpyro.sample("s_b", dist.HalfNormal(0.5))
    Th = numpyro.sample("Theta", dist.Normal(0.0, 1.0))
    ga = numpyro.sample("gamma", dist.Normal(0.0, 0.5)) if scn != "no_suburban" else 0.0
    s_th = numpyro.sample("s_th", dist.HalfNormal(0.5))
    de = numpyro.sample("delta", dist.Normal(0.0, 0.25))
    a = numpyro.deterministic("a", A + s_a * numpyro.sample("za", dist.Normal(0, 1).expand([S])))
    b = numpyro.deterministic("b", B + s_b * numpyro.sample("zb", dist.Normal(0, 1).expand([S])))
    th = numpyro.deterministic("theta", Th + ga * sub + s_th * numpyro.sample("zt", dist.Normal(0, 1).expand([S])))
    eta = off + a[uix] + b[uix] * tau + th[uix] * x + de * y24
    if scn == "extra_noise":
        s_e = numpyro.sample("s_e", dist.HalfNormal(0.3))
        eta = eta + s_e * numpyro.sample("ze", dist.Normal(0, 1).expand([len(off)]))
    phi = numpyro.sample("phi", dist.Gamma(2.0, 0.1))
    numpyro.deterministic("mu", jnp.exp(eta))
    with numpyro.handlers.mask(mask=mask):
        numpyro.sample("y", dist.NegativeBinomial2(jnp.exp(eta), phi), obs=yobs)


def run(scn):
    col = "deaths_incl_crossing" if scn == "incl_crossing" else "deaths"
    yv = panel[col].values.copy()
    if scn == "drop_misfiled":
        yv[[(u, t) in MISFILED for u, t in zip(panel.unit, panel.year)]] = np.nan
    mask = jnp.array(~np.isnan(yv)); yobs = jnp.array(np.nan_to_num(yv).astype(int))
    t0 = time.time()
    mcmc = MCMC(NUTS(model, target_accept_prob=0.95), num_warmup=2000, num_samples=2000, num_chains=4, progress_bar=False)
    mcmc.run(jax.random.PRNGKey(20261109), yobs, mask, scn, extra_fields=("diverging",))
    g = mcmc.get_samples(group_by_chain=True)
    keys = [k for k in ("A", "s_a", "B", "s_b", "Theta", "gamma", "s_th", "delta", "phi", "s_e", "a", "b", "theta") if k in g]
    sm = summary({k: g[k] for k in keys}, prob=0.95)
    rhat = max(float(np.max(v["r_hat"])) for v in sm.values()); neff = min(float(np.min(v["n_eff"])) for v in sm.values())
    ndiv = int(mcmc.get_extra_fields()["diverging"].sum())
    s = {k: np.asarray(v) for k, v in mcmc.get_samples().items() if k in keys + ["mu"]}
    # posterior predictive for every row (used for imputation of unreported state-years)
    rng = np.random.default_rng(1)
    mu = s["mu"]; phi = s["phi"][:, None]
    ypred = rng.poisson(rng.gamma(phi, mu / phi))
    np.savez_compressed(O / f"draws_{scn}.npz", units=np.array(U, dtype=str), years=panel.year.values, unit_of_row=panel.unit.values.astype(str),
                        observed=yv, ypred=ypred.astype(np.int32), **{k: v for k, v in s.items() if k != "mu"}, mu=mu.astype(np.float32))
    q = lambda v: np.percentile(v, [50, 2.5, 97.5])
    pc = lambda v: q(100 * np.expm1(v))
    out = dict(scenario=scn, seconds=round(time.time() - t0), max_rhat=round(rhat, 4), min_neff=round(neff), divergences=ndiv,
               n_obs=int(np.asarray(mask).sum()),
               elasticity_all=q(s["Theta"] + (s["gamma"] * 0 if "gamma" in s else 0)).round(3).tolist(),
               elasticity_non_suburban=q(s["Theta"]).round(3).tolist(),
               elasticity_suburban=q(s["Theta"] + (s["gamma"] if "gamma" in s else 0)).round(3).tolist(),
               risk_trend_pct_per_year=pc(s["B"] / 10).round(2).tolist(),
               shift_2024_pct=pc(s["delta"]).round(1).tolist())
    print(scn, json.dumps(out), flush=True)
    return out


if __name__ == "__main__":
    todo = sys.argv[1:] or ["main", "incl_crossing", "drop_misfiled", "extra_noise", "no_suburban"]
    fn = O / "model_diagnostics.json"
    diag = json.loads(fn.read_text()) if fn.exists() else {}
    for k in todo: diag[k] = run(k)
    fn.write_text(json.dumps(diag, indent=1))
