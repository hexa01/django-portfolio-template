{% load static %}<?xml version="1.0" encoding="UTF-8"?>
<!-- Shows the RSS feed as a page when it is opened in a browser. Feed readers ignore this file. -->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:atom="http://www.w3.org/2005/Atom">
  <xsl:output method="html" encoding="UTF-8" doctype-system="about:legacy-compat"/>
  <xsl:template match="/rss/channel">
    <html lang="en" data-theme="dark">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <meta name="robots" content="noindex"/>
        <link rel="icon" href="{% url 'core:favicon' %}" type="image/svg+xml"/>
        <title><xsl:value-of select="title"/> | RSS feed</title>
        <link rel="stylesheet" href="{% static 'css/tokens.css' %}"/>
        <link rel="stylesheet" href="{% static 'css/base.css' %}"/>
        <link rel="stylesheet" href="{% static 'css/pages.css' %}"/>
        <link rel="stylesheet" href="{% static theme_css %}"/>
        <script>try { var t = localStorage.getItem('theme'); if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t; } catch (e) {}</script>
        <style>
          .feed-note { margin-top: var(--s-3); padding: var(--s-3); max-width: var(--read); background: var(--bg-2); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-2); }
          .feed-note p { margin: 0; }
          .feed-note code { display: block; margin-top: var(--s-1); padding: var(--s-1) var(--s-2); font: 400 var(--t-sm)/1.6 var(--mono); color: var(--text); background: var(--surface); border-radius: 4px; overflow-wrap: anywhere; user-select: all; }
        </style>
      </head>
      <body>
        <main id="main">
          <header class="page-head">
            <div class="wrap">
              <a class="back" href="{% url 'blog:index' %}">Back to the blog</a>
              <h1><xsl:value-of select="title"/></h1>
              <div class="feed-note">
                <p>This is an RSS feed: a list of new posts for feed readers (such as Feedly, Inoreader or NetNewsWire).
                To follow the blog, copy this address into your reader.</p>
                <code><xsl:value-of select="atom:link[@rel='self']/@href"/></code>
              </div>
            </div>
          </header>
          <div class="page-body">
            <div class="wrap">
              <ul class="posts posts-full">
                <xsl:for-each select="item">
                  <li>
                    <time><xsl:value-of select="substring(pubDate, 6, 11)"/></time>
                    <div>
                      <a href="{link}"><h2><xsl:value-of select="title"/></h2></a>
                      <p><xsl:value-of select="description"/></p>
                    </div>
                  </li>
                </xsl:for-each>
              </ul>
            </div>
          </div>
        </main>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
