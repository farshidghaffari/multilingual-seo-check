# Methodology and sources

## Research decision

Reviewed on 24 October 2026:

- [Google: localized versions](https://developers.google.com/search/docs/specialty/international/localized-versions). Source for absolute alternate URLs, self-references and return links.
- [Google: multilingual sites](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites). Context for separate language URLs and user-selectable language links.
- [Google: canonical declarations](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls). Canonicals express a preference; their absence alone is not a ranking failure.
- [Open SEO Crawler](https://github.com/puneetindersingh/open-seo-crawler). An existing broad crawler covering many technical SEO checks.
- [SEO Analyzer](https://github.com/ihuzaifashoukat/seo-analyzer). Another general-purpose modular audit toolkit.

These sources support a focused implementation choice. They do not establish market demand, uniqueness, commercial traction or comparative performance. No code was copied from these projects. This implementation does not claim Google endorsement or complete conformance with all international SEO guidance.

## Observation model

1. Take an explicit list of URLs, or a manifest mapping URLs to saved HTML files.
2. In live mode, read robots.txt and fetch allowed URLs sequentially with timeouts.
3. Parse title, HTML language, canonical and hreflang links from the HTML head, plus indexing directives.
4. Compare only pages actually fetched. Keep unknown targets as coverage warnings.
5. Preserve rule IDs, URLs and evidence in JSON, CSV and Markdown.

HTMLParser performs tolerant parsing rather than browser HTML5 tree correction. Malformed head markup may produce different observations from a browser. Fragments are removed and host/scheme case is normalized for lookup, but path, query and trailing-slash distinctions are retained. Redirected alternates are coverage warnings unless their exact target was checked. Return-link detection is URL-based and does not validate language-label consistency.

SHA-256 records the decoded HTML string, not raw response bytes. It aids comparison but does not archive the page. Live output does not prove Google fetched, indexed or selected any canonical URL.

## Verification

Offline tests use healthy and broken synthetic clusters. Live verification uses only the author's public portfolio homepages. Sample outputs are evidence of this tool's behavior, not a comprehensive SEO audit.
