import sys
import time
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from main_window import SpeedrunPulseApp
from config import LANGUAGES_FILE, THEME_FILE, LOG_FILE
# DEĞİŞİKLİK: İçe aktarma 'utils.py' yerine 'file_handler.py'den yapılıyor.
from file_handler import load_json_file

def main():
    """
    Uygulamanın ana giriş noktası.
    QApplication'ı başlatır, ana pencereyi oluşturur ve olay döngüsünü çalıştırır.
    """
    app = QApplication.instance() or QApplication(sys.argv)

    # Gerekli JSON dosyalarının varlığını kontrol et
    languages = load_json_file(LANGUAGES_FILE)
    theme = load_json_file(THEME_FILE)

    if not (languages and theme):
        QMessageBox.critical(
            None,
            "Initialization Error",
            f"Critical Error: '{LANGUAGES_FILE}' or '{THEME_FILE}' not found or invalid."
        )
        sys.exit(1)

    # Ana uygulama penceresini başlat ve göster
    try:
        window = SpeedrunPulseApp()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        # Beklenmedik hataları log dosyasına yaz
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"--- CRITICAL STARTUP ERROR: {time.ctime()} ---\n")
            f.write(traceback.format_exc())
            f.write("\n")
        QMessageBox.critical(
            None,
            "Critical Startup Error",
            f"A critical error occurred. Please check '{LOG_FILE}' for details.\n\nError: {e}"
        )
        sys.exit(1)

if __name__ == '__main__':
    main()
