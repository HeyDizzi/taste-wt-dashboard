.PHONY: setup refresh dev

setup:            ## one-time: venv + deps
	python3 -m venv .venv && .venv/bin/pip install --quiet pyyaml

refresh:          ## raw exports -> data/processed/*.json (rerun when new data lands)
	.venv/bin/python pipeline/run.py

dev:              ## serve the dashboard at http://127.0.0.1:8471/app/
	@echo "dashboard: http://127.0.0.1:8471/app/"
	@python3 -m http.server 8471 --bind 127.0.0.1
