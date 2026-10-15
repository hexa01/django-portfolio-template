import shutil
import tempfile
from pathlib import Path
from io import BytesIO
from unittest import mock

from PIL import Image

from django.contrib.auth import get_user_model
from django.core.checks import run_checks
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.urls import reverse

from .media import validate_pdf, validate_upload_size
from .models import Education, Experience, FocusArea, SiteProfile, SkillGroup, SocialLink
from .theme import parse_colors

# The manifest storage needs collectstatic; tests don't run it.
PLAIN_STATIC = override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)


class SiteProfileTests(TestCase):
    def test_seeded_profile_exists(self):
        self.assertEqual(SiteProfile.load().pk, 1)

    def test_only_one_profile(self):
        SiteProfile(name='Someone else').save()
        self.assertEqual(SiteProfile.objects.count(), 1)
        self.assertEqual(SiteProfile.load().name, 'Someone else')


@PLAIN_STATIC
class PageTests(TestCase):
    def test_nav_pages_render(self):
        for name in ['core:home', 'core:about', 'core:resume', 'projects:index', 'blog:index', 'contact:index']:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_home_uses_profile_not_hardcoded_identity(self):
        profile = SiteProfile.load()
        profile.name = 'Ada Example'
        profile.role = 'Systems Engineer'
        profile.tagline = 'Builds compilers.'
        profile.meta_description = 'Ada builds compilers.'
        profile.save()
        FocusArea.objects.all().delete()
        FocusArea.objects.create(title='Compilers')

        response = self.client.get(reverse('core:home'))

        self.assertContains(response, '<title>Ada Example | Systems Engineer</title>', html=True)
        self.assertContains(response, 'Compilers')
        self.assertNotContains(response, 'Sushan')

    def test_inner_pages_share_the_page_layout(self):
        for name in ['core:about', 'core:resume', 'projects:index', 'blog:index']:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertTemplateUsed(response, 'page.html')
                self.assertContains(response, 'class="lead"')
                self.assertContains(response, 'id="cta-heading"')
        self.assertNotContains(self.client.get(reverse('contact:index')), 'id="cta-heading"')

    def test_page_colour_is_set_before_the_stylesheets(self):
        html = self.client.get(reverse('core:about')).content.decode()
        self.assertIn('html { background: #0C100E; color-scheme: dark; }', html)
        self.assertLess(html.index('html { background:'), html.index('css/tokens.css'))

    def test_pages_are_prepared_on_hover_except_admin(self):
        response = self.client.get(reverse('core:about'))
        self.assertContains(response, '<script type="speculationrules">')
        self.assertContains(response, '{"not": {"href_matches": "/admin/*"}}')

    def test_blog_is_empty_until_phase_3(self):
        self.assertContains(self.client.get(reverse('blog:index')), 'Writing is on its way')
        self.assertEqual(self.client.get(reverse('blog:detail', args=['any-post'])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('core:home')), 'Latest writing')

    def test_page_title_and_active_nav(self):
        response = self.client.get(reverse('blog:index'))
        self.assertContains(response, f'<title>Blog | {SiteProfile.load().name}</title>', html=True)
        self.assertContains(response, f'<a href="{reverse("blog:index")}" aria-current="page">Blog<span class="nav-mark" aria-hidden="true"></span></a>', html=True)
        self.assertNotContains(response, f'<a href="{reverse("core:home")}" aria-current="page">Home</a>', html=True)

    def test_seo_meta(self):
        response = self.client.get(reverse('core:about'))
        self.assertContains(response, '<link rel="canonical" href="http://testserver/about/">', html=True)
        self.assertContains(response, 'property="og:url" content="http://testserver/about/"')
        home = self.client.get(reverse('core:home'))  # the profile's description is the home page's
        self.assertContains(home, f'name="description" content="{SiteProfile.load().meta_description}"')

    def test_footer_social_links(self):
        SocialLink.objects.create(profile=SiteProfile.load(), label='GitHub', url='https://github.com/example')
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, 'href="https://github.com/example"')

    @override_settings(SITE_THEME='paper')
    def test_active_theme_comes_from_settings(self):
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, '<html lang="en" data-theme="dark">')
        self.assertContains(response, 'css/themes/paper.css')
        self.assertContains(response, '<meta name="theme-color" content="#141311">')

    def test_hero_highlights_from_admin(self):
        profile = SiteProfile.load()
        profile.highlights = 'RAG pipelines\n\n  backend APIs  \n'
        profile.save()
        self.assertEqual(profile.highlight_list, ['RAG pipelines', 'backend APIs'])
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, '<span class="visually-hidden">Focused on RAG pipelines, backend APIs</span>', html=True)
        self.assertContains(response, '<span hidden>backend APIs</span>', html=True)

        profile.highlights = ''
        profile.save()
        self.assertNotContains(self.client.get(reverse('core:home')), 'data-rotator')

    def test_availability_line_shows_only_when_set(self):
        profile = SiteProfile.load()
        profile.availability = 'Open to backend roles'
        profile.save()
        self.assertContains(self.client.get(reverse('core:home')), '<p class="status">Open to backend roles</p>', html=True)
        profile.availability = ''
        profile.save()
        self.assertNotContains(self.client.get(reverse('core:home')), 'class="status"')

    def test_hero_sets_the_surname_apart(self):
        profile = SiteProfile.load()
        profile.name = 'Ada Byron Lovelace'
        profile.save()
        self.assertContains(self.client.get(reverse('core:home')), '<h1 id="hero-name">Ada Byron <em>Lovelace</em></h1>', html=True)
        profile.name = 'Cher'
        profile.save()
        self.assertContains(self.client.get(reverse('core:home')), '<h1 id="hero-name">Cher</h1>', html=True)

    def test_home_has_systems_window(self):
        response = self.client.get(reverse('core:home'))
        self.assertTemplateUsed(response, 'core/_hero_window.html')
        for key in ['web', 'rag', 'events', 'code']:
            self.assertContains(response, f'data-key="{key}"')
        self.assertContains(response, 'data-name="redis" data-info="Checked first. Cache-aside with short TTLs')
        self.assertContains(response, 'js/hero-window.js')

    def test_other_pages_do_not_load_the_window(self):
        response = self.client.get(reverse('blog:index'))
        self.assertNotContains(response, 'hero-window')

    def test_404_uses_site_template(self):
        response = self.client.get('/no-such-page/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Page not found', status_code=404)


