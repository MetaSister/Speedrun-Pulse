# main_window.py
# Bu dosya, uygulamanın ana penceresi olan SpeedrunPulseApp sınıfını ve tüm ana mantığı içerir.

import sys
import requests
import json
import os
import webbrowser
import time
import math
from collections import deque

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QHBoxLayout, QSizePolicy, QMenu, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QCursor

# Modüler içe aktarmalar
from config import *
# DEĞİŞİKLİK: 'load_json_file' artık 'file_handler'dan, diğerleri 'utils'dan geliyor.
from file_handler import load_json_file
from utils import format_time, format_time_delta
from localization import _
from settings import SettingsManager
from api_client import ApiWorker
from ui_components import LastRecordDialog, AllRunsDialog

class SpeedrunPulseApp(QWidget):
    def __init__(self):
        super().__init__()
        self.theme = load_json_file(THEME_FILE)
        self.settings_manager = SettingsManager()
        initial_settings = self.settings_manager.load_settings()
        self.translator = _
        self.translator.set_language(initial_settings.get('language', 'en'))
        
        self.tracked_runs = {}
        self.save_file = TRACKED_RUNS_FILE
        
        self.selected_game_data = {}
        self.selected_level_data = {}
        self.selected_category_data = {}
        self.selected_variable_values = {}
        
        self.full_game_data_cache = None
        self.available_subcategory_variables = []
        
        self.broken_records_history = []
        self.has_unseen_new_wrs = False
        
        self.current_request_id = 0
        
        self.current_sort_order = initial_settings.get('sort_order', 'added_date_desc')
        self.is_checking_records = False
        self.ui_update_needed_after_check = False
        
        self.result_queue = deque()
        self.save_dirty_flag = False
        
        self.active_workers = set()
        self.record_check_queue = deque()
        self.record_check_workers = set()
        
        self.checked_runs_count = 0
        self.total_runs_to_check = 0
        self.all_workers_finished_check = False

        self.autocomplete_timer = QTimer(self)
        self.autocomplete_timer.setSingleShot(True)
        self.autocomplete_timer.timeout.connect(self.search_game_debounced)
        
        self.main_check_timer = QTimer(self)
        self.main_check_timer.timeout.connect(self.check_for_new_records)
        
        self.status_clear_timer = QTimer(self)
        self.status_clear_timer.setSingleShot(True)
        self.status_clear_timer.timeout.connect(self.clear_status_label)

        self.process_results_timer = QTimer(self)
        self.process_results_timer.setInterval(10) 
        self.process_results_timer.timeout.connect(self._process_result_queue)

        self.save_debounce_timer = QTimer(self)
        self.save_debounce_timer.setSingleShot(True)
        self.save_debounce_timer.setInterval(1000)
        self.save_debounce_timer.timeout.connect(self._save_if_dirty)

        self.is_initial_load = True
        
        self.init_ui()
        self._reset_all_selections()
        self.apply_material_style()
        self.load_tracked_runs()
        QTimer.singleShot(100, self.check_for_new_records)
        self.main_check_timer.start(300000)

    def init_ui(self):
        self.setWindowTitle(self.translator.get_string('app_title'))
        self.setGeometry(150, 150, 1200, 850)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)

        self.left_panel_widget = QWidget()
        left_layout = QVBoxLayout(self.left_panel_widget)
        left_layout.setContentsMargins(0,0,0,0)
        left_layout.setSpacing(12)
        
        search_and_menu_layout = QHBoxLayout()
        self.game_search_input = QLineEdit()
        self.game_search_input.setPlaceholderText(_.get_string('search_placeholder'))
        self.game_search_input.setMinimumHeight(40)
        self.game_search_input.textChanged.connect(self.start_autocomplete_timer)
        
        self.search_button = QPushButton(_.get_string('search_button'))
        self.search_button.setFixedSize(100, 40)
        self.search_button.clicked.connect(self.search_game)
        
        self.hamburger_button = QPushButton("≡")
        self.hamburger_button.setObjectName("HamburgerButton")
        self.hamburger_button.setToolTip(_.get_string('menu_options'))
        self.hamburger_button.setFixedSize(40, 40)
        self.hamburger_button.clicked.connect(self.show_options_menu_dialog)

        search_and_menu_layout.addWidget(self.game_search_input)
        search_and_menu_layout.addWidget(self.search_button)
        search_and_menu_layout.addWidget(self.hamburger_button)
        left_layout.addLayout(search_and_menu_layout)

        self.game_results_label = QLabel(_.get_string('game_list_label'))
        self.game_results_label.setObjectName("SectionHeader")
        self.game_results_list_widget = QListWidget()
        self.game_results_list_widget.setMinimumHeight(120)
        self.game_results_list_widget.itemClicked.connect(self.select_game_from_results)
        self.game_results_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.game_results_list_widget.customContextMenuRequested.connect(self.show_game_result_context_menu)
        
        self.level_label = QLabel(_.get_string('il_list_label'))
        self.level_label.setObjectName("SectionHeader")
        self.level_label.setVisible(False)
        self.level_list_widget = QListWidget()
        self.level_list_widget.setMinimumHeight(100)
        self.level_list_widget.itemClicked.connect(self.select_level_from_results)
        self.level_list_widget.setVisible(False)

        self.category_label = QLabel(_.get_string('category_list_label'))
        self.category_label.setObjectName("SectionHeader")
        self.category_list_widget = QListWidget()
        self.category_list_widget.setMinimumHeight(120)
        self.category_list_widget.itemClicked.connect(self.select_category_to_show_variables)
        
        self.variables_label = QLabel(_.get_string('variables_list_label'))
        self.variables_label.setObjectName("SectionHeader")
        self.variables_label.setVisible(False)
        self.variables_list_widget = QListWidget()
        self.variables_list_widget.setMinimumHeight(80)
        self.variables_list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.variables_list_widget.itemClicked.connect(self.handle_variable_selection)
        self.variables_list_widget.setVisible(False)

        for label, widget in [(self.game_results_label, self.game_results_list_widget),
                             (self.level_label, self.level_list_widget),
                             (self.category_label, self.category_list_widget),
                             (self.variables_label, self.variables_list_widget)]:
            left_layout.addWidget(label)
            left_layout.addWidget(widget)

        self.add_run_button = QPushButton(_.get_string('add_run_button'))
        self.add_run_button.setObjectName("AddRunButton")
        self.add_run_button.setFixedSize(200, 40)
        self.add_run_button.clicked.connect(self.add_to_tracked)
        self.add_run_button.setEnabled(False)
        left_layout.addWidget(self.add_run_button, alignment=Qt.AlignCenter)
        left_layout.addStretch(1)

        right_panel_widget = QWidget()
        right_layout = QVBoxLayout(right_panel_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        self.tracked_list_widget = QListWidget()
        self.tracked_list_widget.setObjectName("TrackedRunsList")
        self.tracked_list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.tracked_list_widget.verticalScrollBar().setSingleStep(20)
        self.tracked_list_widget.setSpacing(-2)
        right_layout.addWidget(self.tracked_list_widget, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        right_layout.addWidget(self.status_label)

        button_container_layout = QHBoxLayout()
        self.show_last_record_button = QPushButton(_.get_string('last_record_dialog_title'))
        self.show_last_record_button.setFixedSize(200, 40)
        self.show_last_record_button.clicked.connect(self.show_last_record_notification)
        self.show_last_record_button.setVisible(False)
        
        self.refresh_button = QPushButton(_.get_string('refresh_button'))
        self.refresh_button.setFixedSize(120, 40)
        self.refresh_button.clicked.connect(self.check_for_new_records)
        
        self.clear_new_wr_button = QPushButton(_.get_string('clear_new_wr_button'))
        self.clear_new_wr_button.setFixedSize(250, 40)
        self.clear_new_wr_button.clicked.connect(self.mark_all_new_wrs_as_read)
        self.clear_new_wr_button.setVisible(False)

        button_container_layout.addWidget(self.show_last_record_button, alignment=Qt.AlignCenter)
        button_container_layout.addWidget(self.refresh_button, alignment=Qt.AlignCenter)
        button_container_layout.addWidget(self.clear_new_wr_button, alignment=Qt.AlignCenter)
        right_layout.addLayout(button_container_layout)
        
        main_layout.addWidget(self.left_panel_widget, 2)
        main_layout.addWidget(right_panel_widget, 5)
        self.setLayout(main_layout)

    def _set_search_controls_enabled(self, enabled):
        self.game_search_input.setEnabled(True)
        self.search_button.setEnabled(enabled)
        self.search_button.setText(_.get_string('search_button') if enabled else _.get_string('searching_button'))

    def apply_material_style(self):
        if not self.theme: return
        
        colors = self.theme.get('colors', {})
        fonts = self.theme.get('fonts', {})
        sizes = self.theme.get('sizes', {})
        format_args = {**colors, **fonts, **sizes, 'default_font_family': fonts.get('default_family', 'Roboto, Segoe UI, sans-serif')}
        
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(colors.get('background', '#000000')))
        palette.setColor(QPalette.WindowText, QColor(colors.get('primary', '#FFFFFF')))
        palette.setColor(QPalette.Base, QColor(colors.get('surface', '#000000')))
        palette.setColor(QPalette.Text, QColor(colors.get('primary', '#FFFFFF')))
        palette.setColor(QPalette.Highlight, QColor(colors.get('highlight', '#1A1A1A')))
        palette.setColor(QPalette.HighlightedText, QColor(colors.get('highlighted_text', '#FFD700')))
        self.setPalette(palette)
        self.setFont(QFont(format_args['default_font_family']))
        
        stylesheet = self.theme.get('stylesheets', {}).get('main_app', '')
        try:
            self.setStyleSheet(stylesheet.format(**format_args))
        except KeyError:
            self.setStyleSheet("QWidget { background-color: #333; color: white; }")

    def retranslate_ui(self):
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
        self.hamburger_button.setToolTip(self.translator.get_string('menu_options'))
        
        self.update_tracked_list_ui()
        self.apply_material_style()

    def show_options_menu_dialog(self):
        menu = QMenu(self)

        language_menu = menu.addMenu(_.get_string('menu_language'))
        for lang_code, lang_name in [("en", "English"), ("tr", "Türkçe"), ("de", "Deutsch"), ("es", "Español"), ("pt", "Português"), ("zh", "中文"), ("ja", "日本語"), ("ko", "한국어")]:
            action = language_menu.addAction(lang_name)
            action.setCheckable(True)
            action.setChecked(self.translator.current_language() == lang_code)
            action.triggered.connect(lambda _, lc=lang_code: self.change_language_from_menu(lc))

        sort_menu = menu.addMenu(_.get_string('menu_sort_order'))
        for sort_key, text_key in [("added_date_desc", 'sort_added_date_desc'), ("game_name_asc", 'sort_game_name_asc')]:
            action = sort_menu.addAction(_.get_string(text_key))
            action.setCheckable(True)
            action.setChecked(self.current_sort_order == sort_key)
            action.triggered.connect(lambda _, sk=sort_key: self.change_sort_order_from_menu(sk))
        
        button_pos = self.hamburger_button.mapToGlobal(self.hamburger_button.rect().bottomLeft())
        menu.exec_(button_pos)

    def change_language_from_menu(self, lang_code):
        if self.translator.current_language() != lang_code:
            self.translator.set_language(lang_code)
            self.settings_manager.save_settings(lang_code, self.current_sort_order)
            self.retranslate_ui()

    def change_sort_order_from_menu(self, sort_order):
        if self.current_sort_order != sort_order:
            self.current_sort_order = sort_order
            self.settings_manager.save_settings(self.translator.current_language(), self.current_sort_order)
            self.update_tracked_list_ui()

    def load_tracked_runs(self):
        self.tracked_runs = load_json_file(self.save_file, {})
        self.has_unseen_new_wrs = False
        self.broken_records_history = []
        
        for game_id, game_data in self.tracked_runs.items():
            if '_added_timestamp' not in game_data:
                game_data['_added_timestamp'] = time.time()
            
            for category_data in game_data.get('full_game_categories', {}).values():
                if category_data.get('is_new_record_broken', False):
                    self.has_unseen_new_wrs = True
                    self.broken_records_history.append(self._create_broken_record_info(game_data, category_data))
            
            for level_data in game_data.get('levels', {}).values():
                for category_data in level_data.get('categories', {}).values():
                    if category_data.get('is_new_record_broken', False):
                        self.has_unseen_new_wrs = True
                        self.broken_records_history.append(self._create_broken_record_info(game_data, category_data, level_data))

        self.show_last_record_button.setVisible(self.has_unseen_new_wrs)
        self.clear_new_wr_button.setVisible(self.has_unseen_new_wrs)
        self.update_tracked_list_ui()

    def _request_save(self):
        self.save_dirty_flag = True
        if not self.save_debounce_timer.isActive():
            self.save_debounce_timer.start()

    def _save_if_dirty(self):
        if self.save_dirty_flag:
            self.save_tracked_runs()
            self.save_dirty_flag = False

    def save_tracked_runs(self):
        temp_filename = f"{self.save_file}.tmp"
        try:
            with open(temp_filename, 'w', encoding='utf-8') as f:
                json.dump(self.tracked_runs, f, indent=4, ensure_ascii=False)
            os.replace(temp_filename, self.save_file)
        except Exception:
            self.show_status_message(_.get_string('status_message_save_error'), is_error=True)
            if os.path.exists(temp_filename):
                try: os.remove(temp_filename)
                except OSError: pass

    def _reset_all_selections(self, clear_search=True, clear_game=True):
        if clear_search and hasattr(self, 'game_results_list_widget'):
            self.game_results_list_widget.clear()
        
        if clear_game:
            self.selected_game_data = {'id': None, 'name': None, 'weblink': None}
            self.full_game_data_cache = None
        
        self._reset_lower_selections()

    def _reset_lower_selections(self):
        self.selected_level_data = {'id': None, 'name': None}
        self.selected_category_data = {'id': None, 'name': None, 'is_miscellaneous': False}
        self.selected_variable_values = {}
        self.available_subcategory_variables = []
        
        if hasattr(self, 'level_list_widget'):
            self.level_list_widget.clear()
            self.category_list_widget.clear()
            self.variables_list_widget.clear()
            
            self.level_list_widget.setVisible(False)
            self.level_label.setVisible(False)
            self.variables_list_widget.setVisible(False)
            self.variables_label.setVisible(False)
            self.add_run_button.setEnabled(False)

    def start_autocomplete_timer(self):
        self.autocomplete_timer.start(500)

    def search_game_debounced(self):
        game_name = self.game_search_input.text().strip()
        if len(game_name) >= 2:
            self.search_game(game_name=game_name)
        else:
            self._reset_all_selections()

    def _get_next_request_id(self):
        self.current_request_id += 1
        return self.current_request_id

    def search_game(self, game_name=None):
        if game_name is None:
            game_name = self.game_search_input.text().strip()
        if not game_name:
            self.show_status_message(_.get_string('search_placeholder'), is_error=True)
            return

        self._reset_all_selections(clear_search=False)
        self._set_search_controls_enabled(False)
        
        request_id = self._get_next_request_id()
        url = f"{API_BASE_URL}/games?name={requests.utils.quote(game_name)}&max=20&embed=platforms"
        
        worker = ApiWorker(url, request_id=request_id)
        worker.finished.connect(lambda data, req_id: self.handle_game_search_result(data, req_id, request_id))
        worker.error.connect(self.handle_api_error)
        self.active_workers.add(worker)
        worker.start()

    def handle_game_search_result(self, data, response_id, original_id):
        if original_id != self.current_request_id: return
        self._set_search_controls_enabled(True)
        self.game_results_list_widget.clear()
        
        games = data.get('data', [])
        if not games:
            self.game_results_list_widget.addItem(_.get_string('no_game_found'))
            return
        
        sorted_games = sorted(games, key=lambda g: g.get('names', {}).get('international', '').lower())
        for game in sorted_games:
            name = game.get('names', {}).get('international')
            year = game.get('released')
            display_name = f"{name} ({year})" if year else name
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, {
                'id': game.get('id'), 'name': name, 'name_with_year': display_name,
                'weblink': game.get('weblink')
            })
            self.game_results_list_widget.addItem(item)

    def show_game_result_context_menu(self, position):
        item = self.game_results_list_widget.itemAt(position)
        if item and (game_data := item.data(Qt.UserRole)) and game_data.get('weblink'):
            menu = QMenu(self)
            action = menu.addAction(_.get_string('open_speedrun_com_page'))
            action.triggered.connect(lambda: self._open_weblink(game_data['weblink']))
            menu.exec_(self.game_results_list_widget.mapToGlobal(position))

    def select_game_from_results(self, item):
        game_data = item.data(Qt.UserRole)
        if not game_data or not game_data.get('id'):
            self.show_status_message(_.get_string('invalid_game_selection'), is_error=True)
            return

        self._reset_lower_selections()
        self.selected_game_data = {
            'id': game_data.get('id'),
            'name': game_data.get('name_with_year'),
            'weblink': game_data.get('weblink')
        }
        
        self.show_status_message(_.get_string('loading_game_details', game_name=self.selected_game_data['name']))
        
        request_id = self._get_next_request_id()
        api_url = f"{API_BASE_URL}/games/{self.selected_game_data['id']}?embed=levels,categories.variables"
        worker = ApiWorker(api_url, request_id=request_id)
        worker.finished.connect(lambda data, req_id: self.handle_game_details_result(data, req_id, request_id))
        worker.error.connect(self.handle_api_error)
        self.active_workers.add(worker)
        worker.start()

    def handle_game_details_result(self, data, response_id, original_id):
        if original_id != self.current_request_id: return
        
        game_data = data.get('data')
        if not game_data:
            self.show_status_message(_.get_string('loading_game_details_failed'), is_error=True)
            return

        self.full_game_data_cache = game_data
        self.handle_level_result(game_data.get('levels', {}))
        self.handle_category_result(game_data.get('categories', {}))
        self.show_status_message(_.get_string('game_details_loaded', game_name=self.selected_game_data['name']))

    def handle_level_result(self, levels_data):
        self.level_list_widget.clear()
        levels = levels_data.get('data', [])
        
        self.level_list_widget.setVisible(bool(levels))
        self.level_label.setVisible(bool(levels))
        
        if not levels:
            self.level_list_widget.addItem(_.get_string('no_individual_level_found'))
            self.level_list_widget.setEnabled(False)
            return

        self.level_list_widget.setEnabled(True)
        full_game_item = QListWidgetItem(_.get_string('full_game_option'))
        full_game_item.setData(Qt.UserRole, "full_game_no_level")
        self.level_list_widget.addItem(full_game_item)
        
        for level in levels:
            if level.get('id') and level.get('name'):
                item = QListWidgetItem(level['name'])
                item.setData(Qt.UserRole, {'id': level['id'], 'name': level['name']})
                self.level_list_widget.addItem(item)

    def select_level_from_results(self, item):
        level_data = item.data(Qt.UserRole)
        if level_data is None: return

        self.selected_category_data = {'id': None, 'name': None, 'is_miscellaneous': False}
        self.selected_variable_values = {}
        self.available_subcategory_variables = []
        self.category_list_widget.clear()
        self.variables_list_widget.clear()
        self.variables_list_widget.setVisible(False)
        self.variables_label.setVisible(False)
        self.add_run_button.setEnabled(False)

        is_full_game = (level_data == "full_game_no_level")
        self.selected_level_data = {'id': None, 'name': None} if is_full_game else level_data

        if is_full_game:
            self.handle_category_result(self.full_game_data_cache.get('categories', {}))
        else:
            self.show_status_message(_.get_string('level_categories_loading', level_name=self.selected_level_data['name']))
            request_id = self._get_next_request_id()
            api_url = f"{API_BASE_URL}/levels/{self.selected_level_data['id']}/categories?embed=variables"
            worker = ApiWorker(api_url, request_id=request_id)
            worker.finished.connect(lambda data, req_id: self.handle_category_result(data, req_id, request_id))
            worker.error.connect(self.handle_api_error)
            self.active_workers.add(worker)
            worker.start()

    def handle_category_result(self, categories_data, response_id=None, original_id=None):
        if original_id is not None and original_id != self.current_request_id:
            return
        self.category_list_widget.clear()
        
        all_categories = categories_data.get('data', [])
        
        is_level_context = self.selected_level_data.get('id') is not None
        
        if not is_level_context:
            categories = [cat for cat in all_categories if cat.get('type') == 'per-game']
        else:
            categories = all_categories
        
        categories = [cat for cat in categories if cat.get('id') and cat.get('name')]
        
        if not categories:
            if self.selected_level_data.get('id'):
                msg_key = 'no_suitable_category_for_level'
                level_name = self.selected_level_data.get('name', '')
                self.category_list_widget.addItem(_.get_string(msg_key, level_name=level_name))
            else:
                msg_key = 'no_suitable_category_for_game'
                game_name = self.selected_game_data.get('name', '')
                self.category_list_widget.addItem(_.get_string(msg_key, game_name=game_name))
            return

        for category in categories:
            item_text = category['name']
            if category.get('miscellaneous'):
                item_text += _.get_string('miscellaneous_category')
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, category)
            self.category_list_widget.addItem(item)
        
        self.show_status_message(_.get_string('categories_loaded'))

    def select_category_to_show_variables(self, item):
        category_data = item.data(Qt.UserRole)
        if not category_data: return

        self.selected_category_data = {
            'id': category_data.get('id'),
            'name': category_data.get('name'),
            'is_miscellaneous': category_data.get('miscellaneous', False)
        }
        self.variables_list_widget.clear()
        self.selected_variable_values = {}
        
        self.available_subcategory_variables = [
            var for var in category_data.get('variables', {}).get('data', []) if var.get('is-subcategory')
        ]
        
        if not self.available_subcategory_variables:
            self.variables_list_widget.setVisible(False)
            self.variables_label.setVisible(False)
            self._update_add_run_button_state()
            return

        self.variables_list_widget.setVisible(True)
        self.variables_label.setVisible(True)
        
        for var in self.available_subcategory_variables:
            header_item = QListWidgetItem(_.get_string('select_variable_header', variable_name=var['name']))
            header_item.setFlags(header_item.flags() & ~Qt.ItemIsSelectable)
            self.variables_list_widget.addItem(header_item)
            for value_id, value_info in var.get('values', {}).get('values', {}).items():
                item = QListWidgetItem(f"  {var['name']}: {value_info.get('label', value_id)}")
                item.setData(Qt.UserRole, {
                    'variable_id': var['id'], 'value_id': value_id,
                    'value_name': value_info.get('label'), 'variable_display_name': var['name']
                })
                self.variables_list_widget.addItem(item)
        
        self._update_add_run_button_state()

    def handle_variable_selection(self, clicked_item):
        variable_data = clicked_item.data(Qt.UserRole)
        if not variable_data: return
        
        clicked_variable_id = variable_data['variable_id']
        is_deselection = (clicked_variable_id in self.selected_variable_values and 
                          self.selected_variable_values[clicked_variable_id]['value_id'] == variable_data['value_id'])

        for i in range(self.variables_list_widget.count()):
            item = self.variables_list_widget.item(i)
            if (item_data := item.data(Qt.UserRole)) and item_data.get('variable_id') == clicked_variable_id:
                item.setSelected(False)

        if is_deselection:
            del self.selected_variable_values[clicked_variable_id]
        else:
            clicked_item.setSelected(True)
            self.selected_variable_values[clicked_variable_id] = {
                'variable_id': variable_data['variable_id'],
                'value_id': variable_data['value_id'],
                'value_name': variable_data['value_name'],
                'variable_display_name': variable_data['variable_display_name']
            }
        self._update_add_run_button_state()

    def _get_run_config_key(self, category_id, variable_values):
        if not category_id: return None
        sorted_vars = {var_id: val_data['value_id'] for var_id, val_data in sorted(variable_values.items())}
        return f"{category_id}-{json.dumps(sorted_vars, sort_keys=True)}"

    def _update_add_run_button_state(self):
        is_ready = self.selected_game_data.get('id') and self.selected_category_data.get('id')
        if not is_ready:
            self.add_run_button.setEnabled(False)
            return

        key = self._get_run_config_key(self.selected_category_data['id'], self.selected_variable_values)
        game_id = self.selected_game_data['id']
        level_id = self.selected_level_data.get('id')
        
        is_tracked = False
        if game_id in self.tracked_runs:
            if not level_id:
                is_tracked = key in self.tracked_runs[game_id].get('full_game_categories', {})
            elif level_id in self.tracked_runs[game_id].get('levels', {}):
                is_tracked = key in self.tracked_runs[game_id]['levels'][level_id].get('categories', {})

        self.add_run_button.setEnabled(not is_tracked)
        if is_tracked:
            display_name = self._generate_display_name(
                {'name': self.selected_category_data['name'], 'variables': self.selected_variable_values},
                self.selected_level_data.get('name')
            )
            self.show_status_message(_.get_string('run_already_tracked', display_category_name=display_name), is_error=True)
        elif "already being tracked" in self.status_label.text() or "zaten takip ediliyor" in self.status_label.text():
            self.clear_status_label()

    def add_to_tracked(self):
        if not self.selected_category_data.get('id'):
            self.show_status_message(_.get_string('track_category_missing'), is_error=True)
            return
        
        self.left_panel_widget.setEnabled(False)
        
        game_id = self.selected_game_data['id']
        level_id = self.selected_level_data.get('id')
        category_id = self.selected_category_data['id']
        
        api_variables = {var_id: data['value_id'] for var_id, data in self.selected_variable_values.items()}
        
        api_url = self._build_leaderboard_api_url(
            game_id, category_id, level_id, api_variables, top=1, embeds=['players']
        )
        
        context = {
            'game_id': game_id, 'level_id': level_id, 'run_type': 'il' if level_id else 'full_game',
            'category_id': category_id, 'category_name': self.selected_category_data['name'],
            'is_miscellaneous': self.selected_category_data['is_miscellaneous'],
            'variables_to_store': self.selected_variable_values.copy(),
            'variables_for_key': self.selected_variable_values.copy()
        }

        worker = ApiWorker(api_url)
        worker.finished.connect(lambda data, _: self.handle_add_result(data, context))
        worker.error.connect(lambda err, obj: (self.left_panel_widget.setEnabled(True), self.handle_api_error(err, obj)))
        self.active_workers.add(worker)
        worker.start()
        
        display_name = self._generate_display_name(
            {'name': context['category_name'], 'variables': context['variables_for_key']},
            self.selected_level_data.get('name')
        )
        self.show_status_message(_.get_string('record_tracking', display_category_name=display_name))

    def _create_new_run_info(self, world_record, leaderboard_data, context):
        new_player_names, new_player_weblinks = self._extract_player_info(world_record, leaderboard_data)
        
        return {
            'name': context['category_name'],
            'current_record_time': world_record.get('times', {}).get('primary_t'),
            'weblink': world_record.get('weblink'),
            'run_id': world_record.get('id'),
            'current_runners': new_player_names,
            'player_weblinks': new_player_weblinks,
            'date_completed': world_record.get('date', _.get_string('not_available_abbr')),
            'variables': context['variables_to_store'],
            'is_new_record_broken': False, 
            'is_miscellaneous': context['is_miscellaneous'], 
            'is_obsolete': False
        }

    def handle_add_result(self, leaderboard_data, context):
        self.left_panel_widget.setEnabled(True)
        game_id = context['game_id']
        
        if game_id not in self.tracked_runs:
            self.tracked_runs[game_id] = {
                'name': self.selected_game_data['name'],
                'weblink': self.selected_game_data['weblink'], 'full_game_categories': {}, 'levels': {},
                '_added_timestamp': time.time()
            }
            
        world_record = self._get_new_record_run_obj(leaderboard_data)
        if not world_record:
            display_name = self._generate_display_name(
                {'name': context['category_name'], 'variables': context['variables_for_key']},
                self.selected_level_data.get('name')
            )
            self.show_status_message(_.get_string('no_world_record_found', display_category_name=display_name), is_error=True)
            return

        run_info = self._create_new_run_info(world_record, leaderboard_data, context)

        tracked_key = self._get_run_config_key(context['category_id'], context['variables_for_key'])
        if context['run_type'] == 'full_game':
            self.tracked_runs[game_id]['full_game_categories'][tracked_key] = run_info
        else:
            level_id = context['level_id']
            if level_id not in self.tracked_runs[game_id]['levels']:
                self.tracked_runs[game_id]['levels'][level_id] = {'name': self.selected_level_data['name'], 'categories': {}}
            self.tracked_runs[game_id]['levels'][level_id]['categories'][tracked_key] = run_info
        
        self._request_save()
        self.update_tracked_list_ui()
        self._update_add_run_button_state()
        display_name = self._generate_display_name(run_info, self.selected_level_data.get('name'))
        self.show_status_message(_.get_string('record_tracked_success', display_category_name=display_name))

    def _extract_player_info(self, run_obj, leaderboard_data):
        player_names, player_weblinks = [], []
        player_map = {p['id']: p for p in leaderboard_data.get('data', {}).get('players', {}).get('data', []) if p.get('id')}
        
        for player in run_obj.get('players', []):
            if player.get('rel') == 'guest':
                player_names.append(player.get('name', _.get_string('unknown_player')))
                player_weblinks.append(None)
            elif player.get('rel') == 'user' and (p_data := player_map.get(player.get('id'))):
                player_names.append(p_data.get('names', {}).get('international', p_data.get('name', _.get_string('unknown_player'))))
                player_weblinks.append(p_data.get('weblink'))
        return player_names, player_weblinks

    def update_tracked_list_ui(self):
        scroll_pos = self.tracked_list_widget.verticalScrollBar().value()
        self.tracked_list_widget.clear()
        
        if not self.tracked_runs: return

        key_func = lambda gid: self.tracked_runs[gid].get('name', '').lower() if self.current_sort_order == 'game_name_asc' else self.tracked_runs[gid].get('_added_timestamp', 0)
        sorted_game_ids = sorted(self.tracked_runs.keys(), key=key_func, reverse=(self.current_sort_order == 'added_date_desc'))

        for game_id in sorted_game_ids:
            if game_data := self.tracked_runs.get(game_id):
                self._add_game_frame_to_list(game_id, game_data)
        
        QTimer.singleShot(0, lambda: self.tracked_list_widget.verticalScrollBar().setValue(scroll_pos))

    def _add_game_frame_to_list(self, game_id, game_data):
        game_frame = QFrame(objectName="GameFrame")
        game_frame_layout = QVBoxLayout(game_frame)
        game_frame_layout.setContentsMargins(10, 2, 10, 2)
        game_frame_layout.setSpacing(0)

        game_header_layout = QHBoxLayout()
        
        game_name_button = QPushButton(game_data.get('name', _.get_string('unknown_game')))
        game_name_button.setObjectName("GameLinkButton")
        game_name_button.setCursor(Qt.PointingHandCursor)
        if weblink := game_data.get('weblink'):
            game_name_button.clicked.connect(lambda: webbrowser.open(weblink))
        else:
            game_name_button.setEnabled(False)
        game_name_button.setContextMenuPolicy(Qt.CustomContextMenu)
        game_name_button.customContextMenuRequested.connect(lambda: self.show_game_header_context_menu(game_id))
        
        game_header_layout.addStretch(1)
        game_header_layout.addWidget(game_name_button)
        game_header_layout.addStretch(1)
        game_frame_layout.addLayout(game_header_layout)

        self._add_category_items_to_layout(game_id, game_data, game_frame_layout)

        frame_list_item = QListWidgetItem()
        frame_list_item.setSizeHint(game_frame.sizeHint())
        frame_list_item.setFlags(frame_list_item.flags() & ~Qt.ItemIsSelectable)
        self.tracked_list_widget.addItem(frame_list_item)
        self.tracked_list_widget.setItemWidget(frame_list_item, game_frame)

    def show_game_header_context_menu(self, game_id):
        menu = QMenu(self)
        remove_action = menu.addAction(_.get_string('options_menu_remove_game'))
        remove_action.triggered.connect(lambda: self.delete_tracked_game(game_id))
        menu.exec_(QCursor.pos())

    def _generate_display_name(self, category_data, level_name=None):
        base_name = category_data.get('name', _.get_string('unknown_category'))
        full_name = f"{level_name}: {base_name}" if level_name else base_name
        
        variables = category_data.get('variables', {})
        if variables:
            var_names = sorted([v['value_name'] for v in variables.values() if isinstance(v, dict) and 'value_name' in v])
            if var_names:
                full_name += f" ({', '.join(var_names)})"
        return full_name

    def _create_runner_widget(self, name, weblink, is_obsolete, object_name_prefix=""):
        button = QPushButton(name)
        if weblink and not is_obsolete:
            button.setObjectName(f"{object_name_prefix}RunnerLinkButton")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda: webbrowser.open(weblink))
        else:
            button.setObjectName(f"{object_name_prefix}RunnerButton")
            button.setEnabled(False)
        return button

    def _create_category_item_widget(self, category_data, category_key, game_id, level_id=None, level_name=None, item_type='full_game'):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        if category_data.get('is_obsolete', False):
            status_label = QLabel(_.get_string('obsolete_label'), objectName="obsolete_label", toolTip=_.get_string('obsolete_tooltip'))
            layout.addWidget(status_label, 0, Qt.AlignVCenter)
        elif category_data.get('is_new_record_broken', False):
            status_label = QLabel(_.get_string('new_wr_label'), objectName="new_wr_label")
            layout.addWidget(status_label, 0, Qt.AlignVCenter)

        display_name = self._generate_display_name(category_data, level_name)
        layout.addWidget(QLabel(display_name, wordWrap=True), 1)

        right_group_layout = QHBoxLayout()
        right_group_layout.setContentsMargins(0, 0, 0, 0)
        right_group_layout.setSpacing(8)
        right_group_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        time_button = QPushButton(format_time(category_data.get('current_record_time')))
        time_button.setObjectName("TimeButton")
        weblink = category_data.get('weblink')
        if weblink and weblink != '#' and not category_data.get('is_obsolete', False):
            time_button.setCursor(Qt.PointingHandCursor)
            time_button.setToolTip(_.get_string('speedrun_link_tooltip'))
            time_button.clicked.connect(lambda: self._open_weblink(weblink))
        else:
            time_button.setEnabled(False)
            time_button.setToolTip(_.get_string('speedrun_profile_link_not_available'))

        right_group_layout.addWidget(time_button)

        runners_widget = self._create_runners_cell_widget(
            category_data.get('current_runners', []),
            category_data.get('player_weblinks', []),
            display_name,
            category_data.get('is_obsolete', False)
        )
        right_group_layout.addWidget(runners_widget)

        right_group_layout.addWidget(QLabel(f"{category_data.get('date_completed', '')}"))

        options_button = QPushButton("⋮")
        options_button.setObjectName("OptionsButton")
        options_button.setToolTip(_.get_string('options_button_tooltip'))
        
        options_button.clicked.connect(
            lambda _, cd=category_data, ck=category_key, gid=game_id, lid=level_id, it=item_type: 
            self.show_run_options_menu(options_button, cd, ck, gid, lid, it)
        )
        right_group_layout.addWidget(options_button)
        
        layout.addLayout(right_group_layout, 0)
        
        stylesheet = self.theme.get("stylesheets", {}).get("category_item_widget", "")
        try:
            colors = self.theme.get('colors', {})
            fonts = self.theme.get('fonts', {})
            sizes = self.theme.get('sizes', {})
            format_args = {**colors, **fonts, **sizes}
            format_args['default_font_family'] = fonts.get('default_family', 'Roboto, Segoe UI, sans-serif')
            widget.setStyleSheet(stylesheet.format(**format_args))
        except KeyError:
            pass

        return widget

    def _create_runners_cell_widget(self, names, links, run_title, is_obsolete=False):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        if not names: return widget

        runner_button = self._create_runner_widget(names[0], links[0] if links else None, is_obsolete)
        layout.addWidget(runner_button)
        
        if len(names) > 1:
            more_button = QPushButton(f"+{len(names) - 1}", objectName="MoreRunnersButton")
            more_button.setToolTip(_.get_string('more_runners_button', count=len(names) - 1))
            if not is_obsolete:
                more_button.setCursor(Qt.PointingHandCursor)
                more_button.clicked.connect(lambda: self.show_all_runners_dialog(run_title, names, links))
            else:
                more_button.setEnabled(False)
            layout.addWidget(more_button)
        
        layout.addStretch()
            
        return widget

    def _add_category_items_to_layout(self, game_id, game_data, parent_layout):
        all_widgets = []
        
        fg_items = game_data.get('full_game_categories', {}).items()
        for key, data in fg_items:
            display_name = self._generate_display_name(data)
            is_misc = data.get('is_miscellaneous', False)
            sort_key = 1 if is_misc else 0
            widget = self._create_category_item_widget(data, key, game_id, item_type='full_game')
            all_widgets.append((sort_key, display_name.lower(), widget))

        sorted_levels = sorted(game_data.get('levels', {}).values(), key=lambda l: l.get('name', '').lower())
        for level_data in sorted_levels:
            level_id = next((lid for lid, ldata in game_data['levels'].items() if ldata == level_data), None)
            if not level_id: continue
            
            il_items = level_data.get('categories', {}).items()
            for key, data in il_items:
                display_name = self._generate_display_name(data, level_data.get('name'))
                sort_key = 2
                widget = self._create_category_item_widget(data, key, game_id, level_id, level_data.get('name'), item_type='il')
                all_widgets.append((sort_key, display_name.lower(), widget))
        
        for _, _, widget in sorted(all_widgets, key=lambda x: (x[0], x[1])):
            parent_layout.addWidget(widget)

    def show_run_options_menu(self, button, category_data, category_key, game_id, level_id, item_type):
        menu = QMenu(self)
        is_obsolete = category_data.get('is_obsolete', False)
        
        if is_obsolete:
            menu.addAction(_.get_string('options_menu_remove_run')).triggered.connect(
                lambda: self.delete_tracked_run(game_id, category_key, level_id, item_type)
            )
        else:
            menu.addAction(_.get_string('options_menu_open_run_page')).triggered.connect(
                lambda: self._open_weblink(category_data.get('weblink'), "run")
            )
            menu.addAction(_.get_string('options_menu_open_other_runs')).triggered.connect(
                lambda: self.show_other_runs_dialog(category_data, category_key, game_id, level_id)
            )
            if category_data.get('is_new_record_broken', False):
                menu.addAction(_.get_string('options_menu_mark_as_read')).triggered.connect(
                    lambda: self.mark_run_as_read(game_id, category_key, level_id, item_type)
                )
            
            if runners := category_data.get('current_runners'):
                menu.addSeparator()
                weblinks = category_data.get('player_weblinks', [])
                for i, name in enumerate(runners):
                    if i < len(weblinks) and weblinks[i]:
                        action = menu.addAction(_.get_string('options_menu_open_player_profile', player_name=name))
                        action.triggered.connect(lambda _, link=weblinks[i]: self._open_weblink(link, "player"))

            menu.addSeparator()
            menu.addAction(_.get_string('options_menu_remove_run')).triggered.connect(
                lambda: self.delete_tracked_run(game_id, category_key, level_id, item_type)
            )
            
        menu.exec_(button.mapToGlobal(button.rect().bottomLeft()))

    def show_other_runs_dialog(self, category_data, category_key, game_id, level_id):
        parts = category_key.split('-', 1)
        original_category_id = parts[0]
        variables = {}
        if len(parts) > 1 and parts[1]:
            try:
                variables = json.loads(parts[1])
            except json.JSONDecodeError:
                variables = {}

        game_name = self.tracked_runs.get(game_id, {}).get('name', '')
        level_name = self.tracked_runs.get(game_id, {}).get('levels', {}).get(level_id, {}).get('name')
        run_title = f"{game_name} - {self._generate_display_name(category_data, level_name)}"
        
        AllRunsDialog(game_id, original_category_id, level_id, variables, run_title, parent=self).exec_()

    def show_all_runners_dialog(self, run_display_name, all_runners, all_weblinks):
        # This dialog is now simpler and doesn't need to be a class.
        from ui_components import BaseDialog # Avoid circular import at top level
        from PyQt5.QtWidgets import QScrollArea

        if not isinstance(all_runners, list) or not isinstance(all_weblinks, list):
            self.show_status_message(_.get_string('error_fetching_runner_info'), is_error=True)
            return
        
        dialog = BaseDialog(self, _.get_string('all_runners_dialog_title', run_title=run_display_name))
        dialog.setGeometry(self.x() + 50, self.y() + 50, 400, 500)
        layout = QVBoxLayout(dialog)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        for i, name in enumerate(all_runners):
            link = all_weblinks[i] if i < len(all_weblinks) else None
            runner_widget = self._create_runner_widget(name, link, is_obsolete=False, object_name_prefix="Dialog")
            content_layout.addWidget(runner_widget)
        
        content_layout.addStretch(1)
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        layout.addLayout(dialog._add_standard_buttons())
        dialog.exec_()


    def _open_weblink(self, url, item_type="item"):
        if url and url != '#':
            try:
                webbrowser.open(url)
            except Exception:
                self.show_status_message(_.get_string('web_link_open_failed'), is_error=True)
        else:
            self.show_status_message(_.get_string('web_link_not_available', item_type=item_type), is_error=True)

    def delete_tracked_run(self, game_id, category_key, level_id, run_type):
        if game_id not in self.tracked_runs: return
        
        game_entry = self.tracked_runs[game_id]
        deleted = False
        if run_type == 'full_game' and category_key in game_entry.get('full_game_categories', {}):
            del game_entry['full_game_categories'][category_key]
            deleted = True
        elif run_type == 'il' and level_id and level_id in game_entry.get('levels', {}) and category_key in game_entry['levels'][level_id].get('categories', {}):
            del game_entry['levels'][level_id]['categories'][category_key]
            if not game_entry['levels'][level_id].get('categories'):
                del game_entry['levels'][level_id]
            deleted = True
            
        if deleted:
            if not game_entry.get('full_game_categories') and not game_entry.get('levels'):
                del self.tracked_runs[game_id]
            self._request_save()
            self.update_tracked_list_ui()
            self._update_add_run_button_state()
            self.show_status_message(self.translator.get_string('untrack_run_success'))
        else:
            self.show_status_message(self.translator.get_string('untrack_run_failed'), is_error=True)

    def delete_tracked_game(self, game_id):
        if game_id in self.tracked_runs:
            del self.tracked_runs[game_id]
            self._request_save()
            self.update_tracked_list_ui()
            self._update_add_run_button_state()
            self.show_status_message(self.translator.get_string('game_removed_success'))
        else:
            self.show_status_message(_.get_string('game_not_found_untrack', game_id=game_id), is_error=True)

    def _build_leaderboard_api_url(self, game_id, category_id, level_id, variables, top=None, max_results=None, embeds=None):
        path = f"leaderboards/{game_id}/level/{level_id}/{category_id}" if level_id else f"leaderboards/{game_id}/category/{category_id}"
        params = []
        if top is not None: params.append(f"top={top}")
        if max_results is not None: params.append(f"max={max_results}")
        if embeds: params.append(f"embed={','.join(embeds)}")
        if variables:
            for var_id, value_id in variables.items():
                params.append(f"var-{var_id}={value_id}")
        query_string = f"?{'&'.join(params)}" if params else ""
        return f"{API_BASE_URL}/{path}{query_string}"

    def _get_active_tracked_runs(self):
        for game_id, game_data in self.tracked_runs.items():
            for cat_key, cat_data in game_data.get('full_game_categories', {}).items():
                if not cat_data.get('is_obsolete', False):
                    yield ('full_game', game_id, cat_key, None)
            for level_id, level_data in game_data.get('levels', {}).items():
                for cat_key, cat_data in level_data.get('categories', {}).items():
                    if not cat_data.get('is_obsolete', False):
                        yield ('il', game_id, cat_key, level_id)

    def check_for_new_records(self):
        if self.is_checking_records:
            self.show_status_message(self.translator.get_string('check_already_running'), is_error=True)
            return
        if not self.tracked_runs:
            self.show_status_message(self.translator.get_string('no_records_to_track'), is_error=False)
            return
        
        self.is_checking_records = True
        self.ui_update_needed_after_check = False
        self.refresh_button.setEnabled(False)
        self.main_check_timer.stop()
        
        self.record_check_queue = deque(self._get_active_tracked_runs())
        self.record_check_workers.clear()
        self.result_queue.clear()
        
        self.total_runs_to_check = len(self.record_check_queue)
        self.checked_runs_count = 0
        self.all_workers_finished_check = False

        if self.total_runs_to_check == 0:
            self._finalize_record_check()
            return
            
        self.update_progress_status()
        self.process_results_timer.start()
        
        initial_batch_size = min(self.total_runs_to_check, MAX_CONCURRENT_WORKERS)
        for _ in range(initial_batch_size):
            if self.record_check_queue:
                run_type, game_id, category_key, level_id = self.record_check_queue.popleft()
                self._create_and_start_worker(game_id, category_key, level_id, run_type)

    def _finalize_record_check(self):
        if not self.is_checking_records:
            return
        self.is_checking_records = False

        self.process_results_timer.stop()
        self._save_if_dirty()

        if self.is_initial_load:
            self.is_initial_load = False
        if self.ui_update_needed_after_check:
            self.update_tracked_list_ui()
        
        self.show_status_message(self.translator.get_string('check_complete'))
        self.refresh_button.setEnabled(True)
        if not self.main_check_timer.isActive():
            self.main_check_timer.start(300000)

    def _create_and_start_worker(self, game_id, category_key, level_id, run_type):
        original_category_id = category_key.split('-')[0]
        variables_dict = {}
        if '-' in category_key:
            try:
                variables_json_str = category_key.split('-', 1)[1]
                if variables_json_str:
                    variables_dict = json.loads(variables_json_str)
            except (json.JSONDecodeError, IndexError):
                QTimer.singleShot(0, lambda: self.on_worker_completed(None))
                return
        
        url = self._build_leaderboard_api_url(
            game_id, original_category_id, level_id, variables_dict, top=1,
            embeds=['players', 'category', 'level']
        )
        
        worker = ApiWorker(url)
        worker.run_context = {'game_id': game_id, 'category_key': category_key, 'level_id': level_id, 'run_type': run_type}
        
        worker.finished.connect(lambda data, request_id, w=worker: self.handle_record_check_result(data, w.run_context))
        worker.error.connect(self.handle_api_error)
        worker.worker_completed.connect(lambda w=worker: self.on_worker_completed(w))
        self.record_check_workers.add(worker)
        worker.start()

    def handle_record_check_result(self, leaderboard_data, context):
        self.result_queue.append((leaderboard_data, context))

    def _process_result_queue(self):
        if self.result_queue:
            leaderboard_data, context = self.result_queue.popleft()
            self._process_single_result(leaderboard_data, context)
        
        self._check_if_finished()

    def _check_if_finished(self):
        if self.is_checking_records and self.all_workers_finished_check and not self.result_queue:
            self._finalize_record_check()

    def _process_single_result(self, leaderboard_data, context):
        if not context:
            return

        game_id = context['game_id']
        category_key = context['category_key']
        level_id = context['level_id']
        
        run_data = self._get_tracked_run_data(game_id, category_key, level_id)
        if not run_data: return

        new_record = self._get_new_record_run_obj(leaderboard_data)
        if not new_record:
            self.mark_run_as_obsolete(context)
            return

        data_changed = self._update_run_metadata(run_data, leaderboard_data, game_id, level_id)
        record_updated, is_new_time = self._process_record_update(run_data, new_record, leaderboard_data, game_id, level_id)
        
        if data_changed or record_updated:
            self.ui_update_needed_after_check = True
            self._request_save()
            if is_new_time:
                run_identifier = self._get_run_identifier_for_msg(self.tracked_runs[game_id], run_data, level_id)
                self.show_status_message(_.get_string('new_wr_detected', run_identifier=run_identifier))

    def _get_tracked_run_data(self, game_id, category_key, level_id):
        try:
            if level_id:
                return self.tracked_runs[game_id]['levels'][level_id]['categories'][category_key]
            else:
                return self.tracked_runs[game_id]['full_game_categories'][category_key]
        except KeyError:
            return None

    def _update_run_metadata(self, run_data, leaderboard_data, game_id, level_id):
        changed = False
        category_embed = leaderboard_data.get('data', {}).get('category', {}).get('data', {})
        if (new_name := category_embed.get('name')) and run_data.get('name') != new_name:
            run_data['name'] = new_name
            changed = True
        
        if level_id and (level_embed := leaderboard_data.get('data', {}).get('level', {}).get('data', {})):
            level_data = self.tracked_runs[game_id]['levels'][level_id]
            if (new_name := level_embed.get('name')) and level_data.get('name') != new_name:
                level_data['name'] = new_name
                changed = True
        return changed

    def _process_record_update(self, run_data, new_record, leaderboard_data, game_id, level_id):
        new_time = new_record.get('times', {}).get('primary_t')
        new_runners, new_links = self._extract_player_info(new_record, leaderboard_data)
        new_run_id = new_record.get('id')

        is_new_time = new_time is not None and (run_data.get('current_record_time') is None or new_time < run_data['current_record_time'])
        is_different_runners = run_data.get('current_runners') != new_runners
        is_different_link = run_data.get('weblink') != new_record.get('weblink')
        is_missing_run_id = 'run_id' not in run_data and new_run_id is not None

        if is_new_time or is_different_runners or is_different_link or is_missing_run_id:
            run_data.update({
                'current_record_time': new_time,
                'weblink': new_record.get('weblink'),
                'date_completed': new_record.get('date', _.get_string('not_available_abbr')),
                'run_id': new_run_id,
                'current_runners': new_runners,
                'player_weblinks': new_links
            })
            if is_new_time:
                run_data['is_new_record_broken'] = True
                self.has_unseen_new_wrs = True
                self.show_last_record_button.setVisible(True)
                self.clear_new_wr_button.setVisible(True)
                game_data = self.tracked_runs[game_id]
                level_data = game_data.get('levels', {}).get(level_id) if level_id else None
                self.broken_records_history.append(self._create_broken_record_info(game_data, run_data, level_data))
            
            return True, is_new_time
            
        return False, False

    def _get_new_record_run_obj(self, leaderboard_data):
        try:
            return leaderboard_data['data']['runs'][0]['run']
        except (KeyError, IndexError, TypeError):
            return None

    def _get_run_identifier_for_msg(self, game_data, category_data, level_id):
        level_name = game_data.get('levels', {}).get(level_id, {}).get('name') if level_id else None
        return self._generate_display_name(category_data, level_name)

    def _create_broken_record_info(self, game_data, category_data, level_data=None):
        return {
            'game_name': game_data.get('name', _.get_string('unknown_game')),
            'category_display_name': self._generate_display_name(category_data, level_data.get('name') if level_data else None),
            'formatted_new_time': format_time(category_data.get('current_record_time')),
            'new_player_name': ', '.join(category_data.get('current_runners', [])),
            'new_run_date': f"({category_data.get('date_completed', '')})",
            'weblink': category_data.get('weblink')
        }

    def handle_api_error(self, error_message, exception_obj=None):
        sender_worker = self.sender()
        if not sender_worker: return

        if (hasattr(sender_worker, 'run_context') and sender_worker.run_context and
                isinstance(exception_obj, requests.exceptions.HTTPError) and
                exception_obj.response.status_code == 404):
            self.mark_run_as_obsolete(sender_worker.run_context)
        else:
            is_background_check = self.is_checking_records
            if not is_background_check:
                self.show_status_message(f"{_.get_string('api_error_general_prefix')}: {error_message}".strip(), is_error=True)
                self._set_search_controls_enabled(True)
                self.left_panel_widget.setEnabled(True)
        
        QTimer.singleShot(0, lambda w=sender_worker: self.on_worker_completed(w))

    def mark_run_as_obsolete(self, context):
        run_data = self._get_tracked_run_data(context['game_id'], context['category_key'], context['level_id'])
        if run_data and not run_data.get('is_obsolete'):
            run_data['is_obsolete'] = True
            self.ui_update_needed_after_check = True
            self._request_save()
            run_identifier = self._get_run_identifier_for_msg(self.tracked_runs[context['game_id']], run_data, context['level_id'])
            self.show_status_message(_.get_string('run_is_obsolete_notification', run_identifier=run_identifier), is_error=True)

    def on_worker_completed(self, worker=None):
        if worker is None: worker = self.sender()
        if worker is None: return

        if worker in self.record_check_workers:
            self.record_check_workers.discard(worker)
            if self.is_checking_records:
                self.checked_runs_count += 1
                self.update_progress_status()
                
                if self.checked_runs_count >= self.total_runs_to_check:
                    self.all_workers_finished_check = True
                    self._check_if_finished()

                if self.record_check_queue:
                    run_type, game_id, category_key, level_id = self.record_check_queue.popleft()
                    self._create_and_start_worker(game_id, category_key, level_id, run_type)
        elif worker in self.active_workers:
            self.active_workers.discard(worker)

    def update_progress_status(self):
        if not self.is_checking_records or self.total_runs_to_check == 0: return
        message = _.get_string('checking_records_progress', checked=self.checked_runs_count, total=self.total_runs_to_check)
        self.show_status_message(message, is_error=False, clear_after=0)
        self.status_label.setProperty("status", "progress")
        self.style().polish(self.status_label)

    def show_last_record_notification(self):
        LastRecordDialog(self.broken_records_history, parent=self).exec_()

    def mark_all_new_wrs_as_read(self):
        for game_data in self.tracked_runs.values():
            for category_data in game_data.get('full_game_categories', {}).values():
                category_data['is_new_record_broken'] = False
            for level_data in game_data.get('levels', {}).values():
                for category_data in level_data.get('categories', {}).values():
                    category_data['is_new_record_broken'] = False

        self.broken_records_history.clear()
        self.has_unseen_new_wrs = False
        self._request_save()
        self.update_tracked_list_ui()
        self.show_last_record_button.setVisible(False)
        self.clear_new_wr_button.setVisible(False)
        self.show_status_message(_.get_string('all_marked_as_read'))

    def mark_run_as_read(self, game_id, category_key, level_id, run_type):
        run_data = self._get_tracked_run_data(game_id, category_key, level_id)
        if run_data and run_data.get('is_new_record_broken'):
            run_data['is_new_record_broken'] = False
            self._request_save()
            self.update_tracked_list_ui()

            self.has_unseen_new_wrs = any(
                cat.get('is_new_record_broken')
                for game in self.tracked_runs.values()
                for cat in game.get('full_game_categories', {}).values()
            ) or any(
                cat.get('is_new_record_broken')
                for game in self.tracked_runs.values()
                for level in game.get('levels', {}).values()
                for cat in level.get('categories', {}).values()
            )
            
            self.show_last_record_button.setVisible(self.has_unseen_new_wrs)
            self.clear_new_wr_button.setVisible(self.has_unseen_new_wrs)
            
            self.broken_records_history = [rec for rec in self.broken_records_history if rec.get('weblink') != run_data.get('weblink')]

            self.show_status_message(_.get_string('run_marked_as_read'))

    def clear_status_label(self):
        self.status_label.setText("")
        self.status_label.setProperty("status", "none")
        self.style().polish(self.status_label)

    def show_status_message(self, message, is_error=False, clear_after=5000):
        self.status_clear_timer.stop()
        self.status_label.setText(message)
        self.status_label.setProperty("status", "error" if is_error else "success")
        self.style().polish(self.status_label)
        if clear_after > 0:
            self.status_clear_timer.start(clear_after)

    def closeEvent(self, event):
        self.is_checking_records = False
        all_workers = self.active_workers | self.record_check_workers
        for worker in all_workers:
            try:
                if worker.isRunning():
                    worker.quit()
                    worker.wait(200)
                if worker.isRunning():
                    worker.terminate()
                    worker.wait(100)
            except RuntimeError: 
                pass
        self._save_if_dirty()
        event.accept()
