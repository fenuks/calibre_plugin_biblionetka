from calibre.utils.config import JSONConfig

from .plugin_meta import IDENTIFIER, setting_defaults


def get_prefs():
    prefs = JSONConfig('plugins/{}'.format(IDENTIFIER))
    prefs.defaults = setting_defaults
    return prefs
