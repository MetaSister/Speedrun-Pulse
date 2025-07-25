# file_handler.py
# Bu dosya, döngüsel içe aktarma hatalarını önlemek için
# temel dosya okuma işlemlerini içerir.

import json
import os

def load_json_file(filename, default_data=None):
    """
    Bir JSON dosyasını güvenli bir şekilde yükler.
    Dosya yoksa veya bozuksa, belirtilen varsayılan veriyi döndürür.
    """
    if default_data is None:
        default_data = {}
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return default_data
