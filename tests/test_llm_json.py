from app.summarize import parse_llm_json


def test_parse_llm_json_plain():
    out = parse_llm_json('{"summary":"x","technologies":["Python"],"structure":"y"}')
    assert out["summary"] == "x"


def test_parse_llm_json_code_fence():
    text = """```json\n{\"summary\":\"x\",\"technologies\":[\"Python\"],\"structure\":\"y\"}\n```"""
    out = parse_llm_json(text)
    assert out["structure"] == "y"