#!/usr/bin/env python2
from __future__ import (unicode_literals, division, absolute_import, print_function)
from Queue import Queue

from calibre.ebooks.metadata.sources.base import Source

from .utils import get_prefs
from .parser import Parser
from .config_widget import ConfigWidget
from . import plugin_meta


class BaseSource(Source):
    # custom variables
    IDENTIFIER = plugin_meta.IDENTIFIER
    PREFS = get_prefs()
    BOOK_PAGE_URL_SCHEME = plugin_meta.BOOK_PAGE_URL_SCHEME

    # generic plugin options
    name = plugin_meta.name
    description = plugin_meta.description
    version = plugin_meta.version
    author = plugin_meta.author

    minimum_calibre_version = (2, 0, 0)
    supported_platforms = ['linux', 'osx', 'windows']

    # source plugin options
    capabilities = plugin_meta.capabilities
    touched_fields = plugin_meta.touched_fields

    has_html_comments = True
    supports_gzip_transfer_encoding = True
    can_get_multiple_covers = True
    auto_trim_covers = False
    cached_cover_url_is_reliable = True
    prefer_results_with_isbn = True

    def get_book_url(self, identifiers):
        book_id = identifiers.get(self.IDENTIFIER, None)
        if book_id:
            url = self.BOOK_PAGE_URL_SCHEME.format(book_id)
            return (self.IDENTIFIER, book_id, url)
        else:
            return None

    def identify(self, log, result_queue, abort, title=None, authors=None, identifiers=None, timeout=30):
        if identifiers is None:
            identifiers = {}

        self.cache_identifier_to_cover_url('urls', [])
        parser = Parser(self, log, timeout)
        urls = parser.parse_search_page(title, authors, with_authors=self.PREFS['authors_search'],
                                        only_first_author=self.PREFS['only_first_author'])
        t = self.get_book_url(identifiers)
        if t:
            urls.insert(0, t[2])
        if abort.is_set():
            return

        for url in urls[:self.PREFS['max_results']]:
            mi = parser.parse_book_page(url)
            if mi:
                # self.clean_downloaded_metadata(mi)
                result_queue.put(mi)
            if abort.is_set():
                return

        return

    # cover reladed functions
    def get_cached_cover_url(self, identifiers):
        return self.cached_identifier_to_cover_url('urls')

    def download_cover(self, log, result_queue, abort, title=None, authors=None, identifiers=None, timeout=30, get_best_cover=False):
        if not self.PREFS['covers']:
            return

        if identifiers is None:
            identifiers = {}

        urls = self.get_cached_cover_url(identifiers)
        if not urls and not self.cached_identifier_to_cover_url('nocover'):
            log.info('INFO: No cached cover, need to run identify')
            rq = Queue()
            self.identify(log, rq, abort, title, authors, identifiers, timeout)
            urls = self.get_cached_cover_url(identifiers)
        elif not urls:
            log.warn('WARN: No cover available')
            return
        else:
            log.info('INFO: Found covers in cache')

        if self.PREFS['threads']:
            self.download_multiple_covers(title, authors, urls, get_best_cover, timeout, result_queue, abort, log)
        else:
            for cover in urls[:self.PREFS['max_covers']]:
                self.download_image(cover, timeout, log, result_queue)

    # plugin configuraton window
    def is_customizable(self):
        return True

    def config_widget(self):
        return ConfigWidget()

    def save_settings(self, config_widget):
        return config_widget.save_settings()

    def is_configured(self):
        return True
