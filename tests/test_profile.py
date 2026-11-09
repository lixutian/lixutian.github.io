"""Check the generated profile after `bundle exec jekyll build --safe`.

Run with: python -m unittest discover -s tests -v
Uses only Python's standard library and does not fetch external links.
"""
from html.parser import HTMLParser
import hashlib
import json
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
        self.navigation_links = []
        self.navigation_anchors = []
        self._in_site_nav = False
        self.images = []
        self.ids = set()
        self.metadata = {}
        self.feed(path.read_text(encoding='utf-8'))

    def handle_comment(self, data):
        self.comments.append(data.strip())

    def handle_data(self, data):
        self.text.append(data)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'nav' and attrs.get('id') == 'site-nav':
            self._in_site_nav = True
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
            if self._in_site_nav:
                self.navigation_links.append(attrs['href'])
                self.navigation_anchors.append(attrs)
        if tag == 'img' and attrs.get('src'):
            self.images.append(attrs['src'])
        if tag == 'meta':
            self.metadata[attrs.get('name', attrs.get('property'))] = attrs.get('content')

    def handle_endtag(self, tag):
        if tag == 'nav':
            self._in_site_nav = False

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
                self.assertTrue(any(urlsplit(x).path == '/' and urlsplit(x).fragment == 'news' for x in page.navigation_links))
                self.assertIn('news', self.pages['index.html'].ids)
                self.assertTrue(any(urlsplit(x).path == '/publications/' and not urlsplit(x).fragment for x in page.navigation_links))
                self.assertFalse(any(urlsplit(x).fragment == 'papers' for x in page.navigation_links))
                self.assertNotIn('Undergraduate student in CS, BIT', page.content)
                self.assertNotIn('None now', page.content)
                self.assertNotIn('Paper Title Number', page.content)

    def test_wechat_sidebar_uses_original_qr_with_click_disclosure(self):
        source = (ROOT / 'images/wechat-qr.jpg').read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(),
                         '974729d5b0f57f91e3dab4f79171e3b6dee3f7c2648a55a4b57f7c6de7d4d42c')
        self.assertEqual((SITE / 'images/wechat-qr.jpg').read_bytes(), source)
        for route, page in self.pages.items():
            with self.subTest(route=route):
                html = (SITE / route).read_text(encoding='utf-8')
                self.assertIn('WeChat: 浪迹天涯的小柴', page.content)
                self.assertIn('<details class="wechat-contact" data-wechat-popover>', html)
                self.assertIn('aria-controls="wechat-qr-popover" aria-expanded="false"', html)
                self.assertIn('aria-label="关闭微信二维码"', html)
                self.assertNotIn('wechat-qr-link', html)
                self.assertIn('loading="eager"', html)
                self.assertNotIn('点击图片查看原图', html)
                self.assertIn('assets/js/wechat-popover.js', html)
                self.assertTrue(any(urlsplit(url).path == '/images/wechat-qr.jpg' for url in page.images))
                self.assertFalse(any(urlsplit(url).path == '/images/wechat-qr.jpg' for url in page.links))
        script = (SITE / 'assets/js/main.min.js').read_text(encoding='utf-8')
        self.assertIn('.author__urls-wrapper > button', script)
        self.assertNotIn('.author__urls-wrapper button', script)
        interaction = (SITE / 'assets/js/wechat-popover.js').read_text(encoding='utf-8')
        self.assertNotIn('contextmenu', interaction)
        self.assertNotIn('touchstart', interaction)

    def test_cv_navigation_opens_the_approved_pdf_directly(self):
        source = (ROOT / 'files/cv.pdf').read_bytes()
        generated = (SITE / 'files/cv.pdf').read_bytes()
        self.assertTrue(source.startswith(b'%PDF-'))
        self.assertTrue(source.rstrip().endswith(b'%%EOF'))
        self.assertEqual(generated, source)
        for route, page in self.pages.items():
            with self.subTest(route=route):
                links = [link for link in page.navigation_anchors
                         if urlsplit(link['href']).path == '/files/cv.pdf']
                self.assertEqual(len(links), 1)
                self.assertNotIn('download', links[0])
                self.assertFalse(any(urlsplit(link).path == '/cv/'
                                     for link in page.navigation_links))

    def test_education_and_awards(self):
        for route in ['index.html', 'cv/index.html']:
            text = self.pages[route].content
            with self.subTest(route=route):
                for phrase in ['2030 (expected)', 'June 2025',
                               'National Scholarship', 'Beijing Outstanding Graduate']:
                    self.assertIn(phrase, text)
        for phrase in ['92.7/100', '1/162', 'first three undergraduate years']:
            self.assertIn(phrase, self.pages['cv/index.html'].content)

    def test_homepage_advisors_follow_doctoral_introduction(self):
        home = self.pages['index.html']
        sentence = 'I am advised by Professor Bing Xie and Research Professor Yanzhen Zou'
        self.assertIn(sentence, home.content)
        self.assertLess(home.content.index('I am a Ph.D. student'), home.content.index(sentence))
        self.assertLess(home.content.index(sentence), home.content.index('Before that, I received'))
        self.assertIn('https://cs.pku.edu.cn/info/1231/2036.htm', home.links)
        self.assertIn('https://cs.pku.edu.cn/info/1234/2070.htm', home.links)

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
                for phrase in ['FeatX:', 'FeatLens:', 'FeatOutline:', '2026']:
                    self.assertIn(phrase, text)
                self.assertNotIn('Published in FSE', text)
        for phrase in ['arXiv 2026', 'TOSEM 2026', 'ASE 2026']:
            self.assertIn(phrase, self.pages['index.html'].content)
        lens = self.pages['publication/featlens/index.html'].content
        self.assertIn('Preprint', lens)
        self.assertIn('arXiv', self.pages['publications/index.html'].content)
        self.assertIn('November 7, 2026', self.pages['cv/index.html'].content)

    def test_submission_destination_and_author_position_labels_are_removed(self):
        for route, page in self.pages.items():
            with self.subTest(route=route):
                for text in ['FSE 2027', 'First author', 'Second author',
                             '第一作者', '第二作者', 'not yet accepted']:
                    self.assertNotIn(text, page.content)
        for route in ['index.html', 'cv/index.html', 'publications/index.html']:
            html = (SITE / route).read_text(encoding='utf-8')
            self.assertGreaterEqual(html.count('<strong>Xutian Li</strong>'), 3)

    def test_compact_homepage_sections_and_paper_list(self):
        page = self.pages['index.html']
        for section in ['news', 'papers', 'education', 'honors', 'teaching', 'skills']:
            self.assertIn(section, page.ids)
        for heading in ['🔥 News', '📝 Papers', '📖 Education', '🎖 Honors and Awards', '💻 Teaching Experience', '🔧 Skills']:
            self.assertIn(heading, page.content)
        html = (SITE / 'index.html').read_text(encoding='utf-8')
        self.assertIn('class="page page--homepage"', html)
        self.assertIn('class="page__title sr-only"', html)
        papers = html.split('<ul class="homepage-papers">', 1)[1].split('</ul>', 1)[0]
        self.assertEqual(papers.count('<li>'), 3)
        self.assertEqual(papers.count('<strong>Xutian Li</strong>'), 3)
        for slug in ['featx', 'featlens', 'featoutline']:
            self.assertTrue(any(urlsplit(link).path == f'/publication/{slug}/' for link in page.links))
        self.assertTrue(any(urlsplit(link).path == '/publications/' for link in page.links))
        self.assertNotIn('About Me', page.content)
        self.assertNotIn('Research Interests', page.content)

    def test_papers_index_expands_overviews_and_links_to_detail_pages(self):
        path = SITE / 'publications/index.html'
        html = path.read_text(encoding='utf-8')
        page = self.pages['publications/index.html']
        self.assertIn('class="archive archive--papers"', html)
        self.assertIn('<h1 class="page__title">Papers</h1>', html)
        self.assertEqual(html.count('<article class="papers-entry"'), 3)
        self.assertEqual(html.count('class="papers-entry__overview"'), 3)
        self.assertEqual(html.count('class="papers-entry__links archive__item-links"'), 3)
        for label in ['Journal Articles', 'Conference Papers', 'Preprints / Under Review']:
            self.assertNotIn(label, page.content)
        for phrase in ['JavaParser-based static analysis', 'personalized PageRank',
                       '57.4% method-level Link@3 F1', '55.03%', '42.6%']:
            self.assertIn(phrase, page.content)
        for slug in ['featx', 'featlens', 'featoutline']:
            entry = html.split(f'<article class="papers-entry" id="{slug}"', 1)[1].split('</article>', 1)[0]
            title = entry.split('</h2>', 1)[0]
            self.assertIn(f'href="/publication/{slug}/"', title)
            self.assertIn('<strong>Xutian Li</strong>', entry)
            overview = entry.split('class="papers-entry__overview" itemprop="description">', 1)[1].split('</p>', 1)[0]
            self.assertNotIn('<p>', overview)
            self.assertNotIn('papers-entry__role', entry)
            self.assertNotIn('papers-entry__status', entry)
            self.assertIn('<i>', entry.split('class="papers-entry__venue">', 1)[1].split('</p>', 1)[0])
            self.assertIn('target="_blank" rel="noopener"', entry)
        self.assertLess(html.index('id="featoutline"'), html.index('id="featx"'))
        self.assertLess(html.index('id="featx"'), html.index('id="featlens"'))

    def test_teaching_experience_is_shared_by_homepage_and_cv(self):
        for route in ['index.html', 'cv/index.html']:
            with self.subTest(route=route):
                html = (SITE / route).read_text(encoding='utf-8')
                teaching = html.split('<ul class="teaching-experience">', 1)[1].split('</ul>', 1)[0]
                self.assertEqual(teaching.count('<li>'), 1)
                for phrase in ['2026 Spring', 'Teaching Assistant',
                               'Data Structures and Algorithms B', '数据结构与算法 B']:
                    self.assertIn(phrase, teaching)
                for unsupported in ['Graduate-level', 'in English', 'grading', 'office hours']:
                    self.assertNotIn(unsupported, teaching)
        self.assertIn('teaching', self.pages['index.html'].ids)

    def test_homepage_news_only_announces_published_papers(self):
        html = (SITE / 'index.html').read_text(encoding='utf-8')
        news = html.split('<ul class="homepage-news">', 1)[1].split('</ul>', 1)[0]
        self.assertEqual(news.count('<li>'), 3)
        self.assertIn('2026.11', news)
        self.assertIn('2026.10', news)
        self.assertIn('2025.09', news)
        self.assertIn('FeatOutline', news)
        self.assertIn('FeatX', news)
        self.assertNotIn('FeatLens', news)
        self.assertNotIn('FSE 2027', news)
        self.assertLess(news.index('2026.11'), news.index('2026.10'))

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

    def test_self_hosted_rubik_and_chinese_fonts_are_packaged(self):
        manifest = json.loads((ROOT / 'assets/fonts/manifest.json').read_text())
        self.assertEqual(len(manifest['fonts']), 3)
        css = (SITE / 'assets/css/main.css').read_text(encoding='utf-8')
        self.assertIn('Rubik', css)
        self.assertIn('Trebuchet MS', css)
        for item in manifest['fonts']:
            source = ROOT / 'assets/fonts' / item['file']
            generated = SITE / 'assets/fonts' / item['file']
            data = source.read_bytes()
            self.assertTrue(data.startswith(b'wOF2'))
            self.assertEqual(hashlib.sha256(data).hexdigest(), item['sha256'])
            self.assertEqual(generated.read_bytes(), data)
            self.assertTrue((SITE / 'assets/fonts' / item['license']).is_file())
            self.assertIn(item['file'], css)
        self.assertLess(sum(item['bytes'] for item in manifest['fonts']), 500000)

    def test_chinese_font_subset_covers_profile_text(self):
        manifest = json.loads((ROOT / 'assets/fonts/manifest.json').read_text())
        covered = set(manifest['cjk_codepoints'])
        ranges = [(0x2E80, 0x303F), (0x3400, 0x4DBF), (0x4E00, 0x9FFF),
                  (0xF900, 0xFAFF), (0xFF00, 0xFFEF), (0x20000, 0x3134F)]
        for route, page in self.pages.items():
            required = {ord(c) for c in page.content
                        if any(lo <= ord(c) <= hi for lo, hi in ranges)}
            with self.subTest(route=route):
                self.assertFalse(required - covered, 'Refresh the subset with scripts/build_webfonts.py')

    def test_private_resume_details_are_not_added_to_html(self):
        # The owner approved the original PDF; HTML profiles still omit these details.
        for route, page in self.pages.items():
            with self.subTest(route=route):
                self.assertNotIn('出生年月', page.content)
                self.assertNotIn('2003', page.content)
                self.assertNotRegex(page.content, r'(?<!\d)1[3-9]\d{9}(?!\d)')
                self.assertFalse(any('2025-2.jpg' in x or 'main.pdf' in x
                                     for x in page.links + page.images))
        for excluded in ['local', 'vendor', 'tests', 'scripts', '.bundle']:
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
