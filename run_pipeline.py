"""Re-run: python run_pipeline.py [--refit] [--extract]
  default : model panel, derived quantities and figures from the committed main-model draws, then verify.py
  --refit : refit the five Bayesian models first (NumPyro; pip install -r requirements-bayes.txt; a few minutes)
  --extract : re-extract data/ from the source PDFs in data_raw/ (see README; pip install pymupdf)"""
import pathlib, subprocess, sys
R = pathlib.Path(__file__).resolve().parent
run = lambda *a: subprocess.run([sys.executable, *map(str, a)], cwd=R, check=True)
if "--extract" in sys.argv: run("src/extract_adsi_railway.py"); run("src/extract_route_km.py")
run("src/model_inputs.py")
if "--refit" in sys.argv: run("src/bayes_rail.py")
run("src/derived.py"); run("src/figures.py"); run("verify.py")
