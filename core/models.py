from django.db import models

from .media import (
    delete_replaced, fit_image, previous_files, validate_pdf, validate_upload_size,
)
from .text import render_markdown

LOGO_SIZE = (128, 128)   # shown at ~26px, so this stays sharp on high-density screens
PHOTO_SIZE = (640, 800)  # portrait 4:5, shown at up to ~430px wide


class SiteProfile(models.Model):
    """The site owner's identity. A single row, edited in admin."""

    name = models.CharField(max_length=100, default='Your Name')
    role = models.CharField(max_length=100, blank=True, help_text='e.g. "AI Backend Engineer"')
    highlights = models.TextField(
        blank=True,
        help_text='Short phrases shown one at a time under your role, one per line. e.g. "RAG pipelines"',
    )
    tagline = models.CharField(
        max_length=300, blank=True, help_text='One or two sentences under your name on the homepage.'
    )
    availability = models.CharField(
        max_length=80,
        blank=True,
        help_text='One short line under the homepage buttons, e.g. "Open to backend and AI roles". Leave blank to hide.',
    )
    meta_description = models.CharField(
        max_length=300,
        blank=True,
        help_text='Default search/social description for pages that do not set their own.',
    )
    email = models.EmailField(blank=True)
    logo = models.ImageField(
        upload_to='site/',
        blank=True,
        validators=[validate_upload_size],
        help_text='Optional. Replaces your initials in the header and the browser tab. '
        'Cropped to a square and resized to 128×128, so any size works.',
    )

    # about page
    photo = models.ImageField(
        upload_to='site/', blank=True, validators=[validate_upload_size],
        help_text='Shown on the About page. Cropped to a 4:5 portrait and resized, so any size works.',
    )
    location = models.CharField('based in', max_length=100, blank=True, help_text='e.g. "Pokhara, Nepal"')
    bio = models.TextField(blank=True, help_text='The introduction on the About page. Markdown.')
    how_i_work = models.TextField(blank=True, help_text='Principles, one list item each. Markdown.')
    now = models.TextField(blank=True, help_text="What you're working on and open to. Markdown.")
    bio_html = models.TextField(blank=True, editable=False)
    how_i_work_html = models.TextField(blank=True, editable=False)
    now_html = models.TextField(blank=True, editable=False)

    # resume page
    resume_pdf = models.FileField(
        'resume PDF', upload_to='site/', blank=True, validators=[validate_pdf],
        help_text='The "Download PDF" button appears once this is set. 5 MB max.',
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'site profile'
        verbose_name_plural = 'site profile'

    def __str__(self):
        return self.name

    @property
    def highlight_list(self):
        return [line.strip() for line in self.highlights.splitlines() if line.strip()]

    @property
    def name_parts(self):
        """(first names, last name) so the hero can set the surname apart; a one-word name has no last part."""
        first, _, last = self.name.strip().rpartition(' ')
        return (first, last) if first else (last, '')

    @property
    def initials(self):
        return ''.join(word[0] for word in self.name.split()[:2]).upper() or '?'

    def save(self, *args, **kwargs):
        self.pk = 1
        previous = previous_files(SiteProfile, 1, ['logo', 'photo', 'resume_pdf'])
        if self.logo and not self.logo._committed:  # a new upload
            self.logo.save('logo.png', fit_image(self.logo, LOGO_SIZE), save=False)
        if self.photo and not self.photo._committed:
            self.photo.save('photo.jpg', fit_image(self.photo, PHOTO_SIZE, fmt='JPEG'), save=False)
        self.bio_html = render_markdown(self.bio)
        self.how_i_work_html = render_markdown(self.how_i_work)
        self.now_html = render_markdown(self.now)
        super().save(*args, **kwargs)
        delete_replaced(self, previous)

    @classmethod
    def load(cls):
        profile, _ = cls.objects.get_or_create(pk=1)
        return profile


class SocialLink(models.Model):
    profile = models.ForeignKey(SiteProfile, on_delete=models.CASCADE, related_name='social_links')
    label = models.CharField(max_length=50, help_text='e.g. "GitHub"')
    url = models.URLField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.label


class FocusArea(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class PageText(models.Model):
    """Intro and search text for the fixed pages. Blank fields fall back to defaults built from the profile."""

    class Page(models.TextChoices):
        ABOUT = 'about', 'About'
        PROJECTS = 'projects', 'Projects'
        BLOG = 'blog', 'Blog'
        RESUME = 'resume', 'Resume'
        CONTACT = 'contact', 'Contact'

    LEADS = {
        Page.ABOUT: "Background, how I work, and what I'm focused on now.",
        Page.PROJECTS: 'Selected work, with the decisions behind each.',
        Page.BLOG: 'Articles and notes.',
        Page.RESUME: 'Experience, skills and education.',
        Page.CONTACT: "Questions about work, a project, or something I've written.",
    }
    DESCRIPTIONS = {
        Page.ABOUT: 'About {name}{role}: background, way of working and current focus.',
        Page.PROJECTS: 'Projects by {name}{role}: case studies with architecture and the design decisions behind them.',
        Page.BLOG: 'Articles and notes by {name}{role}.',
        Page.RESUME: 'Resume of {name}{role}: experience, skills and education.',
        Page.CONTACT: 'Contact {name}{role} about work, a project or an article.',
    }

    page = models.CharField(max_length=20, choices=Page.choices, unique=True)
    seo_title = models.CharField(
        'SEO title', max_length=70, blank=True,
        help_text='Optional. The full title in search results and browser tabs, e.g. "About Jane Doe | Data Engineer". '
                  'Empty: the page name and your name.',
    )
    lead = models.CharField(
        'intro', max_length=300, blank=True, help_text='The line under the page heading. Empty: a standard line.',
    )
    meta_description = models.CharField(
        'search description', max_length=160, blank=True,
        help_text='What search results show under the title: unique to this page, 120-160 characters. '
                  'Empty: one generated from your name and role.',
    )

    class Meta:
        ordering = ['page']
        verbose_name = 'page text'

    def __str__(self):
        return self.get_page_display()

    @classmethod
    def context(cls, page, profile):
        """Template context for a fixed page: intro, search description and the optional full title."""
        text = cls.objects.filter(page=page).first() or cls(page=page)
        role = f', {profile.role}' if profile.role else ''
        return {
            'lead': text.lead or cls.LEADS[page],
            'meta_description': text.meta_description or cls.DESCRIPTIONS[page].format(name=profile.name, role=role),
            'full_title': text.seo_title,
        }


class Experience(models.Model):
    role = models.CharField(max_length=100)
    organization = models.CharField(max_length=100)
    start_year = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Leave empty for "present".')
    points = models.TextField(blank=True, help_text='What you owned and achieved, one per line.')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', '-start_year']

    def __str__(self):
        return f'{self.role}, {self.organization}'

    @property
    def period(self):
        return f'{self.start_year} - {self.end_year or "present"}'

    @property
    def point_list(self):
        return [line.strip() for line in self.points.splitlines() if line.strip()]


class Education(models.Model):
    title = models.CharField(max_length=150, help_text='e.g. "BSc Computer Science"')
    organization = models.CharField(max_length=150)
    start_year = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Leave empty for "present".')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', '-start_year']
        verbose_name_plural = 'education'

    def __str__(self):
        return self.title

    @property
    def period(self):
        return f'{self.start_year} - {self.end_year or "present"}'


class SkillGroup(models.Model):
    name = models.CharField(max_length=50, help_text='e.g. "Languages"')
    items = models.CharField(max_length=300, help_text='Comma-separated, e.g. "Python, Go, SQL"')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name

    @property
    def item_list(self):
        return [item.strip() for item in self.items.split(',') if item.strip()]
