from ric.retrieval import BM25Retriever, best_sentences, load_chunks


def test_chunks_cover_all_docs():
    docs = {c.doc for c in load_chunks()}
    for expected in ("BRD.md", "user_stories.md", "findings.md", "data_dictionary.md",
                     "policies/seller_handling_policy.md", "policies/delivery_promise_policy.md",
                     "process/as_is.md", "process/to_be.md"):
        assert expected in docs


def test_mermaid_is_not_indexed():
    assert not any("flowchart" in c.text for c in load_chunks())


def test_search_and_citation():
    hits = BM25Retriever(load_chunks()).search("watchlist escalation for sellers", k=3)
    assert hits and hits[0].chunk.citation == "policies/seller_handling_policy.md § Watchlist and escalation"


def test_best_sentences_picks_relevant_text():
    text = ("Cats are small. The handoff SLA is the shipping limit. Dogs bark. Birds fly. Fish swim. "
            "Ants dig. Bees buzz. Cows moo. Owls hoot.")
    assert best_sentences("what is the handoff sla", text, n=1) == "The handoff SLA is the shipping limit."


def test_short_sections_are_returned_whole():
    assert best_sentences("anything", "One. Two.") == "One. Two."


def test_best_sentences_reads_table_rows():
    text = "| ID | Requirement |\n| --- | --- |\n| FR-02 | Alert sellers 24 hours before the limit |"
    assert "Alert sellers" in best_sentences("FR-02 alert", text)
