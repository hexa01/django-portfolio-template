from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from blog.feeds import PostFeed
from core.sitemaps import SITEMAPS
from core.views import markdown_images, markdown_preview

urlpatterns = [
    path('admin/markdown-preview/', markdown_preview, name='markdown-preview'),
    path('admin/markdown-images/', markdown_images, name='markdown-images'),
    path('admin/', admin.site.urls),
    path('api/agent/', include('agent_content.urls')),
    path('projects/', include('projects.urls')),
    path('blog/', include('blog.urls')),
    path('contact/', include('contact.urls')),
    path('rss/', PostFeed(), name='rss'),
    path('rss/style.xsl', TemplateView.as_view(template_name='blog/feed.xsl', content_type='text/xsl; charset=utf-8'),
         name='rss-style'),
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='sitemap'),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
