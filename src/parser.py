# -*- coding: UTF-8 -*-
#!/usr/bin/env python2
import re
import copy
import datetime

import lxml.html
from calibre.ebooks.metadata.book.base import Metadata
from calibre.utils.date import utc_tz

from .utils import IDENTIFIER
from .parser_base import ParserBase



class Parser(ParserBase):
    url_scheme_title_authors = 'http://www.biblionetka.pl/search.aspx?searchType=book_catalog&searchPhrase={title}%20-%20{authors}'
    url_scheme_title = 'http://www.biblionetka.pl/search.aspx?searchType=book_catalog&searchPhrase={title}'
    book_tag_xpath = '//*[@class="hReview-aggregate"]'

    def parse_search_page(self, root_tag, url, title, authors, with_authors=False, only_first_author=False):
        results = []

        title_tokens = [token for token in title.lower().split(' ') if len(token)>1]
        authors_tokens = self.get_name_tokens(authors)
        for book_record in root_tag.xpath('//div[@id="ctl00_MCP_booksSection"]/ul/li'):
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

    def parse_authors(self, root_tag, book_tag, url):
        book_authors = book_tag.xpath('.//strong[text()[contains(., "Autor")]]')[0].getnext().text_content().strip()
        book_authors = book_authors.partition('(')[0].strip()
        return self.get_names(book_authors, name_reversed=True)

    def parse_identifier(self, root_tag, book_tag, url):
        return re.search(r'id=(\d+)', url).group(1)

    def parse_series(self, root_tag, book_tag, url):
        series = []
        serie_nodes = root_tag.xpath('//li/ul/li/a[preceding::strong[text()[contains(.,"Cykle:")]]]')
        for serie_node in serie_nodes:
            serie_entry = [serie_node.text]
            match = re.search(r'\(tom: (\d+)\)', serie_node.tail)
            if match:
                serie_entry.append(match.group(1))
            else:
                serie_entry.append(None)

            series.append(serie_entry)

        return series

    def parse_rating(self, root_tag, book_tag, url):
        rating_node = root_tag.xpath('//span[@class="rating"]//span[@class="average"]/text()')
        if rating_node:
            rating_value = round(float((rating_node[0]).replace(',', '.')) * 0.83333)
            self.log.info('INFO: Found rating: {}'.format(rating_value))
            return rating_value
        return None

    def parse_languages(self, root_tag, book_tag, url):
        return ['pl']

    def parse_tags(self, root_tag, book_tag, url):
        return root_tag.xpath('//a[@class="tag"]/text()')

    def parse_title(self, root_tag, book_tag, url):
        return book_tag.find_class('fn')[0].text_content().strip()

    def parse_pubdate(self, root_tag, book_tag, url):
        tag = book_tag.xpath('.//strong[text()[contains(., "Rok pierwszego wydania:")]]')
        if tag:
            return datetime.datetime(int(tag[0].tail.strip()), 1, 1, tzinfo=utc_tz)

    def parse_covers(self, root_tag, book_tag, url):
        tag = root_tag.find('.//div[@id="bookShopCoverContent"]')
        if tag is not None:
            return [tag.find('.//img').get('src', '')]

    def parse_translators(self, root_tag, book_tag, url):
        data = book_tag.xpath('.//strong[text()[contains(., "umacz:")]]')
        if data:
            data = data[0].tail.strip()
            return self.get_names(data, name_reversed=True)

        return None

    def parse_original_title(self, root_tag, book_tag, url):
        data = book_tag.xpath('.//strong[text()[(contains(., "oryginalny:")) and not(contains(., "k oryginalny:"))]]')
        if data:
            return data[0].tail.strip()

        return None

    def parse_categories(self, root_tag, book_tag, url):
        data = book_tag.xpath('.//strong[text()[contains(., "Kategoria:")]]')
        try:
            data = data[0]
            return data.tail.strip()
        except:
            self.log.exception('ERROR: Failed to parse categories')

    def parse_genres(self, root_tag, book_tag, url):
        if self.enabled('genres'):
            data = book_tag.xpath('.//strong[text()[contains(., "Gatunek:")]]')
            try:
                data = data[0]
                return data.tail.strip()
            except:
                self.log.exception('ERROR: Failed to parse genres')

    def parse_comments(self, root_tag, book_tag, url):
        tag = root_tag.xpath('.//span/h2[text()[contains(., "Noty wydaw")]]/following::div')
        if tag:
            tag = tag[0]
            tag = tag.find('./p')
            if tag.attrib.has_key('style'):
                del tag.attrib['style']
            return lxml.html.tostring(tag)

        return None
