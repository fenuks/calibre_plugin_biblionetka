# -*- coding: UTF-8 -*-
#!/usr/bin/env python2
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
import re
import copy
import datetime
import urllib2
import cookielib
import socket

import lxml.html

from .utils import IDENTIFIER

from calibre.ebooks.metadata.book.base import Metadata
from calibre.utils.date import utc_tz

URL_SCHEME_TITLE = 'http://www.biblionetka.pl/search.aspx?searchType=book_catalog&searchPhrase={title}'
URL_SCHEME_TITLE_AUTHORS = 'http://www.biblionetka.pl/search.aspx?searchType=book_catalog&searchPhrase={title}%20-%20{authors}'
AUTHORS_JOIN_DELIMETER = ', '
AUTHORS_SPLIT_DELIMETER = ', '
SKIP_AUTHORS = ('Unknown', 'Nieznany')

class Parser():
    def __init__(self, plugin, log, timeout):
        self.plugin = plugin
        self.log = log
        self.timeout = timeout
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        urllib2.install_opener(self.opener)
        self.login()

    @property
    def prefs(self):
        return self.plugin.prefs

    def download_page(self, url):
        try:
            resp = urllib2.urlopen(url, timeout=self.timeout)
            self.log.info('INFO: Download complete: {}'.format(url))
            return resp
        except urllib2.URLError:
            self.log.exception('ERROR: Download failed: {}'.format(url))
            return
        except socket.timeout:
            self.log.exception('ERROR: Download failed, request timed out: {}'.format(url))
            return

    def get_authors(self, authors, name_reversed=False):
        authors_list = []

        for author in authors.split(AUTHORS_SPLIT_DELIMETER):
            if name_reversed:
                tokens = author.split(' ')
                tokens = tokens[1:] + tokens[:1]
                authors_list.append(' '.join(tokens))
            else:
                authors_list.append(author)

        return authors_list

    def get_authors_tokens(self, authors, only_first_author=False):
        authors_tokens = []

        for author in authors:
            for token in author.lower().split(' '):
                if len(token) > 1 and not token.endswith('.'):
                    authors_tokens.append(token)

            if only_first_author:
                break

        return authors_tokens

    def create_authors_string(self, authors, only_first_author=False):
        if only_first_author:
            authors_string = AUTHORS_JOIN_DELIMETER.join(authors[:1])
        else:
            authors_string = AUTHORS_JOIN_DELIMETER.join(authors)

        return authors_string

    def get_translators(self, translators, name_reversed=False):
        translators_list = []

        for author in translators.split(AUTHORS_SPLIT_DELIMETER):
            if name_reversed:
                tokens = author.split(' ')
                tokens = tokens[1:] + tokens[:1]
                translators_list.append(' '.join(tokens))
            else:
                translators_list.append(author)

        return translators_list

    def get_translators_tokens(self, translators, only_first_author=False):
        translators_tokens = []

        for author in translators:
            for token in author.lower().split(' '):
                if len(token) > 1 and not token.endswith('.'):
                    translators_tokens.append(token)

            if only_first_author:
                break

        return translators_tokens

    def create_translators_string(self, translators, only_first_author=False):
        if only_first_author:
            translators_string = AUTHORS_JOIN_DELIMETER.join(translators[:1])
        else:
            translators_string = AUTHORS_JOIN_DELIMETER.join(translators)

        return translators_string

    def create_search_page_url(self, title, authors_string, with_authors=False):
        if not title:
            return ('', with_authors)

        if authors_string and with_authors:
            url = URL_SCHEME_TITLE_AUTHORS.format(title=urllib2.quote(title.encode('utf-8')),
                                        authors=urllib2.quote(authors_string.encode('utf-8')))
        else:
            with_authors = False
            url = URL_SCHEME_TITLE.format(title=urllib2.quote(title.encode('utf-8')))

        return (url, with_authors)

    def login(self):
        pass

    def parse_book_page(self, url):
        # TODO: Support for login-based rating fetching
        # TODO: Move all parsing logic to methods in order to avoid dangling variables
        self.log.info('INFO: Downloading book page: {}'.format(url))
        resp = self.download_page(url)
        if not resp:
            return

        self.log.info('INFO: Parsing book page')
        additional_meta = {}

        tree = lxml.html.parse(resp)
        root = tree.getroot()
        book_tag = root.find_class('hReview-aggregate')[0]

        if self.prefs['title']:
            book_title = book_tag.find_class('fn')[0].text_content().strip()
        else:
            book_title = self.title
        if self.prefs['authors']:
            book_authors = book_tag.xpath('.//strong[text()[contains(., "Autor")]]')[0].getnext().text_content().strip()
            book_authors = book_authors.partition('(')[0].strip()
            book_authors = self.get_authors(book_authors, name_reversed=True)
        else:
            book_authors = self.authors

        mi = Metadata(book_title, book_authors)

        if self.prefs['languages']:
            mi.languages = ['pl']

        if self.prefs['rating']:
            try:
                mi.rating = self.parse_rating(root)
            except:
                self.log.exception('ERROR: Error getting ratings')

        if self.prefs['tags']:
            tag = root.xpath('//a[@class="tag"]/text()')
            if tag:
                mi.tags = tag

        if self.prefs['identifier']:
            identifier_id = re.search(r'id=(\d+)', url).group(1)
            mi.set_identifier(IDENTIFIER, identifier_id)

        if self.prefs['covers']:
            tag = root.find('.//div[@id="bookShopCoverContent"]')
            if tag is not None:
                cover_url = tag.find('.//img').get('src', '')
                if cover_url:
                    mi.has_cover = True
                    self.log.info('INFO: Cover found: ' + cover_url)
                    urls = self.plugin.cached_identifier_to_cover_url('urls')
                    urls.append(cover_url)
                else:
                    self.log.warn('WARN: Cover is not available')
                    self.plugin.cache_identifier_to_cover_url('nocover', True)

        if self.prefs['pubdate']:
            tag = book_tag.xpath('.//strong[text()[contains(., "Rok pierwszego wydania:")]]')
            if tag:
                tag = tag[0]
                mi.pubdate = datetime.datetime(int(tag.tail.strip()), 1, 1, tzinfo=utc_tz)

        if self.prefs['series']:
            try:
                (series, series_index) = self.parse_series(root)
            except:
                self.log.exception('Error parsing series for url: {}'.format(self.url))
                series = series_index = None
            if series:
                mi.series = series
                additional_meta['series'] = series
            if series_index:
                mi.series_index = series_index
                # it can fall if series is not in additional_meta, but assumption is being made index cannot be returned in such case as well
                additional_meta['series'] = additional_meta['series'] + ' [' + str(series_index) + ']'

        # additional metadata parsing
        # TODO: saving in custom columns
        if self.prefs['translators']:
            data = book_tag.xpath('.//strong[text()[contains(., "umacz:")]]')
            try:
                data = data[0]
                data = data.tail.strip()
                additional_meta['translators'] = self.get_translators(data, name_reversed=True)
            except:
                self.log.exception('ERROR: Failed to parse translators')

        if self.prefs['original_title']:
            data = book_tag.xpath('.//strong[text()[(contains(., "oryginalny:")) and not(contains(., "k oryginalny:"))]]')
            try:
                data = data[0]
                additional_meta['original_title'] = data.tail.strip()
            except:
                self.log.exception('ERROR: Failed to parse original title')

        if self.prefs['categories']:
            data = book_tag.xpath('.//strong[text()[contains(., "Kategoria:")]]')
            try:
                data = data[0]
                additional_meta['categories'] = data.tail.strip()
            except:
                self.log.exception('ERROR: Failed to parse categories')

        if self.prefs['genres']:
            data = book_tag.xpath('.//strong[text()[contains(., "Gatunek:")]]')
            try:
                data = data[0]
                additional_meta['genres'] = data.tail.strip()
            except:
                self.log.exception('ERROR: Failed to parse genres')

        if self.prefs['comments']:
            tag = root.xpath('.//span/h2[text()[contains(., "Noty wydaw")]]/following::div')
            if tag:
                tag = tag[0]
                tag = tag.find('./p')
                if tag.attrib.has_key('style'):
                    del tag.attrib['style']
                mi.comments = lxml.html.tostring(tag)

                # Additional informations saved in
                if additional_meta['original_title']:
                    mi.comments = mi.comments + u'<p id="book_original_title">Tytuł oryginału: <em>' + additional_meta['original_title'] + '</em></p>'
                    self.log.debug(u'DEBUG: Embedded original title in comment')
                if 'translators' in additional_meta:
                    mi.comments = mi.comments + u'<p id="tlumaczenie">Tłumaczenie: ' + ', '.join(additional_meta['translators']) + '</p>'
                    self.log.debug(u'DEBUG: Embedded translator(s) in comment')
                if 'categories'in additional_meta:
                    mi.comments = mi.comments + u'<p id="kategoria">Kategoria: ' + additional_meta['categories'] + '</p>'
                    self.log.debug(u'DEBUG: Embedded categories in comment')
                if 'genres' in additional_meta:
                    mi.comments = mi.comments + u'<p id="gatunek">Gatunek: ' + additional_meta['genres'] + '</p>'
                    self.log.debug(u'DEBUG: Embedded genres in comment')
                if 'series' in additional_meta:
                    mi.comments = mi.comments + u'<p id="cykl">Cykl: ' + additional_meta['series'] + '</p>'
                    self.log.debug(u'DEBUG: Embedded series in comment')

        self.log.info('INFO: Parsing book page completed')
        return mi

    def parse_search_page(self, title, authors, with_authors=False, only_first_author=False):
        results = []
        authors = authors or []
        self.authors = copy.copy(authors)
        self.title = title
        authors = [a for a in authors if not a in SKIP_AUTHORS]
        authors_string = self.create_authors_string(authors, only_first_author)
        url, with_authors = self.create_search_page_url(title, authors_string, with_authors)

        self.log.info('INFO: Downloading search page: {}'.format(url))
        resp = self.download_page(url)
        if not resp:
            return results

        self.log.info('INFO: Parsing search page')

        tree = lxml.html.parse(resp)
        root = tree.getroot()

        title_tokens = [token for token in title.lower().split(' ') if len(token)>1]
        authors_tokens = self.get_authors_tokens(authors)
        for book_record in root.xpath('//div[@id="ctl00_MCP_booksSection"]/ul/li'):
            title_match = False
            author_match = not bool(authors_tokens) or not with_authors

            title_tag, author_tag = book_record.xpath('./a')[:2]
            book_title = title_tag.text_content().strip().lower()
            book_authors = author_tag.text_content().partition('(')[0].strip().lower()

            for token in title_tokens:
                if token in book_title:
                    title_match = True
                    break
            if not author_match:
                for token in authors_tokens:
                    if token in book_authors:
                        author_match = True
            if title_match and author_match:
                self.log.info('INFO: Match found: title: {}, author(s): {}'.format(book_title, book_authors))
                results.append('http://www.biblionetka.pl/' + title_tag.attrib['href'])
            else:
                self.log.warn('WARN: No match: title: {}, author(s): {}'.format(book_title, book_authors))

        if not results and with_authors:
            return self.parse_search_page(title, authors, False)

        self.log.info('INFO: Parsing search page completed')
        return results

    def parse_series(self, root):
        try:
            series_node = root.xpath('//li//a[contains(@href,"bookSerie.aspx")]')
            if series_node:
                series_list = root.xpath('//li//a[contains(@href,"bookSerie.aspx")]/text()')
                if series_list:
                    series_text = series_list[0]
                else:
                    series_text = None
            else:
                self.log.info('Series not found')
                return (None, None)

            if series_text:
                for _data in root.xpath('//li/a[contains(@href,"bookSerie.aspx")]/following-sibling::text()[1]'):
                    if 'tom:' in _data:
                        series_info = _data.split(' (tom: ', 1)
                        break
            if series_info:
                series_index_unicode = series_info[1]
                series_index_string = str(series_index_unicode.replace(" ", "").replace(")", ""))
                if series_index_string.isdigit():
                    series_index = int(series_index_string)
                else:
                    series_index = 0
            else:
                series_index = 0
            return (series_text, series_index)
        except:
            return (None, None)

    def parse_rating(self, root):
        rating_node = root.xpath('//span[@class="rating"]//span[@class="average"]/text()')
        if rating_node:
            rating_value = round(float((rating_node[0]).replace(',','.'))*0.83333)
            self.log.info('INFO: Found rating: {}'.format(rating_value))
            return rating_value
        return None
