# Multilingual SEO Check

A small, dependency-free Python CLI that checks the HTML signals connecting translated pages and saves evidence you can inspect or use in CI.

Built by [Farshid Ghaffari](https://farshidghaffari.net/), a plant engineer building websites, SEO workflows and AI tools for technical businesses. The starting problem is practical: a five-language website needs its language links checked every time pages change.

## Run it in one minute

Python 3.10 or newer. No packages, account, API key or paid service required.

```bash
git clone https://github.com/farshidghaffari/multilingual-seo-check.git
cd multilingual-seo-check
python seo_check.py --manifest examples/healthy/manifest.json --output output/healthy
python seo_check.py --manifest examples/broken/manifest.json --output output/broken
```

The healthy example exits `0`. The deliberately broken example exits `1` and demonstrates a missing return link, a relative alternate URL, a missing self-reference and a `noindex` page. Both examples use synthetic HTML at example.com and make no network requests.

For a live site, place each translated URL on a separate line:

```bash
python seo_check.py --urls examples/urls.txt --output output/live
```

The included URL list checks the five homepages of my public portfolio. Replace it with your own pages. Only URLs explicitly listed are fetched. No recursive crawling or automatic fetching of external alternate targets occurs.

## What it checks

| Rule | What the evidence shows | Level |
| --- | --- | --- |
| `alternate_not_absolute` | A hreflang target is not an absolute HTTP(S) URL | Error |
| `missing_return_link` | A checked target does not link back to the source URL | Error |
| `missing_self_reference` | The hreflang set omits its own final URL | Error |
| `duplicate_language` | A language code appears more than once on a page | Error |
| `noindex` | HTML robots/googlebot meta or X-Robots-Tag contains noindex/none | Error |
| `http_status`, `alternate_http_status` | A checked page or alternate returns a non-200 response | Error |
| `canonical_count`, `canonical_other` | Missing, multiple or non-self canonical declarations | Review warning |
| `target_not_checked` | Target omitted from inputs, redirected, blocked or failed; reciprocity unknown | Coverage warning |
| `fetch_incomplete` | A request failed or robots.txt prevented a fetch | Coverage warning |
| `redirected` | Input URL differs from the final URL | Review warning |
| `missing_title`, `missing_html_lang`, `no_html_hreflang` | Missing HTML metadata within this checker's scope | Review warning |

Warnings do not imply a Google policy violation. A missing canonical is not automatically an indexing error. A page can use valid HTTP-header or sitemap hreflang declarations which this HTML checker cannot see.

## Outputs

Every run writes:

- `report.json`: page observations, SHA-256 of decoded HTML, tool version and findings.
- `issues.csv`: one finding per row for sorting, filtering and assigning fixes.
- `report.md`: readable evidence table for reviews and issue discussions.

The source HTML is not included in reports. Page URLs, titles and observed metadata are included. Review outputs before publishing a client audit. CSV cells that could start a spreadsheet formula are escaped.

Exit codes: `0` means no error-level findings in the implemented checks, `1` means findings need attention, and `2` means invalid input or incomplete fetch coverage. Warnings can remain on exit `0`; this is not a full SEO pass.

## Live example and reproducibility

See [the dated live report](examples/live-report-2026-10-24/report.md), [sample findings](examples/broken-report/report.md) and [methodology](docs/methodology.md). A live result is a point-in-time observation, not a promise about today's site. Offline fixtures are stable and reproducible.

```bash
python -m unittest discover -s tests -v
```

CI runs the offline test suite on Python 3.10, 3.11, 3.12 and 3.13. Tests exercise reciprocal clusters, malformed alternates, redirects, noindex, incomplete coverage, robots exclusions, report escaping and CLI exit codes. Live tests are excluded from CI to avoid network-dependent builds.

## Why this project exists

Full SEO crawlers already cover many more checks. This project focuses on a smaller handover problem: a developer or site owner needs to know which translated pages disagree and what evidence supports each finding. It uses explicit inputs, stable rule IDs and machine-readable reports rather than an invented SEO score.

This is an independently written initial release, developed with AI assistance. It is usable as a local CLI and a reference implementation. It has not been validated on large production websites, and no client ranking gains are claimed.

## Scope and limits

- Reads server HTML, without JavaScript rendering.
- Checks only HTML hreflang declarations, not HTTP Link headers or sitemap declarations.
- Does not validate ISO language/region codes, translation quality, page equivalence or every member's full language matrix.
- Does not measure Core Web Vitals, Search Console indexing, traffic, backlinks, rich-result eligibility or AI visibility.
- Does not calculate a ranking score or guarantee better search positions.
- Live mode obeys robots.txt, uses a 30-page default cap, a 2 MB response limit, timeouts and a delay. Failed robots checks stop that origin's fetches. Cross-host redirects are refused.
- Run as a trusted local CLI. Do not expose it as an unauthenticated URL-fetching web service. Only audit sites you are authorized to access.

## Contribute and cite

See [CONTRIBUTING.md](CONTRIBUTING.md) for reproducible bug reports and useful next steps. Cite this repository URL plus a commit SHA and the tool version for reproducibility. This project is a software reference, not a published research paper or standards certification.

MIT license. Author: Farshid Ghaffari.
