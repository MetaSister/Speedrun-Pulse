# ui_components.py
# Bu dosya, ana uygulama tarafından kullanılan özel arayüz bileşenlerini (dialoglar, widget'lar) içerir.

import webbrowser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QWidget, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import THEME_FILE
# DEĞİŞİKLİK: 'load_json_file' artık 'file_handler'dan, diğerleri 'utils'dan geliyor.
from file_handler import load_json_file
from utils import format_time
from localization import _
from api_client import ApiWorker

THEME = load_json_file(THEME_FILE)

def apply_dialog_style(dialog):
    """
    Theme.json dosyasındaki stile göre bir dialogu biçimlendirir.
    """
    if THEME:
        stylesheet = THEME.get('stylesheets', {}).get('dialog', '')
        font_family = THEME.get('fonts', {}).get('default_family', 'Arial')
        dialog.setFont(QFont(font_family))
        format_args = {**THEME.get('colors', {}), **THEME.get('fonts', {}), **THEME.get('sizes', {})}
        components_stylesheet = THEME.get('stylesheets', {}).get('dialog_components', '')
        try:
            dialog.setStyleSheet((stylesheet + components_stylesheet).format(**format_args))
        except KeyError:
            dialog.setStyleSheet("QDialog { background-color: #333; color: white; }")

class BaseDialog(QDialog):
    """
    Tüm özel dialoglar için temel sınıf. Başlık ve stil gibi ortak özellikleri ayarlar.
    """
    def __init__(self, parent=None, window_title=""):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle(window_title)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        apply_dialog_style(self)

    def _add_standard_buttons(self, add_close=True):
        """
        Dialoglara standart bir 'Kapat' butonu ekler.
        """
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        if add_close:
            close_button = QPushButton(_.get_string('close_button'))
            close_button.setFixedSize(100, 35)
            close_button.clicked.connect(self.accept)
            button_layout.addWidget(close_button)

        button_layout.addStretch()
        return button_layout

class NumericTableWidgetItem(QTableWidgetItem):
    """
    Sayısal değerlere göre doğru sıralama yapabilen özel bir QTableWidgetItem.
    """
    def __lt__(self, other):
        try:
            self_data = float(self.data(Qt.UserRole))
            other_data = float(other.data(Qt.UserRole))
            return self_data < other_data
        except (ValueError, TypeError, AttributeError):
            return super().__lt__(other)

