from app.rag import chunk_text


def test_chunk_text_basic():
    text = "A" * 5000
    chunks = chunk_text("x.py", text, chunk_chars=1000, overlap=100)
    assert len(chunks) >= 5
    assert chunks[0].file == "x.py"
    assert chunks[0].text


def test_chunk_text_overlap():
    text = "".join(str(i % 10) for i in range(3000))
    chunks = chunk_text("x.py", text, chunk_chars=500, overlap=50)
    assert len(chunks) > 1
    # overlap means chunk2 starts before chunk1 ends
    assert chunks[0].text[-50:] == chunks[1].text[:50]