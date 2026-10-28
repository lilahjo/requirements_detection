# Prompts

Prompts used with **Gemma-3-1B** (`google/gemma-3-1b-it`) to identify key data elements (KDEs) in the CIS Docker Benchmark PDFs. They are built by `src/prompts.py` (`build_zero_shot`, `build_few_shot`, `build_cot`). `{document_text}` is replaced with the text of the document (or chunk of the document) being analysed.

## zero-shot

The task and the output format only, with no examples.

```text
You are a security analyst. Read the security requirements document below and identify its key data elements (KDEs). A key data element is a thing that the requirements protect or configure, such as a file, a user, a network setting, an image, a log, or a certificate. One key data element can map to several requirements.

Answer only with YAML in exactly this format, numbering the elements element1, element2, and so on:
element1:
  name: "<short name of the key data element>"
  requirements:
    - "<requirement taken from the document>"
    - "<another requirement for the same element>"

Document:
"""
{document_text}
"""

YAML:
```

## few-shot

The same task with two worked examples taken from the CIS Docker Benchmark.

```text
You are a security analyst. Read the security requirements document below and identify its key data elements (KDEs). A key data element is a thing that the requirements protect or configure, such as a file, a user, a network setting, an image, a log, or a certificate. One key data element can map to several requirements.

Answer only with YAML in exactly this format, numbering the elements element1, element2, and so on:
element1:
  name: "<short name of the key data element>"
  requirements:
    - "<requirement taken from the document>"
    - "<another requirement for the same element>"

Example 1
Document:
"""
4.1 Ensure that a user for the container has been created (Manual)
5.24 Ensure that docker exec commands are not used with the user=root option (Manual)
"""
YAML:
element1:
  name: "container user"
  requirements:
    - "Ensure that a user for the container has been created"
    - "Ensure that docker exec commands are not used with the user=root option"

Example 2
Document:
"""
3.1 Ensure that the docker.service file ownership is set to root:root (Automated)
3.2 Ensure that docker.service file permissions are appropriately set (Automated)
4.9 Ensure that COPY is used instead of ADD in Dockerfiles (Manual)
4.10 Ensure secrets are not stored in Dockerfiles (Manual)
"""
YAML:
element1:
  name: "docker.service file"
  requirements:
    - "Ensure that the docker.service file ownership is set to root:root"
    - "Ensure that docker.service file permissions are appropriately set"
element2:
  name: "Dockerfile"
  requirements:
    - "Ensure that COPY is used instead of ADD in Dockerfiles"
    - "Ensure secrets are not stored in Dockerfiles"

Now do the same for this document.
Document:
"""
{document_text}
"""
YAML:
```

## chain-of-thought

The model reasons through four steps first, then writes its YAML after the line `FINAL YAML:`.

```text
You are a security analyst. Read the security requirements document below and identify its key data elements (KDEs). A key data element is a thing that the requirements protect or configure, such as a file, a user, a network setting, an image, a log, or a certificate. One key data element can map to several requirements.

Think step by step:
Step 1: List every requirement in the document. Requirements usually start with "Ensure" and have a section number such as 4.1.
Step 2: For each requirement, name the key data element it protects or configures (for example "container user", "docker.sock", "TLS certificate").
Step 3: Group requirements that share the same key data element.
Step 4: Write the groups as YAML.

Show your reasoning for steps 1 to 3, then write the line FINAL YAML: followed by the YAML and nothing else.

Answer only with YAML in exactly this format, numbering the elements element1, element2, and so on:
element1:
  name: "<short name of the key data element>"
  requirements:
    - "<requirement taken from the document>"
    - "<another requirement for the same element>"

Document:
"""
{document_text}
"""

Reasoning:
```
