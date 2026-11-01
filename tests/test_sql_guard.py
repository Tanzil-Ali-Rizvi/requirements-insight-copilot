from pathlib import Path

import pytest
import yaml

from ric.sql_guard import MAX_ROWS, UnsafeSQL, validate

ATTACKS = yaml.safe_load((Path(__file__).parents[1] / "evals" / "guard_attacks.yaml").read_text())


@pytest.mark.parametrize("sql", [
    "SELECT COUNT(*) FROM fct_orders",
    "with x as (select 1 as a) select a from x",
    "SELECT * FROM fct_orders WHERE order_status = 'delete'",   # keyword inside a string is fine
    "SELECT 1 -- trailing comment",
    "SELECT 1;",
])
def test_allows_read_only_selects(sql):
    out = validate(sql)
    assert out.endswith(f"LIMIT {MAX_ROWS}")


@pytest.mark.parametrize("sql", ATTACKS)
def test_blocks_attacks(sql):
    with pytest.raises(UnsafeSQL):
        validate(sql)


@pytest.mark.parametrize("sql", ["", "   ", "SELEC 1", "SELECT 1; SELECT 2"])
def test_rejects_empty_malformed_or_multiple(sql):
    with pytest.raises(UnsafeSQL):
        validate(sql)
