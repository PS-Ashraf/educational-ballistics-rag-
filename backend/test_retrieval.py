from backend.rag.retrieval import retrieve_context


def test_revolvers_retrieve_results():
    results = retrieve_context("What is a revolver?")

    assert len(results) > 0
    assert len(results) <= 4


def test_revolvers_return_relevant_source():
    results = retrieve_context("What is a revolver?")

    sources = [
        result["metadata"].get("source")
        for result in results
    ]

    assert "1. What is a Revolver.txt" in sources


def test_retrieval_returns_source_metadata():
    results = retrieve_context("What are Indian firearms laws?")

    assert len(results) > 0

    for result in results:
        assert "metadata" in result
        assert "source" in result["metadata"]


def test_indian_law_retrieves_correct_source():
    results = retrieve_context("What are Indian firearms laws?")

    sources = [
        result["metadata"].get("source")
        for result in results
    ]

    assert "Indian Firearms Laws.txt" in sources


def test_out_of_scope_query_returns_no_results():
    results = retrieve_context("What is the capital of France?")

    assert results == []


def test_results_are_limited_to_top_k():
    results = retrieve_context(
        "What is a revolver?",
        top_k=2
    )

    assert len(results) <= 2


def test_results_contain_similarity_and_distance():
    results = retrieve_context("What is a revolver?")

    assert len(results) > 0

    for result in results:
        assert "similarity" in result
        assert "distance" in result
        assert isinstance(result["similarity"], float)
        assert isinstance(result["distance"], float)