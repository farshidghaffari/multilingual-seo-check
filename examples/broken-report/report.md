# Multilingual SEO check

Pages: 2 | Errors: 4 | Warnings: 0

HTML-only observations. These checks do not measure ranking or Google index status.

| Severity | Rule | Page | Target | Evidence |
| --- | --- | --- | --- | --- |
| error | missing_return_link | https://example.com/ | https://example.com/fa/ | Target does not link back to this final URL |
| error | alternate_not_absolute | https://example.com/fa/ | /fa/ | hreflang target must be an absolute HTTP(S) URL |
| error | missing_self_reference | https://example.com/fa/ |  | Hreflang set omits this final URL |
| error | noindex | https://example.com/fa/ |  | Index restriction: noindex, |
