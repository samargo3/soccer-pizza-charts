# pipeline/

Python data pipeline. Code arrives in Phase 1–2, organized as:

- `ingest.py` — fetch + cache raw data from the source.
- `transform.py` — clean, per-90 rates, position tags.
- `compute.py` — percentile ranks within peer groups; export JSON.

See `.cursor/rules/100-python-pipeline.mdc` for conventions.
