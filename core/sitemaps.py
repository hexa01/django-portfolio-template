from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from blog.models import Post
from projects.models import Project


class PageSitemap(Sitemap):
    def items(self):
        return ['core:home', 'core:about', 'projects:index', 'blog:index', 'core:resume', 'contact:index']

    def location(self, name):
        return reverse(name)


class ProjectSitemap(Sitemap):
    def items(self):
        return Project.objects.published()

    def lastmod(self, project):
        return project.updated_at


class PostSitemap(Sitemap):
    def items(self):
        # a cross-post's original lives elsewhere (e.g. Medium), so only that address should be indexed
        return Post.objects.published().filter(canonical_url='')

    def lastmod(self, post):
        return post.updated_at or post.published_at


SITEMAPS = {'pages': PageSitemap, 'projects': ProjectSitemap, 'posts': PostSitemap}
