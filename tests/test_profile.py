"""Check the generated profile after `bundle exec jekyll build --safe`.

Run with: python -m unittest discover -s tests -v
Uses only Python's standard library and does not fetch external links.
"""
from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '_site'
ROUTES = ['index.html', 'cv/index.html', 'publications/index.html',
          'publication/featx/index.html', 'publication/featlens/index.html',
          'publication/featoutline/index.html']


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.text = []
        self.comments = []
        self.links = []
        self.images = []
        self.metadata = {}
        self.feed(path.read_text(encoding='utf-8'))

    def handle_comment(self, data):
        self.comments.append(data.strip())

    def handle_data(self, data):
        self.text.append(data)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag == 'img' and attrs.get('src'):
            self.images.append(attrs['src'])
        if tag == 'meta':
            self.metadata[attrs.get('name', attrs.get('property'))] = attrs.get('content')

    @property
    def content(self):
        return ' '.join(' '.join(self.text).split())


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (SITE / 'index.html').exists():
            raise RuntimeError('Build the Jekyll site before running these checks.')
        cls.pages = {route: Page(SITE / route) for route in ROUTES}

    def test_current_identity_and_navigation(self):
        for route, page in self.pages.items():
            with self.subTest(route=route):
                self.assertIn('Ph.D. student in CS, PKU', page.content)
                self.assertIn('Peking University', page.content)
                self.assertIn('https://github.com/a496263365', page.links)
                self.assertTrue(any(urlsplit(x).path == '/publications/' for x in page.links))
                self.assertNotIn('Undergraduate student in CS, BIT', page.content)
                self.assertNotIn('None now', page.content)
                self.assertNotIn('Paper Title Number', page.content)

    def test_education_and_awards(self):
        for route in ['index.html', 'cv/index.html']:
            text = self.pages[route].content
            with self.subTest(route=route):
                for phrase in ['2030 (expected)', 'June 2025',
                               'National Scholarship', 'Beijing Outstanding Graduate']:
                    self.assertIn(phrase, text)
        for phrase in ['92.7/100', '1/162', 'first three undergraduate years']:
            self.assertIn(phrase, self.pages['cv/index.html'].content)

    def test_homepage_grade_sentence_is_commented_out(self):
        sentence = (
            'Over my first three undergraduate years, my average credit-weighted score '
            'was **92.7/100**, and I ranked **1st out of 162** students in my major.'
        )
        source = (ROOT / '_pages/about.md').read_text(encoding='utf-8')
        self.assertIn(f'<!-- {sentence} -->', source)
        self.assertIn(sentence, self.pages['index.html'].comments)
        for phrase in ['92.7/100', '1st out of 162', 'first three undergraduate years']:
            self.assertNotIn(phrase, self.pages['index.html'].content)

    def test_publication_status_is_consistent(self):
        for route in ['index.html', 'cv/index.html', 'publications/index.html']:
            text = self.pages[route].content
            with self.subTest(route=route):
                for phrase in ['FeatX:', 'FeatLens:', 'FeatOutline:', 'First author',
                               'Second author', 'ASE 2026', 'FSE 2027 (under review)',
                               'Under review — not yet accepted', 'November 7, 2026']:
                    self.assertIn(phrase, text)
                self.assertNotIn('Published in FSE', text)
        lens = self.pages['publication/featlens/index.html'].content
        self.assertIn('Under review — not yet accepted', lens)
        self.assertNotIn('Published in', lens)

    def test_research_metrics_and_scope(self):
        text = self.pages['cv/index.html'].content
        for phrase in ['38 real feature-change commits', '0.385', '42.6%', '41%',
                       'zero LLM calls during online dependency retrieval',
                       '11.2 percentage points', '17.4 percentage points', '55.03%',
                       '57.4%', '13.6%', '70.66%', '24.54%', '1.589', '3.732',
                       'perplexity increased', 'Reproduced a method']:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertIn('https://github.com/uniqueFranky/LLMRep', self.pages['cv/index.html'].links)

    def test_paper_links(self):
        expected = ['https://doi.org/10.1145/3832783.3834646',
                    'https://arxiv.org/abs/2609.26480',
                    'https://doi.org/10.1145/3862475']
        for route in ['index.html', 'cv/index.html', 'publications/index.html']:
            for url in expected:
                with self.subTest(route=route, url=url):
                    self.assertIn(url, self.pages[route].links)

    def test_no_new_private_resume_details(self):
        # The existing public email is intentional; the private resume is not uploaded.
        for route, page in self.pages.items():
            with self.subTest(route=route):
                self.assertNotIn('出生年月', page.content)
                self.assertNotIn('2003', page.content)
                self.assertNotRegex(page.content, r'(?<!\d)1[3-9]\d{9}(?!\d)')
                self.assertFalse(any('2025-2.jpg' in x or 'main.pdf' in x
                                     for x in page.links + page.images))
        for excluded in ['local', 'vendor', 'tests', '.bundle']:
            self.assertFalse((SITE / excluded).exists(), excluded)

    def test_local_links_and_images_resolve(self):
        for route, page in self.pages.items():
            for url in page.links + page.images:
                target = urlsplit(url)
                if target.scheme not in ['', 'http', 'https']:
                    continue
                if target.netloc and target.netloc != 'lixutian.github.io':
                    continue
                # /blog/ is a separately deployed GitHub Pages project, not this build.
                if not target.path or target.path.startswith('/blog/'):
                    continue
                path = unquote(target.path)
                dest = SITE / path.lstrip('/') if path.startswith('/') else (SITE / route).parent / path
                with self.subTest(route=route, url=url):
                    self.assertTrue(dest.is_file() or (dest / 'index.html').is_file(), str(dest))

    def test_no_template_publications_or_unrendered_liquid(self):
        for path in SITE.rglob('*.html'):
            # Other untouched template/demo pages may contain illustrative Liquid code.
            if path.relative_to(SITE).as_posix() in ROUTES:
                text = path.read_text(encoding='utf-8')
                self.assertNotIn('{% include', text)
                self.assertNotIn('{{ site.', text)
        self.assertFalse(list((SITE / 'publication').glob('*paper-title-number*')))
        description = self.pages['index.html'].metadata.get('description', '')
        self.assertIn('Ph.D. student', description)
        self.assertNotIn('personal description', description)


if __name__ == '__main__':
    unittest.main()
