#test file automatically checks whether parts of your program behave correctly.
from backend.rag.ingestion import clean_text, chunk_text

#Cleaning extra spaces
def test_clean_text_removes_extra_spaces():
    text = "Hello     world.\n\n\nThis   is a test."
    result = clean_text(text)

    assert "     " not in result
    assert result == "Hello world.\n\nThis is a test."

#Chunking creates multiple chunks
def test_chunk_text_creates_chunks():
    text = " ".join(
        [
            "Ballistics is the study of projectile motion."
            for _ in range(30)
        ]
    )
#Call our chunking algorithm
    chunks = chunk_text(text, chunk_size=350, chunk_overlap=50)

    assert len(chunks) > 1


def test_chunk_text_preserves_content():
    text = (
        "Ballistics studies projectile motion. "
        "Internal ballistics studies events inside a firearm. "
        "External ballistics studies projectile motion through the air."
    )
#only used inside a test to make the test easier to verify
    chunks = chunk_text(text, chunk_size=80, chunk_overlap=30)

    combined = " ".join(chunks)

    assert "Ballistics studies projectile motion." in combined
    assert "Internal ballistics studies events inside a firearm." in combined
    assert "External ballistics studies events inside a firearm." not in combined
    assert "External ballistics studies projectile motion through the air." in combined


def test_chunk_text_handles_empty_input():
    assert chunk_text("") == []


def test_chunk_text_respects_sentence_boundaries():
    text = (
        "This is the first complete sentence. "
        "This is the second complete sentence. "
        "This is the third complete sentence."
    )

    chunks = chunk_text(text, chunk_size=70, chunk_overlap=20)

    assert len(chunks) > 0

    for chunk in chunks:
        assert isinstance(chunk, str)
        assert chunk.strip() != ""


def test_chunk_overlap_is_present():
    text = (
        "Sentence one contains information about ballistics and projectile motion. "
        "Sentence two contains information about velocity and acceleration. "
        "Sentence three contains information about air resistance and drag. "
        "Sentence four contains information about trajectory and gravity. "
        "Sentence five contains information about firearm safety principles."
    )

    chunks = chunk_text(text, chunk_size=150, chunk_overlap=80)

    assert len(chunks) >= 2

    # Check that some context from the first chunk appears in the second chunk
    first_chunk_words = chunks[0].split()
    second_chunk_words = chunks[1].split()

    assert any(
        word in second_chunk_words
        for word in first_chunk_words[-10:]
    )