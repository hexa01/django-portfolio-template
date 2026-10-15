from django.core.files.base import ContentFile
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse

from core.media import delete_replaced, previous_files, shrink_image, validate_upload_size
from core.svg import clean_svg
from core.text import render_markdown


def validate_diagram(file):
    if file.name.lower().endswith('.svg'):
        clean_svg(file.read())
        file.seek(0)


class ProjectQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Project.Status.PUBLISHED)

    def search(self, query):
        """Full-text search, best matches first. Title counts most, then summary and stack, then the case study."""
        vector = (SearchVector('title', weight='A') + SearchVector('summary', 'stack', weight='B')
                  + SearchVector('problem', 'approach', 'result', weight='C'))
        search = SearchQuery(query, search_type='websearch')
        return self.annotate(document=vector, rank=SearchRank(vector, search)).filter(document=search).order_by('-rank')


class Project(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80, unique=True, help_text='The page address, e.g. "rag-service" gives /projects/rag-service/. Keep it short.')
    summary = models.CharField(max_length=200, help_text='One line: what it does and for whom.')
    year = models.PositiveSmallIntegerField()
    role = models.CharField(max_length=100, blank=True, help_text='What you did, e.g. "Backend, API and system design"')
    stack = models.CharField(max_length=200, blank=True, help_text='Comma-separated, e.g. "Python, FastAPI, Postgres"')

    problem = models.TextField(blank=True, help_text='What was broken or missing, and for whom. Markdown.')
    approach = models.TextField(blank=True, help_text='The design and how the parts fit. Markdown.')
    result = models.TextField(blank=True, help_text='What changed. Real numbers only. Markdown.')
    problem_html = models.TextField(blank=True, editable=False)
    approach_html = models.TextField(blank=True, editable=False)
    result_html = models.TextField(blank=True, editable=False)

    diagram = models.FileField(
        upload_to='projects/', blank=True,
        validators=[FileExtensionValidator(['svg', 'png', 'jpg', 'jpeg', 'webp']), validate_upload_size, validate_diagram],
        help_text='Architecture diagram. SVG is shown inline, follows the light/dark theme and draws in on scroll; '
        'PNG/JPG/WebP show as a still image (resized to 1600px wide).',
    )
    diagram_svg = models.TextField(blank=True, editable=False)
    diagram_caption = models.CharField(max_length=150, blank=True)

    source_url = models.URLField('source code', blank=True)
    demo_url = models.URLField('live demo', blank=True)
    availability_note = models.CharField(
        max_length=100, blank=True,
        help_text='Shown when there is no public link, e.g. "Code private (client work)".',
    )

    featured = models.BooleanField(default=False, help_text='Shown on the homepage.')
    order = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ['order', '-year', 'title']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('projects:detail', args=[self.slug])

    @property
    def stack_list(self):
        return [item.strip() for item in self.stack.split(',') if item.strip()]

    def save(self, *args, **kwargs):
        previous = previous_files(Project, self.pk, ['diagram'])
        if self.diagram and not self.diagram._committed:
            if self.diagram.name.lower().endswith('.svg'):
                self.diagram_svg = clean_svg(self.diagram.read())
                self.diagram.save(f'{self.slug}.svg', ContentFile(self.diagram_svg.encode()), save=False)
            else:
                self.diagram_svg = ''
                self.diagram.save(f'{self.slug}.png', shrink_image(self.diagram, 1600), save=False)
        elif not self.diagram:
            self.diagram_svg = ''
        self.problem_html = render_markdown(self.problem)
        self.approach_html = render_markdown(self.approach)
        self.result_html = render_markdown(self.result)
        super().save(*args, **kwargs)
        delete_replaced(self, previous)


class Decision(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='decisions')
    decision = models.CharField(max_length=200)
    why = models.CharField(max_length=300)
    tradeoff = models.CharField('trade-off', max_length=300)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.decision
