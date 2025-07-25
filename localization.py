# localization.py
# Bu dosya, uygulamanın çoklu dil desteğini yönetir.

from config import LANGUAGES_FILE
# DEĞİŞİKLİK: İçe aktarma 'utils.py' yerine 'file_handler.py'den yapılıyor.
from file_handler import load_json_file

LANGUAGES = load_json_file(LANGUAGES_FILE)

class Translator:
    """
    Uygulama metinlerini farklı dillere çevirmek için kullanılır.
    """
    def __init__(self, initial_lang="en"):
        self._current_lang = initial_lang
        self.strings = {}
        self.set_language(initial_lang)

    def set_language(self, lang_code):
        """
        Uygulamanın dilini değiştirir.
        """
        if lang_code in LANGUAGES:
            self._current_lang = lang_code
            self.strings = LANGUAGES[lang_code]
        else:
            # Dil bulunamazsa İngilizce'ye geri dön
            self._current_lang = "en"
            self.strings = LANGUAGES.get("en", {})

    def current_language(self):
        """
        Mevcut ayarlanmış dil kodunu döndürür.
        """
        return self._current_lang

    def get_string(self, key, default_text="", **kwargs):
        """
        Verilen anahtara karşılık gelen çeviriyi alır.
        Metin içinde {placeholder} gibi formatlamaları destekler.
        """
        s = self.strings.get(key, default_text if default_text else key)
        try:
            return s.format(**kwargs) if kwargs else s
        except (KeyError, IndexError):
            return s
        except Exception:
            return s

# Uygulama genelinde kullanılacak tek bir çevirmen örneği
_ = Translator()
