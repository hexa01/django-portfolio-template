from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Rss201rev2Feed, Stylesheet

from core.models import PageText, SiteProfile

from .models import Post


class BrowsableRss(Rss201rev2Feed):
    # browsers download application/rss+xml; they display application/xml, which feed readers accept too
    content_type = 'application/xml; charset=utf-8'


class PostFeed(Feed):
    """RSS for feed readers and newsletter tools: the 20 latest posts, with their excerpts.
    The XSL stylesheet makes it a readable page when opened in a browser; readers ignore it."""

    feed_type = BrowsableRss

    def stylesheets(self):
        return [Stylesheet(reverse('rss-style'), mimetype='text/xsl')]

    def title(self):
        return f'{SiteProfile.load().name} | Blog'

    def link(self):
        return reverse('blog:index')

    def description(self):
        return PageText.context(PageText.Page.BLOG, SiteProfile.load())['meta_description']

    def items(self):
        return Post.objects.published().select_related('category')[:20]

    def item_title(self, post):
        return post.title

    def item_description(self, post):
        return post.excerpt

    def item_pubdate(self, post):
        return post.published_at

    def item_updateddate(self, post):
        return post.updated_at or post.published_at

    def item_author_name(self):
        return SiteProfile.load().name

    def item_categories(self, post):
        return [tag.name for tag in post.tags.all()]
