# -*- coding: UTF-8 -*-
#!/usr/bin/env python2
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
import re
import copy
import datetime
import urllib
import urllib2
import cookielib
import socket

import lxml.html

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
            self.log.info('INFO: Download complete: ' + url)
            return resp
        except urllib2.URLError as e:
            self.log.error('ERROR: Download failed: ' + url)
            self.log.exception(e)
            return
        except socket.timeout as e:
            self.log.exception(e)
            self.log.error('ERROR: Download failed, request timed out: ' + url)
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

    def parse_book_page_t(self, urls, result_queue, lock):
        while True:
            url = ''
            with lock:
                if urls:
                    url = urls.pop()
            if not url:
                return
            mi = self.parse_book_page(url)
            if mi:
                result_queue.put(mi)
            if abort.is_set():
                return

    def parse_book_page(self, url):
        # TODO: Support for series, login and fetching rating
        # BECKU INFO: zrobione cykle i oceny
        self.log.info('INFO: Downloading book page: ' + url)
        resp = self.download_page(url)
        if not resp:
            return

        self.log.info('INFO: Parsing book page')

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

        #Zadeklarowanie pustych metadanych dodatkowych
        book_translators = ''
        tytul_oryginalu = ''
        book_kategoria = ''
        book_gatunek = ''
        book_cykle = ''

        if self.prefs['get_translators']:
            book_translators = book_tag.xpath('.//strong[text()[contains(., "umacz:")]]')
            try:
                book_translators = book_translators[0]
                book_translators = book_translators.tail.strip()
                book_translators = self.get_translators(book_translators, name_reversed=True)
            except:
                book_translators = None

        if self.prefs['get_original_title']:
            tytul_oryginalu = book_tag.xpath('.//strong[text()[(contains(., "oryginalny:")) and not(contains(., "k oryginalny:"))]]')
            try:
                tytul_oryginalu = tytul_oryginalu[0]
                tytul_oryginalu = tytul_oryginalu.tail.strip()

            except:
                tytul_oryginalu = None

        if self.prefs['get_kategorie']:
            book_kategoria = book_tag.xpath('.//strong[text()[contains(., "Kategoria:")]]')
            try:
                book_kategoria = book_kategoria[0]
                book_kategoria = book_kategoria.tail.strip()
            except:
                book_kategoria = None

        if self.prefs['get_gatunki']:
            #self.log.info('Start tytul oryginalny')
            book_gatunek = book_tag.xpath('.//strong[text()[contains(., "Gatunek:")]]')
            try:
                book_gatunek = book_gatunek[0]
                book_gatunek = book_gatunek.tail.strip()
            except:
                book_gatunek = None

        if self.prefs['get_cykle']:
            try:
                (cykle, cykle_index) = self.parse_cykle(root)
            except:
                self.log.exception('Error parsing cykle for url: %r'%self.url)
                cykle = cykle_index = None
            #TODO: Dodac konfiguracje czy zapisywac cykl jako cykl (series) w glownych metadanych
            if cykle:
                #mi.series = cykle
                book_cykle = cykle
            if cykle_index:
                #mi.series_index = cykle_index
                book_cykle = book_cykle + ' [' + str(cykle_index) + ']'

        else:
            book_authors = self.authors
        mi = Metadata(book_title, book_authors)

        if self.prefs['pubdate']:
            tag = book_tag.xpath('.//strong[text()[contains(., "Rok pierwszego wydania:")]]')
            if tag:
                tag = tag[0]
                mi.pubdate = datetime.datetime(int(tag.tail.strip()), 1, 1, tzinfo=utc_tz)
        if self.prefs['comments']:
            tag = root.xpath('.//span/h2[text()[contains(., "Noty wydaw")]]/following::div')
            if tag:
                tag = tag[0]
                tag = tag.find('./p')
                if tag.attrib.has_key('style'):
                    del tag.attrib['style']
                mi.comments = lxml.html.tostring(tag)
                # Dodatkowe informacje zapisywane w komentarzu
                if tytul_oryginalu:
                    mi.comments = mi.comments + u'<p id="tytul_oryginalu">Tytuł oryginału: <em>' + tytul_oryginalu + '</em></p>'
                    self.log.info(u'BECKY INFO: Do komentarza tytul oryginalu')
                if book_translators:
                    mi.comments = mi.comments + u'<p id="tlumaczenie">Tłumaczenie: ' + ', '.join(book_translators) + '</p>'
                    self.log.info(u'BECKY INFO: Do komentarza dolaczono tlumaczy')
                if book_kategoria:
                    mi.comments = mi.comments + u'<p id="kategoria">Kategoria: ' + book_kategoria + '</p>'
                    self.log.info(u'BECKY INFO: Do komentarza dolaczono kategorie')
                if book_gatunek:
                    mi.comments = mi.comments + u'<p id="gatunek">Gatunek: ' + book_gatunek + '</p>'
                    self.log.info(u'BECKY INFO: Do komentarza dolaczono gatunek')
                if book_cykle:
                    mi.comments = mi.comments + u'<p id="cykl">Cykl: ' + book_cykle + '</p>'
                    self.log.info(u'BECKY INFO: Do komentarza dolaczono cykle')

        if self.prefs['languages']:
            mi.languages = ['pl']
        if self.prefs['rating']:
            try:
                mi.rating = self.parse_rating(root)
            except:
                self.log.exception('BECKY INFO: Error parsing ratings')

        if self.prefs['tags']:
            tag = root.xpath('//a[@class="tag"]/text()')
            if tag:
                mi.tags = tag

        #Zapisanie cykli w metadanych
        if self.prefs['get_cykle']:
            if cykle:
                mi.series = cykle
            if cykle_index:
                mi.series_index = cykle_index

        if self.prefs['identifier']:
            identifier_id = re.search(r'id=(\d+)', url).group(1)
            mi.set_identifier(self.plugin.IDENTIFIER, identifier_id)


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

        self.log.info('INFO: Downloading search page: ' + url)
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

    def parse_cykle(self, root):
        try:
            cykle_node = root.xpath('//li//a[contains(@href,"bookSerie.aspx")]')
            if cykle_node:
                cykle_lst = root.xpath('//li//a[contains(@href,"bookSerie.aspx")]/text()')
                if cykle_lst:
                    cykle_txt = cykle_lst[0]
                else:
                    cykle_txt = None
            else:
                self.log.info('Not found cykle (Nie znaleziono cyklu)')
                return (None, None)
            if cykle_txt:
                ser_string = root.xpath('//li/a[contains(@href,"bookSerie.aspx")]/following-sibling::text()[1]')
                for ser in ser_string:
                    if 'tom:' in ser:
                        ser_info = ser.split(' (tom: ', 1)
                        found = 1
                        break
            if ser_info:
                cykle_index_unicode = ser_info[1]
                cykle_index_string = str(cykle_index_unicode.replace(" ", "").replace(")", ""))
                if cykle_index_string.isdigit() == True:
                    cykle_index = int(cykle_index_string)
                else:
                    cykle_index = 0

            else:
                cykle_index = 0
            cykle = cykle_txt
            return (cykle, cykle_index)
        except:
            return (None, None)


    def parse_rating(self, root):
        rating_node = root.xpath('//span[@class="rating"]//span[@class="average"]/text()')
        if rating_node:
            rating_value = round(float((rating_node[0]).replace(',','.'))*0.83333)
            self.log.info('BECKY INFO: Found rating: %s'%rating_value)
            return rating_value
        return None
