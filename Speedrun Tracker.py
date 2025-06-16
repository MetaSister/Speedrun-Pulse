import sys
import requests
import json
import os
import webbrowser
import logging
import time

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QHBoxLayout, QSizePolicy, QComboBox,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QScrollArea,
    QFrame, QSpacerItem, QAction
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QPoint
from PyQt5.QtGui import QFont, QColor, QPalette, QCursor

# --- Logging Setup ---
# Loglama seviyesini ERROR olarak ayarlayarak hata ayıklama çıktılarını azaltın ve performansı artırın.
# Bu sadece hata ve kritik sorunları günlüğe kaydedecektir.
logging.basicConfig(filename='Speedrun Tracker.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Localization Data ---
# İngilizce ve Türkçe için tüm çevrilebilir dizeleri depolamak için sözlük.
LANGUAGES = {
    "en": {
        "app_title": "Speedrun Record Tracker",
        "search_placeholder": "Search Game",
        "search_button": "Search",
        "searching_button": "Searching...", # New translation
        "game_list_label": "Game List",
        "no_game_found": "No matching games found.",
        "invalid_game_selection": "Invalid game selection. Please try again.",
        "missing_game_id_name": "Selected game ID or name is missing.",
        "loading_game_details": "Loading '{game_name}' details...",
        "game_details_loaded": "'{game_name}' details loaded.",
        "loading_game_details_failed": "Failed to load game details.",
        "il_list_label": "IL (Individual Level) List",
        "full_game_option": "Full Game (Select if no specific level)",
        "loading_full_game_categories": "Loading full game categories...", # New translation
        "no_individual_level_found": "No individual level found for this game.",
        "level_categories_loading": "Loading categories for '{level_name}' level...",
        "categories_loaded": "Categories loaded.",
        "category_list_label": "Category List",
        "separator_per_level_categories": "--- Per-Level Categories ---",
        "separator_per_game_categories": "--- Per-Game Categories ---",
        "no_suitable_category": "No suitable category found.",
        "no_suitable_category_for_level": "No suitable category found for '{level_name}' level.",
        "no_suitable_category_for_game": "No suitable category found for '{game_name}'.",
        "variables_list_label": "Variable List (at least one must be selected)",
        "invalid_category_selection": "Invalid variable selection. Please try again.",
        "loading_variables": "Loading variables for '{category_name}' category...",
        "no_variables_found": "No variables found or required for this category.",
        "variable_auto_selected": "'{variable_name}' variable automatically selected (single valid option).",
        "select_variable_header": "--- Select {variable_name} ---",
        "invalid_variable_selection": "Invalid variable selection. Please try again.",
        "add_run_button": "Track Run",
        "track_category_missing": "You must select a category to track.",
        "run_already_tracked": "'{display_category_name}' is already being tracked.",
        "game_not_selected": "Game not selected.",
        "record_tracking": "Tracking record for '{display_category_name}'...",
        "record_tracked_success": "Record for '{display_category_name}' successfully tracked.",
        "no_world_record_found": "No world record found for '{display_category_name}'. Please try a different category/variable combination.",
        "add_record_general_error": "A general error occurred while adding record: {error}",
        "game_removed_during_api": "Game '{game_id}' was removed or not found while awaiting API response. Operation aborted.",
        "old_record_time_missing": "Old record time is None. Skipping new record check.",
        "new_record_time_missing": "New record time is None. Skipping.",
        "tracked_run_data_missing": "Tracked run data not found: game {game_id}, level {level_id}, category {category_key}, type {run_type}. Data not updated.",
        "new_wr_detected": "New World Record detected for {run_identifier}.",
        "api_error_search_context": "during game search:", # New translation
        "api_error_record_check_context": "during record check:", # New translation
        "api_error_category_level_context": "while loading category/level info:", # New translation
        "api_error_general_prefix": "API Error", # New translation
        "api_error_general": "API Error: {error_message}", # General error message for fallback
        "loading_runs": "Loading runs...",
        "no_runs_found": "No runs found for this category.",
        "all_runs_dialog_title": "{run_title} - All Runs",
        "all_runners_dialog_title": "{run_title} - Other Runners",
        "no_runner_info_found": "No runner information found for this run.",
        "open_profile_tooltip": "Open {runner_name} profile",
        "last_record_dialog_title": "Recently Broken Records",
        "no_new_wr_found": "No new world records broken yet, or application restarted.",
        "options_menu_view_splits": "View Segment Details",
        "options_menu_open_run_page": "Open Run Page",
        "options_menu_open_other_runs": "View Other Runs in Same Category",
        "options_menu_mark_as_read": "Mark as Read",
        "options_menu_open_player_profile": "Open {player_name} Profile",
        "options_menu_remove_run": "Untrack Run",
        "options_menu_remove_game": "Remove Game and All Runs",
        "untrack_run_success": "Run untracked.",
        "untrack_run_failed": "Failed to untrack run (not found).",
        "invalid_tracked_type": "Invalid tracked type or level info.",
        "game_removed_success": "Game and all tracked runs successfully removed.",
        "game_not_found_untrack": "Game ID {game_id} was already not found in tracked items.",
        "checking_for_new_records": "Checking for new records...",
        "no_records_to_track": "No records to track.",
        "status_message_save_error": "An error occurred while saving record data.",
        "web_link_open_failed": "Failed to open web link.",
        "web_link_not_available": "No valid web link found for this {item_type}.",
        "splits_no_data": "No segment data found for this run.",
        "invalid_time": "Invalid Time",
        "close_button": "Close",
        "rank_column": "Rank",
        "runners_column": "Runners",
        "time_column": "Time",
        "date_column": "Date",
        "more_runners_button": "{count} more",
        "speedrun_link_tooltip": "Open run on Speedrun.com",
        "speedrun_profile_link_not_available": "Speedrun.com link not available",
        "all_marked_as_read": "All marked as read.",
        "run_marked_as_read": "Run marked as read.",
        "run_already_marked_read": "This run was already marked as read.",
        "run_mark_read_failed": "Failed to mark run as read (run data not found).",
        "error_fetching_runner_info": "Error loading runner information.",
        "error_loading_splits": "Error loading segment details.",
        "level_select_hint": "Select a level to view its categories, or 'Full Game' for game categories.",
        "category_select_hint": "Select a category to view its variables (if any).",
        "variable_select_hint": "Select variable options (if any).",
        "add_run_hint_incomplete": "Please select all required options (game, category, variables) to track a run.",
        "add_run_hint_already_tracked": "This run is already being tracked.",
        "add_run_hint_ready": "All selections made. Ready to track!",
        "sort_by_label": "Sort By:",
        "sort_added_date_desc": "Added Date (Newest First)",
        "sort_game_name_asc": "Game Name (A-Z)",
        "missing_variable_selection": "You need to select variables for this category. Please select the relevant options from the list above: ({missing_vars}).",
        "error_adding_record_general": "A general error occurred while adding record: {e}",
        "game_info_not_retrieved": "Error: Game information could not be retrieved.",
        "unknown_player": "Unknown",
        "unknown_player_id_missing": "Unknown (ID missing)",
        "unknown_category": "Unknown Category",
        "unknown_game": "Unknown Game",
        "unknown_level": "Unknown Level",
        "miscellaneous_category": " (Misc)",
        "critical_startup_error": "A critical error occurred during application startup. Check 'Speedrun Tracker.log' for more details.",
        "open_speedrun_com_page": "Open Speedrun.com Page",
        "current_selection_status": "Current Selection:",
        "current_game": "Game: {game_name}",
        "current_level": "Level: {level_name}",
        "current_category": "Category: {category_name}",
        "current_variables": "Variables: {variables}",
        "none_selected": "None selected",
        "warning_skipping_variable_data": "Warning: Skipping faulty variable data for '{var_id}': {val_data}. Expected dictionary with 'value_id'.",
        "refresh_button": "Refresh", # New translation
        "clear_new_wr_button": "Mark All New WR's Read", # New translation
        "segment_name_column": "Segment Name", # New translation
        "segment_name_default": "Segment {row}", # New translation
        "not_available_abbr": "N/A", # New translation
        "game_label": "Game: {game_name}", # New translation
        "category_label": "Category: {category_name}", # New translation
        "new_time_label": "New Time: {formatted_new_time}", # New translation
        "runners_label": "Runners: {new_player_name}", # New translation
        "runners_label_prefix": "Runners", # New translation
        "options": "Options", # New translation
        "options_button_tooltip": "Options", # New translation
        "error_populating_table_row": "Error populating table row {row}.", # New translation
        "error_loading_runs": "Error loading runs: {error_message}", # New translation
        "new_wr_label": "New WR!",# New translation
        "date_label": "Date", # New translation
        "menu_options": "Options", # New: Menu title for language/sort
        "menu_language": "Language", # New: Language menu item
        "menu_sort_order": "Sort Order", # New: Sort Order menu item
    },
    "tr": {
        "app_title": "Speedrun Rekor İzleyicisi",
        "search_placeholder": "Oyun Ara",
        "search_button": "Ara",
        "searching_button": "Aranıyor...", # New translation
        "game_list_label": "Oyun Listesi",
        "no_game_found": "Eşleşen oyun bulunamadı.",
        "invalid_game_selection": "Geçersiz oyun seçimi. Lütfen tekrar deneyin.",
        "missing_game_id_name": "Seçilen oyun kimliği veya adı eksik.",
        "loading_game_details": "'{game_name}' detayları yükleniyor...",
        "game_details_loaded": "'{game_name}' detayları yüklendi.",
        "loading_game_details_failed": "Oyun detayları yüklenemedi.",
        "il_list_label": "IL (Bireysel Seviye) Listesi",
        "full_game_option": "Tam Oyun (Belirli bir seviye yoksa seçin)",
        "loading_full_game_categories": "Tam oyun kategorileri yükleniyor...", # New translation
        "no_individual_level_found": "Bu oyun için bireysel seviye bulunamadı.",
        "level_categories_loading": "'{level_name}' seviyesi için kategoriler yükleniyor...",
        "categories_loaded": "Kategoriler yüklendi.",
        "category_list_label": "Kategori Listesi",
        "separator_per_level_categories": "--- Seviye Başına Kategoriler ---",
        "separator_per_game_categories": "--- Oyun Başına Kategoriler ---",
        "no_suitable_category": "Uygun kategori bulunamadı.",
        "no_suitable_category_for_level": "'{level_name}' seviyesi için uygun kategori bulunamadı.",
        "no_suitable_category_for_game": "'{game_name}' için uygun kategori bulunamadı.",
        "variables_list_label": "Değişken Listesi (en az biri seçilmeli)",
        "invalid_category_selection": "Geçersiz değişken seçimi. Lütfen tekrar deneyin.",
        "loading_variables": "'{category_name}' kategorisi için değişkenler yükleniyor...",
        "no_variables_found": "Bu kategori için değişken bulunamadı veya gerekli değil.",
        "variable_auto_selected": "'{variable_name}' değişkeni otomatik olarak seçildi (tek geçerli seçenek).",
        "select_variable_header": "--- {variable_name} Seçin ---",
        "invalid_variable_selection": "Geçersiz değişken seçimi. Lütfen tekrar deneyin.",
        "add_run_button": "Koşuyu Takip Et",
        "track_category_missing": "Takip etmek için bir kategori seçmelisiniz.",
        "run_already_tracked": "'{display_category_name}' zaten takip ediliyor.",
        "game_not_selected": "Oyun seçilmedi.",
        "record_tracking": "'{display_category_name}' için rekor takip ediliyor...",
        "record_tracked_success": "'{display_category_name}' için rekor başarıyla takip edildi.",
        "no_world_record_found": "'{display_category_name}' için dünya rekoru bulunamadı. Lütfen farklı bir kategori/değişken kombinasyonu deneyin.",
        "add_record_general_error": "Kayıt eklenirken genel bir hata oluştu: {error}",
        "game_removed_during_api": "API yanıtı beklenirken oyun {game_id} kaldırıldı veya bulunamadı. İşlem iptal edildi.",
        "old_record_time_missing": "Eski kayıt süresi Yok. Yeni kayıt kontrolü atlanıyor.",
        "new_record_time_missing": "Yeni kayıt süresi Yok. Atlanıyor.",
        "tracked_run_data_missing": "Takip edilen koşu verileri bulunamadı: oyun {game_id}, seviye {level_id}, kategori {category_key}, tür {run_type}. Veriler güncellenmedi.",
        "new_wr_detected": "Yeni Dünya Rekoru algılandı: {run_identifier}",
        "api_error_search_context": "oyun araması sırasında:", # New translation
        "api_error_record_check_context": "kayıt kontrolü sırasında:", # New translation
        "api_error_category_level_context": "kategori/seviye bilgisi yüklenirken:", # New translation
        "api_error_general_prefix": "API Hatası", # New translation
        "api_error_general": "API Hatası: {error_message}", # General error message for fallback
        "loading_runs": "Koşular yükleniyor...",
        "no_runs_found": "Bu kategori için koşu bulunamadı.",
        "all_runs_dialog_title": "{run_title} - Tüm Koşular",
        "all_runners_dialog_title": "{run_title} - Diğer Koşucular",
        "no_runner_info_found": "Bu koşu için koşucu bilgisi bulunamadı.",
        "open_profile_tooltip": "{runner_name} profilini aç",
        "last_record_dialog_title": "Son Kırılan Rekorlar",
        "no_new_wr_found": "Henüz yeni dünya rekoru kırılmadı veya uygulama yeniden başlatıldı.",
        "options_menu_view_splits": "Segment Detaylarını Görüntüle",
        "options_menu_open_run_page": "Koşu Sayfasını Aç",
        "options_menu_open_other_runs": "Aynı Kategorideki Diğer Koşuları Görüntüle",
        "options_menu_mark_as_read": "Okundu Olarak İşaretle",
        "options_menu_open_player_profile": "{player_name} Profilini Aç",
        "options_menu_remove_run": "Koşuyu Takibi Bırak",
        "options_menu_remove_game": "Oyunu ve Tüm Koşuları Kaldır",
        "untrack_run_success": "Koşu takibi bırakıldı.",
        "untrack_run_failed": "Koşu takibi bırakılamadı (bulunamadı).",
        "invalid_tracked_type": "Geçersiz takip edilen tür veya seviye bilgisi.",
        "game_removed_success": "Oyun ve takip edilen tüm koşuları başarıyla kaldırıldı.",
        "game_not_found_untrack": "Oyun kimliği {game_id} zaten takip edilen öğelerde bulunamadı.",
        "checking_for_new_records": "Yeni kayıtlar kontrol ediliyor...",
        "no_records_to_track": "Takip edilecek kayıt yok.",
        "status_message_save_error": "Kayıt verileri kaydedilirken bir hata oluştu.",
        "web_link_open_failed": "Web bağlantısı açılamadı.",
        "web_link_not_available": "Bu {item_type} için geçerli web bağlantısı bulunamadı.",
        "splits_no_data": "Bu koşu için segment verisi bulunamadı.",
        "invalid_time": "Geçersiz Süre",
        "close_button": "Kapat",
        "rank_column": "Sıra",
        "runners_column": "Koşucular",
        "time_column": "Süre",
        "date_column": "Tarih",
        "more_runners_button": "{count} daha",
        "speedrun_link_tooltip": "Koşuyu Speedrun.com'da aç",
        "speedrun_profile_link_not_available": "Speedrun.com bağlantısı mevcut değil",
        "all_marked_as_read": "Tümü okundu olarak işaretlendi.",
        "run_marked_as_read": "Koşu okundu olarak işaretlendi.",
        "run_already_marked_read": "Bu koşu zaten okundu olarak işaretlenmişti.",
        "run_mark_read_failed": "Koşu okundu olarak işaretlenemedi (koşu verileri bulunamadı).",
        "error_fetching_runner_info": "Koşucu bilgisi yüklenirken hata oluştu.",
        "error_loading_splits": "Segment detayları yüklenirken hata oluştu.",
        "level_select_hint": "Kategorilerini görüntülemek için bir seviye seçin veya oyun kategorileri için 'Tam Oyun'u seçin.",
        "category_select_hint": "Değişkenlerini (varsa) görüntülemek için bir kategori seçin.",
        "variable_select_hint": "Değişken seçeneklerini (varsa) seçin.",
        "add_run_hint_incomplete": "Bir koşuyu takip etmek için lütfen gerekli tüm seçenekleri (oyun, kategori, değişkenler) seçin.",
        "add_run_hint_already_tracked": "Bu koşu zaten takip ediliyor.",
        "add_run_hint_ready": "Tüm seçimler yapıldı. Takip etmeye hazır!",
        "sort_by_label": "Sırala:",
        "sort_added_date_desc": "Ekleme Tarihi (En Yeni Önce)",
        "sort_game_name_asc": "Oyun Adı (A-Z)",
        "missing_variable_selection": "Bu kategori için değişken seçmeniz gerekiyor. Lütfen yukarıdaki listeden ilgili seçenekleri seçin: ({missing_vars}).",
        "error_adding_record_general": "Kayıt eklenirken genel bir hata oluştu: {e}",
        "game_info_not_retrieved": "Hata: Oyun bilgisi alınamadı.",
        "unknown_player": "Bilinmiyor",
        "unknown_player_id_missing": "Bilinmiyor (Kimlik eksik)",
        "unknown_category": "Bilinmeyen Kategori",
        "unknown_game": "Bilinmeyen Oyun",
        "unknown_level": "Bilinmeyen Seviye",
        "miscellaneous_category": " (Çeşitli)",
        "critical_startup_error": "Uygulama başlatılırken kritik bir hata oluştu. Daha fazla detay için 'Speedrun Tracker.log' dosyasını kontrol edin.",
        "open_speedrun_com_page": "Speedrun.com Sayfasını Aç",
        "current_selection_status": "Mevcut Seçim:",
        "current_game": "Oyun: {game_name}",
        "current_level": "Seviye: {level_name}",
        "current_category": "Kategori: {category_name}",
        "current_variables": "Değişkenler: {variables}",
        "none_selected": "Hiçbiri seçili değil",
        "warning_skipping_variable_data": "Uyarı: '{var_id}' için hatalı değişken verileri atlanıyor: {val_data}. 'value_id' ile sözlük bekleniyor.",
        "refresh_button": "Yenile", # New translation
        "clear_new_wr_button": "Tüm WR'ları Okundu Olarak İşaretle", # New translation
        "segment_name_column": "Segment Adı", # New translation
        "segment_name_default": "Segment {row}", # New translation
        "not_available_abbr": "Yok", # New translation
        "game_label": "Oyun: {game_name}", # New translation
        "category_label": "Kategori: {category_name}", # New translation
        "new_time_label": "Yeni Süre: {formatted_new_time}", # New translation
        "runners_label": "Koşucular: {new_player_name}", # New translation
        "runners_label_prefix": "Koşucular", # New translation
        "options": "Seçenekler", # New translation
        "options_button_tooltip": "Seçenekler", # New translation
        "error_populating_table_row": "Tablo satırı {row} doldurulurken hata oluştu.",# New translation
        "error_loading_runs": "Koşular yüklenirken hata oluştu: {error_message}",# New translation
        "new_wr_label": "Yeni WR!" ,
        "date_label": "Tarih" ,
        "menu_options": "Seçenekler", # New: Menu title for language/sort
        "menu_language": "Dil", # New: Language menu item
        "menu_sort_order": "Sıralama", # New: Sort Order menu item
    }
}

class Translator:
    """Yönetim Dili seçimi ve dizeleri tercüme."""
    def __init__(self, initial_lang="en"):
        self._current_lang = initial_lang
        self.set_language(initial_lang)

    def set_language(self, lang_code):
        if lang_code in LANGUAGES:
            self._current_lang = lang_code
            self.strings = LANGUAGES[lang_code]
        else:
            logger.warning(f"'{lang_code}' dili bulunamadı. Varsayılan olarak 'en' kullanılıyor.")
            self._current_lang = "en"
            self.strings = LANGUAGES["en"]

    def current_language(self):
        """Geçerli etkin dil kodunu döndürür."""
        return self._current_lang

    def get_string(self, key, **kwargs):
        """İsteğe bağlı biçimlendirme ile anahtara göre çevrilmiş bir dizeyi alır.
           Kilit eksik kwargs'leri sorunsuz bir şekilde ele alır."""
        s = self.strings.get(key, key) # Temel dizeyi veya anahtarın kendisini yedek olarak al
        try:
            return s.format(**kwargs)
        except KeyError as e:
            # Hatayı kaydet ve orijinal dizeyi döndür (biçimlendirilmemiş veya kısmen biçimlendirilmiş)
            logger.warning(f"'{key}' dizesi {kwargs} ile biçimlendirilirken KeyError oluştu: {e}. Biçimlendirilmemiş dize döndürülüyor.")
            return s
        except Exception as e:
            # Diğer beklenmeyen biçimlendirme hatalarını yakala
            logger.error(f"'{key}' dizesi {kwargs} ile biçimlendirilirken beklenmeyen bir hata oluştu: {e}. Biçimlendirilmemiş dize döndürülüyor.", exc_info=True)
            return s

# Çevirmeni genel olarak başlat
_ = Translator("en") # Varsayılan olarak başlangıçta İngilizce olarak ayarla

# --- Settings Manager ---
class SettingsManager:
    """
    Uygulama ayarlarının bir JSON dosyasına yüklenmesini ve kaydedilmesini yönetir.
    """
    def __init__(self, filename='Settings.json'):
        self.filename = filename
        # Ayarları başlatılırken hemen yükle
        self.settings = self.load_settings()

    def load_settings(self):
        """
        Ayarları JSON dosyasından yükler. Dosya yoksa veya bozuksa,
        varsayılan ayarları döndürür.
        """
        default_settings = {
            'language': 'en',
            'sort_order': 'added_date_desc'
        }
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # Tüm anahtarların mevcut olduğundan emin olmak için varsayılanlarla birleştir,
                    # yüklenen ayarları varsayılanlara göre önceliklendir.
                    return {**default_settings, **settings}
            except json.JSONDecodeError as e:
                logger.error(f"{self.filename} dosyasından ayarlar yüklenirken JSONDecodeError oluştu: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"{self.filename} dosyasından ayarlar yüklenirken beklenmeyen bir hata oluştu: {e}", exc_info=True)
        return default_settings

    def save_settings(self, language, sort_order):
        """
        Geçerli dili ve sıralama düzenini ayarlar dosyasına kaydeder.

        Argümanlar:
            language (str): Geçerli dil kodu (örn. 'en', 'tr').
            sort_order (str): Geçerli sıralama düzeni dizesi.
        """
        self.settings['language'] = language
        self.settings['sort_order'] = sort_order
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ayarlar {self.filename} dosyasına kaydedilirken hata oluştu: {e}", exc_info=True)
            # Gerçek bir uygulamada, burada kullanıcıya bir mesaj göstermek isteyebilirsiniz.


# --- API Worker Thread ---
# Bu sınıf, UI'nin donmasını önlemek için API isteklerini ayrı bir iş parçacığında yönetir.
class ApiWorker(QThread):
    finished = pyqtSignal(object, str)  # Başarılı API yanıtında yayınlanan sinyal, şimdi request_id içerir
    error = pyqtSignal(str)        # API isteği hatasında yayınlanan sinyal
    worker_completed = pyqtSignal() # İşçi başarıyla veya başarısız bir şekilde tamamlandığında yayınlanan sinyal

    def __init__(self, url, method='GET', data=None, max_retries=3, initial_retry_delay=1, request_id=None):
        """
        ApiWorker sınıfının başlatıcısı.

        Argümanlar:
            url (str): API isteğinin yapılacağı URL.
            method (str): HTTP yöntemi (örn. 'GET', 'POST'). Varsayılan olarak 'GET'.
            data (dict, isteğe bağlı): İstekle birlikte gönderilecek JSON verisi. Varsayılan olarak None.
            max_retries (int): Zaman aşımı/hata durumunda isteği yeniden deneme sayısı.
            initial_retry_delay (int): İlk yeniden denemeden önceki başlangıç gecikmesi (saniye cinsinden).
            request_id (str, isteğe bağlı): Bu istek için benzersiz bir kimlik, eski yanıtları tanımlamak için kullanılır.
        """
        super().__init__()
        self.url = url
        self.method = method
        self.data = data
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.request_timeout = 30 # API istekleri için zaman aşımı 30 saniyeye çıkarıldı
        self.request_id = request_id # request_id'yi sakla

    def run(self):
        """
        İş parçacığı yürütme yöntemi. API isteğini yapar ve sonucu bir sinyal olarak yayar.
        Ağ ile ilgili hatalar için yeniden deneme mekanizması içerir.
        """
        retries_attempted = 0
        try:
            while retries_attempted <= self.max_retries:
                try:
                    # Belirtilen zaman aşımı ile HTTP isteğini yürüt
                    response = requests.request(self.method, self.url, json=self.data, timeout=self.request_timeout)
                    response.raise_for_status() # Kötü yanıtlar için HTTPError yükselt (4xx veya 5xx)
                    self.finished.emit(response.json(), self.request_id) # Başarılı JSON yanıtını ve request_id'yi yay
                    return # Çalışma yönteminden başarıyla çık
                except requests.exceptions.Timeout:
                    error_msg = f"API isteği zaman aşımına uğradı: {self.url}"
                    logger.error(error_msg, exc_info=True) # Zaman aşımı hatalarını kaydet
                    if retries_attempted < self.max_retries:
                        retry_wait_time = self.initial_retry_delay * (2 ** retries_attempted) # Üstel geri çekilme
                        logger.info(f"{retries_attempted + 1}/{self.max_retries} yeniden deneme {retry_wait_time} saniye içinde: {self.url}")
                        time.sleep(retry_wait_time)
                        retries_attempted += 1
                    else:
                        self.error.emit(error_msg) # Tüm yeniden denemeler bittiğinde hatayı yay
                        return # Hata yaydıktan sonra çık
                except requests.exceptions.HTTPError as e: # HTTP hatalarını özel olarak yakala
                    if e.response.status_code == 420: # 420 Too Many Requests hatası için özel işlem
                        error_msg = f"API isteği hatası (Çok Fazla İstek): {e}\nURL: {self.url}"
                        logger.warning(error_msg, exc_info=True)
                        if retries_attempted < self.max_retries:
                            # 420 hatası için daha uzun bir bekleme süresi, örneğin 60 saniye
                            retry_wait_time = 60 * (2 ** retries_attempted) 
                            logger.info(f"420 hatası için yeniden deneme {retries_attempted + 1}/{self.max_retries}: {retry_wait_time} saniye içinde: {self.url}")
                            time.sleep(retry_wait_time)
                            retries_attempted += 1
                        else:
                            self.error.emit(error_msg)
                            return
                    else: # Diğer HTTP hataları
                        error_msg = f"API isteği hatası: {e}\nURL: {self.url}"
                        logger.error(error_msg, exc_info=True) # İstek hatalarını kaydet
                        self.error.emit(error_msg)
                        return
                except requests.exceptions.RequestException as e:
                    error_msg = f"API isteği hatası: {e}\nURL: {self.url}"
                    logger.error(error_msg, exc_info=True) # İstek hatalarını kaydet
                    self.error.emit(error_msg)
                    return # Hata yaydıktan sonra çık
                except json.JSONDecodeError:
                    error_msg = f"API yanıtı ayrıştırılamadı (geçersiz JSON): {self.url}"
                    logger.error(error_msg, exc_info=True) # JSON ayrıştırma hatalarını kaydet
                    self.error.emit(error_msg)
                    return # Hata yaydıktan sonra çık
        except Exception as e:
            # Oluşabilecek diğer beklenmeyen hataları yakala
            error_msg = f"Beklenmeyen bir hata oluştu: {e}"
            logger.error(error_msg, exc_info=True) # Diğer tüm beklenmeyen hataları kaydet
            self.error.emit(error_msg)
        finally:
            # Bu blok her zaman yürütülecek, tamamlandı sinyalinin her zaman yayılmasını sağlayacak.
            self.worker_completed.emit()

# --- Helper Function for Dialog Styling ---
# QDialog örneklerine tutarlı, malzeme benzeri bir stil uygular.
def apply_material_style_to_dialog(dialog_instance):
    """
    Verilen QDialog örneğine tutarlı bir malzeme tasarım stili uygular.

    Argümanlar:
        dialog_instance (QDialog): Stil uygulanacak iletişim kutusu.
    """
    dialog_instance.setStyleSheet("""
    QDialog {
        background-color: #000000; /* Siyah */
        color: #FFFFFF; /* Beyaz */
    }

    QLabel {
        font-size: 16px;
        color: #FFFFFF;
    }

    QTableWidget {
        background-color: #000000; /* Tablo arka planını siyaha ayarla */
        alternate-background-color: #000000; /* Alternatif satır rengini de siyaha ayarla */
        color: #FFFFFF; /* Tablo genel metin rengi */
        border: 2px solid #FFFFFF;
        gridline-color: #FFFFFF;
    }

    QTableWidget::item {
        color: #FFFFFF; /* Tüm öğe metni beyaz */
        background-color: #000000; /* Tüm öğe arka planı siyah */
        font-size: 12px; /* Tablo öğeleri için yeni sabit yazı tipi boyutu */
        padding: 5px; /* Hücrelere biraz boşluk ekle */
    }

    QTableWidget::item:selected {
        background-color: #000000; /* Seçili öğe arka planını da siyaha ayarla (seçimi gizler) */
        color: #FFFFFF; /* Seçili öğe metni için beyaz */
    }
    /* QTableWidget QHeaderView::section stili buradan kaldırıldı, AllRunsDialog'da doğrudan ele alındı. */

    QPushButton {
        background-color: transparent;
        color: #FFFFFF;
        border: 2px solid #FFFFFF;
        font-size: 15px;
    }

    QPushButton:hover {
        background-color: rgba(255, 255, 255, 0.1);
    }

    QPushButton:pressed {
        background-color: rgba(255, 255, 255, 0.2);
    }

    QScrollBar:vertical {
        background: #000000;
        width: 8px;
    }

    QScrollBar::handle:vertical {
        background: #FFFFFF;
        min-height: 20px;
    }

    /* AllRunsDialog'da kullanılan tablo hücre düğmeleri için stil */
    QPushButton#RunnerLinkButtonInTable, QPushButton#TimeLinkButtonInTable, QPushButton#MoreRunnersButtonInTable {
        background-color: transparent;
        border: none;
        padding: 0;
        margin: 0;
        font-weight: normal;
        text-align: center; /* Metni ortala */
        color: #FFFFFF;
        font-size: 12px; /* Tablo hücre düğmeleri için yeni sabit yazı tipi boyutu */
    }
    QPushButton#RunnerLinkButtonInTable:hover, QPushButton#TimeLinkButtonInTable:hover, QPushButton#MoreRunnersButtonInTable:hover {
        color: #DDDDDD;
    }
    QPushButton#RunnerLinkButtonInTable:pressed, QPushButton#TimeLinkButtonInTable:pressed, QPushButton#MoreRunnersButtonInTable:pressed {
        color: #BBBBBB;
    }
    """)

# --- Splits Details Window ---
# Hız koşusu segmentleri (bölmeleri) hakkında ayrıntılı bilgi gösteren iletişim kutusu.
class SplitsDialog(QDialog):
    """
    Speedrun Segmentleri (bölmeleri) hakkında ayrıntılı bilgi gösteren bir iletişim penceresi.
    """
    def __init__(self, splits_data, run_title="Segment Details", parent=None):
        """
        SplitsDialog sınıfının başlatıcısı.

        Argümanlar:
            splits_data (list): Görüntülenecek bölme verilerini içeren bir liste.
            run_title (str): İletişim kutusu için başlık.
            parent (QWidget, isteğe bağlı): İletişim kutusunun ebeveyni. Varsayılan olarak None.
        """
        super().__init__(parent)
        self.setWindowTitle(run_title)
        self.setGeometry(300, 300, 500, 600)
        # Pencere bayraklarından bağlam yardım düğmesini kaldır
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title_label = QLabel(_.get_string('options_menu_view_splits'))
        title_label.setFont(QFont("Roboto", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        if not splits_data:
            info_label = QLabel(_.get_string('splits_no_data'))
            info_label.setFont(QFont("Roboto", 10))
            info_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(info_label)
        else:
            self.table_widget = QTableWidget()
            self.table_widget.setRowCount(len(splits_data)) # Satır sayısını ayarla
            self.table_widget.setColumnCount(2)
            self.table_widget.setHorizontalHeaderLabels([_.get_string('segment_name_column'), _.get_string('time_column')])

            # Sütunları mevcut alanı dolduracak şekilde uzat
            self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
            self.table_widget.verticalHeader().setVisible(False) # Dikey başlığı gizle
            self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers) # Tabloyu salt okunur yap
            self.table_widget.setFont(QFont("Roboto", 10))

            for row, split in enumerate(splits_data):
                segment_name = split.get('name', _.get_string('segment_name_default').format(row=row + 1))
                # Gerçek zamanı milisaniye cinsinden al, önce 'split' sonra 'realtime_duration_ms' dene
                realtime_ms = split.get('split', {}).get('realtime') or split.get('realtime_duration_ms')

                formatted_time = _.get_string('not_available_abbr')
                if realtime_ms is not None:
                    try:
                        total_seconds = float(realtime_ms) / 1000.0
                        hours = int(total_seconds // 3600)
                        minutes = int((total_seconds % 3600) // 60)
                        seconds = int((total_seconds % 60))
                        milliseconds = int((total_seconds * 1000) % 1000)

                        # Saate, dakikaya, saniyeye, milisaniyeye göre zamanı biçimlendir
                        if hours > 0:
                            formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
                        else:
                            formatted_time = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
                    except ValueError:
                         formatted_time = _.get_string('invalid_time')

                self.table_widget.setItem(row, 0, QTableWidgetItem(segment_name))
                time_item = QTableWidgetItem(formatted_time)
                time_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter) # Zamanı sağa hizala
                self.table_widget.setItem(row, 1, time_item)

            layout.addWidget(self.table_widget)

        close_button = QPushButton(_.get_string('close_button')) # Kapat düğmesi
        close_button.setFont(QFont("Roboto", 10, QFont.Bold))
        close_button.setFixedSize(100, 35)
        close_button.clicked.connect(self.close) # İletişim kutusunu kapatmak için bağla
        layout.addWidget(close_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)
        apply_material_style_to_dialog(self) # Tutarlı stili uygula

# --- All Runners Details Window ---
# Belirli bir hız koşusu için tüm koşucuları görüntülemek için iletişim kutusu.
class AllRunnersDialog(QDialog):
    """
    Belirli bir speedrun için tüm koşucuları görüntülemek için bir iletişim penceresi.
    """
    def __init__(self, run_title, all_runners, all_weblinks, parent=None):
        """
        AllRunnersDialog sınıfının başlatıcısı.

        Argümanlar:
            run_title (str): Koşunun başlığı.
            all_runners (list): Tüm koşucu adlarını içeren bir liste.
            all_weblinks (list): Tüm koşucu web bağlantılarını içeren bir liste.
            parent (QWidget, isteğe bağlı): İletişim kutusunun ebeveyni. Varsayılan olarak None.
        """
        super().__init__(parent)
        self.setWindowTitle(_.get_string('all_runners_dialog_title').format(run_title=run_title))
        # İletişim kutusunu ana pencereye göre konumlandır
        self.setGeometry(parent.x() + parent.width() // 2 - 200, parent.y() + parent.height() // 2 - 250, 400, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        if not all_runners:
            info_label = QLabel(_.get_string('no_runner_info_found'))
            info_label.setFont(QFont("Roboto", 10))
            info_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(info_label)
        else:
            runners_scroll_area = QScrollArea() # Koşucu listesi için kaydırma alanı
            runners_scroll_area.setWidgetResizable(True)
            runners_content_widget = QWidget()
            runners_content_layout = QVBoxLayout(runners_content_widget)
            runners_content_layout.setContentsMargins(0, 0, 0, 0)
            runners_content_layout.setSpacing(5)

            for i, runner_name in enumerate(all_runners):
                runner_weblink = all_weblinks[i] if i < len(all_weblinks) else None

                if runner_weblink:
                    runner_button = QPushButton(runner_name)
                    runner_button.setObjectName("RunnerLinkButtonDialog") # Stil için nesne adı
                    runner_button.setToolTip(_.get_string('open_profile_tooltip').format(runner_name=runner_name))
                    runner_button.setCursor(Qt.PointingHandCursor) # Üzerine gelindiğinde el imleci
                    runner_button.clicked.connect(lambda _, link=runner_weblink: webbrowser.open(link))
                    runner_button.setFont(QFont("Roboto", 11))
                    runner_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                    runner_button.setFixedHeight(30)
                    runners_content_layout.addWidget(runner_button)
                else:
                    runner_label = QLabel(runner_name)
                    runner_label.setStyleSheet(f"color: #FFFFFF;")
                    runner_label.setFont(QFont("Roboto", 11)) # Tutarlılık için yazı tipini açıkça ayarla
                    runners_content_layout.addWidget(runner_label)

            runners_content_layout.addStretch(1) # İçeriği üste it
            runners_scroll_area.setWidget(runners_content_widget)
            layout.addWidget(runners_scroll_area)

        close_button = QPushButton(_.get_string('close_button'))
        close_button.setFont(QFont("Roboto", 10, QFont.Bold))
        close_button.setFixedSize(100, 35)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)
        apply_material_style_to_dialog(self)

# --- Last Broken Records Details Window ---
# Son kırılan dünya rekorlarını görüntülemek için iletişim kutusu.
class LastRecordDialog(QDialog):
    """
    Son kırılan dünya rekorlarını görüntülemek için bir iletişim penceresi.
    """
    def __init__(self, broken_records_list, parent=None):
        """
        LastRecordDialog sınıfının başlatıcısı.

        Argümanlar:
            broken_records_list (list): Kırılan rekorların bir listesi.
            parent (QWidget, isteğe bağlı): İletişim kutusunun ebeveyni. Varsayılan olarak None.
        """
        super().__init__(parent)
        self.setWindowTitle(_.get_string('last_record_dialog_title'))
        # İletişim kutusunu ana pencereye göre konumlandırın ve genişliğini artırın
        self.setGeometry(parent.x() + parent.width() // 2 - 350, parent.y() + parent.height() // 2 - 250, 700, 500) # Genişlik 600'den 700'e çıkarıldı
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        if broken_records_list:
            scroll_area = QScrollArea() # Kayıt listesi için kaydırma alanı
            scroll_area.setWidgetResizable(True)
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(15)

            for record_info in broken_records_list:
                record_entry_widget = QWidget()
                record_entry_layout = QVBoxLayout(record_entry_widget)
                record_entry_layout.setContentsMargins(10, 10, 10, 10) # Her kayıt girişi için iç kenar boşlukları
                record_entry_layout.setSpacing(5)
                # Kayıt girişleri için özel stil uygula - sadece tek bir dış çerçeve
                record_entry_widget.setStyleSheet("""
                    QWidget {
                        background-color: #000000; /* Siyah arka plan */
                        border: 2px solid #FFFFFF; /* Beyaz kenarlık */
                    }
                    QLabel {
                        font-size: 13px;
                        color: #FFFFFF; /* Beyaz metin */
                        margin-bottom: 0px; /* Metin kenarlıkla hizalanmalı */
                        font-weight: normal;
                        border: none; /* ÖNEMLİ: Bu, etiketin iç kenarlığını kaldırır */
                    }
                    QLabel.record_detail_label {
                        font-size: 13px;
                        color: #FFFFFF; /* Beyaz metin */
                        margin-bottom: 0px; /* Metin kenarlıkla hizalanmalı */
                        border: none; /* ÖNEMLİ: Bu, etiketin iç kenarlığını kaldırır */
                    }
                    QPushButton#RecordLinkButton {
                        background-color: transparent;
                        border: 2px solid #FFFFFF; /* Beyaz kenarlık */
                        color: #FFFFFF; /* Beyaz metin */
                        padding: 5px 10px; /* Kenarlıktan boşluk ekle */
                        margin: 0;
                        font-size: 13px;
                        font-weight: bold;
                        text-align: center; /* Düğme metnini ortala */
                    }
                    QPushButton#RecordLinkButton:hover {
                        background-color: rgba(255, 255, 255, 0.1); /* Üzerine gelindiğinde hafif şeffaf beyaz */
                    }
                    QPushButton#RecordLinkButton:pressed {
                        background-color: rgba(255, 255, 255, 0.2); /* Basıldığında daha koyu şeffaf beyaz */
                    }
                """)

                weblink = record_info.get('weblink')
                if weblink and weblink != '#':
                    link_button = QPushButton(_.get_string('options_menu_open_run_page'))
                    link_button.setObjectName("RecordLinkButton")
                    link_button.setCursor(Qt.PointingHandCursor)
                    # Boyut politikasını Minimum ve hizalamayı ortaya ayarla
                    link_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
                    link_button.clicked.connect(lambda _, url=weblink: webbrowser.open(url))
                    record_entry_layout.addWidget(link_button, alignment=Qt.AlignCenter)

                # Oyun adını göster
                game_name_label = QLabel(_.get_string('game_label').format(game_name=record_info['game_name'].strip("'")))
                game_name_label.setFont(QFont("Roboto", 13, QFont.Bold))
                game_name_label.setStyleSheet("color: #FFFFFF;") # Beyaz metin
                record_entry_layout.addWidget(game_name_label)

                # Kategori adını ve seviyesini (varsa) göster
                category_name_text = record_info['category_display_name'].strip("'")
                if record_info['level_name']:
                    category_name_text = f"{record_info['level_name'].strip("'")}: {category_name_text}"
                category_label = QLabel(_.get_string('category_label').format(category_name=category_name_text))
                category_label.setFont(QFont("Roboto", 13, QFont.Bold))
                category_label.setStyleSheet("color: #FFFFFF;") # Beyaz metin
                record_entry_layout.addWidget(category_label)

                new_time_label = QLabel(_.get_string('new_time_label').format(formatted_new_time=record_info['formatted_new_time']))
                new_time_label.setObjectName("record_detail_label")
                record_entry_layout.addWidget(new_time_label)

                # Düzeltilen satır: new_player_name şimdi doğrudan adları içerir
                players_label = QLabel(_.get_string('runners_label').format(new_player_name=record_info['new_player_name']))
                players_label.setObjectName("record_detail_label")
                record_entry_layout.addWidget(players_label)

                # Burada sadece date_completed'ı _create_broken_record_info'dan olduğu gibi kullanıyoruz, yeniden biçimlendirmiyoruz
                date_label = QLabel(f"{_.get_string('date_label')}: {record_info['new_run_date'].strip('()')}")
                date_label.setObjectName("DateLabel")
                record_entry_layout.addWidget(date_label)

                content_layout.addWidget(record_entry_widget)

            content_layout.addStretch(1) # İçeriği üste it
            scroll_area.setWidget(content_widget)
            layout.addWidget(scroll_area)

        else:
            info_label = QLabel(_.get_string('no_new_wr_found'))
            info_label.setFont(QFont("Roboto", 10))
            info_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(info_label)

        close_button = QPushButton(_.get_string('close_button'))
        close_button.setFont(QFont("Roboto", 10, QFont.Bold))
        close_button.setFixedSize(100, 35)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)
        apply_material_style_to_dialog(self)

# --- All Runs Details Window ---
class AllRunsDialog(QDialog):
    """
    Belirli bir oyun/kategori/seviye kombinasyonu için tüm koşuları görüntüler.
    """
    def __init__(self, game_id, category_id, level_id, selected_variable_values, run_title, parent=None):
        super().__init__(parent)
        self.game_id = game_id
        self.category_id = category_id
        self.level_id = level_id
        self.selected_variable_values = selected_variable_values
        self.setWindowTitle(_.get_string('all_runs_dialog_title').format(run_title=run_title))
        self.setGeometry(parent.x() + parent.width() // 2 - 400, parent.y() + parent.height() // 2 - 350, 800, 700)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.parent_app = parent # Ana uygulama referansını sakla (show_all_runners_dialog erişimi için)

        self.runs_data = []
        self.api_worker = None

        self.init_ui()
        apply_material_style_to_dialog(self)
        self.fetch_all_runs()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.status_label = QLabel(_.get_string('loading_runs'))
        self.status_label.setFont(QFont("Roboto", 11))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels([_.get_string('rank_column'), _.get_string('runners_column'), _.get_string('time_column'), _.get_string('date_column')])
        
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers)

        # Satır seçimini devre dışı bırak ve odaklanmayı engelle.
        # Bu, tıklandığında satırın grileşmesine neden olabilir.
        self.table_widget.setSelectionMode(QTableWidget.NoSelection)
        self.table_widget.setFocusPolicy(Qt.NoFocus)

        # Başlık bölümü stilini doğrudan ayarla
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #000000; /* Siyah arka plan */
                color: #FFFFFF; /* Beyaz metin */
                font-weight: bold;
                font-size: 12px; /* Başlık yazı tipini 12 piksel olarak ayarla */
                padding: 5px; /* Başlık hücreleri için daha az dolgu */
                text-align: center; /* Metni ortala */
                border: 2px solid #FFFFFF; /* Tüm kenarlıkları beyaza ayarla */
                border-top: none; /* Üst kenarlığı kaldır */
                border-left: none; /* Sol kenarlığı kaldır */
            }
            QHeaderView::section:last-child {
                border-right: 2px solid #FFFFFF; /* Son sütun için sağ kenarlığı koru */
            }
        """)

        layout.addWidget(self.table_widget)

        close_button = QPushButton(_.get_string('close_button'))
        close_button.setFont(QFont("Roboto", 10, QFont.Bold))
        close_button.setFixedSize(100, 35)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def fetch_all_runs(self):
        variables_str = ""
        if self.selected_variable_values:
            for var_id in sorted(self.selected_variable_values.keys()):
                val_data = self.selected_variable_values[var_id]
                # val_data'nın bir sözlük olup olmadığını ve 'value_id' içerip içermediğini kontrol et
                if isinstance(val_data, dict) and 'value_id' in val_data:
                    variables_str += f"&var-{var_id}={val_data['value_id']}"
                else:
                    # Veri biçimi beklenmedikse uyarıyı kaydet
                    logger.warning(_.get_string('warning_skipping_variable_data').format(var_id=var_id, val_data=val_data))
                    # Bu sık sık olursa kullanıcıya durum etiketi aracılığıyla bilgi verebilirsiniz
                    # self.status_label.setText(f"Uyarı: '{var_id}' için bazı değişken verileri işlenemedi.")


        if not self.level_id: # Tam Oyun kategorisi
            url = f"https://www.speedrun.com/api/v1/leaderboards/{self.game_id}/category/{self.category_id}?top=100&embed=players{variables_str}"
        else: # Bireysel Seviye kategorisi
            url = f"https://www.speedrun.com/api/v1/leaderboards/{self.game_id}/level/{self.level_id}/{self.category_id}?top=100&embed=players{variables_str}"

        self.status_label.setText(_.get_string('loading_runs'))
        self.api_worker = ApiWorker(url)
        self.api_worker.finished.connect(self.handle_all_runs_result)
        self.api_worker.error.connect(self.handle_api_error)
        self.api_worker.start()

    def handle_all_runs_result(self, data, request_id):
        self.status_label.setText("") # Durum mesajını temizle

        leaderboard_data = data.get('data')
        if not leaderboard_data or not leaderboard_data.get('runs'):
            self.status_label.setText(_.get_string('no_runs_found'))
            return

        self.runs_data = []
        runs = leaderboard_data.get('runs', [])
        
        # Sağlam bir şekilde player_id_map oluştur
        players_data_embed = leaderboard_data.get('players', {}).get('data', [])
        player_id_map = {}
        if isinstance(players_data_embed, list):
            for p_data in players_data_embed:
                if isinstance(p_data, dict) and p_data.get('id'):
                    player_id_map[p_data['id']] = p_data

        for i, entry in enumerate(runs):
            run_obj = entry.get('run')
            if not run_obj:
                continue

            rank = i + 1
            time_seconds = run_obj.get('times', {}).get('primary_t')
            formatted_time = SpeedrunTrackerApp.format_time(time_seconds) # Statik metodu kullan
            weblink = run_obj.get('weblink')
            date_completed = run_obj.get('date', _.get_string('not_available_abbr'))

            # Her koşu için oyuncu bilgilerini çıkar
            player_names = []
            player_weblinks = []
            if isinstance(run_obj.get('players'), list):
                for run_player_id_obj in run_obj.get('players', []):
                    if isinstance(run_player_id_obj, dict):
                        if run_player_id_obj.get('rel') == 'user':
                            player_id_to_find = run_player_id_obj.get('id')
                            if player_id_to_find and player_id_to_find in player_id_map:
                                p_data = player_id_map[player_id_to_find]
                                player_names.append(p_data.get('names',{}).get('international', p_data.get('name', _.get_string('unknown_player'))))
                                player_weblinks.append(p_data.get('weblink'))
                            else:
                                player_names.append(_.get_string('unknown_player_id_missing'))
                                player_weblinks.append(None) # ID eksikse, web bağlantısı da eksiktir
                        elif run_player_id_obj.get('rel') == 'guest':
                            player_names.append(run_player_id_obj.get('name', _.get_string('unknown_player')))
                            player_weblinks.append(None) # Misafirlerin web bağlantısı yoktur

            self.runs_data.append({
                'rank': rank,
                'players': player_names, # Adlar listesi olarak sakla
                'player_weblinks': player_weblinks, # Web bağlantıları listesi olarak sakla
                'time_formatted': formatted_time, # Çakışmayı önlemek için yeniden adlandırıldı
                'time_seconds': time_seconds, # Potansiyel gelecek kullanım için ham saniyeleri sakla
                'date': date_completed,
                'weblink': weblink # Koşunun kendi web bağlantısı
            })

        self.display_runs_in_table()

    def display_runs_in_table(self):
        self.table_widget.setRowCount(len(self.runs_data))
        for row, run in enumerate(self.runs_data):
            try:
                # Sıra sütunu
                rank_item = QTableWidgetItem(f"#{run['rank']}")
                rank_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                rank_item.setFont(QFont("Roboto", 10)) # Yazı tipini açıkça ayarla
                self.table_widget.setItem(row, 0, rank_item)

                # Koşucular sütunu
                players_widget = QWidget()
                players_layout = QHBoxLayout(players_widget)
                players_layout.setContentsMargins(0, 0, 0, 0)
                players_layout.setSpacing(0)

                if run['players']: # Herhangi bir oyuncu olup olmadığını kontrol et
                    runner_name_to_display = run['players'][0]
                    runner_weblink_to_display = run['player_weblinks'][0]

                    if runner_weblink_to_display:
                        player_button = QPushButton(runner_name_to_display, players_widget) # Açıkça ebeveyn
                        player_button.setObjectName("RunnerLinkButtonInTable")
                        player_button.setCursor(Qt.PointingHandCursor)
                        player_button.clicked.connect(lambda _, link=runner_weblink_to_display: webbrowser.open(link))
                        player_button.setFont(QFont("Roboto", 12)) # Yazı tipini açıkça ayarla
                        player_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
                        players_layout.addWidget(player_button, alignment=Qt.AlignVCenter)
                    else:
                        player_label = QLabel(runner_name_to_display, players_widget) # Açıkça ebeveyn
                        player_label.setFont(QFont("Roboto", 12)) # Yazı tipini açıkça ayarla
                        player_label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
                        players_layout.addWidget(player_label, alignment=Qt.AlignVCenter)

                # Kalan koşucular için "X more" düğmesi (varsa)
                remaining_runners = len(run['players']) - 1
                if remaining_runners > 0:
                    dot_label = QLabel(" • ") # Nokta ayırıcı eklendi
                    dot_label.setObjectName("dot_separator_table") # Stil için benzersiz nesne adı (gerekirse)
                    dot_label.setFont(QFont("Roboto", 12)) # Nokta için yazı tipi
                    # Dikey hizalamayı ayarlamak için küçük bir margin-top uygula
                    dot_label.setStyleSheet("margin-top: 3px;") # Hizalama ayarlandı
                    players_layout.addWidget(dot_label, alignment=Qt.AlignVCenter)

                    more_button = QPushButton(_.get_string('more_runners_button').format(count=remaining_runners), players_widget) # Açıkça ebeveyn
                    more_button.setObjectName("MoreRunnersButtonInTable")
                    more_button.setCursor(Qt.PointingHandCursor)
                    # Ana uygulama örneğinden iletişim kutusunu çağırmak için self.parent_app kullan
                    more_button.clicked.connect(lambda _, r_names=run['players'], r_links=run['player_weblinks']:
                                                self.parent_app.show_all_runners_dialog(self.windowTitle(), r_names, r_links))
                    more_button.setFont(QFont("Roboto", 12)) # Yazı tipini açıkça ayarla
                    players_layout.addWidget(more_button, alignment=Qt.AlignVCenter)
                
                players_layout.addStretch(1)
                self.table_widget.setCellWidget(row, 1, players_widget)

                # Süre sütunu
                time_widget = QWidget()
                time_layout = QHBoxLayout(time_widget)
                time_layout.setContentsMargins(0, 0, 0, 0)
                time_layout.setSpacing(0)

                time_button = QPushButton(run['time_formatted'], time_widget) # Açıkça ebeveyn
                time_button.setObjectName("TimeLinkButtonInTable")
                time_button.setCursor(Qt.PointingHandCursor)
                time_button.setFont(QFont("Roboto", 12)) # Yazı tipini açıkça ayarla
                
                if run['weblink']:
                    time_button.clicked.connect(lambda _, link=run['weblink']: webbrowser.open(link))
                else:
                    time_button.setEnabled(False)
                
                time_layout.addStretch(1)
                time_layout.addWidget(time_button, alignment=Qt.AlignVCenter)
                time_layout.addStretch(1)
                self.table_widget.setCellWidget(row, 2, time_widget)

                # Tarih sütunu
                date_item = QTableWidgetItem(run['date'])
                date_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                date_item.setFont(QFont("Roboto", 10)) # Yazı tipini açıkça ayarla
                self.table_widget.setItem(row, 3, date_item)
            except Exception as e:
                logger.error(f"Tablo satırı {row} doldurulurken hata oluştu: {e}", exc_info=True)
                # Tablo hücresinde bir hata gösterebilir veya satırı atlayabilirsiniz
                self.status_label.setText(_.get_string('error_populating_table_row').format(row=row), is_error=True)


    def handle_api_error(self, error_message):
        self.status_label.setText(_.get_string('error_loading_runs').format(error_message=error_message))
        logger.error(f"AllRunsDialog API hatası: {error_message}")


# --- Main Application Class ---
# Speedrun Tracker uygulamasının ana penceresi.
class SpeedrunTrackerApp(QWidget):
    """
    Speedrun Record Tracker uygulamasının ana penceresi.
    Kullanıcıların hız koşuları için yeni dünya rekorlarını aramasına, takip etmesine ve görüntülemesine olanak tanır.
    """
    MAX_DISPLAY_RUNNERS = 2 # Listede doğrudan gösterilecek koşucu sayısı
    BASE_ITEM_FONT_SIZE = 12 # Liste öğeleri için temel yazı tipi boyutu
    GAME_HEADER_FONT_SIZE = 18 # Oyun başlıkları için yazı tipi boyutu
    OPTIONS_BUTTON_SIZE = 36 # Üç nokta düğmeleri için sabit boyut (genişlik ve yükseklik)
    OPTIONS_BUTTON_FONT_SIZE = 24 # Üç nokta düğmeleri için yazı tipi boyutu
    HAMBURGER_BUTTON_SIZE = 40 # Hamburger menü düğmesi için sabit boyut

    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager() # Ayarlar yöneticisini başlat
        initial_settings = self.settings_manager.load_settings()

        self.translator = Translator(initial_settings.get('language', 'en')) # Başlangıç dilini yükle
        self.tracked_runs = {} # Takip edilen koşuları saklamak için sözlük
        self.save_file = 'Tracked Runs.json' # Takip edilen koşuları kaydetmek/yüklemek için dosya

        # Seçilen veriler ve API verileri için önbellekler
        self.selected_game_data = {'id': None, 'name': None, 'icon_url': None, 'weblink': None}
        self.selected_level_data = {'id': None, 'name': None}
        # 'is_miscellaneous'ı içerecek şekilde güncellenmiş kategori verileri
        self.selected_category_data = {'id': None, 'name': None, 'is_miscellaneous': False} 
        self.selected_variable_values = {} # {değişken_id: {'value_id': ..., 'value_name': ...}}
        self.full_game_data_cache = None # Tam oyun detayları için önbellek
        self.full_level_data_cache = None # Tam seviye detayları için önbellek
        self.available_subcategory_variables = [] # Mevcut değişkenleri saklamak için

        self.active_check_workers = [] # Etkin API işçi iş parçacıklarını takip etmek için liste
        self.pending_refresh_api_calls = 0 # Yenileme sırasında bekleyen API çağrıları için sayıcı
        self.broken_records_history = [] # Kırılan dünya rekorları hakkında bilgi saklamak için liste
        self.has_unseen_new_wrs = False # Görülmemiş yeni dünya rekorları olup olmadığını gösteren bayrak

        # İstek Kimlikleri: Eski API yanıtlarını önlemek için
        self.current_game_search_request_id = None
        self.current_game_details_request_id = None
        self.current_level_categories_request_id = None
        # YENİ: Kategori ve değişken yükleme için istek Kimliği
        self.current_category_variables_request_id = None 

        # Takip edilen koşular için sıralama düzeni
        # 'added_date_desc': en yeniler önce (_added_timestamp'a göre)
        # 'game_name_asc': oyun adı A-Z
        self.current_sort_order = initial_settings.get('sort_order', 'added_date_desc') # Başlangıç sıralama düzenini yükle

        # Debounced oyun araması için zamanlayıcı (otomatik tamamlama)
        self.autocomplete_timer = QTimer(self)
        self.autocomplete_timer.setSingleShot(True)
        self.autocomplete_timer.timeout.connect(self.search_game_debounced)
        self.current_game_search_worker = None # Geçerli oyun arama işçisine referans

        self.init_ui() # Kullanıcı arayüzünü başlat
        self.apply_material_style() # Özel malzeme tasarım stilini uygula

        self.load_tracked_runs() # Daha önce takip edilen koşuları yükle

        # Yeni dünya rekorlarını periyodik olarak kontrol etmek için zamanlayıcı
        self.timer = QTimer(self)
        self.timer.setInterval(300000) # 5 dakika (300 saniye = 300000 milisaniye)
        self.timer.timeout.connect(self.check_for_new_records)
        self.timer.start() # Periyodik kontrol zamanlayıcısını başlat
        self.check_for_new_records() # Başlatmada ilk kontrolü yap

    def init_ui(self):
        """
        Uygulamanın kullanıcı arayüzünü başlatır ve düzenleri ayarlar.
        """
        self.setWindowTitle(self.translator.get_string('app_title'))
        self.setGeometry(150, 150, 1200, 850) # Pencere konumunu ve boyutunu ayarla

        main_layout = QHBoxLayout() # Ana yatay düzen
        main_layout.setContentsMargins(10, 10, 10, 10) # Ana düzen için kenar boşlukları azaltıldı
        main_layout.setSpacing(20)

        left_layout = QVBoxLayout() # Arama ve seçim için sol dikey düzen
        left_layout.setSpacing(12)

        # Sağ taraf düzeni
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0) # Sağ düzen için iç kenar boşlukları yok
        right_layout.setSpacing(12)

        # Arama girişi ve hamburger düğmesi için yatay düzen
        search_and_menu_layout = QHBoxLayout()
        search_and_menu_layout.setContentsMargins(0, 0, 0, 0) # İç kenar boşlukları yok
        search_and_menu_layout.setSpacing(10) # Öğeler arasında boşluk

        # Hamburger menü düğmesi
        self.hamburger_button = QPushButton("≡") # Unicode hamburger simgesi
        self.hamburger_button.setFixedSize(QSize(self.HAMBURGER_BUTTON_SIZE, self.HAMBURGER_BUTTON_SIZE))
        self.hamburger_button.setObjectName("HamburgerButton")
        self.hamburger_button.setToolTip(self.translator.get_string('menu_options'))
        self.hamburger_button.clicked.connect(self.show_options_menu_dialog)
        self.hamburger_button.setFont(QFont("Roboto", 18, QFont.Bold)) # Simge için daha büyük yazı tipi

        self.game_search_input = QLineEdit()
        self.game_search_input.setPlaceholderText(self.translator.get_string('search_placeholder'))
        self.game_search_input.setMinimumHeight(40)
        self.game_search_input.setFont(QFont("Roboto", 11))
        self.game_search_input.textChanged.connect(self.start_autocomplete_timer) # Debounced aramaya bağla

        self.search_button = QPushButton(self.translator.get_string('search_button'))
        self.search_button.setFixedSize(100, 40)
        self.search_button.clicked.connect(self.search_game) # Arama düğmesini bağla
        self.search_button.setFont(QFont("Roboto", 11, QFont.Bold))

        search_and_menu_layout.addWidget(self.game_search_input)
        search_and_menu_layout.addWidget(self.search_button)
        search_and_menu_layout.addWidget(self.hamburger_button) # Hamburger düğmesini buraya ekle

        left_layout.addLayout(search_and_menu_layout) # Yeni düzeni sol düzene ekle

        # Dil ve sıralama seçenekleri artık doğrudan sağ üstte DEĞİL, menünün içinde olacak.
        # Bu yüzden top_right_controls_layout kaldırıldı.
        
        self.game_results_label = QLabel(self.translator.get_string('game_list_label'))
        self.game_results_label.setFont(QFont("Roboto", 11, QFont.Bold))
        self.game_results_list_widget = QListWidget()
        self.game_results_list_widget.setMinimumHeight(120)
        self.game_results_list_widget.itemClicked.connect(self.select_game_from_results) # Oyun seçimini bağla
        self.game_results_list_widget.setFont(QFont("Roboto", 10))
        # Oyun sonuçları listesi için bağlam menüsünü etkinleştir ("Speedrun.com Sayfasını Aç")
        self.game_results_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.game_results_list_widget.customContextMenuRequested.connect(self.show_game_result_context_menu)
        left_layout.addWidget(self.game_results_label)
        left_layout.addWidget(self.game_results_list_widget)

        self.level_label = QLabel(self.translator.get_string('il_list_label'))
        self.level_label.setFont(QFont("Roboto", 11, QFont.Bold))
        self.level_list_widget = QListWidget()
        self.level_list_widget.setMinimumHeight(100)
        self.level_list_widget.itemClicked.connect(self.select_level_from_results) # Seviye seçimini bağla
        self.level_list_widget.setFont(QFont("Roboto", 10))
        self.level_list_widget.setVisible(False) # Varsayılan olarak gizli
        self.level_label.setVisible(False) # Varsayılan olarak gizli
        left_layout.addWidget(self.level_label)
        left_layout.addWidget(self.level_list_widget)

        self.category_label = QLabel(self.translator.get_string('category_list_label'))
        self.category_label.setFont(QFont("Roboto", 11, QFont.Bold))
        self.category_list_widget = QListWidget()
        self.category_list_widget.setMinimumHeight(120)
        self.category_list_widget.itemClicked.connect(self.select_category_to_show_variables) # Kategori seçimini bağla
        self.category_list_widget.setFont(QFont("Roboto", 10))
        left_layout.addWidget(self.category_label)
        left_layout.addWidget(self.category_list_widget)

        self.variables_label = QLabel(self.translator.get_string('variables_list_label'))
        self.variables_label.setFont(QFont("Roboto", 11, QFont.Bold))
        self.variables_list_widget = QListWidget()
        self.variables_list_widget.setMinimumHeight(80)
        self.variables_list_widget.setFont(QFont("Roboto", 10))
        self.variables_list_widget.setVisible(False) # Varsayılan olarak gizli
        self.variables_label.setVisible(False) # Varsayılan olarak gizli
        self.variables_list_widget.itemClicked.connect(self.handle_variable_selection) # Değişken seçimini bağla
        self.variables_list_widget.setSelectionMode(QListWidget.MultiSelection) # Değişkenler için çoklu seçime izin ver

        left_layout.addWidget(self.variables_label)
        left_layout.addWidget(self.variables_list_widget)

        # Seçilen koşuyu Takip Edilen Koşular Listesine eklemek için düğme
        self.add_run_button = QPushButton(self.translator.get_string('add_run_button'))
        self.add_run_button.setFixedSize(200, 40)
        self.add_run_button.setObjectName("AddRunButton") # Stil için nesne adı
        self.add_run_button.setFont(QFont("Roboto", 11, QFont.Bold))
        self.add_run_button.clicked.connect(self.add_to_tracked) # Koşu ekleme eylemini bağla
        self.add_run_button.setEnabled(False) # Varsayılan olarak devre dışı
        left_layout.addWidget(self.add_run_button, alignment=Qt.AlignCenter) # Düğmeyi ortala

        left_layout.addStretch(1) # İçeriği üste it


        self.tracked_list_widget = QListWidget()
        self.tracked_list_widget.setFont(QFont("Roboto", self.BASE_ITEM_FONT_SIZE))

        # Daha akıcı bir deneyim için piksel piksel kaydırmayı etkinleştir
        self.tracked_list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        # Fare tekerleği için daha küçük bir tek adım değeri ayarla (daha akıcı kaydırma için)
        self.tracked_list_widget.verticalScrollBar().setSingleStep(20)

        right_layout.addWidget(self.tracked_list_widget, 1) # Bu genişlemeli


        # Durum mesajı etiketi (yükseklik ve sarma için ayarlanmış) - tracked_list_widget altına taşındı
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Roboto", 10))
        self.status_label.setStyleSheet("color: #4CAF50;") # Varsayılan başarı rengi
        self.status_label.setWordWrap(True) # Kelime sarmayı ETKİNLEŞTİR
        self.status_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding) # Dikey genişlemeye izin ver
        # self.status_label.setFixedHeight(25) # Sabit yükseklik KALDIRILDI
        right_layout.addWidget(self.status_label)


        button_container_layout = QHBoxLayout() # Eylem düğmeleri için düzen
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(10)

        self.show_last_record_button = QPushButton(self.translator.get_string('last_record_dialog_title'))
        self.show_last_record_button.setFixedSize(200, 40)
        self.show_last_record_button.setFont(QFont("Roboto", 11, QFont.Bold))
        self.show_last_record_button.clicked.connect(self.show_last_record_notification)
        self.show_last_record_button.setVisible(self.has_unseen_new_wrs) # Yeni dünya rekorlarına göre görünürlük
        button_container_layout.addWidget(self.show_last_record_button, alignment=Qt.AlignCenter)

        self.refresh_button = QPushButton(self.translator.get_string('refresh_button'))
        self.refresh_button.setFixedSize(120, 40)
        self.refresh_button.setFont(QFont("Roboto", 11, QFont.Bold))
        self.refresh_button.clicked.connect(self.check_for_new_records) # Yenileme eylemini bağla
        button_container_layout.addWidget(self.refresh_button, alignment=Qt.AlignCenter)

        self.clear_new_wr_button = QPushButton(self.translator.get_string('clear_new_wr_button'))
        self.clear_new_wr_button.setFixedSize(250, 40)
        self.clear_new_wr_button.setFont(QFont("Roboto", 11, QFont.Bold))
        self.clear_new_wr_button.clicked.connect(self.mark_all_new_wrs_as_read) # Tümünü okundu olarak işaretle eylemini bağla
        self.clear_new_wr_button.setVisible(self.has_unseen_new_wrs) # Yeni dünya rekorlarına göre görünürlük
        button_container_layout.addWidget(self.clear_new_wr_button, alignment=Qt.AlignCenter)

        right_layout.addLayout(button_container_layout)

        main_layout.addLayout(left_layout, 2)

        # Dikey ayırıcı çizgi
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setObjectName("Separator")
        main_layout.addWidget(separator)

        main_layout.addLayout(right_layout, 5)

        self.setLayout(main_layout)
        self.update_tracked_list_ui()

    def show_options_menu_dialog(self):
        """
        Hamburger menü düğmesine tıklandığında seçenekler menüsünü görüntüler.
        """
        menu = QMenu(self)
        
        # Dil Seçimi Menüsü
        language_menu = menu.addMenu(self.translator.get_string('menu_language'))
        en_action = language_menu.addAction("English")
        tr_action = language_menu.addAction("Türkçe")
        
        en_action.triggered.connect(lambda: self.change_language_from_menu("en"))
        tr_action.triggered.connect(lambda: self.change_language_from_menu("tr"))

        # Mevcut dili vurgula
        if self.translator.current_language() == "en":
            en_action.setChecked(True)
        else:
            tr_action.setChecked(True)
        en_action.setCheckable(True)
        tr_action.setCheckable(True)


        # Sıralama Seçenekleri Menüsü
        sort_menu = menu.addMenu(self.translator.get_string('menu_sort_order'))
        sort_added_date_desc_action = sort_menu.addAction(self.translator.get_string('sort_added_date_desc'))
        sort_game_name_asc_action = sort_menu.addAction(self.translator.get_string('sort_game_name_asc'))

        sort_added_date_desc_action.triggered.connect(lambda: self.change_sort_order_from_menu("added_date_desc"))
        sort_game_name_asc_action.triggered.connect(lambda: self.change_sort_order_from_menu("game_name_asc"))

        # Mevcut sıralama düzenini vurgula
        if self.current_sort_order == "added_date_desc":
            sort_added_date_desc_action.setChecked(True)
        else:
            sort_game_name_asc_action.setChecked(True)
        sort_added_date_desc_action.setCheckable(True)
        sort_game_name_asc_action.setCheckable(True)


        # Hamburger düğmesinin altında menüyü görüntüle
        button_pos = self.hamburger_button.mapToGlobal(self.hamburger_button.rect().bottomLeft())
        menu.exec_(button_pos)

    def change_language_from_menu(self, lang_code):
        """
        Menüden dil seçimini işler.
        """
        if self.translator.current_language() != lang_code:
            self.translator.set_language(lang_code)
            self.settings_manager.save_settings(lang_code, self.current_sort_order)
            self.retranslate_ui()

    def change_sort_order_from_menu(self, sort_order):
        """
        Menüden sıralama düzeni seçimini işler.
        """
        if self.current_sort_order != sort_order:
            self.current_sort_order = sort_order
            self.settings_manager.save_settings(self.translator.current_language(), self.current_sort_order)
            self.update_tracked_list_ui()


    def change_language(self, index):
        """Uygulamanın dilini açılır kutu seçimine göre değiştirir."""
        # Bu fonksiyon artık doğrudan bir QComboBox ile kullanılmıyor, ancak gelecekteki kullanım için korunuyor.
        # Hamburger menüdeki yeni mantığı change_language_from_menu kullanıyor.
        lang_code = self.lang_combo_box.itemData(index)
        self.translator.set_language(lang_code)
        self.settings_manager.save_settings(lang_code, self.current_sort_order) # Yeni dil ayarını kaydet
        self.retranslate_ui() # Tüm UI öğelerini yeniden çevir

    def retranslate_ui(self):
        """Tüm UI metin dizelerini şu anda seçilen dile göre günceller."""
        self.setWindowTitle(self.translator.get_string('app_title'))
        self.game_search_input.setPlaceholderText(self.translator.get_string('search_placeholder'))
        self.search_button.setText(self.translator.get_string('search_button'))
        self.game_results_label.setText(self.translator.get_string('game_list_label'))
        self.level_label.setText(self.translator.get_string('il_list_label'))
        self.category_label.setText(self.translator.get_string('category_list_label'))
        self.variables_label.setText(self.translator.get_string('variables_list_label'))
        self.add_run_button.setText(self.translator.get_string('add_run_button'))
        self.show_last_record_button.setText(self.translator.get_string('last_record_dialog_title'))
        self.refresh_button.setText(self.translator.get_string('refresh_button'))
        self.clear_new_wr_button.setText(self.translator.get_string('clear_new_wr_button'))

        # Sıralama açılır kutu öğelerini güncelle (bu artık doğrudan görünür değil, ancak dahili olarak güncellenebilir)
        # self.sort_combo_box.blockSignals(True) # Güncelleme sırasında sinyali engelle
        # current_data = self.sort_combo_box.currentData()
        # self.sort_combo_box.clear()
        # self.sort_combo_box.addItem(self.translator.get_string('sort_added_date_desc'), "added_date_desc")
        # self.sort_combo_box.addItem(self.translator.get_string('sort_game_name_asc'), "game_name_asc")
        # # Geçerli current_sort_order ile eşleşecek şekilde geçerli dizini ayarla
        # self.sort_combo_box.setCurrentIndex(self.sort_combo_box.findData(self.current_sort_order)) 
        # self.sort_combo_box.blockSignals(False)

        # Oyun sonuçları listesini yeniden doldur (boş değilse)
        temp_game_items_data = []
        for i in range(self.game_results_list_widget.count()):
            item = self.game_results_list_widget.item(i)
            # Yalnızca geçerli bir oyun öğesiyse (yani, "Oyun bulunamadı" mesajı değilse) verileri sakla
            if item and item.data(Qt.UserRole) and isinstance(item.data(Qt.UserRole), dict):
                temp_game_items_data.append(item.data(Qt.UserRole))

        self.game_results_list_widget.clear()
        if temp_game_items_data:
            # Oyunları uluslararası ada göre alfabetik olarak sırala (API'den zaten sıralı, ancak her ihtimale karşı yeniden sırala)
            games = sorted(temp_game_items_data, key=lambda x: x.get('name', '').lower())
            for game_data_from_item in games:
                game_title_display = game_data_from_item.get('name_with_year') # Bu zaten yılı içeriyor
                item = QListWidgetItem(game_title_display)
                item.setData(Qt.UserRole, game_data_from_item)
                self.game_results_list_widget.addItem(item)
        elif self.game_search_input.text().strip(): # Arama girişi boş değilse, "Oyun bulunamadı" gösterilmiş demektir
             self.game_results_list_widget.addItem(self.translator.get_string('no_game_found'))


        # full_game_data_cache'e göre seviye listesini yeniden doldur
        self.level_list_widget.clear()
        if self.full_game_data_cache and self.full_game_data_cache.get('levels', {}).get('data'):
            self.handle_level_result({'data': self.full_game_data_cache.get('levels', {}).get('data', [])}, self.current_game_details_request_id)
        elif self.selected_game_data['id'] and not self.full_game_data_cache: # Bir oyun seçiliyse ancak seviyeler yüklenmediyse veya seviye yoksa
            self.level_list_widget.addItem(self.translator.get_string('no_individual_level_found'))
            self.level_list_widget.setVisible(True)
            self.level_label.setVisible(True)
            self.level_list_widget.setEnabled(False)


        # Geçerli seçime göre kategori listesini yeniden doldur
        self.category_list_widget.clear()
        if self.selected_level_data['id']: # Belirli bir seviye seçiliyse
            if self.full_level_data_cache:
                self.handle_level_category_result({'data': self.full_level_data_cache}, self.current_category_variables_request_id)
            else:
                # Mantık doğru akarsa olmamalı, ancak bir yedek olarak
                self.category_list_widget.addItem(self.translator.get_string('no_suitable_category_for_level').format(level_name=self.selected_level_data['name']))
        elif self.selected_game_data['id']: # Tam oyun seçiliyse (belirli bir seviye yoksa)
            if self.full_game_data_cache:
                self.handle_category_result({'data': self.full_game_data_cache.get('categories', {}).get('data', [])}, self.current_game_details_request_id)
            else:
                 # Olmamalı, ancak bir yedek olarak
                self.category_list_widget.addItem(self.translator.get_string('no_suitable_category_for_game').format(game_name=self.selected_game_data['name']))

        # Değişkenler listesini yeniden doldur
        self.variables_list_widget.clear()
        if self.selected_category_data['id'] and self.available_subcategory_variables:
             # handle_variables_result'ı mevcut available_subcategory_variables ile tekrar çağır
             # handle_variables_result tarafından beklenen veri yapısını yeniden oluştur
             mock_variables_data = {'data': self.available_subcategory_variables}
             self.handle_variables_result(mock_variables_data, self.current_category_variables_request_id)
        elif self.selected_category_data['id'] and not self.available_subcategory_variables:
            self.variables_list_widget.addItem(self.translator.get_string('no_variables_found'))
            self.variables_list_widget.setVisible(True) # Mesajı göstermek için görünür yap
            self.variables_label.setVisible(True)
            self.variables_list_widget.setEnabled(False) # Seçilemez yap

        self.update_tracked_list_ui() # Yeni dille takip edilen koşuları yeniden çiz
        self._update_add_run_button_state() # Durum mesajı dahil düğme durumunu güncelle

        # Yeniden çeviri sonrası doğru metin oluşturmayı sağlamak için stilleri yeniden uygula
        self.apply_material_style()

    def apply_material_style(self):
        """
        Uygulamaya malzeme tasarım stilini uygular.
        """
        # Koyu tema için QColor nesneleri kullanarak renkleri tanımla
        background_color = QColor("#000000") # Siyah
        on_background_color = QColor("#FFFFFF") # Beyaz
        surface_color = QColor("#000000") # Siyah
        on_surface_color = QColor("#FFFFFF") # Beyaz
        surface_variant_color = QColor("#000000") # Siyah
        outline_color = QColor("#FFFFFF") # Beyaz
        outline_variant_color = QColor("#FFFFFF") # Beyaz

        palette = self.palette()
        palette.setColor(QPalette.Window, background_color)
        palette.setColor(QPalette.WindowText, on_background_color)
        palette.setColor(QPalette.Base, surface_color)
        palette.setColor(QPalette.AlternateBase, surface_variant_color)
        palette.setColor(QPalette.ToolTipBase, QColor("#000000")) # Siyah araç ipucu arka planı
        palette.setColor(QPalette.ToolTipText, QColor("#FFFFFF")) # Beyaz araç ipucu metni
        palette.setColor(QPalette.Text, on_surface_color)
        palette.setColor(QPalette.Button, surface_color)
        palette.setColor(QPalette.ButtonText, on_surface_color)
        palette.setColor(QPalette.Highlight, QColor("#1A1A1A")) # Seçili öğeler için ince vurgu
        palette.setColor(QPalette.HighlightedText, QColor("#FF69B4")) # Vurgulanmış metin için pembe
        self.setPalette(palette)

        # Dinamik renkler için f-dizeleri kullanarak ayrıntılı stil sayfasını uygula
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {background_color.name()};
                color: {on_background_color.name()};
                font-family: "Roboto", "Segoe UI", sans-serif;
            }}
            QLabel {{
                color: {on_surface_color.name()};
                margin-bottom: 6px;
                font-weight: 500;
            }}
            QLabel#TrackedTitleLabel, QLabel#SearchTitleLabel {{
                 color: {on_background_color.name()};
            }}
            QLineEdit {{
                border: 2px solid #FFFFFF;
                padding: 0px; /* Dolgu kaldırıldı */
                font-size: 15px;
                background-color: {surface_color.name()};
                color: {on_surface_color.name()};
            }}
            QLineEdit:focus {{
                border: 2px solid #FFFFFF;
                padding: 0px; /* Dolgu kaldırıldı */
            }}
            QPushButton {{
                background-color: transparent; /* Arka plan rengi kaldırıldı */
                color: #FFFFFF;
                border: 2px solid #FFFFFF; /* Beyaz kenarlık */
                padding: 0px; /* Dolgu kaldırıldı */
                font-size: 15px;
                font-weight: 500;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1); /* Üzerine gelindiğinde hafif beyaz tonu */
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.2); /* Basıldığında daha koyu beyaz tonu */
            }}
            QPushButton:disabled {{
                background-color: #333333;
                color: #888888;
                border: 2px solid #555555;
            }}
            QPushButton#AddRunButton {{ /* "Koşu Ekle" düğmesi için stil */
                background-color: #4CAF50; /* Yeşil */
                color: #FFFFFF;
                border: 2px solid #4CAF50;
                padding: 0px; /* Dolgu kaldırıldı */
                font-size: 15px;
                font-weight: bold;
                outline: none;
            }}
            QPushButton#AddRunButton:hover {{
                background-color: #45a049;
            }}
            QPushButton#AddRunButton:pressed {{
                background-color: #3e8e41;
            }}
            QPushButton#AddRunButton:disabled {{
                background-color: #888888;
                border: 2px solid #888888;
                color: #BBBBBB;
            }}
            QPushButton#HamburgerButton {{
                background-color: transparent;
                border: 2px solid #FFFFFF;
                color: #FFFFFF;
                font-size: 20px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton#HamburgerButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QPushButton#HamburgerButton:pressed {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            QListWidget {{
                border: 2px solid #FFFFFF;
                background-color: {surface_color.name()};
                padding: 0px; /* Dolgu kaldırıldı */
                font-size: {self.BASE_ITEM_FONT_SIZE}px;
                selection-background-color: #333333; /* Daha görünür seçim arka planı */
                selection-color: #FF69B4; /* Seçim için pembe */
                outline: none;
                color: {on_surface_color.name()};
            }}
            QListWidget::item {{
                padding: 0px; /* Dolgu kaldırıldı */
                border-bottom: 2px solid {outline_variant_color.name()};
                color: {on_surface_color.name()};
                min-height: 20px;
            }}
            QListWidget::item:last-child {{
                border-bottom: none;
            }}
            QListWidget::item:selected {{
                background-color: transparent;
                color: #FF69B4; /* Seçimde pembe */
            }}
            QListWidget::item:hover {{
                background-color: transparent;
                color: #1E90FF; /* Üzerine gelindiğinde Dodger Blue */
            }}

            QScrollBar:vertical {{
                border: none;
                background: #000000;
                width: 8px; /* Daha ince dikey kaydırma çubuğu */
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #FFFFFF;
                min-height: 25px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                width: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            QScrollBar:horizontal {{
                border: none;
                background: none;
                height: 0px; /* Yatay kaydırma çubuğunu tamamen gizle */
                width: 0px; /* Yatay kaydırma çubuğunu tamamen gizle */
            }}
            QScrollBar::handle:horizontal {{
                background: none; /* Tutma kolu rengini kaldır */
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
                height: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
            QScrollArea {{
                border: none;
            }}
            QComboBox {{
                border: 2px solid #FFFFFF;
                padding: 5px;
                font-size: 12px; /* QComboBox için yazı tipi boyutunu ayarla */
                background-color: {surface_color.name()};
                color: {on_surface_color.name()};
                selection-background-color: #1A1A1A;
                selection-color: #FF69B4;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAADhJREFUOE9jZGBgYOAdg0h8z2bWf6f2/2c/AwMDUyqjHhAx2gNqQ0h+Dmgd+1iH0BpC9jNQBwAx+go3QvC16QAAAABJRU5ErkJggg==); /* İstediğiniz aşağı ok simgesi base64 ile değiştirin */
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                border: 2px solid #FFFFFF;
                background-color: {surface_color.name()};
                selection-background-color: #1A1A1A;
                selection-color: #FF69B4;
                font-size: 12px; /* QComboBox açılır liste öğeleri için yazı tipi boyutunu ayarla */
            }}

            QPushButton#RunnerLinkButton, QPushButton#TimeButton {{
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
                font-weight: normal;
                text-align: left;
                color: #FFFFFF;
            }}
            QPushButton#RunnerLinkButton:hover {{
                color: #DDDDDD;
            }}
            QPushButton#RunnerLinkButton:pressed {{
                color: #BBBBBB;
            }}

            QPushButton#GameLinkButton {{
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0;
                font-weight: bold;
                text-align: center; /* Metnin düğme içinde ortalanmasını sağlar */
                color: #FFFFFF;
                vertical-align: middle; /* Seçenekler düğmesi ile dikey hizalama */
            }}
            QPushButton#GameLinkButton:hover {{
                color: #DDDDDD;
            }}
            QPushButton#GameLinkButton:pressed {{
                color: #BBBBBB;
            }}
            QLabel.info_label {{
                font-size: {self.BASE_ITEM_FONT_SIZE}px;
                color: #FFFFFF;
                text-align: left;
                padding: 0;
                margin: 0;
            }}
            QPushButton#MoreRunnersButton {{
                background-color: transparent;
                border: none;
                color: #FFFFFF;
                padding: 0;
                margin: 0;
                font-weight: normal;
                text-align: left;
            }}
            QPushButton#MoreRunnersButton:hover {{
                color: #DDDDDD;
            }}
            QPushButton#MoreRuntersButton:pressed {{
                color: #BBBBBB;
            }}
            QLabel.dot_separator {{
                font-weight: bold;
                color: #FFFFFF;
                padding: 0;
                margin: 0;
            }}
            QLabel#DateLabel {{
                color: #FFFFFF;
                padding: 0px; /* Dikey dolgu kaldırıldı */
                margin: 0px; /* Tüm kenar boşlukları kaldırıldı */
            }}
            QMenu {{
                background-color: #000000;
                border: 2px solid #FFFFFF;
                color: #FFFFFF;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 12px;
                background-color: transparent;
            }}
            QMenu::item:selected {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QMenu::separator {{
                height: 1px;
                background-color: #FFFFFF;
                margin: 5px 0px;
            }}

            QFrame#GameFrame {{
                border: 2px solid #FFFFFF;
                background-color: {background_color.name()};
                margin-bottom: 10px;
                padding: 0px; /* Dolgu kaldırıldı */
            }}
            QPushButton#OptionsButton {{
                background-color: transparent;
                border: none;
                border-radius: 18px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: {self.OPTIONS_BUTTON_FONT_SIZE}px;
                min-width: {self.OPTIONS_BUTTON_SIZE}px;
                max-width: {self.OPTIONS_BUTTON_SIZE}px;
                min-height: {self.OPTIONS_BUTTON_SIZE}px;
                max-height: {self.OPTIONS_BUTTON_SIZE}px;
                padding: 0px;
                text-align: center;
            }}
            QPushButton#OptionsButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QPushButton#OptionsButton:pressed {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            QLabel#category_name_label {{
                /* min-height kaldırıldı, içerik ve düzen tarafından belirlenecek */
            }}
        """)

    def load_tracked_runs(self):
        """
        Takip edilen koşu verilerini bir JSON dosyasından yükler.
        """
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'r', encoding='utf-8') as f:
                    self.tracked_runs = json.load(f)
                    # Yeni ekleme: Tüm oyunların '_added_timestamp'a sahip olduğundan emin olun.
                    # Eski kayıtlardan eksikse varsayılan bir değer atayın.
                    for game_id, game_data in self.tracked_runs.items():
                        if '_added_timestamp' not in game_data:
                            # Zaman damgası eksikse eski girişleri listenin altına koymak için 0 ata.
                            game_data['_added_timestamp'] = 0 
            except json.JSONDecodeError as e:
                logger.error(f"Kaydedilen koşular yüklenirken JSONDecodeError oluştu: {e}", exc_info=True)
                self.tracked_runs = {} # Dosya bozuksa sıfırla
            except Exception as e:
                logger.error(f"Kaydedilen koşular yüklenirken beklenmeyen bir hata oluştu: {e}", exc_info=True)
                self.tracked_runs = {} # Diğer hatalarda sıfırla
        else:
            self.tracked_runs = {} # Dosya yoksa boş olarak başlat

        self.has_unseen_new_wrs = False
        self.broken_records_history = []
        # Yüklenen tüm koşular arasında yeni dünya rekorlarını kontrol et ve geçmişi doldur
        if self.tracked_runs:
            for game_id, game_data in self.tracked_runs.items():
                for category_key, category_data in game_data.get('full_game_categories', {}).items():
                    if category_data.get('is_new_record_broken', False):
                        self.has_unseen_new_wrs = True
                        self.broken_records_history.append(self._create_broken_record_info(game_data, category_data))
                for level_id, level_data in game_data.get('levels', {}).items():
                    for category_key, category_data in level_data.get('categories', {}).items():
                        if category_data.get('is_new_record_broken', False):
                            self.has_unseen_new_wrs = True
                            self.broken_records_history.append(self._create_broken_record_info(game_data, category_data, level_data))

        # Yeni dünya rekoru durumuna göre düğme görünürlüğünü güncelle
        self.show_last_record_button.setVisible(self.has_unseen_new_wrs)
        self.clear_new_wr_button.setVisible(self.has_unseen_new_wrs)

        self.update_tracked_list_ui()

    def save_tracked_runs(self):
        """
        Geçerli takip edilen koşu verilerini bir JSON dosyasına kaydeder.
        """
        try:
            with open(self.save_file, 'w', encoding='utf-8') as f:
                json.dump(self.tracked_runs, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Takip edilen koşular kaydedilirken hata oluştu: {e}", exc_info=True)
            self.show_status_message(self.translator.get_string('status_message_save_error'), is_error=True)

    def _reset_all_selections(self):
        """
        Tüm oyun, seviye, kategori ve değişken seçimlerini sıfırlar ve oyun arama sonuçlarını temizler.
        """
        self.selected_game_data = {'id': None, 'name': None, 'icon_url': None, 'weblink': None}
        self.full_game_data_cache = None
        self.game_results_list_widget.clear()
        self._reset_lower_selections()

    def _reset_lower_selections(self):
        """
        Seviye, kategori ve değişken seçimlerini sıfırlar, ancak oyun arama sonuçlarını korur.
        """
        self.selected_level_data = {'id': None, 'name': None}
        # is_miscellaneous bayrağını da burada sıfırla
        self.selected_category_data = {'id': None, 'name': None, 'is_miscellaneous': False} 
        self.selected_variable_values = {} # Değişken değerlerini temizle
        self.full_level_data_cache = None
        self.available_subcategory_variables = [] # Mevcut değişkenleri temizle

        self.category_list_widget.clear()
        self.level_list_widget.clear()
        self.variables_list_widget.clear()

        self.level_list_widget.setVisible(False)
        self.level_label.setVisible(False)
        self.variables_list_widget.setVisible(False)
        self.variables_label.setVisible(False)
        self.add_run_button.setEnabled(False) # Varsayılan olarak devre dışı

    def start_autocomplete_timer(self):
        """
        Metin değiştiğinde otomatik tamamlama zamanlayıcısını yeniden başlatır.
        """
        self.autocomplete_timer.stop()
        self.autocomplete_timer.start(500) # 500ms gecikme

    def search_game_debounced(self):
        """
        Otomatik tamamlama zamanlayıcısı tarafından tetiklenir. Giriş yeterince uzunsa aramayı yapar.
        """
        game_name = self.game_search_input.text().strip()
        if len(game_name) < 2:
            self.game_results_list_widget.clear()
            self._reset_all_selections() # Otomatik tamamlama için de sıfırla
            return
        self.search_game(game_name=game_name)

    def search_game(self, game_name=None):
        """
        Sağlanan isme göre bir oyun araması başlatır.

        Argümanlar:
            game_name (str, isteğe bağlı): Aranacak oyunun adı. None ise, giriş alanından alınır.
        """
        if game_name == None:
            game_name = self.game_search_input.text().strip()

        if not game_name:
            self.show_status_message(self.translator.get_string('search_placeholder'), is_error=True)
            return

        # Önceki aramayı iptal et (eski sonuçları önlemek için)
        if self.current_game_search_worker and self.current_game_search_worker.isRunning():
            self.current_game_search_worker.quit()
            self.current_game_search_worker.wait(100) # İş parçacığının sonlanması için kısa bir bekleme

        self._reset_all_selections() # Yeni bir arama başlatılırken tüm seçimleri sıfırla

        self.search_button.setEnabled(False)
        self.search_button.setText(self.translator.get_string('searching_button')) # Düğme metnini arama göstergesine değiştir

        # Yeni bir istek kimliği oluştur
        self.current_game_search_request_id = str(time.time())

        # Oyun araması için API işçisini oluştur ve başlat
        self.current_game_search_worker = ApiWorker(
            f"https://www.speedrun.com/api/v1/games?name={requests.utils.quote(game_name)}&max=20&embed=platforms",
            request_id=self.current_game_search_request_id
        )
        self.current_game_search_worker.finished.connect(self.handle_game_search_result)
        self.current_game_search_worker.error.connect(self.handle_api_error)
        self.current_game_search_worker.start()

    def handle_game_search_result(self, data, request_id):
        """
        Oyun arama API çağrısının sonucunu işler.

        Argümanlar:
            data (dict): API'den döndürülen oyun arama verileri.
            request_id (str): Bu yanıtla ilişkili istek kimliği.
        """
        # Yanıtın hala en son isteğe ait olup olmadığını kontrol et
        if request_id != self.current_game_search_request_id:
            logger.info(f"handle_game_search_result: Eski yanıt göz ardı ediliyor (istek kimliği uyuşmazlığı).")
            return

        self.search_button.setEnabled(True)
        self.search_button.setText(self.translator.get_string('search_button')) # Düğme metnini geri yükle
        self.game_results_list_widget.clear()

        if data and data.get('data'):
            # Oyunları uluslararası ada göre alfabetik olarak sırala
            games = sorted(data['data'], key=lambda x: x.get('names', {}).get('international', '').lower())

            if not games:
                self.game_results_list_widget.addItem(self.translator.get_string('no_game_found'))
                return

            for game in games:
                game_id = game.get('id')
                game_international_name = game.get('names', {}).get('international')

                if not game_id or not game_international_name:
                    logger.warning(f"handle_game_search_result: Eksik oyun verileri (ID veya isim): {game}")
                    continue

                release_year = game.get('released')
                game_title_display = f"{game_international_name} ({release_year})" if release_year else game_international_name

                item = QListWidgetItem(game_title_display)
                item.setData(Qt.UserRole, {'id': game_id,
                                            'name': game_international_name,
                                            'name_with_year': game_title_display,
                                            'assets': game.get('assets', {}),
                                            'weblink': game.get('weblink')})
                self.game_results_list_widget.addItem(item)
        else:
            self.game_results_list_widget.addItem(self.translator.get_string('no_game_found'))

    def show_game_result_context_menu(self, position):
        """
        Arama sonuçları listesindeki bir oyun öğesine sağ tıklanınca bağlam menüsünü görüntüler.

        Argümanlar:
            position (QPoint): Fare tıklamasının konumu.
        """
        item = self.game_results_list_widget.itemAt(position)
        if item:
            game_data_from_item = item.data(Qt.UserRole)
            if game_data_from_item and game_data_from_item.get('weblink'):
                menu = QMenu(self)
                open_speedrun_link_action = menu.addAction(self.translator.get_string('open_speedrun_com_page'))
                open_speedrun_link_action.triggered.connect(
                    lambda: self._open_weblink(game_data_from_item.get('weblink'), self.translator.get_string('web_link_not_available').format(item_type="game"))
                )
                menu.exec_(self.game_results_list_widget.mapToGlobal(position))

    def select_game_from_results(self, item):
        """
        Arama sonuçları listesinden bir oyunun seçilmesini işler.

        Argümanlar:
            item (QListWidgetItem): Seçilen oyun öğesi.
        """
        game_data_from_item = item.data(Qt.UserRole)
        if not game_data_from_item:
            logger.warning("select_game_from_results: Seçilen oyun öğesinde veri bulunamadı.")
            self.show_status_message(self.translator.get_string('invalid_game_selection'), is_error=True)
            return

        self._reset_lower_selections() # Yeni bir oyun seçildiğinde alt seviye seçimlerini sıfırla

        self.selected_game_data['id'] = game_data_from_item.get('id')
        self.selected_game_data['name'] = game_data_from_item.get('name_with_year')
        self.selected_game_data['weblink'] = game_data_from_item.get('weblink')

        if not self.selected_game_data['id'] or not self.selected_game_data['name']:
            self.show_status_message(self.translator.get_string('missing_game_id_name'), is_error=True)
            logger.error(f"select_game_from_results: Eksik oyun ID'si veya adı: {game_data_from_item}")
            return

        assets = game_data_from_item.get('assets', {})
        icon_asset = assets.get('cover-tiny') or assets.get('icon')
        self.selected_game_data['icon_url'] = icon_asset.get('uri') if icon_asset else None

        self.show_status_message(self.translator.get_string('loading_game_details').format(game_name=self.selected_game_data['name']))

        # Önceki detay çekme iş parçacığını sonlandır
        if hasattr(self, 'details_fetch_worker') and self.details_fetch_worker.isRunning():
            self.details_fetch_worker.quit()
            self.details_fetch_worker.wait(100)

        # Yeni bir istek kimliği oluştur
        self.current_game_details_request_id = str(time.time())

        # Seçilen oyun için oyun detaylarını, seviyeleri ve kategorileri getir
        api_url = f"https://www.speedrun.com/api/v1/games/{self.selected_game_data['id']}?embed=levels,categories.variables"
        self.details_fetch_worker = ApiWorker(api_url, request_id=self.current_game_details_request_id)
        self.details_fetch_worker.finished.connect(self.handle_game_details_result)
        self.details_fetch_worker.error.connect(self.handle_api_error)
        self.details_fetch_worker.start()

    def handle_game_details_result(self, data, request_id):
        """
        Oyun detaylarını (seviyeler ve kategoriler) getirme sonucunu işler.

        Argümanlar:
            data (dict): API'den döndürülen oyun detay verileri.
            request_id (str): Bu yanıtla ilişkili istek kimliği.
        """
        # Yanıtın hala en son isteğe ait olup olmadığını kontrol et
        if request_id != self.current_game_details_request_id:
            logger.info(f"handle_game_details_result: Eski yanıt göz ardı ediliyor (istek kimliği uyuşmazlığı).")
            return

        game_data = data.get('data')
        if not game_data:
            self.show_status_message(self.translator.get_string('loading_game_details_failed'), is_error=True)
            logger.error(f"handle_game_details_result: Oyun detayları yüklenemedi veya boş: {self.selected_game_data['id']}")
            return

        self.full_game_data_cache = game_data # Tam oyun verilerini önbelleğe al

        levels_payload = {'data': game_data.get('levels', {}).get('data', [])}
        categories_payload = {'data': game_data.get('categories', {}).get('data', [])}

        self.handle_level_result(levels_payload, request_id) # İstek Kimliğini de geçir
        self.handle_category_result(categories_payload, request_id) # Kategorileri otomatik yükle, istek Kimliğini de geçir
        self.show_status_message(self.translator.get_string('game_details_loaded').format(game_name=self.selected_game_data['name']), is_error=False)
        # Oyun detayları yüklendikten sonra listelerin etkinleştirildiğinden emin olmak için ekle
        self.on_category_variables_worker_completed()


    def handle_level_result(self, data, request_id):
        """
        Seçilen oyun için mevcut seviyelerle seviye listesi widget'ını doldurur.

        Argümanlar:
            data (dict): API'den döndürülen seviye verileri.
            request_id (str): Bu yanıtla ilişkili istek kimliği.
        """
        # Yanıtın hala en son isteğe ait olup olmadığını kontrol et (bu seviye yüklemesi için)
        # Bu kontrol, handle_game_details_result'tan geliyorsa game_details_request_id'ye bakmalıdır.
        if request_id != self.current_game_details_request_id and request_id != self.current_level_categories_request_id:
            logger.info(f"handle_level_result: Eski yanıt göz ardı ediliyor (istek kimliği uyuşmazlığı).")
            return

        self.level_list_widget.clear()

        if data and data.get('data'):
            self.level_list_widget.setVisible(True)
            self.level_label.setVisible(True)
            # "Tam Oyun" seçeneğini ekle
            full_game_option = QListWidgetItem(_.get_string('full_game_option'))
            full_game_option.setData(Qt.UserRole, "full_game_no_level")
            self.level_list_widget.addItem(full_game_option)

            for level in data['data']:
                level_id = level.get('id')
                level_name = level.get('name')
                if level_id and level_name:
                    item = QListWidgetItem(level_name)
                    item.setData(Qt.UserRole, {'id': level_id, 'name': level_name})
                    self.level_list_widget.addItem(item)
                else:
                    logger.warning(f"handle_level_result: Eksik seviye verileri (ID veya isim): {level}")

            self.level_list_widget.setEnabled(True)
        else:
            self.level_list_widget.addItem(_.get_string('no_individual_level_found'))
            self.level_list_widget.setVisible(True)
            self.level_label.setVisible(True)
            self.level_list_widget.setEnabled(False) # Seviye yoksa seçilemez yap

    def select_level_from_results(self, item):
        """
        Seviye listesinden bir seviyenin seçilmesini işler.

        Argümanlar:
            item (QListWidgetItem): Seçilen seviye öğesi.
        """
        level_data_from_item = item.data(Qt.UserRole)
        if level_data_from_item is None:
            return # Ayırıcıya tıklanırsa hiçbir şey yapma

        self.category_list_widget.clear()
        self.variables_list_widget.clear()
        self.variables_list_widget.setVisible(False)
        self.variables_label.setVisible(False)
        # is_miscellaneous bayrağını da burada sıfırla
        self.selected_category_data = {'id': None, 'name': None, 'is_miscellaneous': False} 
        self.selected_variable_values = {}
        self.full_level_data_cache = None # Seviye değiştiğinde seviye önbelleğini temizle
        self.add_run_button.setEnabled(False) # Seviye değiştiğinde "Koşu Ekle" düğmesini devre dışı bırak
        self.available_subcategory_variables = [] # Yeni seçim için değişkenleri temizle

        # Önceki seviye/kategori iş parçacığını sonlandır
        if hasattr(self, 'level_category_fetch_worker') and self.level_category_fetch_worker.isRunning():
            self.level_category_fetch_worker.quit()
            self.level_category_fetch_worker.wait(100)

        # Kategori/değişken yükleme için yeni bir istek kimliği oluştur
        self.current_category_variables_request_id = str(time.time())
        self.category_list_widget.setEnabled(False) # Getirme sırasında devre dışı bırak
        self.variables_list_widget.setEnabled(False) # Getirme sırasında devre dışı bırak


        if level_data_from_item == "full_game_no_level":
            self.selected_level_data = {'id': None, 'name': None}
            # Tam oyun detayları önbelleğe alınmışsa, kategorileri oradan yükle
            if self.full_game_data_cache:
                 categories_payload = {'data': self.full_game_data_cache.get('categories', {}).get('data', [])}
                 # Geçici olarak game_details_request_id'yi handle_category_result'a istek Kimliği olarak geçir
                 self.handle_category_result(categories_payload, self.current_game_details_request_id)
                 self.on_category_variables_worker_completed() # Önbellekten yüklendiğinde etkinleştir
            else:
                 # Yedek: önbellekte yoksa, API'den getir (nadiren olmalı)
                 self.category_fetch_worker = ApiWorker(
                     f"https://www.speedrun.com/api/v1/games/{self.selected_game_data['id']}/categories?embed=variables",
                     request_id=self.current_category_variables_request_id # Yeni belirli ID'yi kullan
                 )
                 self.category_fetch_worker.finished.connect(self.handle_category_result)
                 self.category_fetch_worker.error.connect(self.handle_api_error)
                 self.category_fetch_worker.worker_completed.connect(self.on_category_variables_worker_completed)
                 self.category_fetch_worker.start()
            self.show_status_message(self.translator.get_string('loading_full_game_categories'), is_error=False)
        else:
            self.selected_level_data['id'] = level_data_from_item['id']
            self.selected_level_data['name'] = level_data_from_item['name']
            self.show_status_message(self.translator.get_string('level_categories_loading').format(level_name=self.selected_level_data['name']))
            # Seçilen seviyeye özgü kategorileri getir
            api_url = f"https://www.speedrun.com/api/v1/levels/{self.selected_level_data['id']}/categories?embed=variables"
            self.level_category_fetch_worker = ApiWorker(api_url, request_id=self.current_category_variables_request_id) # Yeni belirli ID'yi kullan
            self.level_category_fetch_worker.finished.connect(self.handle_level_category_result)
            self.level_category_fetch_worker.error.connect(self.handle_api_error)
            self.level_category_fetch_worker.worker_completed.connect(self.on_category_variables_worker_completed)
            self.level_category_fetch_worker.start()

    def handle_level_category_result(self, data, request_id):
        """
        Seviyeye özgü kategorileri önbelleğe alır ve ardından bunları genel kategori işleyicisine iletir.

        Argümanlar:
            data (dict): API'den döndürülen seviye kategori verileri.
            request_id (str): Bu yanıtla ilişkili istek kimliği.
        """
        # Yanıtın hala en son isteğe ait olup olmadığını kontrol et
        if request_id != self.current_category_variables_request_id: # Yeni belirli ID'yi kontrol et
            logger.info(f"handle_level_category_result: Eski yanıt göz ardı ediliyor (istek kimliği uyuşmazlığı).")
            return

        self.full_level_data_cache = data.get('data', []) # Seviye kategorilerini önbelleğe al
        self.handle_category_result(data, request_id) # Genel kategori işleyicisine ilet, istek Kimliğini de geçir
        self.show_status_message(self.translator.get_string('categories_loaded'), is_error=False)

    def handle_category_result(self, data, request_id):
        """
        Kategori listesi widget'ını doldurur.

        Argümanlar:
            data (dict): API'den döndürülen kategori verileri.
            request_id (str): Bu yanıtla ilişkili istek kimliği.
        """
        # Yanıtın hala en son isteğe ait olup olmadığını kontrol et
        if request_id != self.current_category_variables_request_id and request_id != self.current_game_details_request_id:
            logger.info(f"handle_category_result: Eski yanıt göz ardı ediliyor (istek kimliği uyuşmazlığı).")
            return

        self.category_list_widget.clear()
        categories_added = False
        self.add_run_button.setEnabled(False) # Yeni kategori yüklendiğinde "Koşu Ekle" düğmesini devre dışı bırak
        self.available_subcategory_variables = [] # Yeni seçim için değişkenleri temizle

        per_game_categories = []
        per_level_categories = []

        if data and data.get('data'):
            for category in data['data']:
                category_id = category.get('id')
                category_name = category.get('name')
                category_type = category.get('type')

                if not category_id or not category_name or not category_type:
                    logger.warning(f"handle_category_result: Eksik kategori verileri (ID, isim veya tür): {category}")
                    continue

                item_text = category_name
                if category.get('miscellaneous', False):
                    item_text += self.translator.get_string('miscellaneous_category')

                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, category) # Tüm kategori nesnesini öğeye kaydet

                if category_type == 'per-game':
                    per_game_categories.append(item)
                elif category_type == 'per-level':
                    per_level_categories.append(item)

        # Bir seviye seçili olup olmamasına göre kategorileri görüntüle
        if self.selected_level_data.get('id'):
            if per_level_categories:
                self.category_list_widget.addItem(self.translator.get_string('separator_per_level_categories'))
                for item in per_level_categories:
                    self.category_list_widget.addItem(item)
                categories_added = True
            if per_game_categories:
                self.category_list_widget.addItem(self.translator.get_string('separator_per_game_categories'))
                for item in per_game_categories:
                    self.category_list_widget.addItem(item)
                categories_added = True
        else: # Hiçbir seviye seçili değilse ("Tam Oyun"), yalnızca oyun başına kategorileri göster
            if per_game_categories:
                for item in per_game_categories:
                    self.category_list_widget.addItem(item)
                categories_added = True

        if not categories_added:
            msg_text = self.translator.get_string('no_suitable_category')
            if self.selected_level_data.get('id'):
                msg_text = self.translator.get_string('no_suitable_category_for_level').format(level_name=self.selected_level_data['name'])
            elif self.selected_game_data.get('id'):
                msg_text = self.translator.get_string('no_suitable_category_for_game').format(game_name=self.selected_game_data['name'])
            self.category_list_widget.addItem(msg_text)

        self.variables_list_widget.clear()
        self.variables_list_widget.setVisible(False)
        self.variables_label.setVisible(False)
        # is_miscellaneous'ı da burada varsayılana sıfırla
        self.selected_category_data = {'id': None, 'name': None, 'is_miscellaneous': False} 
        self.selected_variable_values = {}
        self._update_add_run_button_state() # Koşu ekle düğmesi durumunun doğru şekilde güncellendiğinden emin ol

    def select_category_to_show_variables(self, item):
        """
        Bir kategorinin seçilmesini işler ve ilişkili değişkenlerini görüntüler.

        Argümanlar:
            item (QListWidgetItem): Seçilen kategori öğesi.
        """
        if item.text().startswith("---"): # Ayırıcı başlıkları göz ardı et
            return

        category_data_from_item = item.data(Qt.UserRole)
        if not category_data_from_item:
            logger.warning("select_category_to_show_variables: Seçilen kategori öğesinde veri bulunamadı.")
            self.variables_list_widget.clear()
            self.variables_list_widget.setVisible(False)
            self.variables_label.setVisible(False)
            self.show_status_message(self.translator.get_string('invalid_category_selection'), is_error=True)
            self.add_run_button.setEnabled(False)
            return

        self.selected_category_data['id'] = category_data_from_item.get('id')
        self.selected_category_data['name'] = category_data_from_item.get('name')
        # Takip edilen koşularda kullanılmak üzere 'miscellaneous' bayrağını sakla
        self.selected_category_data['is_miscellaneous'] = category_data_from_item.get('miscellaneous', False)

        self.variables_list_widget.clear()
        self.variables_list_widget.setVisible(False)
        self.variables_label.setVisible(False)
        self.selected_variable_values = {} # Yeni bir kategori seçildiğinde değişken seçimlerini temizle
        self.add_run_button.setEnabled(False)
        self.available_subcategory_variables = [] # Yeni seçim için değişkenleri sıfırla

        # Önceki kategori/değişken iş parçacığını sonlandır
        if hasattr(self, 'category_variables_fetch_worker') and self.category_variables_fetch_worker.isRunning():
            self.category_variables_fetch_worker.quit()
            self.category_variables_fetch_worker.wait(100)
            
        # Kategori ve değişken yükleme için yeni bir istek kimliği oluştur
        self.current_category_variables_request_id = str(time.time())
        self.category_list_widget.setEnabled(False) # Getirme sırasında devre dışı bırak
        self.variables_list_widget.setEnabled(False) # Getirme sırasında devre dışı bırak


        variables_data = category_data_from_item.get('variables', {})
        variables_payload = {'data': variables_data.get('data', [])}
        
        # Değişkenler zaten gömülüyse, bunları doğrudan işle.
        if variables_payload['data']:
            self.handle_variables_result(variables_payload, self.current_category_variables_request_id)
            self.on_category_variables_worker_completed() # Tamamlama işleyicisini manuel olarak çağır
        else: # Değişken yok veya boş değişken listesi.
            # Bu, alt kategori değişkenleri olmayan kategoriler için yoldur.
            # self.available_subcategory_variables bu yöntemin başında zaten [] olarak sıfırlanmıştı.
            # Bu nedenle, sadece düğme durumunu doğrudan güncellememiz gerekiyor.
            self.variables_list_widget.clear() # Değişkenler listesinin boş olduğundan emin ol
            self.variables_list_widget.setVisible(False)
            self.variables_label.setVisible(False)
            self.show_status_message(self.translator.get_string('no_variables_found'), is_error=False)
            self._update_add_run_button_state() # Düğmeyi etkinleştirmek için buradan çağır
            self.on_category_variables_worker_completed() # UI öğelerini (listeleri) yeniden etkinleştir


    def _get_non_obsolete_variable_values(self, variable_data):
        """
        Belirli bir değişken için güncel olmayan değerlerin bir sözlüğünü döndürür.

        Argümanlar:
            variable_data (dict): Değişken verileri.

        Döndürür:
            dict: Güncel olmayan değerlerin bir sözlüğü.
        """
        non_obsolete_values = {}
        values_data = variable_data.get('values', {}).get('values', {})
        for value_id, value_info in values_data.items():
            if not value_info.get('obsoletes', False):
                non_obsolete_values[value_id] = value_info
        return non_obsolete_values

    def handle_variables_result(self, data, request_id):
        """
        Mevcut alt kategori değişkenleriyle değişkenler listesi widget'ını doldurur.

        Argümanlar:
            data (dict): API'den döndürülen değişken verileri.
            request_id (str): Bu yanıtla ilişkili istek kimliği.
        """
        # Yanıtın hala en son isteğe ait olup olmadığını kontrol et
        if request_id != self.current_category_variables_request_id:
            logger.info(f"handle_variables_result: Eski yanıt göz ardı ediliyor (istek kimliği uyuşmazlığı).")
            return

        self.variables_list_widget.clear()
        self.variables_list_widget.setVisible(False) # Varsayılan olarak gizli
        self.variables_label.setVisible(False)      # Varsayılan olarak gizli
        self.selected_variable_values = {} # Seçimleri temizle
        self.available_subcategory_variables = [] # Mevcut değişkenleri temizle

        # Yalnızca en az bir güncel olmayan değere sahip alt kategori değişkenlerini topla
        if data and isinstance(data.get('data'), list): # Sağlamlık: 'data' alanının bir liste olduğundan emin ol
            for variable in data['data']:
                if not isinstance(variable, dict): # 'data['data']' içindeki her öğenin bir sözlük olduğundan emin ol
                    logger.warning(f"handle_variables_result: Beklenmeyen değişken öğesi türü: {type(variable)}. Atlanıyor.")
                    continue

                variable_id = variable.get('id')
                variable_name = variable.get('name')
                variable_is_subcategory = variable.get('is-subcategory')

                if variable_is_subcategory and variable_id and variable_name: # Gerekli alanların mevcut olduğundan emin ol
                    non_obsolete_values = self._get_non_obsolete_variable_values(variable)
                    if non_obsolete_values:
                        variable_copy = variable.copy()
                        variable_copy['values'] = {'values': non_obsolete_values}
                        self.available_subcategory_variables.append(variable_copy)
                else:
                    logger.warning(f"handle_variables_result: Eksik veya geçersiz alt kategori değişken verileri: {variable}. Atlanıyor.")

        # Senaryo 1: Alt kategori değişkeni yok veya geçerli seçenek yok
        if not self.available_subcategory_variables:
            self.show_status_message(self.translator.get_string('no_variables_found'), is_error=False)
            self._update_add_run_button_state() # Düğme durumunun doğru şekilde güncellendiğinden emin ol
            return

        # Senaryo 2: Tam olarak bir alt kategori değişkeni ve tam olarak bir güncel olmayan değer
        if len(self.available_subcategory_variables) == 1:
            single_variable = self.available_subcategory_variables[0]
            non_obsolete_values = single_variable['values']['values']

            if len(non_obsolete_values) == 1:
                # Yalnızca bir güncel olmayan değer varsa, otomatik olarak seç ve değişkenler bölümünü gizle
                variable_id = single_variable['id']
                value_id, value_info = list(non_obsolete_values.items())[0] # Tek öğeyi al
                self.selected_variable_values[variable_id] = {'value_id': value_id, 'value_name': value_info['label']}

                self.variables_list_widget.setVisible(False)
                self.variables_label.setVisible(False)
                self.show_status_message(self.translator.get_string('variable_auto_selected').format(variable_name=single_variable['name']), is_error=False)
                self._update_add_run_button_state() # Ekle düğmesini etkinleştir (zaten takip edilmiyorsa)
                return

        # Kullanıcı seçimi gerektiren senaryolar: birden çok değişken veya birden çok seçeneği olan bir değişken
        self.variables_list_widget.setVisible(True)
        self.variables_label.setVisible(True)
        self.variables_list_widget.setEnabled(True)

        for variable in self.available_subcategory_variables:
            variable_id = variable.get('id')
            variable_name = variable.get('name')
            
            # Sağlamlık: 'values' ve iç 'values'ın mevcut ve sözlük olduğundan emin ol
            variable_values_data = variable.get('values', {}).get('values', {}) # Varsayılan olarak boş sözlük

            # Her değişken için bir başlık ekle
            variable_header_item = QListWidgetItem(_.get_string('select_variable_header').format(variable_name=variable_name))
            header_font = QFont("Roboto", 10, QFont.Bold)
            variable_header_item.setFont(header_font)
            variable_header_item.setForeground(QColor("#BBBBBB"))
            variable_header_item.setFlags(variable_header_item.flags() & ~Qt.ItemIsSelectable) # Başlığı seçilemez yap
            self.variables_list_widget.addItem(variable_header_item)

            # Sağlamlık: Yalnızca variable_values_data bir sözlükse yinele
            if isinstance(variable_values_data, dict):
                for value_id, value_info in variable_values_data.items():
                    if not isinstance(value_info, dict): # Her değer bilgisinin bir sözlük olduğundan emin ol
                        logger.warning(f"handle_variables_result: Beklenmeyen değişken değeri öğesi türü: {type(value_info)}. Atlanıyor.")
                        continue

                    # Seçeneği daha net görüntülemek için değişken adıyla ön ekle
                    item_text = f"  {variable_name}: {value_info.get('label', value_id)}"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, {'variable_id': variable_id, 'value_id': value_id, 'value_name': value_info.get('label', value_id)})
                    self.variables_list_widget.addItem(item)
            else:
                logger.warning(f"handle_variables_result: Beklenmeyen değişken değerleri biçimi: {type(variable_values_data)}. Atlanıyor. Değişken: {variable_name}")


        self._update_add_run_button_state() # Düğme durumunun doğru şekilde güncellendiğinden emin ol

    def handle_variable_selection(self, clicked_item):
        """
        Değişken seçeneklerinin seçilmesini/seçiminin kaldırılmasını işler.
        Aynı değişkenden yalnızca bir seçeneğin seçilebilmesini sağlar.

        Argümanlar:
            clicked_item (QListWidgetItem): Tıklanan öğe.
        """
        if clicked_item.text().startswith("---"): # Başlık tıklamalarını göz ardı et
            clicked_item.setSelected(False)
            return

        variable_data = clicked_item.data(Qt.UserRole)
        if not variable_data or 'variable_id' not in variable_data or 'value_id' not in variable_data or 'value_name' not in variable_data:
            logger.warning(f"handle_variable_selection: Eksik veya geçersiz değişken seçim verileri: {variable_data}")
            self.show_status_message(self.translator.get_string('invalid_variable_selection'), is_error=True)
            self.add_run_button.setEnabled(False)
            return

        variable_id = variable_data['variable_id']
        value_id = variable_data['value_id']
        value_name = variable_data['value_name']

        is_selected_now = clicked_item.isSelected()

        # Aynı variable_id'ye ait diğer öğelerin seçimini kaldır
        # Speedrun.com kurallarına göre, değişken başına yalnızca bir değer seçilebilir.
        for i in range(self.variables_list_widget.count()):
            item = self.variables_list_widget.item(i)
            other_variable_data = item.data(Qt.UserRole)
            if other_variable_data and other_variable_data.get('variable_id') == variable_id and item != clicked_item:
                if item.isSelected(): # Aynı variable_id'ye sahip başka bir öğe seçiliyse, seçimini kaldır.
                    item.setSelected(False)

        # clicked_item'ın son seçim durumuna göre selected_variable_values'ı güncelle
        if is_selected_now:
            self.selected_variable_values[variable_id] = {'value_id': value_id, 'value_name': value_name}
        else: # Öğenin seçimi kaldırıldı
            if variable_id in self.selected_variable_values:
                del self.selected_variable_values[variable_id]

        self._update_add_run_button_state() # "Koşu Takip Et" düğmesinin durumunu yeniden değerlendir

    def _update_add_run_button_state(self):
        """
        Bir oyun ve kategori seçili olup olmadığına ve alt kategori değişkenleri varsa, her biri için en az birinin seçili olup olmadığına göre "Koşu Takip Et" düğmesini etkinleştirir/devre dışı bırakır.
        Ayrıca koşunun zaten takip edilip edilmediğini kontrol eder.
        """
        is_game_selected = self.selected_game_data['id'] is not None
        is_category_selected = self.selected_category_data['id'] is not None

        if not is_game_selected or not is_category_selected:
            self.add_run_button.setEnabled(False)
            return

        # Alt kategori değişkenleri varsa, her değişken grubu (isme göre) için bir seçim yapılıp yapılmadığını kontrol et
        if self.available_subcategory_variables:
            unique_variable_names_needed = set(var_def['name'] for var_def in self.available_subcategory_variables)

            all_required_vars_selected = True
            for var_name in unique_variable_names_needed:
                found_selection_for_name = False
                for var_def in self.available_subcategory_variables:
                    # Bu variable_name için seçili bir var_id olup olmadığını kontrol et
                    if var_def['name'] == var_name and var_def['id'] in self.selected_variable_values:
                        found_selection_for_name = True
                        break
                if not found_selection_for_name:
                    all_required_vars_selected = False
                    break

            if not all_required_vars_selected:
                missing_vars_names = []
                for var_name in unique_variable_names_needed:
                    found_selection_for_name = False
                    for var_def in self.available_subcategory_variables:
                        if var_def['name'] == var_name and var_def['id'] in self.selected_variable_values:
                            found_selection_for_name = True
                            break
                    if not found_selection_for_name:
                        missing_vars_names.append(var_name)

                missing_str = ", ".join(missing_vars_names)
                # Daha net mesaj için güncellendi
                self.show_status_message(self.translator.get_string('missing_variable_selection').format(missing_vars=missing_str), is_error=True)
                self.add_run_button.setEnabled(False)
                return
            else:
                # Değişkenler şimdi seçiliyse önceki hata mesajını temizle
                status_text = self.status_label.text()
                if self.translator.get_string('missing_variable_selection', missing_vars="").split(':')[0] in status_text: # Belirli hata mesajını kontrol et
                    self.show_status_message("")

        # Şimdi, koşunun zaten takip edilip edilmediğini kontrol et
        is_run_already_tracked = False
        if self.selected_game_data['id'] in self.tracked_runs:
            game_data = self.tracked_runs[self.selected_game_data['id']]

            # Kategori ID'si ve sıralanmış değişken değeri ID'lerine göre tutarlı bir takip anahtarı oluştur
            current_selected_vars_for_key = {k: v['value_id'] for k, v in sorted(self.selected_variable_values.items())}
            current_tracked_key = f"{self.selected_category_data['id']}-{json.dumps(current_selected_vars_for_key, sort_keys=True)}"

            if not self.selected_level_data['id']: # Tam Oyun kategorisi
                if current_tracked_key in game_data.get('full_game_categories', {}):
                    is_run_already_tracked = True
            else: # Bireysel Seviye kategorisi
                if self.selected_level_data['id'] in game_data.get('levels', {}) and \
                   current_tracked_key in game_data['levels'][self.selected_level_data['id']].get('categories', {}):
                    is_run_already_tracked = True

        if is_run_already_tracked:
            self.show_status_message(self.translator.get_string('run_already_tracked').format(display_category_name=self.selected_category_data['name']), is_error=True)
            self.add_run_button.setEnabled(False)
        else:
            # Düğme etkinleştirilecekse önceki hata mesajlarını temizle
            if self.translator.get_string('run_already_tracked', display_category_name="") not in self.status_label.text() and \
               self.translator.get_string('missing_variable_selection', missing_vars="").split(':')[0] not in self.status_label.text(): # Her iki belirli hatayı da kontrol et
                 self.show_status_message("")
            self.add_run_button.setEnabled(True)

    def add_to_tracked(self):
        """
        Seçilen oyunu, seviyeyi, kategoriyi ve değişkenleri takip edilen koşulara ekler.
        """
        if not self.selected_category_data['id']:
            self.show_status_message(self.translator.get_string('track_category_missing'), is_error=True)
            return

        # "Koşu Takip Et" düğmesinin etkin olup olmadığını son bir güvenlik önlemi olarak açıkça kontrol et.
        if not self.add_run_button.isEnabled():
            self.show_status_message(self.translator.get_string('add_run_hint_already_tracked'), is_error=True)
            return

        if not self.selected_game_data['id'] or not self.selected_game_data['name']:
            self.show_status_message(self.translator.get_string('game_not_selected'), is_error=True)
            return

        category_name_for_storage = self.selected_category_data['name']
        is_miscellaneous_category = self.selected_category_data['is_miscellaneous']

        # Takip edilen koşularda oyun girişini başlat (henüz mevcut değilse)
        if self.selected_game_data['id'] not in self.tracked_runs:
            self.tracked_runs[self.selected_game_data['id']] = {
                'name': self.selected_game_data['name'],
                'icon_url': self.selected_game_data['icon_url'],
                'weblink': self.selected_game_data['weblink'],
                'full_game_categories': {},
                'levels': {},
                '_added_timestamp': time.time() # Yeni ekleme: oyun eklendiğinde zaman damgasını kaydet
            }

        run_type = 'full_game'
        api_url_template = "https://www.speedrun.com/api/v1/leaderboards/{game_id}/category/{category_id}?top=1&embed=players,segments"

        variable_query_params = ""
        display_variable_names = []
        if self.selected_variable_values:
            # Seçilen değişkenler için sorgu parametreleri ve görünen adlar oluştur
            for var_id in sorted(self.selected_variable_values.keys()):
                val_data = self.selected_variable_values[var_id]
                variable_query_params += f"&var-{var_id}={val_data['value_id']}"
                display_variable_names.append(val_data['value_name'])

        display_category_name = category_name_for_storage
        # level_name'in handle_add_result içinde alınması için lambda argümanlarından kaldırıldı
        # level_name = self.selected_level_data['name'] if self.selected_level_data['id'] else None 
        if self.selected_level_data['id']:
            display_category_name = f"{self.selected_level_data['name']}: {display_category_name}"

        if display_variable_names:
            display_variable_names.sort()
            display_category_name += f" ({', '.join(display_variable_names)})"

        # Kategori ID'leri ve seçilen değişkenlerin değerlerini içeren kategorileri depolamak için tutarlı bir anahtar oluştur
        sorted_variable_values_for_key = {k: v['value_id'] for k, v in sorted(self.selected_variable_values.items())}
        tracked_category_key = f"{self.selected_category_data['id']}-{json.dumps(sorted_variable_values_for_key, sort_keys=True)}"


        if not self.selected_level_data['id']: # Tam Oyun kategorisi
            if tracked_category_key in self.tracked_runs[self.selected_game_data['id']]['full_game_categories']:
                self.show_status_message(self.translator.get_string('run_already_tracked').format(display_category_name=display_category_name), is_error=True)
                return
            api_url = api_url_template.format(game_id=self.selected_game_data['id'], category_id=self.selected_category_data['id']) + variable_query_params
        else: # Bireysel Seviye kategorisi
            run_type = 'il'
            api_url_template = "https://www.speedrun.com/api/v1/leaderboards/{game_id}/level/{level_id}/{category_id}?top=1&embed=players,segments"

            # Takip edilen koşularda seviye ve kategori yapısının mevcut olduğundan emin ol
            if self.selected_level_data['id'] not in self.tracked_runs[self.selected_game_data['id']]['levels']:
                self.tracked_runs[self.selected_game_data['id']]['levels'][self.selected_level_data['id']] = {
                    'name': self.selected_level_data['name'], # selected_level_data'dan adı kullan
                    'categories': {}
                }
            if tracked_category_key in self.tracked_runs[self.selected_game_data['id']]['levels'][self.selected_level_data['id']]['categories']:
                 self.show_status_message(self.translator.get_string('run_already_tracked').format(display_category_name=display_category_name), is_error=True)
                 return
            api_url = api_url_template.format(game_id=self.selected_game_data['id'], level_id=self.selected_level_data['id'], category_id=self.selected_category_data['id']) + variable_query_params

        # Yeni takip edilen koşu için mevcut dünya rekorunu almak için API işçisini başlat
        self.add_worker = ApiWorker(api_url)
        self.add_worker.finished.connect(
            # İşleyiciye ek bağlam verileri geçirmek için lambda kullan
            # 'lvl_name' lambda argümanlarından handle_add_result'a kaldırıldı
            lambda data, req_id, cat_id=self.selected_category_data['id'], cat_name=category_name_for_storage,
                   game_id_val=self.selected_game_data['id'], lvl_id=self.selected_level_data['id'],
                   rt=run_type, # lvl_name buradan kaldırıldı
                   var_vals=self.selected_variable_values.copy(),
                   disp_cat_name=display_category_name,
                   is_misc=is_miscellaneous_category: # Miscellaneous bayrağını geçir
                   self.handle_add_result(data, cat_id, cat_name, game_id_val, lvl_id, rt, var_vals, disp_cat_name, is_misc)
        )
        self.add_worker.error.connect(self.handle_api_error)
        self.add_worker.start()
        self.show_status_message(self.translator.get_string('record_tracking').format(display_category_name=display_category_name))
        self.add_run_button.setEnabled(False) # Eklendikten sonra düğmeyi devre dışı bırak, güncellemeden sonra yeniden etkinleştirilecek

    def handle_add_result(self, leaderboard_data, category_id, category_base_name, game_id, level_id, run_type, selected_variable_values, display_category_name, is_miscellaneous):
        """
        Yeni bir koşu ekleme sonucunu işler.

        Argümanlar:
            leaderboard_data (dict): API'den döndürülen liderlik tablosu verileri.
            category_id (str): Kategorinin kimliği.
            category_base_name (str): Kategorinin temel adı.
            game_id (str): Oyunun kimliği.
            level_id (str): Seviyenin kimliği (IL koşuları için).
            # level_name (str): Seviyenin adı. # Buradan kaldırıldı
            run_type (str): Koşu türü ('full_game' veya 'il').
            selected_variable_values (dict): Seçilen değişken değerleri.
            display_category_name (str): UI gösterimi için koşunun tam adı.
            is_miscellaneous (bool): Kategori miscellaneous kategori ise True.
        """
        try:
            # API yanıtı beklenirken oyunun kaldırılıp kaldırılmadığını kontrol et
            if game_id not in self.tracked_runs:
                logger.warning(f"handle_add_result: {game_id} oyunu API yanıtı beklenirken kaldırıldı veya bulunamadı. İşlem iptal edildi.")
                self.show_status_message(self.translator.get_string('game_removed_during_api').format(game_id=game_id), is_error=True)
                self._update_add_run_button_state()
                return

            game_name_with_year = self.tracked_runs[game_id]['name']

            world_record = self._get_new_record_run_obj(leaderboard_data) # Yardımcı fonksiyonu kullan

            if world_record:
                current_record_time_seconds = world_record.get('times', {}).get('primary_t')
                run_weblink = world_record.get('weblink')
                run_date = world_record.get('date', _.get_string('not_available_abbr'))

                new_player_names, new_player_weblinks = self._extract_player_info(world_record, leaderboard_data)

                splits_data_api = leaderboard_data.get('data', {}).get('segments', [])
                if not isinstance(splits_data_api, list):
                    splits_data_api = []
                    logger.warning(f"handle_add_result: Bölme verileri liste biçiminde değil: {type(leaderboard_data.get('data', {}).get('segments'))}. Boş liste kullanılıyor.")

                run_info = {
                    'name': category_base_name, # Temel kategori adı
                    'display_name': display_category_name, # UI gösterimi için tam ad
                    'current_record_time': current_record_time_seconds,
                    'weblink': run_weblink,
                    'current_runners': new_player_names,
                    'player_weblinks': new_player_weblinks,
                    'date_completed': run_date,
                    'splits': splits_data_api,
                    'variables': selected_variable_values, # Seçilen değişkenleri kaydet
                    'is_new_record_broken': False, # Yeni dünya rekoru bayrağı başlangıçta False
                    'is_miscellaneous': is_miscellaneous # Miscellaneous bayrağını sakla
                }

                # Depolanan değişkenler için anahtar yalnızca tutarlılık için ID'leri içermelidir
                stored_variables_for_key = {k: v['value_id'] for k, v in selected_variable_values.items()}
                tracked_category_key = f"{category_id}-{json.dumps(stored_variables_for_key, sort_keys=True)}"

                if run_type == 'full_game':
                    if tracked_category_key in self.tracked_runs[game_id]['full_game_categories']:
                        self.show_status_message(self.translator.get_string('run_already_tracked').format(display_category_name=display_category_name), is_error=True)
                        return
                    self.tracked_runs[game_id]['full_game_categories'][tracked_category_key] = run_info
                elif run_type == 'il':
                    # Takip edilen koşularda seviye ve kategori yapısının mevcut olduğundan emin ol
                    if level_id not in self.tracked_runs[game_id]['levels']:
                        self.tracked_runs[game_id]['levels'][level_id] = {
                            'name': self.selected_level_data['name'], # selected_level_data'dan adı kullan
                            'categories': {}
                        }
                    if tracked_category_key in self.tracked_runs[self.selected_game_data['id']]['levels'][level_id]['categories']:
                         self.show_status_message(self.translator.get_string('run_already_tracked').format(display_category_name=display_category_name), is_error=True)
                         return
                    self.tracked_runs[self.selected_game_data['id']]['levels'][level_id]['categories'][tracked_category_key] = run_info

                self.save_tracked_runs()
                self.update_tracked_list_ui()
                self.show_status_message(self.translator.get_string('record_tracked_success').format(display_category_name=display_category_name))
                self._update_add_run_button_state() # Ekledikten sonra düğme durumunu güncelle
            else:
                self.show_status_message(self.translator.get_string('no_world_record_found').format(display_category_name=display_category_name), is_error=True)
                logger.warning(f"handle_add_result: API yanıtı beklenmedik veya boş (dünya rekoru bulunamadı): {leaderboard_data} için {display_category_name}")
                self._update_add_run_button_state()
        except Exception as e:
            logger.error(f"handle_add_result'ta beklenmeyen bir hata oluştu: {e}", exc_info=True)
            self.show_status_message(self.translator.get_string('error_adding_record_general').format(e=e), is_error=True)
            self._update_add_run_button_state()

    def _extract_player_info(self, run_obj, leaderboard_data):
        """
        Koşu ve liderlik tablosu verilerinden oyuncu adlarını ve web bağlantılarını çıkarır.

        Argümanlar:
            run_obj (dict): Koşu nesnesi.
            leaderboard_data (dict): Liderlik tablosu verileri.

        Döndürür:
            tuple: Oyuncu adları ve web bağlantılarının listelerini içeren bir demet.
        """
        player_names = []
        player_weblinks = []
        
        players_data_embed = leaderboard_data.get('data', {}).get('players', {}).get('data', [])

        # Oyuncu ID'lerini ayrıntılı bilgilerine hızlı erişim için bir sözlük oluştur
        player_id_map = {}
        if isinstance(players_data_embed, list):
            for p_data in players_data_embed:
                if isinstance(p_data, dict) and p_data.get('id'):
                    player_id_map[p_data['id']] = p_data

        if isinstance(run_obj.get('players'), list):
            for run_player_id_obj in run_obj.get('players', []):
                if isinstance(run_player_id_obj, dict):
                    if run_player_id_obj.get('rel') == 'user':
                        player_id_to_find = run_player_id_obj.get('id')
                        if player_id_to_find and player_id_to_find in player_id_map:
                            p_data = player_id_map[player_id_to_find]
                            player_names.append(p_data.get('names',{}).get('international', p_data.get('name', _.get_string('unknown_player'))))
                            player_weblinks.append(p_data.get('weblink'))
                        else:
                            logger.warning(f"_extract_player_info: {player_id_to_find} oyuncu ID'si gömülü oyuncu verilerinde bulunamadı.")
                            player_names.append(_.get_string('unknown_player_id_missing'))
                            player_weblinks.append(None) # ID eksikse, web bağlantısı da eksiktir
                    elif run_player_id_obj.get('rel') == 'guest':
                        player_names.append(run_player_id_obj.get('name', _.get_string('unknown_player')))
                        player_weblinks.append(None)
        return player_names, player_weblinks

    @staticmethod
    def format_time(total_seconds_float):
        """
        Toplam saniyeyi (float) insan tarafından okunabilir bir zaman dizesine biçimlendirir.

        Argümanlar:
            total_seconds_float (float): Biçimlendirilecek toplam saniye sayısı.

        Döndürür:
            str: Biçimlendirilmiş zaman dizesi.
        """
        if total_seconds_float == None:
            return _.get_string('not_available_abbr')
        try:
            total_seconds = float(total_seconds_float)

            # Çok küçük pozitif değerleri 0 olarak ele al (örn. "-0ms" durumlarını önlemek için).
            if total_seconds < 0.001 and total_seconds >= 0:
                return "0s"

            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int((total_seconds % 60))
            milliseconds = int((total_seconds - int(total_seconds)) * 1000)

            formatted_parts = []
            if hours > 0:
                formatted_parts.append(f"{hours}h") # Saatler için 'h' olarak değiştirildi
            if minutes > 0 or hours > 0:
                # Saat varsa dakikaları her zaman göster
                formatted_parts.append(f"{minutes:02d}m")
            if seconds >= 0:
                # Toplam süre sıfır değilse saniyeleri her zaman göster
                if total_seconds > 0 or milliseconds > 0: # Süre 0 değilse saniyelerin her zaman gösterildiğinden emin ol
                   formatted_parts.append(f"{seconds:02d}s")
            if milliseconds > 0: # Milisaniyeler varsa, toplam zamandan bağımsız olarak göster
                 formatted_parts.append(f"{milliseconds:03d}ms")

            return " ".join(formatted_parts) if formatted_parts else "0s"
        except (ValueError, TypeError):
            logger.error(f"format_time: Geçersiz zaman değeri '{total_seconds_float}'.", exc_info=True)
            return _.get_string('invalid_time')
    
    def on_sort_order_changed(self, index):
        """
        Sıralama açılır kutusundaki değişikliği işler.
        """
        # Bu fonksiyon artık doğrudan bir QComboBox ile kullanılmıyor, ancak gelecekteki kullanım için korunuyor.
        # Hamburger menüdeki yeni mantığı change_sort_order_from_menu kullanıyor.
        self.current_sort_order = self.sort_combo_box.currentData()
        self.settings_manager.save_settings(self.translator.current_language(), self.current_sort_order) # Yeni sıralama düzenini kaydet
        self.update_tracked_list_ui()

    def update_tracked_list_ui(self):
        """
        Takip edilen koşuların QListWidget'taki görüntüsünü geçerli sıralama düzenine göre günceller.
        """
        scroll_bar = self.tracked_list_widget.verticalScrollBar()
        old_scroll_position = scroll_bar.value() if scroll_bar else 0

        self.tracked_list_widget.clear()
        if not self.tracked_runs:
            # Liste temizlense bile kaydırma konumunu geri yükle
            if scroll_bar:
                scroll_bar.setValue(old_scroll_position)
            return

        # Seçilen kriterlere göre oyun ID'lerini sırala
        if self.current_sort_order == 'added_date_desc':
            sorted_game_ids = sorted(self.tracked_runs.keys(), 
                                     key=lambda gid: self.tracked_runs[gid].get('_added_timestamp', 0), 
                                     reverse=True)
        elif self.current_sort_order == 'game_name_asc':
            sorted_game_ids = sorted(self.tracked_runs.keys(),
                                     key=lambda gid: self.tracked_runs[gid].get('name', '').lower())
        else: # Beklenmeyen bir şey olursa added_date_desc'e varsayılan
            sorted_game_ids = sorted(self.tracked_runs.keys(), 
                                     key=lambda gid: self.tracked_runs[gid].get('_added_timestamp', 0), 
                                     reverse=True)


        for game_id in sorted_game_ids:
            game_data = self.tracked_runs.get(game_id)
            if not game_data:
                logger.warning(f"update_tracked_list_ui: {game_id} oyun kimliği için eksik veri.")
                continue

            # Her oyun için kategorileri gruplamak için bir QFrame oluştur
            game_frame = QFrame()
            game_frame.setObjectName("GameFrame")
            game_frame_layout = QVBoxLayout(game_frame)
            game_frame_layout.setContentsMargins(10, 10, 10, 10)
            game_frame_layout.setSpacing(5)

            game_name_with_year = game_data.get('name', _.get_string('unknown_game'))
            game_weblink = game_data.get('weblink')

            # Oyun adı düğmesi
            game_name_button = QPushButton(game_name_with_year)
            game_name_button.setObjectName("GameLinkButton")
            game_name_button.setCursor(Qt.PointingHandCursor)
            game_name_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            game_name_button.setFixedHeight(self.OPTIONS_BUTTON_SIZE)
            game_name_button.setFont(QFont("Roboto", self.GAME_HEADER_FONT_SIZE, QFont.Bold))
            game_name_button.setToolTip(_.get_string('open_speedrun_com_page').format(game_name=game_name_with_year))
            if game_weblink:
                game_name_button.clicked.connect(lambda _, link=game_weblink: webbrowser.open(link))
            else:
                game_name_button.setEnabled(False)

            # Oyun seçenekleri düğmesi (üç nokta)
            options_button = QPushButton("⋮")
            options_button.setFixedSize(QSize(self.OPTIONS_BUTTON_SIZE, self.OPTIONS_BUTTON_SIZE))
            options_button.setObjectName("OptionsButton")
            options_button.setToolTip(_.get_string('options'))
            options_button.clicked.connect(
                lambda _, data={'type': 'game_header', 'game_id': game_id}: self.show_options_menu(options_button, data)
            )

            # Oyun adı ve seçenekler düğmesi için iç düzen (QHBoxLayout)
            game_header_layout = QHBoxLayout()
            game_header_layout.setContentsMargins(0, 0, 0, 0)
            game_header_layout.setSpacing(2)
            game_header_layout.addStretch(1)
            game_header_layout.addWidget(game_name_button, alignment=Qt.AlignVCenter)
            game_header_layout.addWidget(options_button, alignment=Qt.AlignVCenter)
            game_header_layout.addStretch(1)

            game_frame_layout.addLayout(game_header_layout)

            # Bu oyun çerçevesine belirli sıralama ile kategori öğeleri ekle
            self._add_category_items_to_layout(game_id, game_data, game_frame_layout)

            game_frame.adjustSize()

            # Çerçeveyi QListWidget'a özel bir öğe olarak ekle
            frame_list_item = QListWidgetItem()
            frame_list_item.setSizeHint(game_frame.sizeHint())
            frame_list_item.setFlags(frame_list_item.flags() & ~Qt.ItemIsSelectable)
            self.tracked_list_widget.addItem(frame_list_item)
            self.tracked_list_widget.setItemWidget(frame_list_item, game_frame)

        # Kaydırma konumunu geri yükle
        if scroll_bar:
            # Eski kaydırma konumunu yeni maksimuma sıkıştır
            max_scroll = scroll_bar.maximum()
            scroll_bar.setValue(min(old_scroll_position, max_scroll))

    def _create_category_item_widget(self, category_data, category_key, current_game_id, current_level_id=None, current_level_name=None, item_type='full_game'):
        """
        Takip edilen liste için tek bir kategori öğesi widget'ı oluşturur.
        Bu, _add_category_items_to_layout'tan çağrılan bir yardımcı fonksiyondur.
        """
        category_display_name = category_data.get('display_name', category_data.get('name', _.get_string('unknown_category')))
        formatted_time = self.format_time(category_data.get('current_record_time'))

        runners = category_data.get('current_runners', [_.get_string('unknown_player')])
        runner_weblinks = category_data.get('player_weblinks', [None] * len(runners))

        weblink = category_data.get('weblink', '#')
        date_completed = category_data.get('date_completed', _.get_string('not_available_abbr')) # Buradan parantezler kaldırıldı
        splits_data_for_dialog = category_data.get('splits', [])
        
        original_category_id = category_key.split('-')[0] 
        selected_variables_for_this_run = category_data.get('variables', {})

        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(10)

        item_widget.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                min-height: {self.OPTIONS_BUTTON_SIZE}px;
            }}
            QLabel {{
                font-family: "Roboto", "Segoe UI", sans-serif;
                font-size: {self.BASE_ITEM_FONT_SIZE}px;
                color: #FFFFFF;
                font-weight: normal;
                padding: 0;
                margin: 0;
            }}
            QLabel#new_wr_label {{
                font-weight: normal;
                color: #FFD700; /* Altın */
                font-size: {self.BASE_ITEM_FONT_SIZE}px;
            }}
            QLabel.dot_separator {{
                font-weight: bold;
                color: #FFFFFF;
                padding: 0;
                margin: 0;
            }}
            QLabel#DateLabel {{
                color: #FFFFFF;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
                font-family: "Roboto", "Segoe UI", sans-serif;
                font-size: {self.BASE_ITEM_FONT_SIZE}px;
                font-weight: normal;
                text-align: left;
            }}
            QPushButton#RunnerLinkButton {{
                font-weight: bold;
                color: #FFFFFF;
            }}
            QPushButton#RunnerLinkButton:hover {{
                color: #DDDDDD;
            }}
            QPushButton#RunnerLinkButton:pressed {{
                color: #BBBBBB;
            }}
            QPushButton#TimeButton {{
                font-weight: normal;
                color: #FFFFFF;
                text-align: right;
            }}
            QPushButton#TimeButton:hover {{
                color: #DDDDDD;
            }}
            QPushButton#TimeButton:pressed {{
                color: #BBBBBB;
            }}
            QPushButton#MoreRunnersButton {{
                color: #FFFFFF;
            }}
            QPushButton#MoreRunnersButton:hover, QPushButton#MoreRunnersButton:pressed {{
                color: #DDDDDD;
            }}
            QPushButton#OptionsButton {{
                background-color: transparent;
                border: none;
                border-radius: 18px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: {self.OPTIONS_BUTTON_FONT_SIZE}px;
                min-width: {self.OPTIONS_BUTTON_SIZE}px;
                max-width: {self.OPTIONS_BUTTON_SIZE}px;
                min-height: {self.OPTIONS_BUTTON_SIZE}px;
                max-height: {self.OPTIONS_BUTTON_SIZE}px;
                padding: 0px;
                text-align: center;
            }}
            QPushButton#OptionsButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QPushButton#OptionsButton:pressed {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
        """)

        if category_data.get('is_new_record_broken', False):
            new_wr_label = QLabel(_.get_string('new_wr_label'))
            new_wr_label.setObjectName("new_wr_label")
            item_layout.addWidget(new_wr_label, alignment=Qt.AlignVCenter)

        category_name_actual_label = QLabel(category_display_name)
        category_name_actual_label.setObjectName("category_name_label")
        category_name_actual_label.setWordWrap(True)
        category_name_actual_label.setFont(QFont("Roboto", self.BASE_ITEM_FONT_SIZE)) # Yazı tipini açıkça ayarla
        item_layout.addWidget(category_name_actual_label, 5, alignment=Qt.AlignVCenter)

        time_button = QPushButton(formatted_time)
        time_button.setObjectName("TimeButton")
        time_button.setCursor(Qt.PointingHandCursor)
        time_button.setFont(QFont("Roboto", self.BASE_ITEM_FONT_SIZE)) # Yazı tipini açıkça ayarla
        time_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        if weblink and weblink != '#':
            time_button.clicked.connect(lambda _, url=weblink: webbrowser.open(url))
            time_button.setToolTip(_.get_string('speedrun_link_tooltip'))
        else:
            time_button.setEnabled(False)
            time_button.setToolTip(_.get_string('speedrun_profile_link_not_available'))
        
        item_layout.addItem(QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum))
        item_layout.addWidget(time_button, alignment=Qt.AlignVCenter)

        runners_date_container_layout = QHBoxLayout()
        runners_date_container_layout.setContentsMargins(0, 0, 0, 0)
        runners_date_container_layout.setSpacing(1)
        runners_date_container_layout.addStretch(1)
        runners_date_container_layout.setAlignment(Qt.AlignVCenter)

        for i, runner_name in enumerate(runners):
            if i < self.MAX_DISPLAY_RUNNERS:
                if i > 0:
                    dot_label = QLabel(" • ")
                    dot_label.setObjectName("dot_separator")
                    dot_label.setFont(QFont("Roboto", self.BASE_ITEM_FONT_SIZE)) # Yazı tipini açıkça ayarla
                    dot_label.setStyleSheet("margin-top: 0px;") # Hizalama ayarlandı
                    runners_date_container_layout.addWidget(dot_label, alignment=Qt.AlignVCenter)

                runner_weblink = runner_weblinks[i] if i < len(runner_weblinks) else None

                if runner_weblink:
                    runner_button = QPushButton(runner_name)
                    runner_button.setObjectName("RunnerLinkButton")
                    runner_button.setToolTip(_.get_string('open_profile_tooltip').format(runner_name=runner_name))
                    runner_button.setCursor(Qt.PointingHandCursor)
                    runner_button.setFont(QFont("Roboto", self.BASE_ITEM_FONT_SIZE)) # Yazı tipini açıkça ayarla
                    runner_button.clicked.connect(lambda _, link=runner_weblink: webbrowser.open(link))
                    runners_date_container_layout.addWidget(runner_button, alignment=Qt.AlignVCenter)
                else:
                    runner_label = QLabel(runner_name)
                    runner_label.setFont(QFont("Roboto", self.BASE_ITEM_FONT_SIZE)) # Yazı tipini açıkça ayarla
                    runners_date_container_layout.addWidget(runner_label, alignment=Qt.AlignVCenter)
            else:
                break

        remaining_runners = len(runners) - self.MAX_DISPLAY_RUNNERS
        if remaining_runners > 0:
            # Önde gösterilen koşucular varsa "daha fazla" düğmesinden önce nokta ekle
            if self.MAX_DISPLAY_RUNNERS > 0 and len(runners) > self.MAX_DISPLAY_RUNNERS:
                dot_label_more = QLabel(" • ")
                dot_label_more.setObjectName("dot_separator")
                dot_label_more.setFont(QFont("Roboto", self.BASE_ITEM_FONT_SIZE)) # Yazı tipini açıkça ayarla
                dot_label_more.setStyleSheet("margin-top: 0px;") # Hizalama ayarlandı
                runners_date_container_layout.addWidget(dot_label_more, alignment=Qt.AlignVCenter)

            more_button = QPushButton(_.get_string('more_runners_button').format(count=remaining_runners))
            more_button.setObjectName("MoreRunnersButton")
            more_button.setCursor(Qt.PointingHandCursor)
            more_button.setFont(QFont("Roboto", self.BASE_ITEM_FONT_SIZE)) # Yazı tipini açıkça ayarla
            more_button.clicked.connect(lambda _, r_names=runners, r_links=runner_weblinks: self.show_all_runners_dialog(category_display_name, r_names, r_links))
            runners_date_container_layout.addWidget(more_button, alignment=Qt.AlignVCenter)

        runners_date_container_layout.addSpacing(10)

        # date_completed'ı olduğu gibi kullanıyoruz, burada parantez eklemiyoruz
        date_label = QLabel(f"{date_completed}") # Buraya parantez ekle
        date_label.setObjectName("DateLabel")
        date_label.setFont(QFont("Roboto", self.BASE_ITEM_FONT_SIZE)) # Yazı tipini açıkça ayarla
        date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        runners_date_container_layout.addWidget(date_label, alignment=Qt.AlignVCenter)

        item_layout.addLayout(runners_date_container_layout, 1)

        options_button = QPushButton("⋮")
        options_button.setFixedSize(QSize(self.OPTIONS_BUTTON_SIZE, self.OPTIONS_BUTTON_SIZE))
        options_button.setObjectName("OptionsButton")
        options_button.setToolTip(_.get_string('options_button_tooltip'))
        options_button.clicked.connect(
            lambda _, data=
            {
                'game_id': current_game_id,
                'category_key': category_key,
                'original_category_id': original_category_id,
                'level_id': current_level_id,
                'type': item_type,
                'weblink': weblink,
                'splits': splits_data_for_dialog,
                'current_runners': runners,
                'player_weblinks': runner_weblinks,
                'category_name': category_display_name,
                'is_new_record_broken': category_data.get('is_new_record_broken', False),
                'selected_variables_for_this_run': selected_variables_for_this_run
            }: self.show_options_menu(options_button, data)
        )
        item_layout.addWidget(options_button, alignment=Qt.AlignVCenter)

        item_widget.adjustSize()
        return item_widget


    def _add_category_items_to_layout(self, game_id, game_data, parent_layout):
        """
        Ana, Miscellaneous ve IL kategorileri için özel sıralama ile bir düzene
        kategoriye özgü widget'lar oluşturmak ve eklemek için yardımcı fonksiyon.

        Argümanlar:
            game_id (str): Oyunun kimliği.
            game_data (dict): Oyun verileri.
            parent_layout (QVBoxLayout): Widget'ların ekleneceği ana düzen.
        """
        main_category_widgets = []
        misc_category_widgets = []
        il_category_widgets = []

        # Tam Oyun Kategorilerini İşle
        if game_data.get('full_game_categories'):
            # Ana/Misc içinde tutarlı alfabetik sıralama sağlamak için anahtarları sırala
            sorted_fg_category_keys = sorted(game_data['full_game_categories'].keys(),
                                             key=lambda c_key: game_data['full_game_categories'][c_key].get('display_name', '').lower())
            for category_key in sorted_fg_category_keys:
                category_data = game_data['full_game_categories'].get(category_key)
                if category_data:
                    item_widget = self._create_category_item_widget(category_data, category_key, game_id, item_type='full_game')
                    # category_data'da depolanan 'is_miscellaneous' bayrağını kontrol et
                    if category_data.get('is_miscellaneous', False): 
                        misc_category_widgets.append(item_widget)
                    else:
                        main_category_widgets.append(item_widget)

        # Bireysel Seviye (IL) kategorilerini işle
        if game_data.get('levels'):
            # Seviyeleri isme göre alfabetik olarak sırala
            sorted_level_ids = sorted(game_data['levels'].keys(), key=lambda lid: game_data['levels'][lid].get('name', '').lower())
            for level_id in sorted_level_ids:
                level_data = game_data['levels'].get(level_id)
                if not level_data:
                    continue

                if level_data.get('categories'):
                    # Seviye içindeki IL kategorilerini alfabetik olarak sırala
                    sorted_il_category_keys = sorted(level_data['categories'].keys(),
                                                    key=lambda c_key: level_data['categories'][c_key].get('display_name', '').lower())
                    for category_key, category_data in level_data['categories'].items(): # Corrected iteration
                        if category_data:
                            item_widget = self._create_category_item_widget(category_data, category_key, game_id, current_level_id=level_id, current_level_name=level_data.get('name'), item_type='il')
                            il_category_widgets.append(item_widget)

        # Kategorileri ebeveyn_düzenine istenen sırayla ekle: Ana, Miscellaneous, IL
        for widget in main_category_widgets:
            parent_layout.addWidget(widget)
        for widget in misc_category_widgets:
            parent_layout.addWidget(widget)
        for widget in il_category_widgets:
            parent_layout.addWidget(widget)


    def show_options_menu(self, button, data):
        """
        Takip edilen oyunlar veya koşular için eylemler içeren bir bağlam menüsü görüntüler.

        Argümanlar:
            button (QPushButton): Menüyü tetikleyen düğme.
            data (dict): Seçilen öğe ile ilgili veriler.
        """
        menu = QMenu(self)

        item_type = data.get('type')

        if item_type == 'game_header':
            # Oyun seviyesi seçenekleri
            remove_game_action = menu.addAction(self.translator.get_string('options_menu_remove_game'))
            remove_game_action.triggered.connect(lambda: self.delete_tracked_game(data.get('game_id')))
        else:
            # Kategori/Koşu seviyesi seçenekleri
            view_splits_action = menu.addAction(self.translator.get_string('options_menu_view_splits'))
            view_splits_action.triggered.connect(lambda: self.view_splits_details_from_data(data))

            open_run_link_action = menu.addAction(self.translator.get_string('options_menu_open_run_page'))
            open_run_link_action.triggered.connect(lambda: self._open_weblink(data.get('weblink'), self.translator.get_string('web_link_not_available').format(item_type="record")))

            # 'Aynı Kategorideki Diğer Koşuları Görüntüle' için yeni düğme ekle
            view_other_runs_action = menu.addAction(self.translator.get_string('options_menu_open_other_runs'))
            view_other_runs_action.triggered.connect(lambda: self.show_other_runs_dialog(data))


            # "Koşu Sayfasını Aç"tan sonra "Okundu Olarak İşaretle" eylemini ekle
            if data.get('is_new_record_broken', False):
                mark_as_read_action = menu.addAction(self.translator.get_string('options_menu_mark_as_read'))
                mark_as_read_action.triggered.connect(
                    lambda: self.mark_run_as_read(data.get('game_id'), data.get('category_key'), data.get('level_id'), data.get('type'))
                )

            player_weblinks = data.get('player_weblinks', [])
            current_runners = data.get('current_runners', [])

            if player_weblinks and current_runners:
                menu.addSeparator() # Oyuncu profillerinden önce ayırıcı
                for i, player_weblink in enumerate(player_weblinks):
                    if player_weblink and i < len(current_runners):
                        player_name = current_runners[i]
                        action = menu.addAction(self.translator.get_string('options_menu_open_player_profile').format(player_name=player_name))
                        action.triggered.connect(lambda _, link=player_weblink: self._open_weblink(link, self.translator.get_string('web_link_not_available').format(item_type="player")))

            menu.addSeparator() # "Takibi Bırak"tan önce ayırıcı
            remove_action = menu.addAction(self.translator.get_string('options_menu_remove_run'))
            remove_action.triggered.connect(lambda: self.delete_tracked_run(data.get('game_id'), data.get('category_key'), data.get('level_id'), data.get('type')))

        # Menüyü geçerli imleç konumunda aç
        menu.exec_(QCursor.pos())

    def show_other_runs_dialog(self, data):
        """
        Aynı kategori ve değişkenlerdeki diğer tüm koşuları görüntülemek için bir iletişim kutusu açar.
        Argümanlar:
            data (dict): Kategori ve koşu ile ilgili veriler.
        """
        game_id = data.get('game_id')
        original_category_id = data.get('original_category_id') # API çağrısı için bunu kullan
        level_id = data.get('level_id')
        category_name = data.get('category_name')
        selected_variables_for_this_run = data.get('selected_variables_for_this_run', {})

        game_name = self.translator.get_string("unknown_game")
        if game_id and game_id in self.tracked_runs:
            game_name = self.tracked_runs[game_id].get('name', self.translator.get_string("unknown_game"))

        dialog_title = f"{game_name} - {category_name}"

        all_runs_dialog = AllRunsDialog(game_id, original_category_id, level_id, selected_variables_for_this_run, dialog_title, parent=self)
        all_runs_dialog.exec_()


    def _open_weblink(self, url, error_message):
        """
        Verilen URL'yi varsayılan web tarayıcısında açar.

        Argümanlar:
            url (str): Açılacak URL.
            error_message (str): URL geçerli değilse görüntülenecek hata mesajı.
        """
        if url and url != '#':
            try:
                webbrowser.open(url)
            except Exception as e:
                logger.error(f"Web bağlantısı açılırken hata oluştu: {url} - {e}", exc_info=True)
                self.show_status_message(self.translator.get_string('web_link_open_failed'), is_error=True)
        else:
            self.show_status_message(error_message, is_error=True)

    def view_splits_details_from_data(self, data):
        """
        Bir koşunun segment detaylarıyla SplitsDialog'u görüntüler.

        Argümanlar:
            data (dict): Koşu ile ilgili veriler.
        """
        splits_data = data.get('splits', [])
        if not isinstance(splits_data, list):
            splits_data = []
            logger.warning(f"view_splits_details_from_data: Beklenmeyen bölme verileri biçimi. Boş liste kullanılıyor.")

        game_id = data.get('game_id')
        cat_name = data.get('category_name')

        game_name = self.translator.get_string("unknown_game")
        if game_id and game_id in self.tracked_runs:
             game_name = self.tracked_runs[game_id].get('name', self.translator.get_string("unknown_game"))
        else:
            logger.error(f"view_splits_details_from_data: {game_id} oyun kimliği takip edilen öğelerde bulunamadı.")
            self.show_status_message(self.translator.get_string('game_info_not_retrieved'), is_error=True)
            return

        dialog_title = f"{game_name} - {cat_name}"
        
        splits_dialog = SplitsDialog(splits_data, run_title=dialog_title, parent=self)
        splits_dialog.exec_()

    def show_all_runners_dialog(self, run_display_name, all_runners, all_weblinks):
        """
        Bir koşu için tüm koşucuların listesiyle AllRunnersDialog'u görüntüler.

        Argümanlar:
            run_display_name (str): Koşunun görünen adı.
            all_runners (list): Tüm koşucu adlarının bir listesi.
            all_weblinks (list): Tüm koşucu web bağlantılarının bir listesi.
        """
        if not isinstance(all_runners, list) or not isinstance(all_weblinks, list):
            logger.error(f"show_all_runners_dialog: Koşucular veya web bağlantıları listesi için geçersiz tür. Koşucular: {type(all_runners)}, Web bağlantıları: {type(all_weblinks)}")
            self.show_status_message(self.translator.get_string('error_fetching_runner_info'), is_error=True)
            return

        runners_dialog = AllRunnersDialog(run_display_name, all_runners, all_weblinks, parent=self)
        runners_dialog.exec_()

    def delete_tracked_run(self, game_id, category_key, level_id, run_type):
        """
        Depolanan verilerden belirli bir takip edilen koşuyu siler.

        Argümanlar:
            game_id (str): Oyunun kimliği.
            category_key (str): Kategorinin anahtarı.
            level_id (str): Seviyenin kimliği (IL koşuları için).
            run_type (str): Koşu türü ('full_game' veya 'il').
        """
        if game_id not in self.tracked_runs:
            self.show_status_message(self.translator.get_string('game_not_found_untrack').format(game_id=game_id), is_error=True)
            logger.warning(f"delete_tracked_run: {game_id} oyunu takip edilen öğelerde bulunamadı.")
            return

        game_entry = self.tracked_runs[game_id]

        if run_type == 'full_game':
            if category_key in game_entry.get('full_game_categories', {}):
                del game_entry['full_game_categories'][category_key]
                self.show_status_message(self.translator.get_string('untrack_run_success'))
            else:
                logger.warning(f"delete_tracked_run: Tam oyun kategorisi {category_key}, {game_id} oyununda bulunamadı.")
                self.show_status_message(self.translator.get_string('untrack_run_failed'), is_error=True)

        elif run_type == 'il' and level_id:
            if level_id in game_entry.get('levels', {}) and \
               category_key in game_entry['levels'][level_id].get('categories', {}):
                del game_entry['levels'][level_id]['categories'][category_key]
                self.show_status_message(self.translator.get_string('untrack_run_success'))
                # Seviyede daha fazla kategori kalmazsa, seviyeyi de sil
                if not game_entry['levels'][level_id].get('categories'):
                    del game_entry['levels'][level_id]
            else:
                logger.warning(f"delete_tracked_run: IL kategorisi {category_key}, {level_id} seviyesinde, {game_id} oyununda bulunamadı.")
                self.show_status_message(self.translator.get_string('untrack_run_failed'), is_error=True)
        else:
                logger.error(f"delete_tracked_run: Geçersiz koşu türü '{run_type}' veya {game_id} için eksik seviye ID'si.")
                self.show_status_message(self.translator.get_string('invalid_tracked_type'), is_error=True)
                return

        # Oyunun daha fazla kategorisi veya seviyesi yoksa, oyun girişini de sil
        if not game_entry.get('full_game_categories') and not game_entry.get('levels'):
            del self.tracked_runs[game_id]

        self.save_tracked_runs()
        self.update_tracked_list_ui()
        self._update_add_run_button_state()

    def delete_tracked_game(self, game_id):
        """
        Belirli bir oyun için takip edilen tüm koşuları siler.

        Argümanlar:
            game_id (str): Silinecek oyunun kimliği.
        """
        if game_id in self.tracked_runs:
            del self.tracked_runs[game_id]
            self.save_tracked_runs()
            self.update_tracked_list_ui()
            self.show_status_message(self.translator.get_string('game_removed_success'))
            self._update_add_run_button_state()
        else:
            self.show_status_message(self.translator.get_string('game_not_found_untrack').format(game_id=game_id), is_error=True)
            logger.warning(f"delete_tracked_game: {game_id} oyunu takip edilen öğelerde zaten bulunamadı.")

    def check_for_new_records(self):
        """
        Tüm takip edilen koşular için yeni dünya rekorlarını kontrol etmeyi başlatır.
        """
        if not self.tracked_runs:
            self.show_status_message(self.translator.get_string('no_records_to_track'), is_error=False)
            return

        self.refresh_button.setEnabled(False)
        self.timer.stop() # Manuel veya otomatik yenileme sırasında periyodik zamanlayıcıyı durdur

        # Etkin işçileri ve bekleyen API çağrıları sayaçlarını sıfırla
        self.active_check_workers = []
        self.pending_refresh_api_calls = 0
        self.show_status_message(self.translator.get_string('checking_for_new_records'))

        # Tüm takip edilen koşuları yinele ve her biri için API işçileri oluştur
        for game_id, game_data in self.tracked_runs.copy().items(): # Yineleme sırasında değişikliklere izin vermek için .copy() kullan
            for category_key, _ in game_data.get('full_game_categories', {}).copy().items():
                self._create_and_start_worker(game_id, category_key, None, 'full_game')

            for level_id, level_data_loop in game_data.get('levels', {}).copy().items():
                for category_key, _ in level_data_loop.get('categories', {}).copy().items():
                    self._create_and_start_worker(game_id, category_key, level_id, 'il')

        # Hiçbir API çağrısı başlatılmadıysa (örn. tracked_runs boşsa), düğmeleri etkinleştir
        if self.pending_refresh_api_calls == 0:
            self.refresh_button.setEnabled(True)
            self.timer.start()

    def _create_and_start_worker(self, game_id, category_key, level_id, run_type):
        """
        Belirli bir koşu için rekoru kontrol etmek üzere bir ApiWorker oluşturur ve başlatır.

        Argümanlar:
            game_id (str): Oyunun kimliği.
            category_key (str): Kategorinin anahtarı (kategori ID'si ve değişkenleri içerir).
            level_id (str): Seviyenin kimliği (IL koşuları için).
            run_type (str): Koşu türü ('full_game' veya 'il').
        """
        original_category_id = category_key.split('-')[0]
        variables_str = ""
        if '-' in category_key: # Varsa URL'ye değişkenleri ekle
            try:
                variables_dict_raw = category_key.split('-', 1)[1]
                parsed_vars = json.loads(variables_dict_raw)
                for var_id, var_value_id in parsed_vars.items():
                    variables_str += f"&var-{var_id}={var_value_id}"
            except json.JSONDecodeError as e:
                logger.error(f"_create_and_start_worker: Değişken anahtarı ayrıştırılırken JSONDecodeError oluştu: {category_key}: {e}", exc_info=True)
                return

        # Koşu türüne (tam oyun veya bireysel seviye) göre API URL'sini oluştur
        if run_type == 'full_game':
            url = f"https://www.speedrun.com/api/v1/leaderboards/{game_id}/category/{original_category_id}?top=1&embed=players,segments{variables_str}"
        else: # 'il'
            url = f"https://www.speedrun.com/api/v1/leaderboards/{game_id}/level/{level_id}/{original_category_id}?top=1&embed=players,segments{variables_str}"

        worker = ApiWorker(url)
        worker.finished.connect(
            lambda data, req_id, g_id=game_id, c_key=category_key, l_id=level_id, rt=run_type:
                self.handle_record_check_result(data, g_id, c_key, l_id, rt)
        )
        worker.error.connect(self.handle_api_error)
        worker.worker_completed.connect(self.on_worker_completed) # worker_completed sinyalini bağla
        self.active_check_workers.append(worker)
        self.pending_refresh_api_calls += 1
        worker.start()

    def handle_record_check_result(self, leaderboard_data, game_id, category_key, level_id, run_type):
        """
        Yeni bir dünya rekoru olup olmadığını kontrol eden bir API çağrısının sonucunu işler.

        Argümanlar:
            leaderboard_data (dict): API'den döndürülen liderlik tablosu verileri.
            game_id (str): Oyunun kimliği.
            category_key (str): Kategorinin anahtarı.
            level_id (str): Seviyenin kimliği (IL koşuları için).
            run_type (str): Koşu türü ('full_game' veya 'il').
        """
        try:
            # API çağrısı sırasında oyunun kaldırılıp kaldırılmadığını kontrol et
            if game_id not in self.tracked_runs:
                logger.warning(f"handle_record_check_result: {game_id} oyunu API yanıtı beklenirken kaldırıldı veya bulunamadı. İşlem iptal edildi.")
                return

            game_data = self.tracked_runs[game_id]
            current_tracked_run_data = None

            if run_type == 'full_game':
                current_tracked_run_data = game_data.get('full_game_categories', {}).get(category_key)
            elif run_type == 'il':
                level_entry = game_data.get('levels', {}).get(level_id)
                if level_entry:
                    current_tracked_run_data = level_entry.get('categories', {}).get(category_key)

            if not current_tracked_run_data:
                logger.warning(f"handle_record_check_result: Takip edilen koşu verileri bulunamadı: oyun {game_id}, seviye {level_id}, kategori {category_key}, tür {run_type}. Veriler güncellenmedi.")
                return

            run_identifier_for_msg = self._get_run_identifier_for_msg(game_data, current_tracked_run_data, level_id)

            old_record_time = current_tracked_run_data.get('current_record_time')
            if old_record_time == None:
                logger.warning(self.translator.get_string('old_record_time_missing').format(run_identifier=run_identifier_for_msg))
                return

            new_record_run_obj = self._get_new_record_run_obj(leaderboard_data)

            if new_record_run_obj:
                new_record_time_seconds = new_record_run_obj.get('times', {}).get('primary_t')

                if new_record_time_seconds == None: # Corrected from '==='
                    logger.warning(self.translator.get_string('new_record_time_missing').format(run_identifier=run_identifier_for_msg))
                    return

                # If a new, faster record is found
                if new_record_time_seconds < old_record_time:
                    current_tracked_run_data['current_record_time'] = new_record_time_seconds
                    current_tracked_run_data['weblink'] = new_record_run_obj.get('weblink')
                    current_tracked_run_data['date_completed'] = new_record_run_obj.get('date', _.get_string('not_available_abbr'))
                    current_tracked_run_data['current_runners'], current_tracked_run_data['player_weblinks'] = \
                        self._extract_player_info(new_record_run_obj, leaderboard_data)
                    current_tracked_run_data['splits'] = leaderboard_data.get('data', {}).get('segments', [])
                    current_tracked_run_data['is_new_record_broken'] = True # Set New WR flag
                    self.has_unseen_new_wrs = True

                    self.save_tracked_runs()
                    self.update_tracked_list_ui()

                    # Show relevant buttons if new WRs are detected
                    self.show_last_record_button.setVisible(True)
                    self.clear_new_wr_button.setVisible(True)

                    # Add new broken record to history
                    new_broken_record_info = self._create_broken_record_info(game_data, current_tracked_run_data,
                                                                             game_data.get('levels', {}).get(level_id))
                    self.broken_records_history.append(new_broken_record_info)
                    self.show_status_message(self.translator.get_string('new_wr_detected').format(run_identifier=run_identifier_for_msg))
            else:
                logger.warning(f"handle_record_check_result: API response unexpected or empty: {leaderboard_data} for {run_identifier_for_msg}")

        except Exception as e:
            logger.error(f"An unexpected error occurred in handle_record_check_result: {e}", exc_info=True)
            self.show_status_message(self.translator.get_string('api_error_general').format(error_message=e), is_error=True)

    def _get_new_record_run_obj(self, leaderboard_data):
        """
        Extracts the top run object from the leaderboard data.

        Args:
            leaderboard_data (dict): The leaderboard data.

        Returns:
            dict or None: The top run object, or None if not found.
        """
        if leaderboard_data and isinstance(leaderboard_data, dict):
            data_key = leaderboard_data.get('data')
            if data_key and isinstance(data_key, dict):
                runs_list = data_key.get('runs')
                if runs_list and isinstance(runs_list, list) and len(runs_list) > 0:
                    run_entry = runs_list[0].get('run')
                    if run_entry and isinstance(run_entry, dict):
                        return run_entry
        return None

    def _get_run_identifier_for_msg(self, game_data, category_data, level_id):
        """
        Constructs a descriptive name for the run for status messages.

        Args:
            game_data (dict): The game data.
            category_data (dict): The category data.
            level_id (str): The ID of the level.

        Returns:
            str: A descriptive name for the run.
        """
        level_name_part = f"{game_data.get('levels', {}).get(level_id, {}).get('name', _.get_string('unknown_level'))}: " if level_id else ""
        return f"'{level_name_part}{category_data.get('display_name', _.get_string('unknown_category'))}'"

    def _create_broken_record_info(self, game_data, category_data, level_data=None):
        """
        Creates an information dictionary for the broken records history.

        Args:
            game_data (dict): The game data.
            category_data (dict): The category data.
            level_data (dict, optional): The level data. Defaults to None.

        Returns:
            dict: The broken record information.
        """
        game_name = game_data.get('name', _.get_string('unknown_game'))
        level_name = level_data.get('name', None) if level_data else None
        category_display_name = category_data.get('display_name', _.get_string('unknown_category'))

        return {
            'game_name': game_name,
            'level_name': level_name,
            'category_display_name': category_display_name,
            'formatted_new_time': self.format_time(category_data.get('current_record_time')),
            # Corrected: Store only player names, without a language-specific prefix
            'new_player_name': ', '.join(category_data.get('current_runners', [_.get_string('unknown_player')])),
            'new_run_date': f"({category_data.get('date_completed', _.get_string('not_available_abbr'))})",
            'weblink': category_data.get('weblink')
        }

    def handle_api_error(self, error_message):
        """
        Handles API errors by displaying a status message and managing thread states.

        Args:
            error_message (str): The error message.
        """
        sender_worker = self.sender()
        if sender_worker:
            # Call remove() before checking if the item is in the list
            if sender_worker in self.active_check_workers:
                self.active_check_workers.remove(sender_worker)

            # This is part of the refresh logic, so decrement the counter
            if self.pending_refresh_api_calls > 0:
                 self.pending_refresh_api_calls -= 1

            if self.pending_refresh_api_calls <= 0:
                self.pending_refresh_api_calls = 0
                self.refresh_button.setEnabled(True)
                if not self.timer.isActive():
                    self.timer.start()

        error_context = ""
        if hasattr(sender_worker, 'url'):
            if "games?name=" in sender_worker.url:
                error_context = self.translator.get_string('api_error_search_context')
                self.search_button.setEnabled(True)
                self.search_button.setText(self.translator.get_string('search_button'))
            elif "leaderboards/" in sender_worker.url:
                error_context = self.translator.get_string('api_error_record_check_context')
            elif "/categories" in sender_worker.url or "/levels/" in sender_worker.url:
                error_context = self.translator.get_string('api_error_category_level_context')
                # If this is a category/variable fetch error, re-enable the lists
                self.category_list_widget.setEnabled(True)
                self.variables_list_widget.setEnabled(True)


        full_message = f"{self.translator.get_string('api_error_general_prefix')}: {error_context} {error_message}".strip()
        self.show_status_message(full_message, is_error=True)

    def on_worker_completed(self):
        """
        Callback function when an ApiWorker task is completed.
        """
        if self.pending_refresh_api_calls > 0:
            self.pending_refresh_api_calls -= 1

        # When all pending API calls are completed, enable buttons and restart timer
        if self.pending_refresh_api_calls <= 0:
            self.pending_refresh_api_calls = 0
            if self.refresh_button:
                self.refresh_button.setEnabled(True)
            if self.timer and not self.timer.isActive():
                self.timer.start()

    def on_category_variables_worker_completed(self):
        """
        Specific completion handler for category and variable loading threads.
        Re-enables the category and variable list widgets.
        """
        self.category_list_widget.setEnabled(True)
        self.variables_list_widget.setEnabled(True)

    def show_last_record_notification(self):
        """
        Displays the LastRecordDialog with the history of broken records.
        """
        last_record_dialog = LastRecordDialog(self.broken_records_history, parent=self)
        last_record_dialog.exec_()

    def mark_all_new_wrs_as_read(self):
        """
        Marks all new world records as "read" and clears their flags.
        """
        for game_id, game_data in self.tracked_runs.items():
            for category_key, category_data in game_data.get('full_game_categories', {}).items():
                category_data['is_new_record_broken'] = False
            for level_id, level_data in game_data.get('levels', {}).items():
                for category_key, category_data in level_data.get('categories', {}).items():
                    category_data['is_new_record_broken'] = False

        self.broken_records_history = [] # Clear history
        self.has_unseen_new_wrs = False # Reset flag

        self.save_tracked_runs()
        self.update_tracked_list_ui() # Update the UI

        self.show_last_record_button.setVisible(False)
        self.clear_new_wr_button.setVisible(False)

        self.show_status_message(self.translator.get_string('all_marked_as_read'))

    def mark_run_as_read(self, game_id, category_key, level_id, run_type):
        """
        Marks a specific 'New WR' run as read, clears its flag, and updates the UI.

        Args:
            game_id (str): The ID of the game.
            category_key (str): The key of the category.
            level_id (str): The ID of the level (for IL runs).
            run_type (str): The type of run ('full_game' or 'il').
        """
        if game_id not in self.tracked_runs:
            self.show_status_message(self.translator.get_string('run_mark_read_failed').format(run_data="game not found"), is_error=True)
            logger.warning(f"mark_run_as_read: Game {game_id} not found in tracked runs.")
            return

        target_run_data = None
        if run_type == 'full_game':
            target_run_data = self.tracked_runs[game_id].get('full_game_categories', {}).get(category_key)
        elif run_type == 'il' and level_id:
            level_entry = self.tracked_runs[game_id].get('levels', {}).get(level_id)
            if level_entry:
                target_run_data = level_entry.get('categories', {}).get(category_key)

        if target_run_data:
            if target_run_data.get('is_new_record_broken', False):
                target_run_data['is_new_record_broken'] = False
                self.show_status_message(self.translator.get_string('run_marked_as_read'))
            else:
                self.show_status_message(self.translator.get_string('run_already_marked_read'), is_error=False)
                return # No need to proceed if already read

            # Remove from broken_records_history
            identifier_to_remove = self._get_run_identifier_for_msg(
                self.tracked_runs[game_id], target_run_data, level_id
            )
            # Filter broken records history, keeping records that do not match the one being marked.
            # Create a new list by retaining records that do not match the identifier.
            self.broken_records_history = [
                rec for rec in self.broken_records_history
                if self._get_run_identifier_for_msg(
                    {'name': rec['game_name']}, # Mock game_data for comparison
                    {'display_name': rec['category_display_name']}, # Mock category_data for comparison
                    rec.get('level_name') # Pass level_name if present
                ) != identifier_to_remove
            ]

            # Re-evaluate self.has_unseen_new_wrs based on remaining new WRs
            self.has_unseen_new_wrs = any(
                c_data.get('is_new_record_broken', False)
                for g_data in self.tracked_runs.values()
                for c_data in g_data.get('full_game_categories', {}).values()
            ) or any(
                c_data_il.get('is_new_record_broken', False)
                for g_data in self.tracked_runs.values()
                for l_data in g_data.get('levels', {}).values()
                for c_data_il in l_data.get('categories', {}).values()
            )

            self.show_last_record_button.setVisible(self.has_unseen_new_wrs)
            self.clear_new_wr_button.setVisible(self.has_unseen_new_wrs)

            self.save_tracked_runs()
            self.update_tracked_list_ui()
            self._update_add_run_button_state()
        else:
            self.show_status_message(self.translator.get_string('run_mark_read_failed').format(run_data="run data not found"), is_error=True)
            logger.warning(f"mark_run_as_read: Target run data not found: game {game_id}, level {level_id}, category {category_key}, type {run_type}.")

    def show_status_message(self, message, is_error=False):
        """
        Displays a temporary status message to the user.

        Args:
            message (str): The message to display.
            is_error (bool): Whether the message is an error message. If True, shown in pink, otherwise green.
        """
        self.status_label.setText(message)
        if is_error:
            self.status_label.setStyleSheet("color: #FF69B4;") # Pink for errors
        else:
            self.status_label.setStyleSheet("color: #4CAF50;") # Green for success

        QTimer.singleShot(5000, lambda: self.status_label.setText("")) # Clear message after 5 seconds

    def closeEvent(self, event):
        """
        Event handler when the application is closed.
        Stops all active API workers to ensure a clean exit.

        Args:
            event (QCloseEvent): The close event.
        """
        for worker in self.active_check_workers:
            if worker.isRunning():
                worker.quit()
                worker.wait(1000) # Wait for thread to terminate (max 1 second)

        self.save_tracked_runs() # Save the current state of tracked runs
        # Settings are automatically saved on change, so no need for an explicit save here
        event.accept() # Accept the close event

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        window = SpeedrunTrackerApp()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Critical error occurred during application startup: {e}", exc_info=True)
        # Simplified print message for critical startup errors
        print(_.get_string("critical_startup_error"))

