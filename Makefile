.PHONY: install data warehouse analysis backtest test evals app

install:
	pip install -r requirements-dev.txt

data:          ## download raw Olist CSVs (only needed to rebuild the warehouse)
	python scripts/fetch_data.py

warehouse:     ## raw CSVs -> star schema Parquet
	python scripts/build_warehouse.py

analysis:      ## run every governed metric -> reports/findings.json
	python scripts/run_analysis.py

backtest:      ## delivery-estimate backtest -> reports/backtest.json
	python scripts/backtest_estimates.py

test:
	pytest -q

evals:
	python evals/run_evals.py

app:
	streamlit run app/streamlit_app.py
