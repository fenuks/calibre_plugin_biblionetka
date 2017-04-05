from calibre.utils.config import JSONConfig

IDENTIFIER = 'biblionetka'
BOOK_PAGE_URL_SCHEME = 'http://www.biblionetka.pl/book.aspx?id={}'


def get_prefs():
    return JSONConfig('plugins/{}'.format(IDENTIFIER))
