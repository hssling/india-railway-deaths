# Railway deaths in India, 2014–2024: police records, passenger traffic and official railway statistics

This repository holds the data and code for a state-level analysis of railway deaths in India.
- **Deaths:** police-recorded railway deaths for 22 states (99.8% of all deaths) in 2014, 2015 and 2018–2024, from NCRB *Accidental Deaths & Suicides in India*.
- **Denominators:** linked to population, route-kilometres and national passenger-kilometres.
- **Model:** a Bayesian hierarchical model estimates how deaths respond to passenger traffic, using the 2020–21 collapse of rail travel. It also estimates the trend in risk and the effect of NCRB's 2024 reclassification.
- **Comparison:** the counts are set against the railways' own fatality returns (Annual Statistical Statements, Statement 41(F)).

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24065923.svg)](https://doi.org/10.5281/zenodo.24065923)
[![reproduce-and-verify](https://github.com/hssling/india-railway-deaths/actions/workflows/verify.yml/badge.svg)](https://github.com/hssling/india-railway-deaths/actions/workflows/verify.yml)

**Status.** The accompanying manuscript has been submitted for publication. Please cite this archive until the article is out: Siddalingaiah H S. *Railway deaths in India, 2014-2024: data and code* (v1.0.0). Zenodo; 2026. https://doi.org/10.5281/zenodo.24065923

## Main findings

| | Estimate (95% credible interval) |
|---|---|
| Police-recorded railway deaths, 9 years | 193 643 (22 413 in 2024; 75.2% falls from trains or people struck on the tracks) |
| 2024 total with unreported state-years imputed | 23 281 (22 648–25 401) |
| Elasticity of deaths to passenger-km | 0.72 (0.49–0.94); a 10% traffic fall brings a 7.3% fall in deaths |
| Deaths still occurring when traffic fell 59.5% (2020) | 54.2% (45.1–65.6) of the deaths expected at 2019 traffic |
| Change in risk per unit of traffic | +0.8% a year (−1.8 to 3.6) |
| Railway Board returns as % of police records | 41.3–46.8% (2022–23 to 2024–25) |

- **Neither system is complete.** The railways' returns come from only 5–6 of 17 zones. Central and Eastern Railway, which run the Mumbai and Kolkata suburban networks, report no deaths. Meanwhile Karnataka reported no railway deaths to the police in 2018–2024, although South Western Railway reports about 1 280 a year.
- **Highest risk per route-km:** Delhi, Haryana, Maharashtra and West Bengal.

## Reproduce

```bash
pip install -r requirements.txt
python verify.py          # recomputes 97 reported numbers from data/ and outputs/ (seconds)
python run_pipeline.py    # rebuilds the model panel, derived quantities and figures from the committed draws, then verifies
```

Optional steps:

- **Refit the five Bayesian models:** run `pip install -r requirements-bayes.txt`, then `python run_pipeline.py --refit`.
- **Re-extract the data from the source PDFs:** run `pip install -r requirements-extract.txt`, place the files listed below under `data_raw/` (or set `RAILWAY_RAW`), then run `python run_pipeline.py --extract`.

GitHub Actions rebuilds the outputs and runs `verify.py` on every push. Only the main model's posterior draws are committed. The sensitivity models are summarised in `outputs/model_diagnostics.json`.

## Contents

| Path | Contents |
|---|---|
| `data/railway_state_year.csv`, `..._wide.csv` | NCRB railway, railway-crossing and traffic deaths, cases and injured by state, year and category. Extracted by word coordinates. |
| `data/railway_validation_log.txt` | 6 939 checks that state rows equal the printed totals and that categories equal row totals. Three printed-text errors are documented. |
| `data/state_route_km.csv` | Route-km by state from the Year Books 2016–17, 2018–19 and 2024–25. |
| `data/national_passenger_km.csv` | Passenger-km by financial year, from the Year Books and the Economic Survey statistical appendix, with sources. |
| `data/rb_statement41f_fatalities.csv` | Railway Board Statement 41(F) fatalities by zone and category for 2022–23 to 2024–25. Printed inconsistencies are logged. |
| `data/state_population.csv` | Technical Group population projections. |
| `data/model_panel.csv` | Analysis panel of 22 states. Unreported state-years are set to missing (see `src/model_inputs.py`). |
| `docs/extraction_notes.md` | Tables and pages used, category definitions, and the 2024 reclassification. |
| `src/` | `extract_adsi_railway.py`, `extract_route_km.py`, `model_inputs.py`, `bayes_rail.py` (model, five scenarios), `derived.py`, `figures.py`. |
| `outputs/` | Main-model draws, diagnostics, derived quantities, imputations, state rates, reconciliation, figures. |
| `results/expected_key_results.json` | Values reported in the manuscript, checked by `verify.py`. |

## Source documents (not redistributed)

`data_raw/` should contain:

- `ncrb/ADSI_<year>.pdf`: NCRB *Accidental Deaths & Suicides in India* for 2014, 2015 and 2018–2024 ([ncrb.gov.in](https://www.ncrb.mha.gov.in/accidental-deaths-suicides-in-india-adsi.html)).
- `railway/IR_Year_Book_2016-17_ircep.pdf`, `IR_Year_Book_2018-19_ircep.pdf` and `IR_Year_Book_2024-25_English.pdf`: Indian Railways Year Books ([indianrailways.gov.in](https://indianrailways.gov.in), [ircep.gov.in](https://ircep.gov.in)).

Statement 41(F) values and the passenger-km series were transcribed with page references. The Annual Statistical Statements are on the Railway Board reports page, and the Economic Survey statistical appendix is on [indiabudget.gov.in](https://indiabudget.gov.in).

## Licences

- **Code:** MIT.
- **Derived data:** CC BY 4.0.
- **Government reports:** cited, not redistributed.

## Author

Siddalingaiah H S, Department of Community Medicine, Shridevi Institute of Medical Sciences and Research Hospital, Tumakuru, Karnataka, India. ORCID [0000-0002-4771-8285](https://orcid.org/0000-0002-4771-8285).
