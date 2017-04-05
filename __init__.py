#!/usr/bin/env python2
from __future__ import (unicode_literals, division, absolute_import, print_function)
__license__ = 'GPL v3'
__copyright__ = '2017, fenuks'
__docformat__ = 'restructuredtext en'

from Queue import Queue

from calibre.ebooks.metadata.sources.base import Source

from .utils import IDENTIFIER
from .utils import get_prefs
from .parser import Parser
from .config import ConfigWidget

BOOK_PAGE_URL_SCHEME = 'http://www.biblionetka.pl/book.aspx?id={}'

class Biblionetka(Source):
    # custom variables
    covers = []
    identified = False

    # generic plugin options
    name = 'biblioNETka.pl'
    description = 'Pobiera metadane z serwisu {}'.format(name)
    author = 'fenuks'
    version = (1, 0, 5)
    minimum_calibre_version = (2, 0, 0)
    supported_platforms = ['linux', 'osx', 'windows']

    # source plugin options
    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'pubdate', 'comments', 'languages', 'rating', 'tags', 'series',
                                'identifier:{}'.format(IDENTIFIER)])
    has_html_comments = True
    supports_gzip_transfer_encoding = True
    can_get_multiple_covers = True
    auto_trim_covers = False
    cached_cover_url_is_reliable = True
    prefer_results_with_isbn = True
    prefs = get_prefs()

    def get_book_url(self, identifiers):
        book_id = identifiers.get(IDENTIFIER, None)
        if book_id:
            url = BOOK_PAGE_URL_SCHEME.format(book_id)
            return (IDENTIFIER, book_id, url)
        else:
            return None

    def identify(self, log, result_queue, abort, title=None, authors=None, identifiers=None, timeout=30):
        if identifiers is None:
            identifiers = {}

        self.cache_identifier_to_cover_url('urls', [])
        parser = Parser(self, log, timeout)
        urls = parser.parse_search_page(title, authors, with_authors=self.prefs['authors_search'],
                                        only_first_author=self.prefs['only_first_author'])
        t = self.get_book_url(identifiers)
        if t:
            urls.insert(0, t[2])
        if abort.is_set():
            return

        for url in urls[:self.prefs['max_results']]:
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
        if not self.prefs['covers']:
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

        if self.prefs['threads']:
            self.download_multiple_covers(title, authors, urls, get_best_cover, timeout, result_queue, abort, log)
        else:
            for cover in urls[:self.prefs['max_covers']]:
                self.download_image(cover, timeout, log, result_queue)

    # plugin configuraton window
    def is_customizable(self):
        return True

    def config_widget(self):
        return ConfigWidget()

    def save_settings(self, config_widget):
        return config_widget.save_settings()

    def is_configured(self):
        try:
            self.prefs['series']
            return True
        except:
            return False