class OpsTests(TestCase):
    def test_health_ok(self):
        response = self.client.get(reverse('core:health'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertIn('no-cache', response['Cache-Control'])

    def test_health_reports_db_failure_without_details(self):
        with mock.patch('core.views.connection.cursor', side_effect=DatabaseError('secret detail')):
            response = self.client.get(reverse('core:health'))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'error'})

    def test_robots(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertContains(response, 'Disallow: /admin/')


@PLAIN_STATIC
class AdminTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser('admin', 'a@example.com', 'pw')
        self.client.force_login(user)

    def test_profile_changelist_redirects_to_single_profile(self):
        response = self.client.get(reverse('admin:core_siteprofile_changelist'))
        self.assertRedirects(response, reverse('admin:core_siteprofile_change', args=[1]), fetch_redirect_response=False)

    def test_profile_cannot_be_added_or_deleted(self):
        self.assertEqual(self.client.get(reverse('admin:core_siteprofile_add')).status_code, 403)
        self.assertEqual(self.client.get(reverse('admin:core_siteprofile_delete', args=[1])).status_code, 403)

    def test_profile_page_has_content_only(self):
        response = self.client.get(reverse('admin:core_siteprofile_change', args=[1]))
        self.assertContains(response, 'In the header')
        self.assertNotContains(response, 'accent')


def png_upload(width, height, name='photo.png'):
    buffer = BytesIO()
    Image.new('RGB', (width, height), (200, 120, 40)).save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


@PLAIN_STATIC
class LogoTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def test_initials_from_name(self):
        profile = SiteProfile.load()
        for name, expected in [('Sushan Poudel', 'SP'), ('ada lovelace byron', 'AL'), ('Cher', 'C')]:
            profile.name = name
            self.assertEqual(profile.initials, expected)

    def test_large_upload_is_cropped_to_a_small_square(self):
        profile = SiteProfile.load()
        profile.logo = png_upload(3000, 1800)
        profile.save()
        with Image.open(profile.logo.path) as stored:
            self.assertEqual(stored.size, (128, 128))
            self.assertEqual(stored.format, 'PNG')

    def test_replacing_or_clearing_the_logo_deletes_the_old_file(self):
        profile = SiteProfile.load()
        profile.logo = png_upload(400, 400)
        profile.save()
        first = profile.logo.path
        profile.logo = png_upload(500, 300)
        profile.save()
        self.assertFalse(Path(first).exists())
        second = profile.logo.path
        profile.logo = None
        profile.save()
        self.assertFalse(Path(second).exists())

    def test_header_shows_initials_without_logo_and_image_with_one(self):
        response = self.client.get(reverse('core:home'))
        initials = SiteProfile.load().initials
        self.assertContains(response, f'<span class="brand-mono" aria-hidden="true">{initials}</span>', html=True)
        self.assertContains(response, reverse('core:favicon'))

        profile = SiteProfile.load()
        profile.logo = png_upload(300, 300)
        profile.save()
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, f'class="brand-logo" src="{profile.logo.url}"')
        self.assertNotContains(response, 'brand-mono')

    def test_oversized_file_is_rejected(self):
        big = mock.Mock(size=5 * 1024 * 1024 + 1)
        with self.assertRaises(ValidationError):
            validate_upload_size(big)
        validate_upload_size(mock.Mock(size=1024))  # fine


