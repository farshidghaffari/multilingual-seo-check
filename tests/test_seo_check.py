import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
from seo_check import audit, parse_page, normalize, main, write_report, fetch_pages, SameOriginRedirects
from urllib.request import Request


def page(url, target=None, extra='', status=200):
    target = target or url
    return parse_page(url, f'<html lang="en"><head><title>Demo</title><link rel="canonical" href="{url}"><link rel="alternate" hreflang="en" href="{url}"><link rel="alternate" hreflang="fa" href="{target}">{extra}</head></html>', status)


class Checks(unittest.TestCase):
    def rules(self, pages): return {i['rule'] for i in audit(pages)}

    def test_healthy_reciprocal_cluster(self):
        a, b = 'https://example.com/', 'https://example.com/fa/'
        def make(url):
            return parse_page(url, f'<html lang="en"><head><title>Demo</title><link rel="canonical" href="{url}"><link rel="alternate" hreflang="en" href="{a}"><link rel="alternate" hreflang="fa" href="{b}"></head></html>')
        self.assertEqual(audit([make(a), make(b)]), [])

    def test_missing_return_link(self):
        self.assertIn('missing_return_link', self.rules([page('https://example.com/', 'https://example.com/fa/'), page('https://example.com/fa/')]))

    def test_not_checked_is_not_broken(self):
        rules = self.rules([page('https://example.com/', 'https://example.com/fa/')])
        self.assertIn('target_not_checked', rules)
        self.assertNotIn('missing_return_link', rules)

    def test_relative_alternate(self):
        self.assertIn('alternate_not_absolute', self.rules([page('https://example.com/', '/fa/')]))

    def test_self_reference_missing(self):
        p = page('https://example.com/')
        p['alternates'] = [{'language':'fa','url':'https://example.com/fa/'}]
        self.assertIn('missing_self_reference', self.rules([p]))

    def test_duplicate_language(self):
        p = page('https://example.com/')
        p['alternates'].append({'language':'en','url':p['url']})
        self.assertIn('duplicate_language', self.rules([p]))

    def test_non_200_alternate(self):
        a, b = 'https://example.com/', 'https://example.com/fa/'
        self.assertIn('alternate_http_status', self.rules([page(a, b), page(b, a, status=404)]))

    def test_meta_and_header_noindex(self):
        for extra, headers in [('<meta name="robots" content="noindex, follow">', {}), ('', {'X-Robots-Tag':'noindex'})]:
            p = parse_page('https://example.com/', '<head>'+extra+'</head>', headers=headers)
            self.assertIn('noindex', self.rules([p]))

    def test_noindex_none(self):
        self.assertIn('noindex',self.rules([page('https://example.com/',extra='<meta name="googlebot" content="none">')]))

    def test_head_only_and_case(self):
        p = parse_page('https://example.com/', '<HTML LANG="fa"><HEAD><TITLE>الف &amp; ب</TITLE><LINK REL="CANONICAL" HREF="/" /></HEAD><body><link rel="alternate" hreflang="en" href="https://example.com/"></body></HTML>')
        self.assertEqual(p['title'], 'الف & ب')
        self.assertEqual(p['canonicals'], ['https://example.com/'])
        self.assertEqual(p['alternates'], [])

    def test_canonical_count_and_base(self):
        p=parse_page('https://example.com/path/', '<head><base href="https://example.com/"><link rel="canonical" href="fa/"></head>')
        self.assertEqual(p['canonicals'],['https://example.com/fa/'])
        self.assertIn('canonical_other', self.rules([p]))
        p['canonicals'] *= 2
        self.assertIn('canonical_count',self.rules([p]))

    def test_error_not_clean(self):
        p={'url':'https://example.com/', 'error':'timeout'}
        self.assertIn('fetch_incomplete',self.rules([p]))
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(write_report([p], d)['summary']['incomplete_pages'],1)

    def test_url_validation(self):
        for url in ['/fa/', 'file:///etc/passwd', 'https://a:b@example.com/']:
            with self.assertRaises(ValueError): normalize(url)
        self.assertEqual(normalize('HTTPS://EXAMPLE.COM#x'),'https://example.com/')

    def test_redirect_boundaries(self):
        with self.assertRaises(URLError):
            SameOriginRedirects().redirect_request(Request('https://example.com/'),None,302,'',{},'https://other.com/')

    def test_robots_disallow_no_page_fetch(self):
        with patch('seo_check.read_response',return_value=(200,'https://example.com/robots.txt',{},'User-agent: *\nDisallow: /')), patch('seo_check.time.sleep'):
            pages=fetch_pages(['https://example.com/'])
            self.assertIn('Disallowed',pages[0]['error'])

    def test_robots_server_failure_no_page_fetch(self):
        with patch('seo_check.read_response',return_value=(503,'https://example.com/robots.txt',{},'')), patch('seo_check.time.sleep'):
            self.assertIn('503',fetch_pages(['https://example.com/'])[0]['error'])

    def test_csv_formula_escape(self):
        p={'url':'https://example.com/', 'error':'=malicious()'}
        with tempfile.TemporaryDirectory() as d:
            write_report([p],d)
            self.assertIn("'=malicious()",Path(d,'issues.csv').read_text())
            self.assertEqual(json.loads(Path(d,'report.json').read_text())['issues'][0]['evidence'],'=malicious()')

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--manifest','examples/healthy/manifest.json','--output',d]),0)
            self.assertEqual(main(['--manifest','examples/broken/manifest.json','--output',d]),1)
            with patch('seo_check.fetch_pages',return_value=[{'url':'https://example.com/','error':'timeout'}]):
                path=Path(d,'urls.txt');path.write_text('https://example.com/')
                self.assertEqual(main(['--urls',str(path),'--output',d]),2)


if __name__ == '__main__': unittest.main()
