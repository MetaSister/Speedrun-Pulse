# utils.py
# Bu dosya, uygulama genelinde kullanılan genel amaçlı yardımcı fonksiyonları içerir.

import json
import os
import math
from localization import _ # Paylaşılan çevirmen örneğini içe aktar

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
            # Dosya okuma veya parse etme hatası durumunda varsayılanı döndür
            pass
    return default_data

def format_time(total_seconds):
    """
    Saniye cinsinden verilen süreyi okunabilir bir formata (örn: 1h 02m 34s 567ms) dönüştürür.
    """
    if total_seconds is None or not math.isfinite(total_seconds):
        return _.get_string('not_available_abbr')
    if total_seconds < 0.001: return "0s"

    s = int(total_seconds)
    ms = int(round((total_seconds - s) * 1000))
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    
    parts = []
    if h > 0: parts.append(f"{h}h")
    if h > 0 or m > 0: parts.append(f"{m:02d}m" if h > 0 else f"{m}m")
    parts.append(f"{s:02d}s" if (h > 0 or m > 0) else f"{s}s")
    if ms > 0: parts.append(f"{ms:03d}ms")
    
    return " ".join(parts) if parts else "0s"

def format_time_delta(total_seconds):
    """
    Süre farkını okunabilir bir formatta (örn: (-1m 30s)) döndürür.
    """
    if total_seconds is None or total_seconds <= 0 or not math.isfinite(total_seconds):
        return ""
    return f"(-{format_time(total_seconds)})"