class FaviconTests(TestCase):
    def test_favicon_uses_initials_and_theme_colours(self):
        response = self.client.get(reverse('core:favicon'))
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertContains(response, 'fill="#8DBFA0"')
        self.assertContains(response, 'fill="#0C100E"')
        self.assertContains(response, f'>{SiteProfile.load().initials}</text>')


def contrast(a, b):
    def luminance(hex_value):
        rgb = [int(hex_value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    high, low = sorted([luminance(a), luminance(b)], reverse=True)
    return (high + 0.05) / (low + 0.05)


class ThemeTests(TestCase):
    themes = sorted((Path(__file__).resolve().parent.parent / 'static/css/themes').glob('*.css'))
    required = ['bg', 'bg-2', 'surface', 'border', 'border-strong', 'text', 'text-2', 'muted', 'accent']

    def test_every_theme_is_complete_and_readable(self):
        self.assertTrue(self.themes)
        for path in self.themes:
            for mode, colors in parse_colors(path.read_text()).items():
                with self.subTest(theme=path.stem, mode=mode):
                    self.assertEqual([t for t in self.required if t not in colors], [])
                    for token in ['text', 'text-2', 'accent']:
                        self.assertGreaterEqual(contrast(colors[token], colors['bg']), 4.5, token)

    @override_settings(SITE_THEME='nope')
    def test_missing_theme_fails_the_system_check(self):
        self.assertIn('core.E001', [e.id for e in run_checks()])


def pdf_upload(content=b'%PDF-1.7 sample', name='resume.pdf'):
    return SimpleUploadedFile(name, content, content_type='application/pdf')


@PLAIN_STATIC
class AboutAndResumeTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def test_about_renders_markdown_from_admin(self):
        profile = SiteProfile.load()
        profile.bio = 'I build **reliable** backends.'
        profile.how_i_work = '- Measure first'
        profile.save()
        response = self.client.get(reverse('core:about'))
        self.assertContains(response, '<p>I build <strong>reliable</strong> backends.</p>', html=True)
        self.assertContains(response, '<li>Measure first</li>', html=True)
        self.assertNotContains(response, '<h2>Now</h2>', html=True)  # empty sections stay hidden

    def test_photo_is_cropped_to_a_portrait_jpeg(self):
        profile = SiteProfile.load()
        profile.photo = png_upload(2000, 1200)
        profile.save()
        with Image.open(profile.photo.path) as stored:
            self.assertEqual((stored.size, stored.format), ((640, 800), 'JPEG'))
        self.assertContains(self.client.get(reverse('core:about')), f'src="{profile.photo.url}"')

    def test_resume_entries_and_present_period(self):
        Experience.objects.create(role='Backend Engineer', organization='Acme Labs', start_year=2023, points='Owned the API\nCut p95 latency')
        Education.objects.create(title='BSc CS', organization='Some University', start_year=2018, end_year=2022)
        SkillGroup.objects.create(name='Languages', items='Python, Go')
        response = self.client.get(reverse('core:resume'))
        self.assertContains(response, '2023 - present')
        self.assertContains(response, '<li>Cut p95 latency</li>', html=True)
        self.assertContains(response, '<li>Go</li>', html=True)

    def test_pdf_button_only_with_a_pdf(self):
        self.assertNotContains(self.client.get(reverse('core:resume')), 'Download PDF')
        profile = SiteProfile.load()
        profile.resume_pdf = pdf_upload()
        profile.save()
        self.assertContains(self.client.get(reverse('core:resume')), 'Download PDF')

    def test_pdf_validator_rejects_other_files(self):
        with self.assertRaises(ValidationError):
            validate_pdf(pdf_upload(b'not a pdf', 'resume.pdf'))
        with self.assertRaises(ValidationError):
            validate_pdf(pdf_upload(b'%PDF-1.7', 'resume.exe'))
        validate_pdf(pdf_upload())  # fine


class MarkdownPreviewTests(TestCase):
    def test_preview_renders_for_staff_only(self):
        from django.contrib.auth.models import User
        url = reverse('markdown-preview')
        self.assertEqual(self.client.post(url, {'text': '## Hi'}).status_code, 302)  # to the admin login
        self.client.force_login(User.objects.create_user('editor', is_staff=True))
        self.assertContains(self.client.post(url, {'text': '## Hi'}), '<h2 id="hi">Hi</h2>', html=True)
        self.assertEqual(self.client.get(url).status_code, 405)


@PLAIN_STATIC
class SiteSearchTests(TestCase):
    def test_finds_published_projects_and_posts_only(self):
        from django.utils import timezone
        from blog.models import Post
        from projects.models import Project
        Project.objects.create(slug='cache-bot', title='Cache bot', summary='Semantic caching for a chatbot.', year=2026,
                               status=Project.Status.PUBLISHED)
        Project.objects.create(slug='secret', title='Secret caching', summary='Draft.', year=2026)
        Post.objects.create(slug='cache-post', title='Two cache layers', excerpt='About caching.', body='Caching text.',
                            status=Post.Status.PUBLISHED, published_at=timezone.now())
        page = self.client.get(reverse('core:search'), {'q': 'caching'})
        self.assertContains(page, 'Cache bot')
        self.assertContains(page, 'Two cache layers')
        self.assertNotContains(page, 'Secret caching')
        self.assertContains(page, 'name="robots" content="noindex, follow"')

        panel = self.client.get(reverse('core:search'), {'q': 'caching', 'panel': 1})
        self.assertContains(panel, 'Cache bot')
        self.assertNotContains(panel, '<html')  # just the results, for the header panel
        self.assertContains(self.client.get(reverse('core:search'), {'q': 'zzzz', 'panel': 1}), 'No projects or posts match')
        self.assertContains(self.client.get(reverse('core:search'), {'q': 'c', 'panel': 1}), 'Go to')


@PLAIN_STATIC
class SeoTests(TestCase):
    def setUp(self):
        from django.utils import timezone
        from blog.models import Post
        from projects.models import Project
        self.project = Project.objects.create(slug='cache-bot', title='Cache bot', summary='A bot.', year=2026,
                                              status=Project.Status.PUBLISHED)
        Project.objects.create(slug='hidden', title='Hidden', summary='Draft.', year=2026)
        self.post = Post.objects.create(slug='own-post', title='My post', excerpt='Mine.', body='## One\n\nText.',
                                        status=Post.Status.PUBLISHED, published_at=timezone.now())
        Post.objects.create(slug='medium-post', title='Elsewhere', excerpt='Cross-posted.', body='Text.',
                            status=Post.Status.PUBLISHED, published_at=timezone.now(),
                            canonical_url='https://medium.com/@someone/elsewhere-1')

    def test_sitemap_lists_pages_and_published_content_but_not_cross_posts(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        for path in ('/about/', '/blog/', '/projects/cache-bot/', '/blog/own-post/'):
            self.assertIn(f'http://testserver{path}</loc>', xml)
        self.assertNotIn('/projects/hidden/', xml)
        self.assertNotIn('/blog/medium-post/', xml)

    def test_robots_points_to_the_sitemap(self):
        self.assertContains(self.client.get('/robots.txt'), 'Sitemap: http://testserver/sitemap.xml')

    def test_rss_has_published_posts(self):
        response = self.client.get('/rss/')
        self.assertEqual(response['Content-Type'], 'application/xml; charset=utf-8')  # shown by browsers, not downloaded
        self.assertContains(response, '<?xml-stylesheet href="/rss/style.xsl"')
        style = self.client.get('/rss/style.xsl')
        self.assertEqual(style['Content-Type'], 'text/xsl; charset=utf-8')
        self.assertTrue(style.content.startswith(b'<?xml'))  # nothing may come before the XML declaration
        self.assertContains(response, '<title>My post</title>')
        self.assertContains(self.client.get(reverse('core:home')), 'type="application/rss+xml"')

    def test_structured_data_on_home_post_and_project(self):
        import json
        import re

        def schema(path):
            html = self.client.get(path).content.decode()
            return [json.loads(block) for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]

        self.assertEqual([item['@type'] for item in schema('/')], ['WebSite', 'Person'])
        article, crumbs = schema('/blog/own-post/')
        self.assertEqual(article['@type'], 'BlogPosting')
        self.assertEqual(article['headline'], 'My post')
        self.assertIn('/og/posts/own-post.png', article['image'])
        self.assertEqual([i['name'] for i in crumbs['itemListElement']], ['Home', 'Blog', 'My post'])
        self.assertEqual(schema('/projects/cache-bot/')[0]['@type'], 'BreadcrumbList')

    def test_admin_text_cannot_break_out_of_structured_data(self):
        self.post.title = '</script><script>alert(1)</script>'
        self.post.save()
        html = self.client.get('/blog/own-post/').content.decode()
        self.assertNotIn('<script>alert(1)', html)

    def test_preview_cards_are_png_and_only_for_published_content(self):
        for path in ('/og/site.png', '/og/projects/cache-bot.png', '/og/posts/own-post.png'):
            response = self.client.get(path)
            self.assertEqual(response['Content-Type'], 'image/png', path)
            self.assertTrue(response.content.startswith(b'\x89PNG'))
        self.assertEqual(self.client.get('/og/projects/hidden.png').status_code, 404)
        page = self.client.get('/blog/own-post/')
        self.assertContains(page, '<meta property="og:image" content="http://testserver/og/posts/own-post.png?v=')
        self.assertContains(page, 'linkedin.com/sharing/share-offsite/?url=http%3A%2F%2Ftestserver%2Fblog%2Fown-post%2F')


@PLAIN_STATIC
class PageTextTests(TestCase):
    PAGES = {'about': '/about/', 'projects': '/projects/', 'blog': '/blog/', 'resume': '/resume/', 'contact': '/contact/'}

    def description(self, path):
        import re
        return re.search(r'<meta name="description" content="([^"]*)"', self.client.get(path).content.decode()).group(1)

    def test_every_fixed_page_gets_its_own_description_by_default(self):
        from .models import PageText
        self.assertEqual(sorted(PageText.objects.values_list('page', flat=True)), sorted(self.PAGES))  # rows from the migration
        descriptions = [self.description(path) for path in self.PAGES.values()]
        self.assertEqual(len(set(descriptions + [self.description('/')])), 6)  # unique, and none copies the home page's
        profile = SiteProfile.load()
        self.assertIn(profile.name, descriptions[0])

    def test_admin_values_replace_defaults_and_seo_title_is_the_full_title(self):
        from .models import PageText
        PageText.objects.filter(page='projects').update(
            seo_title='Projects | Backend case studies', lead='Hand-picked work.', meta_description='Custom description.')
        response = self.client.get('/projects/')
        self.assertContains(response, '<title>Projects | Backend case studies</title>', html=True)
        self.assertContains(response, 'Hand-picked work.')
        self.assertEqual(self.description('/projects/'), 'Custom description.')

    def test_filtered_blog_lists_keep_their_own_title(self):
        from blog.models import Category
        from .models import PageText
        PageText.objects.filter(page='blog').update(seo_title='The blog | Notes')
        Category.objects.create(name='Guides', slug='guides')
        self.assertContains(self.client.get('/blog/'), '<title>The blog | Notes</title>', html=True)
        self.assertNotContains(self.client.get('/blog/?category=guides'), 'The blog | Notes')

    @override_settings(SITE_INDEXABLE=False)
    def test_hidden_site_is_noindex_everywhere(self):
        self.assertContains(self.client.get('/'), '<meta name="robots" content="noindex, nofollow">', html=True)
        robots = self.client.get('/robots.txt').content.decode()
        self.assertIn('Disallow: /\n', robots)
        self.assertNotIn('Sitemap:', robots)
