import http.cookiejar
import urllib.request, urllib.error, urllib.parse
import socket
import lxml.html
import copy
from typing import Tuple, Optional

from .utils import IDENTIFIER

from calibre.ebooks.metadata.book.base import Metadata


class ParserBase:
    names_split_delimiter = ', '
    names_join_delimiter = ', '
    url_scheme_title = None  # need to be set
    url_scheme_title_authors = None # need to be set
    book_tag_xpath = None
    SKIP_AUTHORS = ('Unknown', 'Nieznany')

    def __init__(self, plugin, log, timeout):
        self.plugin = plugin
        self.prefs = plugin.PREFS
        self.log = log
        self.timeout = timeout
        self.cj = http.cookiejar.CookieJar()
        self.title = ''
        self.authors = []
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        urllib.request.install_opener(self.opener)

    def run(self, title: str, authors, identifier_url, abort):
        """Runs parser."""
        authors_search = self.prefs['authors_search']
        only_first_author = self.prefs['only_first_author']

        results = []
        authors = authors or []
        self.authors = copy.copy(authors)
        self.title = title
        authors = [a for a in authors if not a in self.SKIP_AUTHORS]
        authors_string = self.get_name_string(authors, only_first_author)
        title_url, authors_url = self.get_search_page_url(title, authors_string)

        self.log.info('INFO: Parsing search page')
        book_page_urls = self.parse_search_page(title_url, title, authors, only_first_author)
        if authors_search and len(book_page_urls) < self.prefs['max_results']:
            book_page_urls.extend(self.parse_search_page(authors_url, title, authors, only_first_author))

        if identifier_url:
            book_page_urls.insert(0, identifier_url)

        if abort.is_set():
            return results

        for url in book_page_urls[:self.prefs['max_results']]:
            mi = self.parse_book_page(url)

            if mi:
                results.append(mi)

            if abort.is_set():
                return results

        return results

    def get_search_page_url(self, title: str, authors_string: Optional[str], with_authors: bool=False) -> Tuple[str, str]:
        """Returns url to page with search results for given book and author"""

        title_url = self.url_scheme_title.format(title=urllib.parse.quote(title.encode('utf-8')))
        author_url = self.url_scheme_title_authors.format(title=urllib.parse.quote(title.encode('utf-8')),
                                                       authors=urllib.parse.quote(authors_string.encode('utf-8'))) if authors_string else None
        return (title_url, author_url)

    def parse_book_page(self, url):
        # TODO: Support for login-based rating fetching
        # TODO: Move all parsing logic to methods in order to avoid dangling variables
        # TODO: Saving metadata in custom columns
        # TODO: Configurable embedding metadata in comment
        # TODO: missing items
        # original language, first polish publish date, publisher serie, form

        self.log.info('INFO: Downloading book page: {}'.format(url))
        root_tag = self.get_lxml_root(url)

        if not root_tag:
            return None

        book_tag = self.get_book_tag(root_tag)

        if self.prefs['title']:
            book_title = self.parse_title(root_tag, book_tag, url)
        else:
            book_title = self.title

        if self.prefs['authors']:
            book_authors = self.parse_authors(root_tag, book_tag, url)
        else:
            book_authors = self.authors

        mi = Metadata(book_title, book_authors)
        additional_meta = {}

        if self.enabled('languages'):
            languages = self.parse_languages(root_tag, book_tag, url)
            if languages:
                mi.languages = languages

        if self.enabled('rating'):
            rating = self.parse_rating(root_tag, book_tag, url)
            if rating != None:
                mi.rating = rating

        if self.enabled('tags'):
            tags = self.parse_tags(root_tag, book_tag, url)
            if tags:
                mi.tags = tags

        if self.enabled('identifier'):
            identifier = self.parse_identifier(root_tag, book_tag, url)
            if identifier:
                mi.set_identifier(IDENTIFIER, identifier)

        if self.enabled('pubdate'):
            pubdate = self.parse_pubdate(root_tag, book_tag, url)
            if pubdate:
                mi.pubdate = pubdate

        if self.enabled('covers'):
            covers = self.parse_covers(root_tag, book_tag, url)
            if covers:
                mi.has_cover = True
                self.plugin.cached_identifier_to_cover_url('urls').extend(covers)
            else:
                self.plugin.cache_identifier_to_cover_url('nocover', True)
                # TODO: is this necessary?

        if self.enabled('series'):
            series = self.parse_series(root_tag, book_tag, url)
            if series:
                additional_meta['series'] = [self.get_series_string(name, index) for name, index in series]
                name, index = series[0]
                mi.series = name
                if index is not None:
                    mi.series_index = index

        if self.enabled('translators'):
            translators = self.parse_translators(root_tag, book_tag, url)
            if translators:
                additional_meta['translators'] = translators

        if self.enabled('original_title'):
            original_title = self.parse_original_title(root_tag, book_tag, url)
            if original_title:
                additional_meta['original_title'] = original_title

        if self.enabled('categories'):
            categories = self.parse_categories(root_tag, book_tag, url)
            if categories:
                additional_meta['categories'] = categories

        if self.enabled('genres'):
            genres = self.parse_genres(root_tag, book_tag, url)
            if genres:
                additional_meta['genres'] = genres

        if self.enabled('comments'):
            comments = self.parse_comments(root_tag, book_tag, url) or ''
            additional_comments = self.format_additional_comment(additional_meta)

            if comments or additional_comments:
                mi.comments = comments + additional_comments

        self.log.info('INFO: Parsing book page completed')

        return mi

    def get_series_string(self, name, number):
        if number is not None:
            return name + '[{}]'.format(number)

        return name

    def format_additional_comment(self, additional_meta):
        comments = ''
        if 'original_title' in additional_meta:
            comments += '<p id="tytul_oryginalu">Tytuł oryginału: <em>' + additional_meta['original_title'] + '</em></p>'
            self.log.debug('DEBUG: Embedded original title in comment')
        if 'translators' in additional_meta:
            comments += '<p id="tlumaczenie">Tłumaczenie: ' + ', '.join(additional_meta['translators']) + '</p>'
            self.log.debug('DEBUG: Embedded translator(s) in comment')
        if 'categories'in additional_meta:
            comments += '<p id="kategoria">Kategoria: ' + additional_meta['categories'] + '</p>'
            self.log.debug('DEBUG: Embedded categories in comment')
        if 'genres' in additional_meta:
            comments += '<p id="gatunek">Gatunek: ' + additional_meta['genres'] + '</p>'
            self.log.debug('DEBUG: Embedded genres in comment')
        if 'series' in additional_meta:
            comments += '<p id="cykl">Cykle: ' + ', '.join(additional_meta['series']) + '</p>'
            self.log.debug('DEBUG: Embedded series in comment')

        return comments

    def get_book_tag(self, root_tree):
        book_tag = None
        if self.book_tag_xpath:
            match = root_tree.xpath(self.book_tag_xpath)
            if len(match) == 1:
                book_tag = match[0]
            else:
                self.log.error('Found another number that one[{}] tag containing book details'.format(match))
                raise ValueError('Bad book xpath')

        return book_tag

    def get_lxml_root(self, url):
        """Downloads page from URL and returns LXML root"""

        resp = self.download_page(url)
        if resp:
            return lxml.html.parse(resp).getroot()

        return None

    def download_page(self, url):
        """Downloads page"""

        try:
            resp = urllib.request.urlopen(url, timeout=self.timeout)
            self.log.info('INFO: Download complete: {}'.format(url))
            return resp
        except urllib.error.URLError:
            self.log.exception('ERROR: Download failed: {}'.format(url))
        except socket.timeout:
            self.log.exception('ERROR: Download failed, request timed out: {}'.format(url))

    def get_names(self, names, name_reversed=False):
        """Returns names list parsed from string."""

        names_list = [] # use set() instead of list?

        for name in names.split(self.names_split_delimiter):
            if name_reversed:
                tokens = name.split(' ')
                tokens = tokens[1:] + tokens[:1]
                names_list.append(' '.join(tokens))
            else:
                names_list.append(name)

        return names_list

    # calibre Source class provides similar get_author_tokens and get_title_tokens
    def get_name_tokens(self, names, only_first_name=False):
        """Returns list of tokens from list of names."""

        names_tokens = []

        for name in names:
            for token in name.lower().split(' '):
                if len(token) > 1 and not token.endswith('.'):
                    names_tokens.append(token)

            if only_first_name:
                break

        return names_tokens

    def get_name_string(self, names, only_first_name=False):
        """Creates string from names list."""

        if only_first_name:
            names_string = self.names_join_delimiter.join(names[:1])
        else:
            names_string = self.names_join_delimiter.join(names)

        return names_string

    def enabled(self, metadata_field):
        """Checks if given metadata piece is supported and/or enabled"""

        if metadata_field in self.prefs.defaults and self.prefs.get(metadata_field, False):
            self.log.debug('Writing {} metadata field enabled, processing…'.format(metadata_field))
            return True

        self.log.debug('Writing {} metadata field disabled, skipping…'.format(metadata_field))
        return False

    #### METHODS THAT NEED TO BE IMPLEMENTED
    def parse_search_page(self, url, title, authors, with_authors=False, only_first_author=False):
        """Returns list of book pages url."""

        raise NotImplementedError

    def parse_series(self, root_tag, book_tag, url):
        """Returns list of book series."""

        raise NotImplementedError

    def parse_authors(self, root_tag, book_tag, url):
        """Returns list of book authors."""

        raise NotImplementedError

    def parse_covers(self, root_tag, book_tag, url):
        """Returns list with cover urls"""

        raise NotImplementedError

    def parse_identifier(self, root_tag, book_tag, url):
        """Returns book unique id."""

        raise NotImplementedError

    def parse_languages(self, root_tag, book_tag, url):
        """Returns list of languages."""

        raise NotImplementedError

    def parse_rating(self, root_tag, book_tag, url):
        """Returns either integer from [0-5] range or None."""

        raise NotImplementedError

    def parse_tags(self, root_tag, book_tag, url):
        """Returns list of book tags."""

        raise NotImplementedError

    def parse_title(self, root_tag, book_tag, url):
        """Returns string containing book title."""

        raise NotImplementedError

    def parse_pubdate(self, root_tag, book_tag, url):
        """Returns datetime object with publication date."""

        raise NotImplementedError

    def parse_translators(self, root_tag, book_tag, url):
        """Returns list with translators."""

        raise NotImplementedError

    def parse_original_title(self, root_tag, book_tag, url):
        """Returns original title of the book."""

        raise NotImplementedError

    def parse_categories(self, root_tag, book_tag, url):
        """Returns book's categories."""

        raise NotImplementedError

    def parse_genres(self, root_tag, book_tag, url):
        """Returns book's genres."""

        raise NotImplementedError

    def parse_comments(self, root_tag, book_tag, url):
        """Returns book's comments."""

        raise NotImplementedError
