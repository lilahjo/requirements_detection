# requirements_detection

```
kde-pipeline/
├── README.md                  # names, BannerIDs, emails, "LLM: Gemma-3-1B"
├── PROMPT.md                  # zero-shot / few-shot / chain-of-thought sections
├── requirements.txt           # pinned versions, e.g. PyYAML==6.0.2
├── pytest.ini                 # pythonpath = src
├── .github/workflows/tests.yml
├── src/
│   ├── prompts.py             # A: validate_inputs, build_zero_shot, build_few_shot, build_cot
│   ├── extractor.py           # B: run_gemma_on_docs, write_llm_log
│   ├── comparator.py          # B: load_yamls, diff_element_names, diff_requirements
│   ├── executor.py            # C: read_diff_files, map_to_hadolint_rules, run_hadolint, write_csv
│   └── main.py                # C: takes two PDFs, runs the whole pipeline
├── tests/
│   ├── test_prompts.py
│   ├── test_extractor.py
│   ├── test_comparator.py
│   └── test_executor.py
├── data/
│   ├── docker-cis-v0.pdf
│   ├── docker-cis-v1.pdf
│   ├── docker-cis-v2.pdf
│   └── dockerfiles.zip
└── outputs/                   # YAMLs, TEXT files, CSV (generated)
```

## Team

| Name | Role | Banner ID | Email|
|---|---|---|---|
| Lilah Johnson |Task-3 | 904300259|laj0039|
| Fredrika Dunson |Task-1 functions 1-4 |||
| Trinity|Task-1 functions 5-6 |||

