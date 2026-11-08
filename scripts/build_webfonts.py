#!/usr/bin/env python3
"""Package the selected Rubik fonts and a site-specific Noto Sans SC subset.

Optional build-time dependencies: fonttools and brotli. Build Jekyll first so
_site contains the current text. Only font binaries/licenses are downloaded;
site text is never sent to a remote font service.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CJK_RANGES = [(0x2E80, 0x303F), (0x3400, 0x4DBF), (0x4E00, 0x9FFF),
              (0xF900, 0xFAFF), (0xFF00, 0xFFEF), (0x20000, 0x3134F)]


def is_cjk(char):
    return any(lo <= ord(char) <= hi for lo, hi in CJK_RANGES)


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ['script', 'style']:
            self.skip_depth += 1
        if not self.skip_depth:
            self.parts.extend(value for key, value in attrs
                              if key in ['alt', 'title', 'aria-label', 'content'] and value)

    def handle_endtag(self, tag):
        if tag in ['script', 'style'] and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)


def get_source(relative, url, digest, source_dir):
    cached = ROOT / 'local/webfont-sources' / relative
    candidate = source_dir / relative
    path = candidate if candidate.is_file() else cached
    if not path.is_file():
        request = urllib.request.Request(url, headers={'User-Agent': 'homepage-font-build'})
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f'Upstream source changed: {relative}; review before updating the source lock.')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError(f'Source checksum mismatch: {relative}')
    return path


def main():
    from fontTools import subset
    from fontTools.ttLib import TTFont

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=ROOT / '_site')
    parser.add_argument('--source-dir', type=Path, default=ROOT / 'local/font-preview/assets')
    args = parser.parse_args()
    if not (args.site / 'index.html').is_file():
        raise SystemExit('Build the Jekyll site before rebuilding webfonts.')
    characters = set()
    for html in args.site.rglob('*.html'):
        text = VisibleText()
        text.feed(html.read_text(encoding='utf-8'))
        characters.update(ord(char) for char in ''.join(text.parts) if is_cjk(char))
    if not characters:
        raise SystemExit('No Chinese characters found; refusing to create an empty subset.')
    output = ROOT / 'assets/fonts'
    output.mkdir(parents=True, exist_ok=True)
    result = {'cjk_codepoints': sorted(characters), 'fonts': []}
    for entry in json.loads((ROOT / 'scripts/font-sources.json').read_text()):
        source = get_source(entry['source_file'], entry['source_url'], entry['source_sha256'], args.source_dir)
        license_path = get_source(entry['license_source'], entry['license_url'], entry['license_sha256'], args.source_dir)
        (output / entry['license_output']).write_bytes(license_path.read_bytes())
        with TTFont(source, recalcTimestamp=False) as font:
            if entry['subset']:
                missing = characters - set(font.getBestCmap())
                if missing:
                    raise ValueError(f'Chinese source font lacks characters: {sorted(missing)}')
                options = subset.Options()
                options.name_IDs = ['*']
                options.name_languages = ['*']
                options.layout_features = ['*']
                options.ignore_missing_unicodes = False
                subsetter = subset.Subsetter(options=options)
                subsetter.populate(unicodes=characters)
                subsetter.subset(font)
            font.flavor = 'woff2'
            target = output / entry['output_file']
            font.save(target)
        data = target.read_bytes()
        assert data.startswith(b'wOF2')
        result['fonts'].append({
            'file': entry['output_file'], 'family': entry['family'], 'style': entry['style'],
            'weights': entry['weights'], 'subset': entry['subset'], 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(), 'source_url': entry['source_url'],
            'source_sha256': entry['source_sha256'], 'license': entry['license_output']})
        print(f'{target.name}: {len(data):,} bytes')
    (output / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'Packaged Rubik plus {len(characters)} Chinese/punctuation characters. Original outlines and weights are retained.')


if __name__ == '__main__':
    main()
