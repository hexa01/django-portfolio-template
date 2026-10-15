import re
from urllib.parse import urlparse

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.media import delete_replaced, previous_files, shrink_image, validate_upload_size
from core.text import render_article


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=40, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Post.Status.PUBLISHED, published_at__lte=timezone.now())

    def search(self, query):
        """Full-text search, best matches first. Title counts most, then the excerpt, then the body."""
        vector = SearchVector('title', weight='A') + SearchVector('excerpt', weight='B') + SearchVector('body', weight='C')
        search = SearchQuery(query, search_type='websearch')
        return (self.annotate(document=vector, rank=SearchRank(vector, search))
                .filter(document=search).order_by('-rank', '-published_at'))


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=80, unique=True, help_text='The page address, e.g. "semantic-caching" for /blog/semantic-caching/. Keep it short.')
    excerpt = models.CharField(max_length=300, help_text='One or two sentences for the post list and search results.')
    body = models.TextField(help_text='Markdown. Use ## and ### for sections; they become the "On this page" list.')
    body_html = models.TextField(blank=True, editable=False)
    toc = models.JSONField(default=list, blank=True, editable=False)
    reading_minutes = models.PositiveSmallIntegerField(default=1, editable=False)

    cover = models.ImageField(
        upload_to='blog/', blank=True, validators=[validate_upload_size],
        help_text='Optional. Shown at the top of the post and when shared. Resized to 1600px wide.',
    )
    cover_alt = models.CharField('cover description', max_length=200, blank=True, help_text='What the cover shows, for screen readers.')
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name='posts')
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(
        'published date', null=True, blank=True,
        help_text='The date shown on the post. For older writing, set it to when it was first published. '
                  'Left empty, it is set when you publish; a future date schedules the post.',
    )
    canonical_url = models.URLField(
        'original address', blank=True,
        help_text='If this post was first published elsewhere (e.g. Medium), its address. Search engines then treat that as the original.',
    )
    seo_title = models.CharField(max_length=70, blank=True, help_text='Optional. Replaces the title in search results.')
    seo_description = models.CharField(max_length=160, blank=True, help_text='Optional. Replaces the excerpt in search results.')
    updated_at = models.DateTimeField(
        'updated date', null=True, blank=True,
        help_text='Optional. Set it when you make a real change to the content; shown as "Updated" on the post.',
    )

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ['-published_at', '-id']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:detail', args=[self.slug])

    @property
    def origin_name(self):
        host = (urlparse(self.canonical_url).hostname or '').removeprefix('www.')
        return 'Medium' if host == 'medium.com' or host.endswith('.medium.com') else host

    @property
    def word_count(self):
        return len(self.body.split())

    def checklist(self):
        """Advisory editorial checks. Never blocks saving or publishing."""
        checks = [
            ('Excerpt is 50 to 160 characters', 50 <= len(self.excerpt) <= 160),
            ('Title is 70 characters or fewer (or an SEO title is set)', len(self.title) <= 70 or bool(self.seo_title)),
            ('Address (slug) is 60 characters or fewer', len(self.slug) <= 60),
            ('Has a category', bool(self.category_id)),
            ('Has at least one tag', bool(self.pk) and self.tags.exists()),
            ('Long posts have section headings', self.word_count < 600 or len(self.toc) >= 2),
            ('Every image in the body has a description', not re.search(r'!\[\s*\]\(', self.body)),
            ('Cover has a description', not self.cover or bool(self.cover_alt)),
        ]
        return checks

    def save(self, *args, **kwargs):
        previous = previous_files(Post, self.pk, ['cover'])
        if self.cover and not self.cover._committed:
            self.cover.save(f'{self.slug}.png', shrink_image(self.cover, 1600), save=False)
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        self.body_html, self.toc, self.reading_minutes = render_article(self.body)
        super().save(*args, **kwargs)
        delete_replaced(self, previous)
