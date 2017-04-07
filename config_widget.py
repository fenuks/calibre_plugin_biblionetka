#!/usr/bin/env python2
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__ = 'GPL v3'
__copyright__ = '2014, fenuks'
__docformat__ = 'restructuredtext en'

from PyQt5.Qt import Qt, QWidget, QFormLayout, QVBoxLayout, QHBoxLayout, QGroupBox, \
    QLabel, QLineEdit, QIntValidator, QDoubleValidator, QCheckBox

from .utils import get_prefs
# from prefs_mock import get_prefs

prefs = get_prefs()


class ConfigWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.main_layout = QVBoxLayout()
        self.l = QFormLayout()
        self.l2 = QHBoxLayout()
        self.l3 = QHBoxLayout()

        self.group_box = QGroupBox('Ustawienia ogólne')
        self.group_box2 = QGroupBox('Pobieraj metadane')
        self.group_box3 = QGroupBox('Pobieraj dodatkowe metadane i dołącz je do komentarza')

        # general settings
        self.max_results_label = QLabel('Maksymalna liczba wyników')
        self.max_results_label.setToolTip('Maksymalna liczba pobieranych metadanych. Dla książek o nieunikalnych tytułach \
pierwszy wynik może być niepoprawny')
        self.max_results = QLineEdit(self)
        self.max_results.setValidator(QIntValidator())
        self.max_results.setText(str(prefs['max_results']))
        self.max_results_label.setBuddy(self.max_results)
        self.l.addRow(self.max_results_label, self.max_results)

        self.authors_search_label = QLabel('Używaj autorów do wyszukiwań')
        self.authors_search_label.setToolTip('Wyszukuj uwzględniając autorów. Może poprawić trafność wyników, ale błędni autorzy spowodują brak wyników')
        self.authors_search = QCheckBox()
        self.authors_search.setChecked(prefs['authors_search'])
        self.authors_search_label.setBuddy(self.authors_search)
        self.l.addRow(self.authors_search_label, self.authors_search)

        self.only_first_author_label = QLabel('Używaj tylko pierwszego autora do wyszukiwania')
        self.only_first_author_label.setToolTip('Używaj tylko pierwszego autora do wyszukiwań, obowiązuje tylko gdy wyszukiwanie z autorami jest aktywowane')
        self.only_first_author = QCheckBox()
        self.only_first_author.setChecked(prefs['only_first_author'])
        self.only_first_author_label.setBuddy(self.only_first_author)
        self.l.addRow(self.only_first_author_label, self.only_first_author)

        self.covers_label = QLabel('Pobieraj okładki')
        self.covers = QCheckBox()
        self.covers.setChecked(prefs['covers'])
        self.covers_label.setBuddy(self.covers)
        self.l.addRow(self.covers_label, self.covers)

        self.max_covers_label = QLabel('Maksymalna liczba okładek')
        self.max_covers_label.setToolTip('Maksymalna liczba pobieranych okładek')
        self.max_covers = QLineEdit(self)
        self.max_covers.setValidator(QIntValidator())
        self.max_covers.setText(str(prefs['max_covers']))
        self.max_covers_label.setBuddy(self.max_covers)
        self.l.addRow(self.max_covers_label, self.max_covers)

        self.threads_label = QLabel('Wielowątkowe przetwarzanie')
        self.threads_label.setToolTip('Przyśpiesza pracę używając wielu wątków')
        self.threads = QCheckBox()
        self.threads.setChecked(prefs['threads'])
        self.threads_label.setBuddy(self.threads)
        self.l.addRow(self.threads_label, self.threads)

        self.max_threads_label = QLabel('Maksymalna liczba wątków')
        self.max_threads = QLineEdit(self)
        self.max_threads.setValidator(QIntValidator())
        self.max_threads.setText(str(prefs['max_threads']))
        self.max_threads_label.setBuddy(self.max_threads)
        self.l.addRow(self.max_threads_label, self.max_threads)

        self.thread_delay_label = QLabel('Opóźnienie wątku')
        self.thread_delay_label.setToolTip('Czas oczekiwania na uruchomienie kolejnego wątku')
        self.thread_delay = QLineEdit(self)
        self.thread_delay.setValidator(QDoubleValidator())
        self.thread_delay.setText(str(prefs['thread_delay']))
        self.thread_delay_label.setBuddy(self.thread_delay)
        self.l.addRow(self.thread_delay_label, self.thread_delay)

        # metadata settings
        if 'title' in prefs.defaults:
            self.title = QCheckBox('Tytuł')
            self.title.setChecked(prefs['title'])
            self.l2.addWidget(self.title)

        if 'authors' in prefs.defaults:
            self.authors = QCheckBox('Autorzy')
            self.authors.setChecked(prefs['authors'])
            self.l2.addWidget(self.authors)

        if 'pubdate' in prefs.defaults:
            self.pubdate = QCheckBox('Data wydania')
            self.pubdate.setChecked(prefs['pubdate'])
            self.l2.addWidget(self.pubdate)

        if 'publisher' in prefs.defaults:
            self.publisher = QCheckBox('Wydawca')
            self.publisher.setChecked(prefs['publisher'])
            self.l2.addWidget(self.publisher)
        
        if 'isbn' in prefs.defaults:
            self.isbn = QCheckBox('ISBN')
            self.isbn.setChecked(prefs['isbn'])
            self.l2.addWidget(self.isbn)

        if 'comments' in prefs.defaults:
            self.comments = QCheckBox('Opis')
            self.comments.setChecked(prefs['comments'])
            self.l2.addWidget(self.comments)

        if 'languages' in prefs.defaults:
            self.languages = QCheckBox('Języki')
            self.languages.setChecked(prefs['languages'])
            self.l2.addWidget(self.languages)

        if 'rating' in prefs.defaults:
            self.rating = QCheckBox('Ocena')
            self.rating.setChecked(prefs['rating'])
            self.l2.addWidget(self.rating)

        if 'tags' in prefs.defaults:
            self.tags = QCheckBox('Etykiety (tagi)')
            self.tags.setChecked(prefs['tags'])
            self.l2.addWidget(self.tags)

        if 'series' in prefs.defaults:
            self.series = QCheckBox('Cykle')
            self.series.setChecked(prefs['series'])
            self.l2.addWidget(self.series)

        if 'identifier' in prefs.defaults:
            self.identifier = QCheckBox('Identyfikator')
            self.identifier.setChecked(prefs['identifier'])
            self.l2.addWidget(self.identifier)

        # custom metadata
        if 'translators' in prefs.defaults:
            self.translators = QCheckBox('Tłumaczenie')
            self.translators.setChecked(prefs['translators'])
            self.l3.addWidget(self.translators)

        if 'original_title' in prefs.defaults:
            self.original_title = QCheckBox('Tytuł oryginału')
            self.original_title.setChecked(prefs['original_title'])
            self.l3.addWidget(self.original_title)

        if 'categories' in prefs.defaults:
            self.categories = QCheckBox('Kategorie')
            self.categories.setChecked(prefs['categories'])
            self.l3.addWidget(self.categories)

        if 'genres' in prefs.defaults:
            self.genres = QCheckBox('Gatunki')
            self.genres.setChecked(prefs['genres'])
            self.l3.addWidget(self.genres)

        self.group_box.setLayout(self.l)
        self.group_box2.setLayout(self.l2)
        self.group_box3.setLayout(self.l3)
        self.main_layout.addWidget(self.group_box)
        self.main_layout.addWidget(self.group_box2)
        self.main_layout.addWidget(self.group_box3)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.main_layout)

    def save_settings(self):
        prefs['max_results'] = int(self.max_results.text())
        prefs['authors_search'] = self.authors_search.isChecked()
        prefs['only_first_author'] = self.only_first_author.isChecked()
        prefs['covers'] = self.covers.isChecked()
        prefs['max_covers'] = int(self.max_covers.text())
        prefs['threads'] = self.threads.isChecked()
        prefs['max_threads'] = int(self.max_threads.text())
        prefs['thread_delay'] = float(self.thread_delay.text().replace(',', '.'))

        # metadata settings
        if 'title' in prefs.defaults:
            prefs['title'] = self.title.isChecked()
        if 'authors' in prefs.defaults:
            prefs['authors'] = self.authors.isChecked()
        if 'pubdate' in prefs.defaults:
            prefs['pubdate'] = self.pubdate.isChecked()
        if 'publisher' in prefs.defaults:
            prefs['publisher'] = self.publisher.isChecked()
        if 'isbn' in prefs.defaults:
            prefs['isbn'] = self.isbn.isChecked()
        if 'comments' in prefs.defaults:
            prefs['comments'] = self.comments.isChecked()
        if 'languages' in prefs.defaults:
            prefs['languages'] = self.languages.isChecked()
        if 'rating' in prefs.defaults:
            prefs['rating'] = self.rating.isChecked()
        if 'tags' in prefs.defaults:
            prefs['tags'] = self.tags.isChecked()
        if 'series' in prefs.defaults:
            prefs['series'] = self.series.isChecked()
        if 'identifier' in prefs.defaults:
            prefs['identifier'] = self.identifier.isChecked()

        # custom metadata settings
        if 'translators' in prefs.defaults:
            prefs['translators'] = self.translators.isChecked()
        if 'original_title' in prefs.defaults:
            prefs['original_title'] = self.original_title.isChecked()
        if 'categories' in prefs.defaults:
            prefs['categories'] = self.categories.isChecked()
        if 'genres' in prefs.defaults:
            prefs['genres'] = self.genres.isChecked()

        return prefs


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = ConfigWidget()
    w.show()
    sys.exit(app.exec_())
