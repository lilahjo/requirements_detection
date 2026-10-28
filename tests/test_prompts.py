import pytest
import yaml

from prompts import (
    COT_ANSWER_MARKER,
    build_cot,
    build_few_shot,
    build_zero_shot,
    validate_inputs,
)

SAMPLE_TEXT = "4.1 Ensure that a user for the container has been created (Manual)"


def _write_pdf(path, text):
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref_at = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref_at,
    )
    path.write_bytes(bytes(out))
    return path


def test_validate_inputs(tmp_path):
    first = _write_pdf(tmp_path / "cis-r1.pdf", SAMPLE_TEXT)
    second = _write_pdf(tmp_path / "cis-r2.pdf", "5.5 Ensure that privileged containers are not used")

    doc1, doc2 = validate_inputs(first, str(second))
    assert doc1["name"] == "cis-r1"
    assert doc2["name"] == "cis-r2"
    assert "user for the container" in doc1["text"]
    assert "privileged containers" in doc2["text"]

    same1, same2 = validate_inputs(first, first)
    assert same1["text"] == same2["text"]

    not_pdf = tmp_path / "notes.pdf"
    not_pdf.write_text("just text")
    wrong_ext = tmp_path / "cis.txt"
    wrong_ext.write_bytes(first.read_bytes())
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")

    with pytest.raises(FileNotFoundError):
        validate_inputs(first, tmp_path / "missing.pdf")
    with pytest.raises(ValueError):
        validate_inputs(first, not_pdf)
    with pytest.raises(ValueError):
        validate_inputs(wrong_ext, first)
    with pytest.raises(ValueError):
        validate_inputs(first, empty)
    with pytest.raises(ValueError):
        validate_inputs(first, tmp_path)
    with pytest.raises(TypeError):
        validate_inputs(first, None)


def test_build_zero_shot():
    prompt = build_zero_shot(SAMPLE_TEXT)
    assert isinstance(prompt, str)
    assert SAMPLE_TEXT in prompt
    assert "key data element" in prompt
    assert "requirements:" in prompt
    assert prompt.rstrip().endswith("YAML:")
    with pytest.raises(ValueError):
        build_zero_shot("   ")


def test_build_few_shot():
    prompt = build_few_shot(SAMPLE_TEXT)
    assert isinstance(prompt, str)
    assert SAMPLE_TEXT in prompt
    assert "Example 1" in prompt and "Example 2" in prompt
    assert prompt.rstrip().endswith("YAML:")

    example = prompt.split("Example 2")[0].split("YAML:\n", 1)[1].split("\n\n")[0]
    parsed = yaml.safe_load(example)
    assert parsed["element1"]["name"] == "container user"
    assert len(parsed["element1"]["requirements"]) == 2

    with pytest.raises(TypeError):
        build_few_shot(None)


def test_build_cot():
    text = SAMPLE_TEXT + "\nmountpoint -- \"$(docker info -f '{{ .DockerRootDir }}')\""
    prompt = build_cot(text)
    assert isinstance(prompt, str)
    assert text in prompt
    assert "step by step" in prompt
    assert COT_ANSWER_MARKER in prompt
    assert prompt.rstrip().endswith("Reasoning:")
    with pytest.raises(ValueError):
        build_cot("")
