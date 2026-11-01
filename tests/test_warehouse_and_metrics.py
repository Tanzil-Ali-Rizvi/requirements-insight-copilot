import pytest

from ric.metrics import BY_KEY, METRICS
from ric.sql_guard import validate
from ric.warehouse import query


def test_row_counts():
    assert query("SELECT COUNT(*) AS n FROM fct_orders").n[0] == 99_441
    assert query("SELECT COUNT(*) AS n FROM fct_order_items").n[0] == 112_650
    assert query("SELECT COUNT(*) AS n FROM dim_seller").n[0] == 3_095


def test_order_grain_is_unique():
    assert query("SELECT COUNT(*) - COUNT(DISTINCT order_id) AS d FROM fct_orders").d[0] == 0


@pytest.mark.parametrize("sql", [
    "SELECT * FROM read_csv_auto('/etc/passwd')",
    "SELECT * FROM 'data/warehouse/fct_orders.parquet'",
    "SET enable_external_access = true",
])
def test_sandbox_blocks_file_access_even_without_guard(sql):
    with pytest.raises(Exception):
        query(sql)


@pytest.mark.parametrize("metric", METRICS, ids=lambda m: m.key)
def test_every_metric_runs_and_summarises(metric):
    df = query(validate(metric.sql))
    assert len(df) > 0
    assert len(metric.summarize(df)) > 20


def test_headline_numbers():
    df = query(validate(BY_KEY["late_rate_overall"].sql))
    assert int(df.delivered_orders[0]) == 96_470
    assert int(df.late_orders[0]) == 6_534
    assert round(float(df.late_rate[0]), 3) == 0.068
    handoff = query(validate(BY_KEY["seller_handoff"].sql)).set_index("seller_handoff")
    assert handoff.loc["Late handoff", "late_rate"] > 3 * handoff.loc["On-time handoff", "late_rate"]
