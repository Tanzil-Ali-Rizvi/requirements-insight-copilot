"""The copilot: routes a question to documents, data or both, and answers with its source.

Route "docs"  -> retrieve BRD / policy / story sections, answer extractively (or with an LLM), cite sections.
Route "data"  -> match a governed metric and run its SQL; with an LLM configured, unmatched questions
                 are translated to SQL, checked by the guard and run on the sandboxed warehouse.
Route "both"  -> do both and show them together (e.g. "are we meeting the handoff target?").
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

import pandas as pd
from rank_bm25 import BM25Okapi

from . import llm
from .metrics import METRICS, Metric
from .retrieval import Hit, best_sentences, default_retriever
from .sql_guard import UnsafeSQL, validate
from .text import tokenize
from .warehouse import SCHEMA_DOC, query

DOC_CUES = re.compile(
    r"\b(requirements?|brd|polic(y|ies)|sla|acceptance|criteria|user stor(y|ies)|stakeholders?|raci|scope|"
    r"objectives?|targets?|approv\w*|owns?|owner|responsible|accountable|process|definition|define[ds]?|"
    r"defined|escalat\w*|watchlist|compensation|refund|exemptions?|notice|alerts?|scorecard|out of scope|"
    r"exempt\w*|in scope|risks?|mitigation|assumptions?|constraints?|nfr|fr-\d+|br-\d+|us-\d+|to-be|as-is|"
    r"recommend\w*|should we|plan|rule|must|allowed|privacy|retrain\w*|how is .* set|what happens)\b",
    re.IGNORECASE)
DATA_CUES = re.compile(
    r"\b(how many|how much|what share|share of|rates?|percent\w*|%|which (states?|regions?|sellers?|categor\w+|months?)|"
    r"trend|monthly|by month|over time|average|avg|median|compare|top|worst|best|highest|lowest|revenue|gmv|"
    r"count|number of|late orders|review scores?|stars?|days|lose time|cause|drive[sr]?|concentrat\w*|"
    r"interstate|how accurate|avoid\w*|volume|status)\b",
    re.IGNORECASE)

BOTH_CUES = re.compile(
    r"\b(meet\w*|on track|against|versus the|vs the|compared? (to|with) the)\b.*\b(targets?|sla|objectives?|goals?)\b",
    re.IGNORECASE)

METRIC_MIN_SCORE = 2.5   # BM25 score below which no governed metric is a confident match


@dataclass
class Answer:
    question: str
    route: str                      # docs | data | both | none
    text: str
    citations: list[str] = field(default_factory=list)
    metric: str | None = None
    sql: str | None = None
    table: pd.DataFrame | None = None
    mode: str = "offline"           # offline | llm
    error: str | None = None


@lru_cache(maxsize=1)
def _metric_index() -> BM25Okapi:
    return BM25Okapi([tokenize(m.search_text) for m in METRICS])


# A governed metric only answers questions about deliveries and orders; anything else is out of scope.
DOMAIN = frozenset(tokenize(
    "late lateness delay delays delayed deliver delivery delivered deliveries order orders parcel parcels "
    "shipment shipments ship shipping dispatch handoff handoffs carrier carriers transit seller sellers review "
    "reviews stars star promise promised estimate estimated revenue gmv status cancelled canceled peak "
    "on-time missed arrive arrived waiting unhappy fulfilment bottleneck"))


def match_metric(question: str) -> tuple[Metric | None, float]:
    tokens = tokenize(question)
    if not DOMAIN.intersection(tokens):
        return None, 0.0
    scores = _metric_index().get_scores(tokens)
    i = max(range(len(scores)), key=lambda j: scores[j])
    return (METRICS[i], float(scores[i])) if scores[i] >= METRIC_MIN_SCORE else (None, float(scores[i]))


def route(question: str) -> str:
    # "Are we meeting the target?" needs the number from the data and the target from the documents.
    if BOTH_CUES.search(question) and match_metric(question)[0]:
        return "both"
    doc_cues = len(DOC_CUES.findall(question))
    data_cues = len(DATA_CUES.findall(question))
    if doc_cues and data_cues:
        return "docs" if doc_cues > data_cues else "data"
    if doc_cues:
        return "docs"
    if data_cues:
        return "data"
    metric, score = match_metric(question)
    hits = default_retriever().search(question, k=1)
    if metric and (not hits or score >= hits[0].score * 0.5):
        return "data"
    return "docs" if hits else "none"


# ---------------------------------------------------------------- docs
def _answer_docs(question: str) -> Answer:
    hits: list[Hit] = default_retriever().search(question, k=4)
    if not hits:
        return Answer(question, "docs", "I could not find this in the project documents.")
    if llm.enabled():
        context = "\n\n".join(f"[{i + 1}] {h.chunk.citation}\n{h.chunk.text}" for i, h in enumerate(hits))
        text = llm.chat([
            {"role": "system", "content": "You answer questions about a business-requirements project using ONLY "
             "the numbered context. Cite sources like [1]. If the context does not contain the answer, say so."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ])
        return Answer(question, "docs", text, [h.chunk.citation for h in hits], mode="llm")
    top = hits[0].chunk
    return Answer(question, "docs", best_sentences(question, top.text), [top.citation] +
                  [h.chunk.citation for h in hits[1:2]])


# ---------------------------------------------------------------- data
def _run_metric(question: str, metric: Metric) -> Answer:
    sql = validate(metric.sql)
    df = query(sql)
    return Answer(question, "data", metric.summarize(df), [f"Governed metric: {metric.title}"],
                  metric=metric.key, sql=metric.sql.strip(), table=df)


def _llm_sql(question: str) -> Answer:
    messages = [
        {"role": "system", "content": "Write one DuckDB SELECT query that answers the question. Use only these "
         f"tables:\n{SCHEMA_DOC}\nReturn only SQL, no explanation, no code fences."},
        {"role": "user", "content": question},
    ]
    last_error = ""
    for _ in range(2):
        sql = llm.chat(messages).strip().removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
        try:
            df = query(validate(sql))
        except UnsafeSQL as exc:
            return Answer(question, "data", "The generated query was blocked by the SQL guard.", sql=sql,
                          mode="llm", error=str(exc))
        except Exception as exc:  # SQL error: give the model one chance to fix it
            last_error = str(exc)
            messages += [{"role": "assistant", "content": sql},
                         {"role": "user", "content": f"That failed: {last_error}. Return a corrected query."}]
            continue
        summary = llm.chat([
            {"role": "system", "content": "Summarise the query result in 1-2 sentences for a business reader. "
             "Use only numbers shown in the result."},
            {"role": "user", "content": f"Question: {question}\nResult:\n{df.head(20).to_string(index=False)}"},
        ])
        return Answer(question, "data", summary, ["Generated SQL (checked by the guard)"], sql=sql, table=df, mode="llm")
    return Answer(question, "data", "I could not write a working query for that.", mode="llm", error=last_error)


def _answer_data(question: str) -> Answer:
    metric, _ = match_metric(question)
    if metric:
        return _run_metric(question, metric)
    if llm.enabled():
        return _llm_sql(question)
    examples = "; ".join(m.question for m in METRICS[:6])
    return Answer(question, "none", "That is outside the governed questions I can answer offline. "
                  f"Try for example: {examples}. Configure an LLM to ask free-form data questions.")


# ---------------------------------------------------------------- entry point
def ask(question: str) -> Answer:
    question = question.strip()
    r = route(question)
    if r == "docs":
        return _answer_docs(question)
    if r == "data":
        return _answer_data(question)
    if r == "both":
        d, q = _answer_data(question), _answer_docs(question)
        return Answer(question, "both", f"**Data:** {d.text}\n\n**Documents:** {q.text}",
                      d.citations + q.citations, d.metric, d.sql, d.table, mode=q.mode)
    return Answer(question, "none", "I could not find an answer in the documents or the data.")