class LastRecordDialog(BaseDialog):
    """
    Son kırılan rekorları gösteren dialog.
    """
    def __init__(self, broken_records_list, parent=None):
        super().__init__(parent, window_title=_.get_string('last_record_dialog_title'))
        self.setGeometry(parent.x() + 50, parent.y() + 50, 700, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        if broken_records_list:
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            content_layout.setSpacing(15)
            
            for record in broken_records_list:
                entry_widget = self._create_record_entry_widget(record)
                content_layout.addWidget(entry_widget)
            
            content_layout.addStretch(1)
            scroll_area.setWidget(content_widget)
            layout.addWidget(scroll_area)
        else:
            layout.addWidget(QLabel(_.get_string('no_new_wr_found'), alignment=Qt.AlignCenter))
        
        layout.addLayout(self._add_standard_buttons())

    def _create_record_entry_widget(self, record_info):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        stylesheet = THEME.get('stylesheets', {}).get('last_record_entry', '')
        if stylesheet:
            try:
                widget.setStyleSheet(stylesheet.format(**THEME.get('colors', {})))
            except KeyError:
                pass

        weblink = record_info.get('weblink')
        if weblink and weblink != '#':
            link_button = QPushButton(_.get_string('options_menu_open_run_page'))
            link_button.setObjectName("RecordLinkButton")
            link_button.setCursor(Qt.PointingHandCursor)
            link_button.clicked.connect(lambda: webbrowser.open(weblink))
            layout.addWidget(link_button, alignment=Qt.AlignCenter)

        layout.addWidget(QLabel(_.get_string('game_label', game_name=record_info['game_name'])))
        layout.addWidget(QLabel(_.get_string('category_label', category_name=record_info['category_display_name'])))
        layout.addWidget(QLabel(_.get_string('new_time_label', formatted_new_time=record_info['formatted_new_time'])))
        layout.addWidget(QLabel(_.get_string('runners_label', new_player_name=record_info['new_player_name'])))
        layout.addWidget(QLabel(f"{_.get_string('date_label')}: {record_info['new_run_date'].strip('()')}"))
        
        return widget

class BaseTableDialog(BaseDialog):
    """
    İçinde bir QTableWidget barındıran dialoglar için temel sınıf.
    """
    def __init__(self, parent=None, window_title=""):
        super().__init__(parent, window_title=window_title)
        self.translator = self.parent_app.translator if self.parent_app else _
        self.api_worker = None
        self._setup_table_ui()

    def _setup_table_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(10)

        self.status_label = QLabel("", objectName="StatusLabel", alignment=Qt.AlignCenter)
        self.layout.addWidget(self.status_label)

        self.table_widget = QTableWidget()
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_widget.setSelectionMode(QTableWidget.NoSelection)
        self.table_widget.setFocusPolicy(Qt.NoFocus)
        self.table_widget.setSortingEnabled(True)
        self.layout.addWidget(self.table_widget, 1)

        self.layout.addLayout(self._add_standard_buttons())

    def handle_api_error(self, error_message, exception_obj=None):
        if not self.isVisible(): return
        self.status_label.setText(self.translator.get_string('error_loading_runs', error_message=error_message))
        self.status_label.setProperty("status", "error")
        self.style().polish(self.status_label)
        self.table_widget.setSortingEnabled(True)

    def closeEvent(self, event):
        if self.api_worker and self.api_worker.isRunning():
            try:
                self.api_worker.finished.disconnect()
                self.api_worker.error.disconnect()
                self.api_worker.quit()
                self.api_worker.wait(200)
            except (TypeError, RuntimeError):
                pass
        super().closeEvent(event)

class AllRunsDialog(BaseTableDialog):
    """
    Bir kategoriye ait tüm koşuları (leaderboard) gösteren dialog.
    """
    def __init__(self, game_id, category_id, level_id, variables, run_title, parent=None):
        super().__init__(parent, window_title=_.get_string('leaderboard_dialog_title', run_title=run_title))
        self.setGeometry(parent.x() + 50, parent.y() + 50, 800, 700)

        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels([
            _.get_string('rank_column'), 
            _.get_string('runners_column'), 
            _.get_string('time_column'), 
            _.get_string('date_column')
        ])
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        self.fetch_all_runs(game_id, category_id, level_id, variables)

    def fetch_all_runs(self, game_id, category_id, level_id, variables):
        url = self.parent_app._build_leaderboard_api_url(
            game_id=game_id,
            category_id=category_id,
            level_id=level_id,
            variables=variables,
            top=200,
            embeds=['players']
        )
        self.status_label.setText(_.get_string('loading_runs'))
        self.table_widget.setVisible(False)

        self.api_worker = ApiWorker(url)
        self.api_worker.finished.connect(self.handle_all_runs_result)
        self.api_worker.error.connect(self.handle_api_error)
        self.api_worker.start()

    def handle_all_runs_result(self, data, _):
        if not self.isVisible(): return
        
        self.status_label.setText("")
        inner_data = data.get('data')

        if not inner_data or not inner_data.get('runs'):
            self.status_label.setText(self.translator.get_string('no_runs_found'))
            self.table_widget.setVisible(True)
            return

        all_runs = inner_data.get('runs', [])
        
        self.table_widget.setSortingEnabled(False)
        self.table_widget.setRowCount(len(all_runs))

        for row, entry in enumerate(all_runs):
            run_obj = entry.get('run', {})
            if not run_obj: continue

            player_names, player_weblinks = self.parent_app._extract_player_info(run_obj, data)
            
            rank = entry.get('place', row + 1)
            rank_item = NumericTableWidgetItem(f"#{rank}")
            rank_item.setData(Qt.UserRole, rank)
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.table_widget.setItem(row, 0, rank_item)

            players_widget = self.parent_app._create_runners_cell_widget(player_names, player_weblinks, self.windowTitle())
            self.table_widget.setCellWidget(row, 1, players_widget)

            time_button = QPushButton(format_time(run_obj.get('times', {}).get('primary_t')))
            time_button.setObjectName("TimeLinkButtonInTable")
            if run_obj.get('weblink'):
                time_button.setCursor(Qt.PointingHandCursor)
                time_button.clicked.connect(lambda _, link=run_obj['weblink']: webbrowser.open(link))
            else:
                time_button.setEnabled(False)
            self.table_widget.setCellWidget(row, 2, time_button)

            date_item = QTableWidgetItem(run_obj.get('date', self.translator.get_string('not_available_abbr')))
            date_item.setTextAlignment(Qt.AlignCenter)
            self.table_widget.setItem(row, 3, date_item)

        self.status_label.setText(self.translator.get_string('total_runs_loaded', count=self.table_widget.rowCount()))
        self.table_widget.setSortingEnabled(True)
        self.table_widget.setVisible(True)
