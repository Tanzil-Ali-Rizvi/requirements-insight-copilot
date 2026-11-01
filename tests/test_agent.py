import pytest

from ric import agent, llm


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(llm, "enabled", lambda: False)


def test_docs_answer_cites_section():
    a = agent.ask("What is the seller handoff SLA?")
    assert a.route == "docs"
    assert a.citations[0] == "policies/seller_handling_policy.md § Handoff SLA"
    assert "shipping limit" in a.text


def test_data_answer_has_table_sql_and_summary():
    a = agent.ask("Which regions get the most late deliveries?")
    assert a.route == "data" and a.metric == "late_rate_by_region"
    assert a.table is not None and "customer_region" in a.table.columns
    assert a.sql.startswith("SELECT")
    assert "Northeast" in a.text


def test_both_route_combines_data_and_documents():
    a = agent.ask("Are we meeting the late rate target?")
    assert a.route == "both"
    assert "6.8%" in a.text and "5.0%" in a.text


def test_offline_unmatched_data_question_explains_limits():
    for q in ("What is the average weight of products sold on Tuesdays?", "What is the weather in Sao Paulo?"):
        a = agent.ask(q)
        assert a.metric is None and a.table is None


def test_llm_sql_is_guarded(monkeypatch):
    monkeypatch.setattr(llm, "enabled", lambda: True)
    monkeypatch.setattr(llm, "chat", lambda messages, **kw: "DROP TABLE fct_orders")
    a = agent._llm_sql("delete everything")
    assert "blocked" in a.text and a.error


def test_llm_sql_retries_once_on_error(monkeypatch):
    replies = iter(["SELECT nope FROM fct_orders", "SELECT COUNT(*) AS n FROM fct_orders", "There are 99,441 orders."])
    monkeypatch.setattr(llm, "enabled", lambda: True)
    monkeypatch.setattr(llm, "chat", lambda messages, **kw: next(replies))
    a = agent._llm_sql("how many orders?")
    assert a.table.n[0] == 99_441 and a.text == "There are 99,441 orders." and a.mode == "llm"
