#!/usr/bin/env python2
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
__license__   = 'GPL v3'
__copyright__ = '2014, fenuks'
__docformat__ = 'restructuredtext en'

import importlib
import threading
from Queue import Queue

from calibre.ebooks.metadata.sources.base import Source
from calibre.utils.config import JSONConfig

class Biblionetka(Source):
    # custom variables
    IDENTIFIER = 'biblionetka' # must be the same as import name
    BOOK_PAGE_URL_SCHEME = 'http://www.biblionetka.pl/book.aspx?id={}'
    covers = []
    identified = False

    # generic plugin options
    name                    = 'biblioNETka.pl'
    description             = 'Pobiera metadane z serwisu biblioNETka.pl'
    author                  = 'fenuks'
    version                 = (1, 0, 4)
    minimum_calibre_version = (2, 0, 0)
    supported_platforms = ['linux', 'osx', 'windows']

    # source plugin options
    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'pubdate', 'comments', 'languages', 'rating', 'tags', 'series', 'identifier:'+IDENTIFIER])
    has_html_comments = True
    supports_gzip_transfer_encoding = True
    can_get_multiple_covers = True
    auto_trim_covers = False
    cached_cover_url_is_reliable = True
    prefer_results_with_isbn = True
    prefs = JSONConfig('plugins/' + IDENTIFIER)

    def get_book_url(self, identifiers):
        book_id = identifiers.get(self.IDENTIFIER, None)
        if book_id:
            url = self.BOOK_PAGE_URL_SCHEME.format(book_id)
            return (self.IDENTIFIER, book_id, url)
        else:
            return None

    def identify(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30):
        self.cache_identifier_to_cover_url('urls', [])
        parser_module = importlib.import_module('calibre_plugins.{}.parser'.format(self.IDENTIFIER))
        parser = parser_module.Parser(self, log, timeout)
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

    def download_cover(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30, get_best_cover=False):
        if not self.prefs['covers']:
            return

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
        config_widget = importlib.import_module('calibre_plugins.{}.config'.format(self.IDENTIFIER))
        return config_widget.ConfigWidget()

    def save_settings(self, config_widget):
        return config_widget.save_settings()

    def is_configured(self):
        try:
            self.prefs['max_results']
            return True
        except:
            return False
