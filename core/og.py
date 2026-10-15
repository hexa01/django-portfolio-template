"""Social preview cards (1200×630 PNG): the card LinkedIn, Slack or WhatsApp shows for a shared link.
Drawn with Pillow in the active theme's dark colours and the site's own IBM Plex fonts."""

import hashlib
from functools import lru_cache
from io import BytesIO

from django.contrib.staticfiles import finders
from django.urls import reverse
from PIL import Image, ImageDraw, ImageFont

from .theme import theme_colors

WIDTH, HEIGHT = 1200, 630
PAD = 80


@lru_cache
def _font(weight, size):
    return ImageFont.truetype(finders.find(f'fonts/ibm-plex-sans-latin-{weight}-normal.woff2'), size)


def _wrap(draw, text, font, width):
    lines, line = [], ''
    for word in text.split():
        candidate = f'{line} {word}'.strip()
        if draw.textlength(candidate, font=font) <= width or not line:
            line = candidate
        else:
            lines.append(line)
            line = word
    return lines + [line] if line else lines


def _fit(draw, text, width, max_lines=4):
    """The largest title size (72 down to 44px) that fits in max_lines; the last line is cut with … if needed."""
    for size in range(72, 43, -4):
        font = _font(600, size)
        lines = _wrap(draw, text, font, width)
        if len(lines) <= max_lines:
            return font, lines
    lines = lines[:max_lines]
    while draw.textlength(lines[-1] + '…', font=font) > width:
        lines[-1] = lines[-1].rsplit(' ', 1)[0]
    lines[-1] += '…'
    return font, lines


def url(request, name, slug, title):
    """A card's address. ?v= follows the title, so social sites fetch a new card when it changes."""
    version = hashlib.sha1(title.encode()).hexdigest()[:8]
    return request.build_absolute_uri(reverse(name, args=[slug])) + f'?v={version}'


def card(title, kicker, name, initials):
    colors = theme_colors()['dark']
    image = Image.new('RGB', (WIDTH, HEIGHT), colors['bg'])
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=colors['border'], width=2)

    # monogram and name, as in the site header
    draw.rounded_rectangle((PAD, PAD, PAD + 56, PAD + 56), radius=10, fill=colors['accent'])
    draw.text((PAD + 28, PAD + 29), initials, font=_font(600, 22), fill=colors['bg'], anchor='mm')
    draw.text((PAD + 76, PAD + 29), name, font=_font(600, 30), fill=colors['text'], anchor='lm')

    # title, bottom-aligned above the kicker
    font, lines = _fit(draw, title, WIDTH - 2 * PAD)
    line_height = round(font.size * 1.18)
    kicker_y = HEIGHT - PAD
    y = kicker_y - 28 - 24 - line_height * len(lines)
    for line in lines:
        draw.text((PAD, y), line, font=font, fill=colors['text'])
        y += line_height
    draw.text((PAD, kicker_y), kicker, font=_font(400, 28), fill=colors['text-2'], anchor='ls')

    buffer = BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()
