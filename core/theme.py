import re
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders


def parse_colors(css):
    blocks = {'dark': r':root\s*\{(.*?)\}', 'light': r'\[data-theme="light"\]\s*\{(.*?)\}'}
    return {
        theme: dict(re.findall(r'--([\w-]+):\s*(#[0-9A-Fa-f]{6})', re.search(pattern, css, re.S).group(1)))
        for theme, pattern in blocks.items()
    }


@lru_cache
def _read(path, mtime):
    return parse_colors(path.read_text())


def theme_colors():
    """Hex colours from the active theme file, for the favicon and browser bar."""
    path = Path(finders.find(f'css/themes/{settings.SITE_THEME}.css'))
    return _read(path, path.stat().st_mtime)
