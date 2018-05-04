# custom options
IDENTIFIER = "biblionetka"
BOOK_PAGE_URL_SCHEME = "http://www.biblionetka.pl/book.aspx?id={}"

# plugin options
name = "biblioNETka.pl"
description = "Pobiera metadane z serwisu {}".format(name)
version = (1, 0, 5)
author = "fenuks"

# source plugin options
capabilities = frozenset(["identify", "cover"])
touched_fields = frozenset([
    "title",
    "authors",
    "pubdate",
    "comments",
    "languages",
    "rating",
    "tags",
    "series",
    "identifier:{}".format(IDENTIFIER),
])

setting_defaults = {
    # general settings, required, values modification is allowed, but deletion *will* break things
    "max_results": 2,
    "authors_search": True,
    "only_first_author": False,
    "covers": True,
    "max_covers": 5,
    "threads": True,
    "max_threads": 3,
    "thread_delay": 0.1,
    # metadata settings, optional, delete/comment out to disable
    "title": True,
    "authors": True,
    "pubdate": True,
    # 'publisher': True,
    # 'isbn': True,
    "comments": True,
    "languages": True,
    "rating": True,
    "tags": True,
    "identifier": True,
    "series": True,
    # custom metadata settings, optional, delete/comment out to disable
    "translators": True,
    "original_title": True,
    "categories": True,
    "genres": True,
}
