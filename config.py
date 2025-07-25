# config.py
# Bu dosya, uygulama genelinde kullanılan sabitleri ve yapılandırma ayarlarını içerir.

# API ve Dosya Yolları
API_BASE_URL = "https://www.speedrun.com/api/v1"
SETTINGS_FILE = 'Settings.json'
LANGUAGES_FILE = 'Languages.json'
THEME_FILE = 'Theme.json'
TRACKED_RUNS_FILE = 'Tracked Runs.json'
LOG_FILE = 'Speedrun Pulse.log'

# API İstek Ayarları
MAX_CONCURRENT_WORKERS = 100  # Aynı anda çalışacak maksimum worker sayısı
REQUEST_TIMEOUT = 10          # Saniye cinsinden istek zaman aşımı
RETRY_MAX_ATTEMPTS = 3        # Başarısız istekler için maksimum yeniden deneme sayısı
RETRY_INITIAL_DELAY = 1       # Saniye cinsinden ilk yeniden deneme gecikmesi
