# Contributing

Run `python -m unittest discover -s tests -v` before proposing changes.

For a bug report, include the Python version, tool version, a minimal synthetic HTML fixture, expected findings and actual rule IDs. Remove client data and credentials. Keep network access out of unit tests.

Useful next steps:

1. Validate language and region identifiers against an explicit maintained registry.
2. Compare complete cluster language maps, with tests for valid regional variants.
3. Support HTTP Link and XML sitemap hreflang as separate input methods.
4. Add report-to-report comparison for newly introduced error signatures.

Do not introduce arbitrary ranking scores or claims about Google indexing. New checks should describe their evidence, severity, limitations and authoritative reference.
