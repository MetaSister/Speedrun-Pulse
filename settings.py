# settings.py
# Bu dosya, uygulama ayarlarını yönetmek için kullanılır (Settings.json).

import json
from config import SETTINGS_FILE
# DEĞİŞİKLİK: İçe aktarma 'utils.py' yerine 'file_handler.py'den yapılıyor.
from file_handler import load_json_file

class SettingsManager:
    """
    Uygulama ayarlarını yükler ve kaydeder.
    """
    def __init__(self, filename=SETTINGS_FILE):
        self.filename = filename
        self.settings = self.load_settings()

    def load_settings(self):
        """
        Ayarları dosyadan yükler. Varsayılan değerler tanımlıdır.
        """
        default_settings = {'language': 'en', 'sort_order': 'added_date_desc'}
        loaded_settings = load_json_file(self.filename, default_settings)
        # Yüklenen ayarları varsayılanlarla birleştirerek eksik anahtarları telafi et
        return {**default_settings, **loaded_settings}

    def save_settings(self, language, sort_order):
        """
        Mevcut ayarları dosyaya kaydeder.
        """
        self.settings['language'] = language
        self.settings['sort_order'] = sort_order
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception:
            # Kaydetme hatası durumunda sessizce geç
            pass
