# LinkedIn draft

A five-language website gives you five ways to serve customers, and several ways to connect the wrong pages.

I built a small open-source Python tool to check the HTML signals between translations: hreflang return links, self-references, canonical declarations, noindex directives and HTTP status.

It runs locally with no API key or third-party Python packages. Every finding includes a rule ID and evidence, with JSON, CSV and Markdown reports you can hand to a developer.

I tested it against deliberately broken fixtures and the five homepages of my own website. The included offline suite has 18 tests. The live check found no issues within the implemented rules; it does not measure ranking or Google indexing.

This is the same habit I learned running an industrial gas plant: diagnose, measure and document before claiming a result.

Repository: https://github.com/farshidghaffari/multilingual-seo-check

Initial release. AI-assisted implementation, with documented scope and reproducible examples.

#TechnicalSEO #InternationalSEO #Python #OpenSource
