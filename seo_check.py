"""Evidence-based checks for small multilingual sites. Python 3.10+, stdlib only."""
from __future__ import annotations
import argparse
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser

VERSION = '0.1.0'
AGENT = 'MultilingualSEOCheck/0.1 (+https://github.com/farshidghaffari)'
LIMIT = 2_000_000


def normalize(url):
    p = urlsplit(url)
    if p.scheme.lower() not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('Expected an absolute HTTP(S) URL without credentials')
    if p.fragment:
        p = p._replace(fragment='')
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or '/', p.query, ''))


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.head_depth = 0
        self.in_title = False
        self.title = ''
        self.lang = ''
        self.canonicals = []
        self.alternates = []
        self.robots = []
        self.base = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html': self.lang = a.get('lang', '')
        if tag == 'head': self.head_depth += 1
        if not self.head_depth: return
        if tag == 'title': self.in_title = True
        if tag == 'base' and self.base is None: self.base = a.get('href', '')
        if tag == 'meta' and a.get('name', '').lower() in ('robots', 'googlebot'):
            self.robots.append(a.get('content', ''))
        if tag != 'link': return
        rel = a.get('rel', '').lower().split()
        if 'canonical' in rel: self.canonicals.append(a.get('href', ''))
        if 'alternate' in rel and 'hreflang' in a:
            self.alternates.append({'language': a['hreflang'].lower(), 'url': a.get('href', '')})

    def handle_endtag(self, tag):
        if tag == 'head': self.head_depth = max(0, self.head_depth - 1)
        if tag == 'title': self.in_title = False

    def handle_data(self, data):
        if self.in_title: self.title += data


def parse_page(url, html, status=200, headers=None, requested_url=None):
    p = PageParser()
    p.feed(html)
    base = urljoin(url, p.base) if p.base else url
    return {'url': normalize(url), 'requested_url': requested_url or url,
            'status': status, 'title': p.title.strip(), 'lang': p.lang,
            'canonicals': [urljoin(base, x) if x else '' for x in p.canonicals],
            'alternates': p.alternates, 'robots': p.robots,
            'x_robots_tag': (headers or {}).get('X-Robots-Tag', ''),
            'sha256': hashlib.sha256(html.encode('utf-8')).hexdigest(), 'error': None}


def audit(pages):
    issues = []
    by_url = {p['url']: p for p in pages if not p.get('error')}
    def add(p, rule, evidence, target='', severity='error'):
        issues.append(dict(url=p['url'], rule=rule, severity=severity, target=target, evidence=evidence))
    for p in pages:
        if p.get('error'):
            add(p, 'fetch_incomplete', p['error'], severity='warning')
            continue
        if p['status'] != 200: add(p, 'http_status', str(p['status']))
        if p['requested_url'] != p['url']:
            add(p, 'redirected', 'Requested URL redirects to final URL', p['requested_url'], 'warning')
        if not p['title']: add(p, 'missing_title', 'No non-empty title in HTML head', severity='warning')
        if not p['lang']: add(p, 'missing_html_lang', 'No HTML lang attribute', severity='warning')
        directives = ','.join(p['robots'] + [p['x_robots_tag']]).lower()
        tokens = set(directives.replace(':', ',').replace(' ', ',').split(','))
        if tokens & {'noindex', 'none'}: add(p, 'noindex', 'Index restriction: ' + directives)
        if len(p['canonicals']) != 1:
            add(p, 'canonical_count', f"Expected one canonical, found {len(p['canonicals'])}", severity='warning')
        elif p['canonicals'][0] != p['url']:
            add(p, 'canonical_other', 'Canonical differs from final URL; review intent', p['canonicals'][0], 'warning')
        alts = p['alternates']
        if not alts:
            add(p, 'no_html_hreflang', 'No HTML hreflang; sitemap and HTTP header methods not checked', severity='warning')
            continue
        seen = set()
        targets = set()
        for alt in alts:
            lang, raw = alt['language'], alt['url']
            if lang in seen: add(p, 'duplicate_language', 'Multiple entries for ' + lang, raw)
            seen.add(lang)
            try:
                target = normalize(raw)
                targets.add(target)
            except ValueError:
                add(p, 'alternate_not_absolute', 'hreflang target must be an absolute HTTP(S) URL', raw)
                continue
            other = by_url.get(target)
            if other is None:
                add(p, 'target_not_checked', 'Target absent, blocked or failed; reciprocity unknown', target, 'warning')
                continue
            if other['status'] != 200: add(p, 'alternate_http_status', str(other['status']), target)
            if not any(a['url'] == p['url'] for a in other['alternates']):
                add(p, 'missing_return_link', 'Target does not link back to this final URL', target)
        if p['url'] not in targets: add(p, 'missing_self_reference', 'Hreflang set omits this final URL')
    return sorted(issues, key=lambda i: (i['url'], i['rule'], i['target'], i['evidence']))


class SameOriginRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(req.full_url).netloc != urlsplit(newurl).netloc or urlsplit(newurl).scheme not in ('http','https'):
            raise URLError('Cross-origin redirect not fetched')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_response(opener, url, timeout):
    try:
        response = opener.open(Request(url, headers={'User-Agent': AGENT}), timeout=timeout)
    except HTTPError as exc:
        response = exc
    with response as r:
        data = r.read(LIMIT + 1)
        if len(data) > LIMIT: raise ValueError('Response exceeds 2 MB limit')
        charset = r.headers.get_content_charset() or 'utf-8'
        return r.status, r.geturl(), r.headers, data.decode(charset, errors='replace')


def fetch_pages(urls, delay=0.5, timeout=15):
    opener = build_opener(SameOriginRedirects())
    policies = {}
    pages = []
    for url in urls:
        try:
            origin = urlunsplit((*urlsplit(url)[:2], '', '', ''))
            if origin not in policies:
                status, _, _, body = read_response(opener, origin + '/robots.txt', timeout)
                if status == 404:
                    body = 'User-agent: *\nAllow: /'
                elif status != 200:
                    raise ValueError(f'robots.txt returned {status}; crawl skipped')
                rp = RobotFileParser()
                rp.parse(body.splitlines())
                policies[origin] = rp
                time.sleep(delay)
            rp = policies[origin]
            if not rp.can_fetch(AGENT, url): raise ValueError('Disallowed by robots.txt')
            time.sleep(max(delay, rp.crawl_delay(AGENT) or 0))
            status, final, headers, body = read_response(opener, url, timeout)
            if headers.get_content_type() not in ('text/html', 'application/xhtml+xml'):
                raise ValueError('Not an HTML response')
            pages.append(parse_page(final, body, status, headers, url))
        except (OSError, ValueError, LookupError) as exc:
            pages.append({'url': url, 'requested_url': url, 'error': str(exc)})
    return pages


def load_manifest(path):
    path = Path(path)
    entries = json.loads(path.read_text(encoding='utf-8'))
    if not entries: raise ValueError('Manifest must contain at least one page')
    return [parse_page(normalize(e['url']), (path.parent / e['file']).read_text(encoding='utf-8'),
                       e.get('status', 200), e.get('headers')) for e in entries]


def write_report(pages, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    issues = audit(pages)
    report = {'tool_version': VERSION, 'pages': pages, 'issues': issues,
              'summary': {'pages': len(pages), 'errors': sum(i['severity']=='error' for i in issues),
                          'warnings': sum(i['severity']=='warning' for i in issues),
                          'incomplete_pages': sum(bool(p.get('error')) for p in pages)}}
    (directory / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (directory / 'issues.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['url','rule','severity','target','evidence'])
        w.writeheader()
        # Guard spreadsheet exports against formulas from untrusted HTML.
        w.writerows({k: "'"+v if v.startswith(('=','+','-','@','\t','\r','\n')) else v for k,v in i.items()} for i in issues)
    def cell(v): return str(v).replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')
    lines = ['# Multilingual SEO check', '', f"Pages: {len(pages)} | Errors: {report['summary']['errors']} | Warnings: {report['summary']['warnings']}", '',
             'HTML-only observations. These checks do not measure ranking or Google index status.', '',
             '| Severity | Rule | Page | Target | Evidence |', '| --- | --- | --- | --- | --- |']
    lines += ['| ' + ' | '.join(cell(i[k]) for k in ('severity','rule','url','target','evidence'))+' |' for i in issues]
    if not issues: lines += ['','No issues found within the implemented checks.']
    (directory / 'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument('--manifest', type=Path, help='Offline JSON list of url/file pairs')
    src.add_argument('--urls', type=Path, help='Explicit URL list, one URL per line')
    parser.add_argument('--output', type=Path, default=Path('output'))
    parser.add_argument('--max-pages', type=int, default=30)
    parser.add_argument('--delay', type=float, default=0.5)
    parser.add_argument('--timeout', type=float, default=15)
    args = parser.parse_args(argv)
    try:
        if args.max_pages < 1 or args.delay < 0 or args.timeout <= 0:
            raise ValueError('Page limit and timeout must be positive; delay must be non-negative')
        if args.manifest:
            pages = load_manifest(args.manifest)
            if len(pages) > args.max_pages: raise ValueError('Manifest exceeds --max-pages')
        else:
            urls = list(dict.fromkeys(normalize(l.strip()) for l in args.urls.read_text(encoding='utf-8').splitlines() if l.strip() and not l.lstrip().startswith('#')))
            if not urls or len(urls) > args.max_pages: raise ValueError('URL list empty or exceeds --max-pages')
            pages = fetch_pages(urls, args.delay, args.timeout)
        report = write_report(pages, args.output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report['summary']))
    if report['summary']['incomplete_pages']: return 2
    return 1 if report['summary']['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
