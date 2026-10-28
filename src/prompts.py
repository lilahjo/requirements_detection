"""Task-1, functions 1-4: input validation and prompt construction.

validate_inputs() checks the two requirement PDFs and returns their text.
build_zero_shot(), build_few_shot() and build_cot() each turn the text of one
document into a prompt string that asks Gemma-3-1B for key data elements (KDEs)
in the YAML shape the rest of the pipeline expects:

    element1:
      name: "user privileges"
      requirements:
        - "Ensure a user for the container has been created"

The prompt text here is mirrored in PROMPT.md; keep the two in sync.
"""

import logging
import os
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

# Benchmark PDFs are ~2 MB; anything this large is almost certainly the wrong file.
MAX_FILE_BYTES = 50 * 1024 * 1024
PDF_MAGIC = b"%PDF-"

# The chain-of-thought prompt asks the model to put its YAML after this line,
# so the LLM runner can split the reasoning from the answer.
COT_ANSWER_MARKER = "FINAL YAML:"

PROMPT_TYPES = ("zero-shot", "few-shot", "chain-of-thought")

# pypdf logs a warning for every malformed xref entry in the CIS PDFs.
logging.getLogger("pypdf").setLevel(logging.ERROR)


# ---------------------------------------------------------------------------
# Function 1: input validation
# ---------------------------------------------------------------------------

