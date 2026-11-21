.PHONY: install test demo plot
install:
	python -m pip install -e '.[dev]'
test:
	python -m pytest -q
demo:
	python scripts/run_synthetic_demo.py --config configs/synthetic_demo.yaml
plot:
	python scripts/make_plots.py --input outputs/synthetic_demo/results.json --output outputs/synthetic_demo/metrics.png