def _validate_one(path):
    """Validate a single PDF path and return {"name", "path", "text"}."""
    if not isinstance(path, (str, os.PathLike)):
        raise TypeError(f"Expected a file path, got {type(path).__name__}")
    if isinstance(path, str) and not path.strip():
        raise ValueError("File path is empty")

    pdf_path = Path(path).expanduser()
    if not pdf_path.exists():
        raise FileNotFoundError(f"Input file not found: {pdf_path}")
    if not pdf_path.is_file():
        raise ValueError(f"Input path is not a file: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Input file must have a .pdf extension: {pdf_path.name}")

    size = pdf_path.stat().st_size
    if size == 0:
        raise ValueError(f"Input file is empty: {pdf_path.name}")
    if size > MAX_FILE_BYTES:
        raise ValueError(
            f"Input file is too large ({size} bytes, limit {MAX_FILE_BYTES}): {pdf_path.name}"
        )

    with open(pdf_path, "rb") as handle:
        if handle.read(len(PDF_MAGIC)) != PDF_MAGIC:
            raise ValueError(f"Input file is not a valid PDF: {pdf_path.name}")

    try:
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            raise ValueError(f"Encrypted PDFs are not supported: {pdf_path.name}")
        pages = [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as err:
        raise ValueError(f"Could not read PDF {pdf_path.name}: {err}") from err

    text = "\n".join(pages).strip()
    if not text:
        raise ValueError(f"No extractable text in PDF: {pdf_path.name}")

    return {"name": pdf_path.stem, "path": str(pdf_path.resolve()), "text": text}


def validate_inputs(first_pdf, second_pdf):
    """Validate the two requirements documents and extract their text.

    Each path must point to an existing, non-empty, readable, unencrypted PDF
    under MAX_FILE_BYTES that contains extractable text. The same file may be
    passed twice (the TA runs v1+v1 and v2+v2).

    Returns a tuple of two dicts, one per document, each with:
        name -- file name without extension, e.g. "docker-cis-v0"
                (used to name the output YAML, e.g. docker-cis-v0-kdes.yaml)
        path -- absolute path to the PDF
        text -- the full extracted text

    Raises TypeError, ValueError or FileNotFoundError on bad input.
    """
    return _validate_one(first_pdf), _validate_one(second_pdf)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_TASK_DESCRIPTION = (
    "You are a security analyst. Read the security requirements document below "
    "and identify its key data elements (KDEs). A key data element is a thing that "
    "the requirements protect or configure, such as a file, a user, a network "
    "setting, an image, a log, or a certificate. One key data element can map to "
    "several requirements."
)

_OUTPUT_FORMAT = (
    "Answer only with YAML in exactly this format, numbering the elements "
    "element1, element2, and so on:\n"
    "element1:\n"
    "  name: \"<short name of the key data element>\"\n"
    "  requirements:\n"
    "    - \"<requirement taken from the document>\"\n"
    "    - \"<another requirement for the same element>\""
)

ZERO_SHOT_TEMPLATE = (
    _TASK_DESCRIPTION + "\n\n"
    + _OUTPUT_FORMAT + "\n\n"
    "Document:\n"
    "\"\"\"\n"
    "{document_text}\n"
    "\"\"\"\n\n"
    "YAML:"
)

FEW_SHOT_TEMPLATE = (
    _TASK_DESCRIPTION + "\n\n"
    + _OUTPUT_FORMAT + "\n\n"
    "Example 1\n"
    "Document:\n"
    "\"\"\"\n"
    "4.1 Ensure that a user for the container has been created (Manual)\n"
    "5.24 Ensure that docker exec commands are not used with the user=root option (Manual)\n"
    "\"\"\"\n"
    "YAML:\n"
    "element1:\n"
    "  name: \"container user\"\n"
    "  requirements:\n"
    "    - \"Ensure that a user for the container has been created\"\n"
    "    - \"Ensure that docker exec commands are not used with the user=root option\"\n\n"
    "Example 2\n"
    "Document:\n"
    "\"\"\"\n"
    "3.1 Ensure that the docker.service file ownership is set to root:root (Automated)\n"
    "3.2 Ensure that docker.service file permissions are appropriately set (Automated)\n"
    "4.9 Ensure that COPY is used instead of ADD in Dockerfiles (Manual)\n"
    "4.10 Ensure secrets are not stored in Dockerfiles (Manual)\n"
    "\"\"\"\n"
    "YAML:\n"
    "element1:\n"
    "  name: \"docker.service file\"\n"
    "  requirements:\n"
    "    - \"Ensure that the docker.service file ownership is set to root:root\"\n"
    "    - \"Ensure that docker.service file permissions are appropriately set\"\n"
    "element2:\n"
    "  name: \"Dockerfile\"\n"
    "  requirements:\n"
    "    - \"Ensure that COPY is used instead of ADD in Dockerfiles\"\n"
    "    - \"Ensure secrets are not stored in Dockerfiles\"\n\n"
    "Now do the same for this document.\n"
    "Document:\n"
    "\"\"\"\n"
    "{document_text}\n"
    "\"\"\"\n"
    "YAML:"
)

COT_TEMPLATE = (
    _TASK_DESCRIPTION + "\n\n"
    "Think step by step:\n"
    "Step 1: List every requirement in the document. Requirements usually start "
    "with \"Ensure\" and have a section number such as 4.1.\n"
    "Step 2: For each requirement, name the key data element it protects or "
    "configures (for example \"container user\", \"docker.sock\", \"TLS certificate\").\n"
    "Step 3: Group requirements that share the same key data element.\n"
    "Step 4: Write the groups as YAML.\n\n"
    "Show your reasoning for steps 1 to 3, then write the line "
    + COT_ANSWER_MARKER + " followed by the YAML and nothing else.\n\n"
    + _OUTPUT_FORMAT + "\n\n"
    "Document:\n"
    "\"\"\"\n"
    "{document_text}\n"
    "\"\"\"\n\n"
    "Reasoning:"
)


def _check_document_text(document_text):
    if not isinstance(document_text, str):
        raise TypeError(f"document_text must be a string, got {type(document_text).__name__}")
    text = document_text.strip()
    if not text:
        raise ValueError("document_text is empty")
    return text


# ---------------------------------------------------------------------------
# Functions 2-4: prompt builders
# ---------------------------------------------------------------------------

def build_zero_shot(document_text):
    """Return a zero-shot prompt asking for the KDEs in document_text."""
    return ZERO_SHOT_TEMPLATE.format(document_text=_check_document_text(document_text))


def build_few_shot(document_text):
    """Return a few-shot prompt (two worked examples) for the KDEs in document_text."""
    return FEW_SHOT_TEMPLATE.format(document_text=_check_document_text(document_text))


def build_cot(document_text):
    """Return a chain-of-thought prompt for the KDEs in document_text.

    The model is told to reason first and put its YAML after COT_ANSWER_MARKER.
    """
    return COT_TEMPLATE.format(document_text=_check_document_text(document_text))
