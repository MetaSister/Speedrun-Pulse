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
# Set logging level to INFO to increase debugging output.
# This will log messages at INFO, WARNING, ERROR, and CRITICAL levels.
logging.basicConfig(filename='Speedrun Tracker.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Helper Functions (JSON Loading) ---
def load_json_file(filename, default_data=None):
    """
    Loads a JSON file and returns its content.
    Returns default data if the file is not found or corrupted.
    """
    if default_data is None:
        default_data = {}
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading data from {filename}: {e}", exc_info=True)
    return default_data

# --- Load Language and Theme Data ---
LANGUAGES = load_json_file('Languages.json')
THEME = load_json_file('Theme.json')

# --- Translator Class ---
class Translator:
    """Manages language selection and translates strings."""
    def __init__(self, initial_lang="en"):
        self._current_lang = initial_lang
        self.strings = {}
        self.set_language(initial_lang)

    def set_language(self, lang_code):
        if lang_code in LANGUAGES:
            self._current_lang = lang_code
            self.strings = LANGUAGES[lang_code]
        else:
            logger.warning(f"Language '{lang_code}' not found. Defaulting to 'en'.")
            self._current_lang = "en"
            self.strings = LANGUAGES.get("en", {})

    def current_language(self):
        """Returns the current active language code."""
        return self._current_lang

    def get_string(self, key, **kwargs):
        """Retrieves a translated string by key with optional formatting."""
        s = self.strings.get(key, key)
        try:
            # If kwargs exist, format. Otherwise, return the string directly.
            if kwargs:
                return s.format(**kwargs)
            return s
        except (KeyError, IndexError) as e:
            logger.warning(f"Error formatting string '{key}' with {kwargs}: {e}. Returning unformatted string.")
            return s
        except Exception as e:
            logger.error(f"An unexpected error occurred while formatting string '{key}' with {kwargs}: {e}. Returning unformatted string.", exc_info=True)
            return s

# --- Global Translator and Settings Manager ---
_ = Translator() # Initialize with default language

class SettingsManager:
    """Manages loading and saving application settings to a JSON file."""
    def __init__(self, filename='Settings.json'):
        self.filename = filename
        self.settings = self.load_settings()

    def load_settings(self):
        """Loads settings from the JSON file."""
        default_settings = {
            'language': 'en',
            'sort_order': 'added_date_desc'
        }
        loaded_settings = load_json_file(self.filename, default_settings)
        return {**default_settings, **loaded_settings}

    def save_settings(self, language, sort_order):
        """Saves the current language and sort order to the settings file."""
        self.settings['language'] = language
        self.settings['sort_order'] = sort_order
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving settings to {self.filename}: {e}", exc_info=True)


# --- API Worker Thread ---
# This class manages API requests in a separate thread to prevent the UI from freezing.
class ApiWorker(QThread):
    finished = pyqtSignal(object, str)  # Signal emitted on successful API response, now includes request_id
    error = pyqtSignal(str)        # Signal emitted on API request error
    worker_completed = pyqtSignal() # Signal emitted when the worker completes, successfully or unsuccessfully

    def __init__(self, url, method='GET', data=None, max_retries=3, initial_retry_delay=1, request_id=None, app_instance=None):
        """
        Initializer for the ApiWorker class.

        Arguments:
            url (str): The URL to make the API request to.
            method (str): HTTP method (e.g., 'GET', 'POST'). Defaults to 'GET'.
            data (dict, optional): JSON data to send with the request. Defaults to None.
            max_retries (int): Number of times to retry the request in case of timeout/error.
            initial_retry_delay (int): Initial delay before the first retry (in seconds).
            request_id (str, optional): A unique ID for this request, used to identify stale responses.
            app_instance (SpeedrunTrackerApp, optional): Main application instance for updating status messages.
        """
        super().__init__()
        self.url = url
        self.method = method
        self.data = data
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.request_timeout = 30 # Increased timeout for API requests to 30 seconds
        self.request_id = request_id # Store the request_id
        self._app_instance = app_instance # Store the main app instance

    def run(self):
        """
        Thread execution method. Makes the API request and emits the result as a signal.
        Includes a retry mechanism for network-related errors.
        """
        retries_attempted = 0
        try:
            while retries_attempted <= self.max_retries:
                try:
                    # Execute HTTP request with specified timeout
                    response = requests.request(self.method, self.url, json=self.data, timeout=self.request_timeout)
                    response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                    self.finished.emit(response.json(), self.request_id) # Emit successful JSON response and request_id
                    return # Exit the run method successfully
                except requests.exceptions.Timeout:
                    error_msg = f"API request timed out: {self.url}"
                    logger.error(error_msg, exc_info=True) # Log timeout errors
                    if retries_attempted < self.max_retries:
                        retry_wait_time = self.initial_retry_delay * (2 ** retries_attempted) # Exponential backoff
                        logger.info(f"{retries_attempted + 1}/{self.max_retries} retrying in {retry_wait_time} seconds: {self.url}")
                        if self._app_instance:
                            self._app_instance.show_status_message(
                                self._app_instance.translator.get_string('timeout_retrying', wait_time=int(retry_wait_time)),
                                is_error=True
                            )
                        time.sleep(retry_wait_time)
                        retries_attempted += 1
                    else:
                        self.error.emit(error_msg) # Emit error when all retries are exhausted
                        return # Exit after emitting error
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429: # Too Many Requests
                        retry_after = e.response.headers.get('Retry-After')
                        wait_time = self.initial_retry_delay * (2 ** retries_attempted) # Exponential backoff as fallback
                        if retry_after:
                            try:
                                wait_time = int(retry_after)
                            except ValueError:
                                pass # Use exponential backoff if Retry-After is not a valid integer

                        if retries_attempted < self.max_retries:
                            if self._app_instance:
                                self._app_instance.show_status_message(
                                    self._app_instance.translator.get_string('rate_limit_waiting', wait_time=int(wait_time)),
                                    is_error=False
                                )
                            logger.warning(f"API request hit rate limit (429). Retrying in {wait_time} seconds: {self.url}")
                            time.sleep(wait_time)
                            retries_attempted += 1
                        else:
                            final_error_msg = self._app_instance.translator.get_string('rate_limit_exhausted') if self._app_instance else "Rate limit retries exhausted."
                            self.error.emit(final_error_msg)
                            return
                    else: # Other HTTP errors
                        error_msg = f"API request error: {e}\nURL: {self.url}"
                        logger.error(error_msg, exc_info=True)
                        self.error.emit(error_msg)
                        return
                except requests.exceptions.RequestException as e:
                    error_msg = f"API request error: {e}\nURL: {self.url}"
                    logger.error(error_msg, exc_info=True) # Log request errors
                    self.error.emit(error_msg)
                    return # Exit after emitting error
                except json.JSONDecodeError:
                    error_msg = f"Failed to parse API response (invalid JSON): {self.url}"
                    logger.error(error_msg, exc_info=True) # Log JSON parsing errors
                    self.error.emit(error_msg)
                    return # Exit after emitting error
        except Exception as e:
            # Catch any other unexpected errors that might occur
            error_msg = f"An unexpected error occurred: {e}"
            logger.error(error_msg, exc_info=True) # Log all other unexpected errors
            self.error.emit(error_msg)
        finally:
            # This block will always execute, ensuring the completed signal is always emitted.
            self.worker_completed.emit()


# --- Helper Function (Dialog Style) ---
def apply_material_style_to_dialog(dialog_instance):
    """
    Applies a consistent material design style to the given QDialog instance.
    """
    if THEME:
        stylesheet = THEME.get('stylesheets', {}).get('dialog', '')
        # Format colors into the stylesheet
        formatted_stylesheet = stylesheet.format(**THEME.get('colors', {}))
        dialog_instance.setStyleSheet(formatted_stylesheet)

# --- Window Classes (SplitsDialog, AllRunnersDialog, etc.) ---
class SplitsDialog(QDialog):
    """
    A dialog window that displays detailed information about speedrun segments (splits).
    """
    def __init__(self, splits_data, run_title="Segment Details", parent=None):
        """
        Initializer for the SplitsDialog class.

        Arguments:
            splits_data (list): A list containing the split data to display.
            run_title (str): Title for the dialog.
            parent (QWidget, optional): The parent of the dialog. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle(run_title)
        self.setGeometry(300, 300, 500, 600)
        # Remove context help button from window flags
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
            self.table_widget.setRowCount(len(splits_data)) # Set row count
            self.table_widget.setColumnCount(2)
            self.table_widget.setHorizontalHeaderLabels([_.get_string('segment_name_column'), _.get_string('time_column')])

            # Stretch columns to fill available space
            self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
            self.table_widget.verticalHeader().setVisible(False) # Hide vertical header
            self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers) # Make table read-only
            self.table_widget.setFont(QFont("Roboto", 10))

            for row, split in enumerate(splits_data):
                segment_name = split.get('name', _.get_string('segment_name_default', row=row + 1))
                # Get realtime in milliseconds, try 'split' then 'realtime_duration_ms' first
                realtime_ms = split.get('split', {}).get('realtime') or split.get('realtime_duration_ms')

                formatted_time = _.get_string('not_available_abbr')
                if realtime_ms is not None:
                    try:
                        total_seconds = float(realtime_ms) / 1000.0
                        hours = int(total_seconds // 3600)
                        minutes = int((total_seconds % 3600) // 60)
                        seconds = int((total_seconds % 60))
                        milliseconds = int((total_seconds * 1000) % 1000)

                        # Format time based on hours, minutes, seconds, milliseconds
                        if hours > 0:
                            formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
                        else:
                            formatted_time = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
                    except ValueError:
                         formatted_time = _.get_string('invalid_time')

                self.table_widget.setItem(row, 0, QTableWidgetItem(segment_name))
                time_item = QTableWidgetItem(formatted_time)
                time_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter) # Align time to the right
                self.table_widget.setItem(row, 1, time_item)

            layout.addWidget(self.table_widget)

        close_button = QPushButton(_.get_string('close_button')) # Close button
        close_button.setFont(QFont("Roboto", 10, QFont.Bold))
        close_button.setFixedSize(100, 35)
        close_button.clicked.connect(self.close) # Connect to close the dialog
        layout.addWidget(close_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)
        apply_material_style_to_dialog(self) # Apply consistent style

class AllRunnersDialog(QDialog):
    """
    A dialog window to display all runners for a specific speedrun.
    """
    def __init__(self, run_title, all_runners, all_weblinks, parent=None):
        """
        Initializer for the AllRunnersDialog class.

        Arguments:
            run_title (str): The title of the run.
            all_runners (list): A list containing all runner names.
            all_weblinks (list): A list containing all runner web links.
            parent (QWidget, optional): The parent of the dialog. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle(_.get_string('all_runners_dialog_title', run_title=run_title))
        # Position the dialog relative to the main window
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
            runners_scroll_area = QScrollArea() # Scroll area for the runner list
            runners_scroll_area.setWidgetResizable(True)
            runners_content_widget = QWidget()
            runners_content_layout = QVBoxLayout(runners_content_widget)
            runners_content_layout.setContentsMargins(0, 0, 0, 0)
            runners_content_layout.setSpacing(5)

            for i, runner_name in enumerate(all_runners):
                runner_weblink = all_weblinks[i] if i < len(all_weblinks) else None

                if runner_weblink:
                    runner_button = QPushButton(runner_name)
                    runner_button.setObjectName("RunnerLinkButtonDialog") # Object name for styling
                    runner_button.setToolTip(_.get_string('open_profile_tooltip', runner_name=runner_name))
                    runner_button.setCursor(Qt.PointingHandCursor) # Hand cursor on hover
                    runner_button.clicked.connect(lambda _, link=runner_weblink: webbrowser.open(link))
                    runner_button.setFont(QFont("Roboto", 11))
                    runner_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                    runner_button.setFixedHeight(30)
                    runners_content_layout.addWidget(runner_button)
                else:
                    runner_label = QLabel(runner_name)
                    runner_label.setStyleSheet(f"color: #FFFFFF;")
                    runner_label.setFont(QFont("Roboto", 11)) # Explicitly set font for consistency
                    runners_content_layout.addWidget(runner_label)

            runners_content_layout.addStretch(1) # Push content to the top
            runners_scroll_area.setWidget(runners_content_widget)
            layout.addWidget(runners_scroll_area)

        close_button = QPushButton(_.get_string('close_button'))
        close_button.setFont(QFont("Roboto", 10, QFont.Bold))
        close_button.setFixedSize(100, 35)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)
        apply_material_style_to_dialog(self)

class LastRecordDialog(QDialog):
    """
    A dialog window to display recently broken world records.
    """
    def __init__(self, broken_records_list, parent=None):
        """
        Initializer for the LastRecordDialog class.

        Arguments:
            broken_records_list (list): A list of broken records.
            parent (QWidget, optional): The parent of the dialog. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle(_.get_string('last_record_dialog_title'))
        # Position the dialog relative to the main window and increase its width
        self.setGeometry(parent.x() + parent.width() // 2 - 350, parent.y() + parent.height() // 2 - 250, 700, 500) # Width increased from 600 to 700
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        if broken_records_list:
            scroll_area = QScrollArea() # Scroll area for record list
            scroll_area.setWidgetResizable(True)
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(15)

            for record_info in broken_records_list:
                record_entry_widget = QWidget()
                record_entry_layout = QVBoxLayout(record_entry_widget)
                record_entry_layout.setContentsMargins(10, 10, 10, 10) # Inner margins for each record entry
                record_entry_layout.setSpacing(5)
                # Apply custom style for record entries - only a single outer frame
                record_entry_widget.setStyleSheet("""
                    QWidget {
                        background-color: #000000; /* Black background */
                        border: 2px solid #FFFFFF; /* White border */
                    }
                    QLabel {
                        font-size: 13px;
                        color: #FFFFFF; /* White text */
                        margin-bottom: 0px; /* Text should align with border */
                        font-weight: normal;
                        border: none; /* IMPORTANT: This removes the inner border of the label */
                    }
                    QLabel.record_detail_label {
                        font-size: 13px;
                        color: #FFFFFF; /* White text */
                        margin-bottom: 0px; /* Text should align with border */
                        border: none; /* IMPORTANT: This removes the inner border of the label */
                    }
                    QPushButton#RecordLinkButton {
                        background-color: transparent;
                        border: 2px solid #FFFFFF; /* White border */
                        color: #FFFFFF; /* White text */
                        padding: 5px 10px; /* Add padding from border */
                        margin: 0;
                        font-size: 13px;
                        font-weight: bold;
                        text-align: center; /* Center button text */
                    }
                    QPushButton#RecordLinkButton:hover {
                        background-color: rgba(255, 255, 255, 0.1); /* Slight transparent white on hover */
                    }
                    QPushButton#RecordLinkButton:pressed {
                        background-color: rgba(255, 255, 255, 0.2); /* Darker transparent white on pressed */
                    }
                """)

                weblink = record_info.get('weblink')
                if weblink and weblink != '#':
                    link_button = QPushButton(_.get_string('options_menu_open_run_page'))
                    link_button.setObjectName("RecordLinkButton")
                    link_button.setCursor(Qt.PointingHandCursor)
                    # Set size policy to Minimum and alignment to center
                    link_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
                    link_button.clicked.connect(lambda _, url=weblink: webbrowser.open(url))
                    record_entry_layout.addWidget(link_button, alignment=Qt.AlignCenter)

                # Show game name
                game_name_label = QLabel(_.get_string('game_label', game_name=record_info['game_name'].strip("'")))
                game_name_label.setFont(QFont("Roboto", 13, QFont.Bold))
                game_name_label.setStyleSheet("color: #FFFFFF;") # White text
                record_entry_layout.addWidget(game_name_label)

                # Show category name and level (if any)
                category_name_text = record_info['category_display_name'].strip("'")
                if record_info['level_name']:
                    category_name_text = f"{record_info['level_name'].strip("'")}: {category_name_text}"
                category_label = QLabel(_.get_string('category_label', category_name=category_name_text))
                category_label.setFont(QFont("Roboto", 13, QFont.Bold))
                category_label.setStyleSheet("color: #FFFFFF;") # White text
                record_entry_layout.addWidget(category_label)

                new_time_label = QLabel(_.get_string('new_time_label', formatted_new_time=record_info['formatted_new_time']))
                new_time_label.setObjectName("record_detail_label")
                record_entry_layout.addWidget(new_time_label)

                # Corrected line: new_player_name now directly contains the names
                players_label = QLabel(_.get_string('runners_label', new_player_name=record_info['new_player_name']))
                players_label.setObjectName("record_detail_label")
                record_entry_layout.addWidget(players_label)

                # Here we simply use date_completed as it comes from _create_broken_record_info, not reformatting
                date_label = QLabel(f"{_.get_string('date_label')}: {record_info['new_run_date'].strip('()')}")
                date_label.setObjectName("DateLabel")
                record_entry_layout.addWidget(date_label)

                content_layout.addWidget(record_entry_widget)

            content_layout.addStretch(1) # Push content to the top
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


class AllRunsDialog(QDialog):
    """
    Displays all runs for a specific game/category/level combination.
    """
    def __init__(self, game_id, category_id, level_id, selected_variable_values, run_title, parent=None):
        super().__init__(parent)
        self.game_id = game_id
        self.category_id = category_id
        self.level_id = level_id
        self.selected_variable_values = selected_variable_values
        self.setWindowTitle(_.get_string('all_runs_dialog_title', run_title=run_title))
        self.setGeometry(parent.x() + parent.width() // 2 - 400, parent.y() + parent.height() // 2 - 350, 800, 700)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.parent_app = parent # Store reference to the main app (for show_all_runners_dialog access)

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

        # Disable row selection and prevent focusing.
        self.table_widget.setSelectionMode(QTableWidget.NoSelection)
        self.table_widget.setFocusPolicy(Qt.NoFocus)

        # Set header section style directly
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #000000;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
                padding: 5px;
                text-align: center;
                border: 2px solid #FFFFFF;
                border-top: none;
                border-left: none;
            }
            QHeaderView::section:last-child {
                border-right: 2px solid #FFFFFF;
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
        # selected_variable_values is now keyed by variable_name, so we need to get variable_id from inside
        if self.selected_variable_values:
            # Check if it's the new format (dict of dicts, keyed by variable display name)
            if all(isinstance(v, dict) and 'variable_id' in v and 'value_id' in v for v in self.selected_variable_values.values()):
                # New format: {'Variable Name': {'variable_id': 'id', 'value_id': 'value_id', ...}}
                # Convert to {variable_id: value_id} for API
                for var_data in self.selected_variable_values.values():
                    variables_str += f"&var-{var_data['variable_id']}={var_data['value_id']}"
            else:
                # Assume old format: {'variable_id': 'value_id'} directly
                for var_id, value_id in self.selected_variable_values.items():
                    variables_str += f"&var-{var_id}={value_id}"

        url_template = "https://www.speedrun.com/api/v1/leaderboards/{game_id}/{path}?top=100&embed=players{variables}"
        path = f"level/{self.level_id}/{self.category_id}" if self.level_id else f"category/{self.category_id}"
        url = url_template.format(game_id=self.game_id, path=path, variables=variables_str)
        
        self.status_label.setText(_.get_string('loading_runs'))
        self.api_worker = ApiWorker(url)
        self.api_worker.finished.connect(self.handle_all_runs_result)
        self.api_worker.error.connect(self.handle_api_error)
        self.api_worker.start()

    def handle_all_runs_result(self, data, request_id):
        self.status_label.setText("") 

        leaderboard_data = data.get('data')
        if not leaderboard_data or not leaderboard_data.get('runs'):
            self.status_label.setText(_.get_string('no_runs_found'))
            return

        self.runs_data = []
        runs = leaderboard_data.get('runs', [])
        
        players_data_embed = leaderboard_data.get('players', {}).get('data', [])
        player_id_map = {p_data['id']: p_data for p_data in players_data_embed if isinstance(p_data, dict) and p_data.get('id')}

        for i, entry in enumerate(runs):
            run_obj = entry.get('run')
            if not run_obj:
                continue

            rank = i + 1
            time_seconds = run_obj.get('times', {}).get('primary_t')
            formatted_time = SpeedrunTrackerApp.format_time(time_seconds)
            weblink = run_obj.get('weblink')
            date_completed = run_obj.get('date', _.get_string('not_available_abbr'))

            player_names = []
            player_weblinks = []
            for run_player_id_obj in run_obj.get('players', []):
                if isinstance(run_player_id_obj, dict):
                    if run_player_id_obj.get('rel') == 'user':
                        player_id_to_find = run_player_id_obj.get('id')
                        p_data = player_id_map.get(player_id_to_find)
                        if p_data:
                            player_names.append(p_data.get('names',{}).get('international', p_data.get('name', _.get_string('unknown_player'))))
                            player_weblinks.append(p_data.get('weblink'))
                        else:
                            player_names.append(_.get_string('unknown_player_id_missing'))
                            player_weblinks.append(None)
                    elif run_player_id_obj.get('rel') == 'guest':
                        player_names.append(run_player_id_obj.get('name', _.get_string('unknown_player')))
                        player_weblinks.append(None)

            self.runs_data.append({
                'rank': rank,
                'players': player_names,
                'player_weblinks': player_weblinks,
                'time_formatted': formatted_time,
                'time_seconds': time_seconds,
                'date': date_completed,
                'weblink': weblink
            })

        self.display_runs_in_table()

    def display_runs_in_table(self):
        self.table_widget.setRowCount(len(self.runs_data))
        for row, run in enumerate(self.runs_data):
            try:
                # Rank column
                rank_item = QTableWidgetItem(f"#{run['rank']}")
                rank_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                rank_item.setFont(QFont("Roboto", 10))
                self.table_widget.setItem(row, 0, rank_item)

                # Runners column
                players_widget = QWidget()
                players_layout = QHBoxLayout(players_widget)
                players_layout.setContentsMargins(0, 0, 0, 0)
                players_layout.setSpacing(0)

                if run['players']:
                    runner_name_to_display = run['players'][0]
                    runner_weblink_to_display = run['player_weblinks'][0]

                    if runner_weblink_to_display:
                        player_button = QPushButton(runner_name_to_display, players_widget)
                        player_button.setObjectName("RunnerLinkButtonInTable")
                        player_button.setCursor(Qt.PointingHandCursor)
                        player_button.clicked.connect(lambda _, link=runner_weblink_to_display: webbrowser.open(link))
                        player_button.setFont(QFont("Roboto", 12))
                        player_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
                        players_layout.addWidget(player_button, alignment=Qt.AlignVCenter)
                    else:
                        player_label = QLabel(runner_name_to_display, players_widget)
                        player_label.setFont(QFont("Roboto", 12))
                        player_label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
                        players_layout.addWidget(player_label, alignment=Qt.AlignVCenter)

                remaining_runners = len(run['players']) - 1
                if remaining_runners > 0:
                    dot_label = QLabel(" • ")
                    dot_label.setObjectName("dot_separator_table")
                    dot_label.setFont(QFont("Roboto", 12))
                    dot_label.setStyleSheet("margin-top: 3px;")
                    players_layout.addWidget(dot_label, alignment=Qt.AlignVCenter)
                    
                    more_button = QPushButton(_.get_string('more_runners_button', count=remaining_runners), players_widget)
                    more_button.setObjectName("MoreRunnersButtonInTable")
                    more_button.setCursor(Qt.PointingHandCursor)
                    more_button.clicked.connect(lambda _, r_names=run['players'], r_links=run['player_weblinks']:
                                                self.parent_app.show_all_runners_dialog(self.windowTitle(), r_names, r_links))
                    more_button.setFont(QFont("Roboto", 12))
                    players_layout.addWidget(more_button, alignment=Qt.AlignVCenter)
                
                players_layout.addStretch(1)
                self.table_widget.setCellWidget(row, 1, players_widget)

                # Time column
                time_widget = QWidget()
                time_layout = QHBoxLayout(time_widget)
                time_layout.setContentsMargins(0, 0, 0, 0)
                time_layout.setSpacing(0)
                time_button = QPushButton(run['time_formatted'], time_widget)
                time_button.setObjectName("TimeLinkButtonInTable")
                time_button.setCursor(Qt.PointingHandCursor)
                time_button.setFont(QFont("Roboto", 12))
                if run['weblink']:
                    time_button.clicked.connect(lambda _, link=run['weblink']: webbrowser.open(link))
                else:
                    time_button.setEnabled(False)
                time_layout.addStretch(1)
                time_layout.addWidget(time_button, alignment=Qt.AlignVCenter)
                time_layout.addStretch(1)
                self.table_widget.setCellWidget(row, 2, time_widget)

                # Date column
                date_item = QTableWidgetItem(run['date'])
                date_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                date_item.setFont(QFont("Roboto", 10))
                self.table_widget.setItem(row, 3, date_item)

            except Exception as e:
                logger.error(f"Error populating table row {row}: {e}", exc_info=True)
                self.status_label.setText(_.get_string('error_populating_table_row', row=row))
                if self.parent_app and self.parent_app.theme:
                    error_color = self.parent_app.theme.get('colors', {}).get('error', '#FF69B4')
                    self.status_label.setStyleSheet(f"color: {error_color};")


    def handle_api_error(self, error_message):
        self.status_label.setText(_.get_string('error_loading_runs', error_message=error_message))
        if self.parent_app and self.parent_app.theme:
            error_color = self.parent_app.theme.get('colors', {}).get('error', '#FF69B4')
            self.status_label.setStyleSheet(f"color: {error_color};")
        logger.error(f"AllRunsDialog API error: {error_message}")


# --- Main Application Class ---
class SpeedrunTrackerApp(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize Theme and Settings
        self.theme = THEME
        self.settings_manager = SettingsManager()
        initial_settings = self.settings_manager.load_settings()

        # Initialize Translator
        self.translator = _
        self.translator.set_language(initial_settings.get('language', 'en'))
        
        # Load Constants from Theme
        self.MAX_DISPLAY_RUNNERS = 2
        self.BASE_ITEM_FONT_SIZE = self.theme.get("fonts", {}).get("base_item_size", 12)
        self.GAME_HEADER_FONT_SIZE = self.theme.get("fonts", {}).get("game_header_size", 18)
        self.OPTIONS_BUTTON_SIZE = self.theme.get("sizes", {}).get("options_button", 36)
        self.HAMBURGER_BUTTON_SIZE = self.theme.get("sizes", {}).get("hamburger_button", 40)

        # State Variables
        self.tracked_runs = {}
        self.save_file = 'Tracked Runs.json'
        self.selected_game_data = {'id': None, 'name': None, 'icon_url': None, 'weblink': None}
        self.selected_level_data = {'id': None, 'name': None}
        # Category data updated to include `is_miscellaneous` flag
        self.selected_category_data = {'id': None, 'name': None, 'is_miscellaneous': False} 
        # selected_variable_values will now be keyed by variable name
        self.selected_variable_values = {} # { 'Variable Name': {'variable_id': 'id', 'value_id': 'value_id', 'value_name': 'value_name'} }
        self.full_game_data_cache = None
        self.full_level_data_cache = None
        self.available_subcategory_variables = [] # Raw list of subcategory variables from API
        self.active_check_workers = []
        self.pending_refresh_api_calls = 0
        self.total_runs_to_check = 0 # New: Total number of runs to check
        self.checked_runs_count = 0  # New: Number of runs checked
        self.broken_records_history = []
        self.has_unseen_new_wrs = False
        self.current_game_search_request_id = None
        self.current_game_details_request_id = None
        self.current_level_categories_request_id = None
        self.current_category_variables_request_id = None
        self.current_sort_order = initial_settings.get('sort_order', 'added_date_desc')
        
        # Status flags to prevent refresh crash
        self.is_checking_records = False
        self.ui_update_needed_after_check = False


        # Timers
        self.autocomplete_timer = QTimer(self)
        self.autocomplete_timer.setSingleShot(True)
        self.autocomplete_timer.timeout.connect(self.search_game_debounced)
        self.current_game_search_worker = None

        self.timer = QTimer(self)
        self.timer.setInterval(300000) # 5 minutes
        self.timer.timeout.connect(self.check_for_new_records)
        
        # UI and Data Loading
        self.init_ui()
        self.apply_material_style()
        self.load_tracked_runs()
        self.timer.start()
        self.check_for_new_records()

    def init_ui(self):
        """Initializes the application's user interface and sets up layouts."""
        self.setWindowTitle(self.translator.get_string('app_title'))
        self.setGeometry(150, 150, 1200, 850)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(12)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        search_and_menu_layout = QHBoxLayout()
        search_and_menu_layout.setContentsMargins(0, 0, 0, 0)
        search_and_menu_layout.setSpacing(10)

        self.hamburger_button = QPushButton("≡")
        self.hamburger_button.setFixedSize(QSize(self.HAMBURGER_BUTTON_SIZE, self.HAMBURGER_BUTTON_SIZE))
        self.hamburger_button.setObjectName("HamburgerButton")
        self.hamburger_button.setToolTip(self.translator.get_string('menu_options'))
        self.hamburger_button.clicked.connect(self.show_options_menu_dialog)
        self.hamburger_button.setFont(QFont(self.theme.get("fonts", {}).get("default_family", "Roboto"), self.theme.get("fonts", {}).get("hamburger_button_font_size", 18), QFont.Bold))

        self.game_search_input = QLineEdit()
        self.game_search_input.setPlaceholderText(self.translator.get_string('search_placeholder'))
        self.game_search_input.setMinimumHeight(40)
        self.game_search_input.setFont(QFont(self.theme.get("fonts", {}).get("default_family", "Roboto"), 11))
        self.game_search_input.textChanged.connect(self.start_autocomplete_timer)

        self.search_button = QPushButton(self.translator.get_string('search_button'))
        self.search_button.setFixedSize(100, 40)
        self.search_button.clicked.connect(self.search_game)
        self.search_button.setFont(QFont(self.theme.get("fonts", {}).get("default_family", "Roboto"), 11, QFont.Bold))

        search_and_menu_layout.addWidget(self.game_search_input)
        search_and_menu_layout.addWidget(self.search_button)
        search_and_menu_layout.addWidget(self.hamburger_button)
        left_layout.addLayout(search_and_menu_layout)

        # ... (Creation of other widgets, texts are set with _.get_string)
        self.game_results_label = QLabel(self.translator.get_string('game_list_label'))
        self.game_results_label.setFont(QFont("Roboto", 11, QFont.Bold))
        self.game_results_list_widget = QListWidget()
        self.game_results_list_widget.setMinimumHeight(120)
        self.game_results_list_widget.itemClicked.connect(self.select_game_from_results)
        self.game_results_list_widget.setFont(QFont("Roboto", 10))
        self.game_results_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.game_results_list_widget.customContextMenuRequested.connect(self.show_game_result_context_menu)
        left_layout.addWidget(self.game_results_label)
        left_layout.addWidget(self.game_results_list_widget)

        self.level_label = QLabel(self.translator.get_string('il_list_label'))
        self.level_label.setFont(QFont("Roboto", 11, QFont.Bold))
        self.level_list_widget = QListWidget()
        self.level_list_widget.setMinimumHeight(100)
        self.level_list_widget.itemClicked.connect(self.select_level_from_results)
        self.level_list_widget.setFont(QFont("Roboto", 10))
        self.level_list_widget.setVisible(False)
        self.level_label.setVisible(False)
        left_layout.addWidget(self.level_label)
        left_layout.addWidget(self.level_list_widget)

        self.category_label = QLabel(self.translator.get_string('category_list_label'))
        self.category_label.setFont(QFont("Roboto", 11, QFont.Bold))
        self.category_list_widget = QListWidget()
        self.category_list_widget.setMinimumHeight(120)
        self.category_list_widget.itemClicked.connect(self.select_category_to_show_variables)
        self.category_list_widget.setFont(QFont("Roboto", 10))
        left_layout.addWidget(self.category_label)
        left_layout.addWidget(self.category_list_widget)

        self.variables_label = QLabel(self.translator.get_string('variables_list_label'))
        self.variables_label.setFont(QFont("Roboto", 11, QFont.Bold))
        self.variables_list_widget = QListWidget()
        self.variables_list_widget.setMinimumHeight(80)
        self.variables_list_widget.setFont(QFont("Roboto", 10))
        self.variables_list_widget.setVisible(False)
        self.variables_label.setVisible(False)
        # selection mode removed, now we'll manage selections manually
        self.variables_list_widget.setSelectionMode(QListWidget.MultiSelection) 
        self.variables_list_widget.itemClicked.connect(self.handle_variable_selection)
        left_layout.addWidget(self.variables_label)
        left_layout.addWidget(self.variables_list_widget)

        self.add_run_button = QPushButton(self.translator.get_string('add_run_button'))
        self.add_run_button.setFixedSize(200, 40)
        self.add_run_button.setObjectName("AddRunButton")
        self.add_run_button.setFont(QFont("Roboto", 11, QFont.Bold))
        self.add_run_button.clicked.connect(self.add_to_tracked)
        self.add_run_button.setEnabled(False)
        left_layout.addWidget(self.add_run_button, alignment=Qt.AlignCenter)
        left_layout.addStretch(1)

        self.tracked_list_widget = QListWidget()
        self.tracked_list_widget.setFont(QFont("Roboto", self.BASE_ITEM_FONT_SIZE))
        self.tracked_list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.tracked_list_widget.verticalScrollBar().setSingleStep(20)
        right_layout.addWidget(self.tracked_list_widget, 1)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Roboto", 10))
        self.status_label.setWordWrap(True)
        self.status_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        right_layout.addWidget(self.status_label)

        # Progress bar removed

        button_container_layout = QHBoxLayout()
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(10)

        self.show_last_record_button = QPushButton(self.translator.get_string('last_record_dialog_title'))
        self.show_last_record_button.setFixedSize(200, 40)
        self.show_last_record_button.setFont(QFont("Roboto", 11, QFont.Bold))
        self.show_last_record_button.clicked.connect(self.show_last_record_notification)
        self.show_last_record_button.setVisible(self.has_unseen_new_wrs)
        button_container_layout.addWidget(self.show_last_record_button, alignment=Qt.AlignCenter)

        self.refresh_button = QPushButton(self.translator.get_string('refresh_button'))
        self.refresh_button.setFixedSize(120, 40)
        self.refresh_button.setFont(QFont("Roboto", 11, QFont.Bold))
        self.refresh_button.clicked.connect(self.check_for_new_records)
        button_container_layout.addWidget(self.refresh_button, alignment=Qt.AlignCenter)

        self.clear_new_wr_button = QPushButton(self.translator.get_string('clear_new_wr_button'))
        self.clear_new_wr_button.setFixedSize(250, 40)
        self.clear_new_wr_button.setFont(QFont("Roboto", 11, QFont.Bold))
        self.clear_new_wr_button.clicked.connect(self.mark_all_new_wrs_as_read)
        self.clear_new_wr_button.setVisible(self.has_unseen_new_wrs)
        button_container_layout.addWidget(self.clear_new_wr_button, alignment=Qt.AlignCenter)

        right_layout.addLayout(button_container_layout)

        main_layout.addLayout(left_layout, 2)
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setObjectName("Separator")
        main_layout.addWidget(separator)
        main_layout.addLayout(right_layout, 5)

        self.setLayout(main_layout)
        self.update_tracked_list_ui()

    def apply_material_style(self):
        """Applies the material design style to the application."""
        if not self.theme:
            return

        colors = self.theme.get('colors', {})
        fonts = self.theme.get('fonts', {})
        sizes = self.theme.get('sizes', {})
        
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(colors.get('background', '#000000')))
        palette.setColor(QPalette.WindowText, QColor(colors.get('on_background', '#FFFFFF')))
        palette.setColor(QPalette.Base, QColor(colors.get('surface', '#000000')))
        palette.setColor(QPalette.AlternateBase, QColor(colors.get('surface_variant', '#000000')))
        palette.setColor(QPalette.ToolTipBase, QColor(colors.get('tooltip_base', '#000000')))
        palette.setColor(QPalette.ToolTipText, QColor(colors.get('tooltip_text', '#FFFFFF')))
        palette.setColor(QPalette.Text, QColor(colors.get('on_surface', '#FFFFFF')))
        palette.setColor(QPalette.Button, QColor(colors.get('surface', '#000000')))
        palette.setColor(QPalette.ButtonText, QColor(colors.get('on_surface', '#FFFFFF')))
        palette.setColor(QPalette.Highlight, QColor(colors.get('highlight', '#1A1A1A')))
        palette.setColor(QPalette.HighlightedText, QColor(colors.get('highlighted_text', '#FF69B4')))
        self.setPalette(palette)

        stylesheet = self.theme.get('stylesheets', {}).get('main_app', '')
        # Format colors, fonts, and sizes into the stylesheet
        format_args = {**colors, **fonts, **sizes, "default_font_family": fonts.get("default_family", "Roboto")}
        format_args["base_item_font_size"] = self.BASE_ITEM_FONT_SIZE
        format_args["options_button_font_size"] = fonts.get("options_button_size", 24)
        format_args["options_button_size"] = self.OPTIONS_BUTTON_SIZE

        self.setStyleSheet(stylesheet.format(**format_args))

    def retranslate_ui(self):
        """Updates all UI text strings according to the currently selected language."""
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

        # Refill lists and other dynamic texts
        temp_game_items_data = []
        for i in range(self.game_results_list_widget.count()):
            item = self.game_results_list_widget.item(i)
            if item and item.data(Qt.UserRole) and isinstance(item.data(Qt.UserRole), dict):
                temp_game_items_data.append(item.data(Qt.UserRole))

        self.game_results_list_widget.clear()
        if temp_game_items_data:
            games = sorted(temp_game_items_data, key=lambda x: x.get('name', '').lower())
            for game_data_from_item in games:
                game_title_display = game_data_from_item.get('name_with_year')
                item = QListWidgetItem(game_title_display)
                item.setData(Qt.UserRole, game_data_from_item)
                self.game_results_list_widget.addItem(item)
        elif self.game_search_input.text().strip():
             self.game_results_list_widget.addItem(self.translator.get_string('no_game_found'))
        
        self.level_list_widget.clear()
        game_name_for_translation = self.selected_game_data.get('name', '')
        level_name_for_translation = self.selected_level_data.get('name', '')

        if self.full_game_data_cache and self.full_game_data_cache.get('levels', {}).get('data'):
            self.handle_level_result({'data': self.full_game_data_cache.get('levels', {}).get('data', [])}, self.current_game_details_request_id)
        elif self.selected_game_data['id'] and not self.full_game_data_cache:
            self.level_list_widget.addItem(self.translator.get_string('no_individual_level_found'))
            self.level_list_widget.setVisible(True)
            self.level_label.setVisible(True)
            self.level_list_widget.setEnabled(False)

        self.category_list_widget.clear()
        if self.selected_level_data['id']: 
            if self.full_level_data_cache:
                self.handle_level_category_result({'data': self.full_level_data_cache}, self.current_category_variables_request_id)
            else:
                self.category_list_widget.addItem(self.translator.get_string('no_suitable_category_for_level', level_name=level_name_for_translation))
        elif self.selected_game_data['id']:
            if self.full_game_data_cache:
                self.handle_category_result({'data': self.full_game_data_cache.get('categories', {}).get('data', [])}, self.current_game_details_request_id)
            else:
                self.category_list_widget.addItem(self.translator.get_string('no_suitable_category_for_game', game_name=game_name_for_translation))

        self.variables_list_widget.clear()
        if self.selected_category_data['id'] and self.available_subcategory_variables:
             mock_variables_data = {'data': self.available_subcategory_variables}
             self.handle_variables_result(mock_variables_data, self.current_category_variables_request_id)
        elif self.selected_category_data['id'] and not self.available_subcategory_variables:
            self.variables_list_widget.addItem(self.translator.get_string('no_variables_found'))
            self.variables_list_widget.setVisible(True)
            self.variables_label.setVisible(True)
            self.variables_list_widget.setEnabled(False)

        self.update_tracked_list_ui()
        self._update_add_run_button_state()
        self.apply_material_style()

    def show_options_menu_dialog(self):
        """Displays the options menu when the hamburger menu button is clicked."""
        menu = QMenu(self)
        
        language_menu = menu.addMenu(self.translator.get_string('menu_language'))
        en_action = language_menu.addAction("English")
        tr_action = language_menu.addAction("Türkçe")
        en_action.triggered.connect(lambda: self.change_language_from_menu("en"))
        tr_action.triggered.connect(lambda: self.change_language_from_menu("tr"))
        en_action.setCheckable(True)
        tr_action.setCheckable(True)
        if self.translator.current_language() == "en":
            en_action.setChecked(True)
        else:
            tr_action.setChecked(True)

        sort_menu = menu.addMenu(self.translator.get_string('menu_sort_order'))
        sort_added_date_desc_action = sort_menu.addAction(self.translator.get_string('sort_added_date_desc'))
        sort_game_name_asc_action = sort_menu.addAction(self.translator.get_string('sort_game_name_asc'))
        sort_added_date_desc_action.triggered.connect(lambda: self.change_sort_order_from_menu("added_date_desc"))
        sort_game_name_asc_action.triggered.connect(lambda: self.change_sort_order_from_menu("game_name_asc"))
        sort_added_date_desc_action.setCheckable(True)
        sort_game_name_asc_action.setCheckable(True)
        if self.current_sort_order == "added_date_desc":
            sort_added_date_desc_action.setChecked(True)
        else:
            sort_game_name_asc_action.setChecked(True)

        button_pos = self.hamburger_button.mapToGlobal(self.hamburger_button.rect().bottomLeft())
        menu.exec_(button_pos)

    def change_language_from_menu(self, lang_code):
        """Handles language selection from the menu."""
        if self.translator.current_language() != lang_code:
            self.translator.set_language(lang_code)
            self.settings_manager.save_settings(lang_code, self.current_sort_order)
            self.retranslate_ui()

    def change_sort_order_from_menu(self, sort_order):
        """Handles sort order selection from the menu."""
        if self.current_sort_order != sort_order:
            self.current_sort_order = sort_order
            self.settings_manager.save_settings(self.translator.current_language(), self.current_sort_order)
            self.update_tracked_list_ui()

    # ... (Rest of the methods remain the same)
    # load_tracked_runs, save_tracked_runs, _reset_all_selections, etc.
    # These methods are already set up to use the global `_` (Translator) and `THEME` variables.
    def load_tracked_runs(self):
        """
        Loads tracked run data from a JSON file.
        """
        self.tracked_runs = load_json_file(self.save_file, {})
        for game_id, game_data in self.tracked_runs.items():
            if '_added_timestamp' not in game_data:
                game_data['_added_timestamp'] = 0 
        
        self.has_unseen_new_wrs = False
        self.broken_records_history = []
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
                            # Pass level_data argument to _create_broken_record_info
                            self.broken_records_history.append(self._create_broken_record_info(game_data, category_data, level_data))

        self.show_last_record_button.setVisible(self.has_unseen_new_wrs)
        self.clear_new_wr_button.setVisible(self.has_unseen_new_wrs)
        self.update_tracked_list_ui()

    def save_tracked_runs(self):
        """
        Saves the current tracked run data to a JSON file.
        """
        try:
            with open(self.save_file, 'w', encoding='utf-8') as f:
                json.dump(self.tracked_runs, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving tracked runs: {e}", exc_info=True)
            self.show_status_message(self.translator.get_string('status_message_save_error'), is_error=True)

    def _reset_all_selections(self):
        """
        Resets all game, level, category, and variable selections, and clears game search results.
        """
        self.selected_game_data = {'id': None, 'name': None, 'icon_url': None, 'weblink': None}
        self.full_game_data_cache = None
        self.game_results_list_widget.clear()
        self._reset_lower_selections()

    def _reset_lower_selections(self):
        """
        Resets level, category, and variable selections, but preserves game search results.
        """
        self.selected_level_data = {'id': None, 'name': None}
        # Reset is_miscellaneous flag here too
        self.selected_category_data = {'id': None, 'name': None, 'is_miscellaneous': False} 
        self.selected_variable_values = {}
        self.full_level_data_cache = None
        self.available_subcategory_variables = []

        self.category_list_widget.clear()
        self.level_list_widget.clear()
        self.variables_list_widget.clear()

        self.level_list_widget.setVisible(False)
        self.level_label.setVisible(False)
        self.variables_list_widget.setVisible(False)
        self.variables_label.setVisible(False)
        self.add_run_button.setEnabled(False)

    def start_autocomplete_timer(self):
        """
        Restarts the autocomplete timer when text changes.
        """
        self.autocomplete_timer.stop()
        self.autocomplete_timer.start(500)

    def search_game_debounced(self):
        """
        Triggered by the autocomplete timer. Performs the search if the input is long enough.
        """
        game_name = self.game_search_input.text().strip()
        if len(game_name) < 2:
            self.game_results_list_widget.clear()
            self._reset_all_selections()
            return
        self.search_game(game_name=game_name)

    def search_game(self, game_name=None):
        """
        Initiates a game search based on the provided name.
        """
        if game_name is None:
            game_name = self.game_search_input.text().strip()

        if not game_name:
            self.show_status_message(self.translator.get_string('search_placeholder'), is_error=True)
            return

        if self.current_game_search_worker and self.current_game_search_worker.isRunning():
            self.current_game_search_worker.quit()
            self.current_game_search_worker.wait(100)

        self._reset_all_selections()

        self.search_button.setEnabled(False)
        self.search_button.setText(self.translator.get_string('searching_button'))

        self.current_game_search_request_id = str(time.time())
        self.current_game_search_worker = ApiWorker(
            f"https://www.speedrun.com/api/v1/games?name={requests.utils.quote(game_name)}&max=20&embed=platforms",
            request_id=self.current_game_search_request_id,
            app_instance=self # Pass app_instance
        )
        self.current_game_search_worker.finished.connect(self.handle_game_search_result)
        self.current_game_search_worker.error.connect(self.handle_api_error)
        self.current_game_search_worker.start()

    def handle_game_search_result(self, data, request_id):
        """
        Handles the result of the game search API call.
        """
        if request_id != self.current_game_search_request_id:
            logger.info("handle_game_search_result: Ignoring stale response.")
            return

        self.search_button.setEnabled(True)
        self.search_button.setText(self.translator.get_string('search_button'))
        self.game_results_list_widget.clear()

        if data and data.get('data'):
            games = sorted(data['data'], key=lambda x: x.get('names', {}).get('international', '').lower())
            if not games:
                self.game_results_list_widget.addItem(self.translator.get_string('no_game_found'))
                return

            for game in games:
                game_id = game.get('id')
                game_international_name = game.get('names', {}).get('international')
                if not game_id or not game_international_name:
                    logger.warning(f"handle_game_search_result: Missing game data: {game}")
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
        Displays the context menu when an item in the search results list is right-clicked.
        """
        item = self.game_results_list_widget.itemAt(position)
        if item:
            game_data_from_item = item.data(Qt.UserRole)
            if game_data_from_item and game_data_from_item.get('weblink'):
                menu = QMenu(self)
                open_speedrun_link_action = menu.addAction(self.translator.get_string('open_speedrun_com_page'))
                open_speedrun_link_action.triggered.connect(
                    lambda: self._open_weblink(game_data_from_item.get('weblink'), self.translator.get_string('web_link_not_available', item_type="game"))
                )
                menu.exec_(self.game_results_list_widget.mapToGlobal(position))

    def select_game_from_results(self, item):
        """
        Handles the selection of a game from the search results list.
        """
        game_data_from_item = item.data(Qt.UserRole)
        if not game_data_from_item:
            logger.warning("select_game_from_results: No data found for the selected game item.")
            self.show_status_message(self.translator.get_string('invalid_game_selection'), is_error=True)
            return

        self._reset_lower_selections()

        self.selected_game_data['id'] = game_data_from_item.get('id')
        self.selected_game_data['name'] = game_data_from_item.get('name_with_year')
        self.selected_game_data['weblink'] = game_data_from_item.get('weblink')

        if not self.selected_game_data['id'] or not self.selected_game_data['name']:
            self.show_status_message(self.translator.get_string('missing_game_id_name'), is_error=True)
            logger.error(f"select_game_from_results: Missing game ID or name: {game_data_from_item}")
            return

        assets = game_data_from_item.get('assets', {})
        icon_asset = assets.get('cover-tiny') or assets.get('icon')
        self.selected_game_data['icon_url'] = icon_asset.get('uri') if icon_asset else None

        self.show_status_message(self.translator.get_string('loading_game_details', game_name=self.selected_game_data['name']))

        if hasattr(self, 'details_fetch_worker') and self.details_fetch_worker.isRunning():
            self.details_fetch_worker.quit()
            self.details_fetch_worker.wait(100)

        self.current_game_details_request_id = str(time.time())

        api_url = f"https://www.speedrun.com/api/v1/games/{self.selected_game_data['id']}?embed=levels,categories.variables"
        self.details_fetch_worker = ApiWorker(api_url, request_id=self.current_game_details_request_id, app_instance=self)
        self.details_fetch_worker.finished.connect(self.handle_game_details_result)
        self.details_fetch_worker.error.connect(self.handle_api_error)
        self.details_fetch_worker.start()

    def handle_game_details_result(self, data, request_id):
        """
        Handles the result of fetching game details (levels and categories).
        """
        if request_id != self.current_game_details_request_id:
            logger.info("handle_game_details_result: Ignoring stale response.")
            return

        game_data = data.get('data')
        if not game_data:
            self.show_status_message(self.translator.get_string('loading_game_details_failed'), is_error=True)
            logger.error(f"handle_game_details_result: Failed to load game details: {self.selected_game_data['id']}")
            return

        self.full_game_data_cache = game_data

        levels_payload = {'data': game_data.get('levels', {}).get('data', [])}
        categories_payload = {'data': game_data.get('categories', {}).get('data', [])}

        self.handle_level_result(levels_payload, request_id)
        self.handle_category_result(categories_payload, request_id)
        self.show_status_message(self.translator.get_string('game_details_loaded', game_name=self.selected_game_data['name']), is_error=False)
        self.on_category_variables_worker_completed()


    def handle_level_result(self, data, request_id):
        """
        Populates the level list widget with available levels for the selected game.
        """
        if request_id != self.current_game_details_request_id and request_id != self.current_level_categories_request_id:
            logger.info("handle_level_result: Ignoring stale response.")
            return

        self.level_list_widget.clear()

        if data and data.get('data'):
            self.level_list_widget.setVisible(True)
            self.level_label.setVisible(True)
            full_game_option = QListWidgetItem(self.translator.get_string('full_game_option'))
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
                    logger.warning(f"handle_level_result: Missing level data: {level}")

            self.level_list_widget.setEnabled(True)
        else:
            self.level_list_widget.addItem(self.translator.get_string('no_individual_level_found'))
            self.level_list_widget.setVisible(True)
            self.level_label.setVisible(True)
            self.level_list_widget.setEnabled(False)

    def select_level_from_results(self, item):
        """
        Handles the selection of a level from the level list.
        """
        level_data_from_item = item.data(Qt.UserRole)
        if level_data_from_item is None:
            return

        self.category_list_widget.clear()
        self.variables_list_widget.clear()
        self.variables_list_widget.setVisible(False)
        self.variables_label.setVisible(False)
        # Reset is_miscellaneous flag here too
        self.selected_category_data = {'id': None, 'name': None, 'is_miscellaneous': False} 
        self.selected_variable_values = {}
        self.full_level_data_cache = None
        self.add_run_button.setEnabled(False)
        self.available_subcategory_variables = []

        if hasattr(self, 'level_category_fetch_worker') and self.level_category_fetch_worker.isRunning():
            self.level_category_fetch_worker.quit()
            self.level_category_fetch_worker.wait(100)

        self.current_category_variables_request_id = str(time.time())
        self.category_list_widget.setEnabled(False)
        self.variables_list_widget.setEnabled(False)


        if level_data_from_item == "full_game_no_level":
            self.selected_level_data = {'id': None, 'name': None}
            if self.full_game_data_cache:
                 categories_payload = {'data': self.full_game_data_cache.get('categories', {}).get('data', [])}
                 self.handle_category_result(categories_payload, self.current_game_details_request_id)
                 self.on_category_variables_worker_completed()
            else:
                 self.category_fetch_worker = ApiWorker(
                     f"https://www.speedrun.com/api/v1/games/{self.selected_game_data['id']}/categories?embed=variables",
                     request_id=self.current_category_variables_request_id,
                     app_instance=self # Pass app_instance
                 )
                 self.category_fetch_worker.finished.connect(self.handle_category_result)
                 self.category_fetch_worker.error.connect(self.handle_api_error)
                 self.category_fetch_worker.worker_completed.connect(self.on_category_variables_worker_completed)
                 self.category_fetch_worker.start()
            self.show_status_message(self.translator.get_string('loading_full_game_categories'), is_error=False)
        else:
            self.selected_level_data['id'] = level_data_from_item['id']
            self.selected_level_data['name'] = level_data_from_item['name']
            self.show_status_message(self.translator.get_string('level_categories_loading', level_name=self.selected_level_data['name']))
            api_url = f"https://www.speedrun.com/api/v1/levels/{self.selected_level_data['id']}/categories?embed=variables"
            self.level_category_fetch_worker = ApiWorker(api_url, request_id=self.current_category_variables_request_id, app_instance=self)
            self.level_category_fetch_worker.finished.connect(self.handle_level_category_result)
            self.level_category_fetch_worker.error.connect(self.handle_api_error)
            self.level_category_fetch_worker.worker_completed.connect(self.on_category_variables_worker_completed)
            self.level_category_fetch_worker.start()

    def handle_level_category_result(self, data, request_id):
        """
        Caches level-specific categories and passes them to the general category handler.
        """
        if request_id != self.current_category_variables_request_id:
            logger.info("handle_level_category_result: Ignoring stale response.")
            return

        self.full_level_data_cache = data.get('data', [])
        self.handle_category_result(data, request_id)
        self.show_status_message(self.translator.get_string('categories_loaded'), is_error=False)

    def handle_category_result(self, data, request_id):
        """
        Populates the category list widget.
        """
        if request_id != self.current_category_variables_request_id and request_id != self.current_game_details_request_id:
            logger.info("handle_category_result: Ignoring stale response.")
            return

        self.category_list_widget.clear()
        categories_added = False
        self.add_run_button.setEnabled(False)
        self.available_subcategory_variables = []

        per_game_categories = []
        per_level_categories = []

        if data and data.get('data'):
            for category in data['data']:
                category_id = category.get('id')
                category_name = category.get('name')
                category_type = category.get('type')
                if not category_id or not category_name or not category_type:
                    logger.warning(f"handle_category_result: Missing category data: {category}")
                    continue

                item_text = category_name
                if category.get('miscellaneous', False):
                    item_text += self.translator.get_string('miscellaneous_category')

                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, category)

                if category_type == 'per-game':
                    per_game_categories.append(item)
                elif category_type == 'per-level':
                    per_level_categories.append(item)
        
        if self.selected_level_data.get('id'):
            if per_level_categories:
                self.category_list_widget.addItem(self.translator.get_string('separator_per_level_categories'))
                for item in per_level_categories: self.category_list_widget.addItem(item)
                categories_added = True
            if per_game_categories:
                self.category_list_widget.addItem(self.translator.get_string('separator_per_game_categories'))
                for item in per_game_categories: self.category_list_widget.addItem(item)
                categories_added = True
        else:
            if per_game_categories:
                for item in per_game_categories: self.category_list_widget.addItem(item)
                categories_added = True

        if not categories_added:
            msg_key = 'no_suitable_category'
            format_args = {}
            if self.selected_level_data.get('id'):
                msg_key = 'no_suitable_category_for_level'
                format_args = {'level_name': self.selected_level_data.get('name', '')} # Added default ''
            elif self.selected_game_data.get('id'):
                msg_key = 'no_suitable_category_for_game'
                format_args = {'game_name': self.selected_game_data.get('name', '')} # Added default ''
            self.category_list_widget.addItem(self.translator.get_string(msg_key, **format_args))

        self.variables_list_widget.clear()
        self.variables_list_widget.setVisible(False)
        self.variables_label.setVisible(False)
        # Reset is_miscellaneous to default here too
        self.selected_category_data = {'id': None, 'name': None, 'is_miscellaneous': False} 
        self.selected_variable_values = {}
        self._update_add_run_button_state()

    def select_category_to_show_variables(self, item):
        """
        Handles the selection of a category and displays its associated variables.
        """
        if item.text().startswith("---"):
            return

        category_data_from_item = item.data(Qt.UserRole)
        if not category_data_from_item:
            logger.warning("select_category_to_show_variables: No data found for the selected category item.")
            self.variables_list_widget.clear()
            self.variables_list_widget.setVisible(False)
            self.variables_label.setVisible(False)
            self.show_status_message(self.translator.get_string('invalid_category_selection'), is_error=True)
            self.add_run_button.setEnabled(False)
            return

        self.selected_category_data['id'] = category_data_from_item.get('id')
        self.selected_category_data['name'] = category_data_from_item.get('name')
        # Store 'miscellaneous' flag for use in tracked runs
        self.selected_category_data['is_miscellaneous'] = category_data_from_item.get('miscellaneous', False)

        self.variables_list_widget.clear()
        self.variables_list_widget.setVisible(False)
        self.variables_label.setVisible(False)
        self.selected_variable_values = {}
        self.add_run_button.setEnabled(False)
        self.available_subcategory_variables = []

        if hasattr(self, 'category_variables_fetch_worker') and self.category_variables_fetch_worker.isRunning():
            self.category_variables_fetch_worker.quit()
            self.category_variables_fetch_worker.wait(100)
            
        self.current_category_variables_request_id = str(time.time())
        self.category_list_widget.setEnabled(False)
        self.variables_list_widget.setEnabled(False)

        variables_data = category_data_from_item.get('variables', {})
        variables_payload = {'data': variables_data.get('data', [])}
        
        if variables_payload['data']:
            self.handle_variables_result(variables_payload, self.current_category_variables_request_id)
            self.on_category_variables_worker_completed()
        else:
            self.variables_list_widget.clear()
            self.variables_list_widget.setVisible(False)
            self.variables_label.setVisible(False)
            self.show_status_message(self.translator.get_string('no_variables_found'), is_error=False)
            self._update_add_run_button_state()
            self.on_category_variables_worker_completed()


    def _get_non_obsolete_variable_values(self, variable_data):
        """
        Returns a dictionary of non-obsolete values for a given variable.
        """
        non_obsolete_values = {}
        values_data = variable_data.get('values', {}).get('values', {})
        for value_id, value_info in values_data.items():
            if not value_info.get('obsoletes', False):
                non_obsolete_values[value_id] = value_info
        return non_obsolete_values

    def handle_variables_result(self, data, request_id):
        """
        Populates the variables list widget with available subcategory variables.
        """
        logger.info(f"handle_variables_result called. request_id: {request_id}")
        if request_id != self.current_category_variables_request_id:
            logger.info("handle_variables_result: Ignoring stale response.")
            return

        self.variables_list_widget.clear()
        self.variables_list_widget.setVisible(False)
        self.variables_label.setVisible(False)
        self.selected_variable_values = {} # Clear selected variable values each time
        self.available_subcategory_variables = []

        if data and isinstance(data.get('data'), list):
            for variable in data['data']:
                if not isinstance(variable, dict):
                    logger.warning(f"handle_variables_result: Unexpected variable item type: {type(variable)}.")
                    continue

                variable_id = variable.get('id')
                variable_name = variable.get('name') # Variable name
                variable_is_subcategory = variable.get('is-subcategory')

                if variable_is_subcategory and variable_id and variable_name:
                    non_obsolete_values = self._get_non_obsolete_variable_values(variable)
                    if non_obsolete_values:
                        variable_copy = variable.copy()
                        variable_copy['values'] = {'values': non_obsolete_values}
                        self.available_subcategory_variables.append(variable_copy)
                        logger.info(f"Added subcategory variable: {variable_name} (ID: {variable_id})")
                else:
                    logger.warning(f"handle_variables_result: Missing subcategory variable data or not is-subcategory: {variable}.")

        if not self.available_subcategory_variables:
            self.show_status_message(self.translator.get_string('no_variables_found'), is_error=False)
            self._update_add_run_button_state()
            return

        # Auto-select for single variable, single value case (still by ID, not variable name)
        # This part remains unchanged because the auto-selection here refers to a single logical variable from the API.
        if len(self.available_subcategory_variables) == 1:
            single_variable = self.available_subcategory_variables[0]
            non_obsolete_values = single_variable['values']['values']
            if len(non_obsolete_values) == 1:
                variable_id = single_variable['id']
                value_id, value_info = list(non_obsolete_values.items())[0]
                # Update selected_variable_values by variable name
                self.selected_variable_values[single_variable['name']] = {'variable_id': variable_id, 'value_id': value_id, 'value_name': value_info['label']}
                
                self.variables_list_widget.setVisible(False)
                self.variables_label.setVisible(False)
                self.show_status_message(self.translator.get_string('variable_auto_selected', variable_name=single_variable['name']), is_error=False)
                logger.info(f"Automatically selected single subcategory variable: {single_variable['name']} -> {value_info['label']}")
                self._update_add_run_button_state()
                return

        self.variables_list_widget.setVisible(True)
        self.variables_label.setVisible(True)
        self.variables_list_widget.setEnabled(True)

        # Add ID to header if variable names are duplicated
        variable_names = [v['name'] for v in self.available_subcategory_variables]
        name_counts = {name: variable_names.count(name) for name in set(variable_names)}

        for variable in self.available_subcategory_variables:
            variable_id = variable.get('id')
            variable_name = variable.get('name')
            variable_values_data = variable.get('values', {}).get('values', {})
            
            header_text = self.translator.get_string('select_variable_header', variable_name=variable_name)
            if name_counts.get(variable_name, 0) > 1:
                header_text += f" (ID: {variable_id})" # Add ID to header if name is duplicated

            variable_header_item = QListWidgetItem(header_text)
            variable_header_item.setFont(QFont("Roboto", 10, QFont.Bold))
            variable_header_item.setForeground(QColor("#BBBBBB"))
            variable_header_item.setFlags(variable_header_item.flags() & ~Qt.ItemIsSelectable)
            self.variables_list_widget.addItem(variable_header_item)

            if isinstance(variable_values_data, dict):
                for value_id, value_info in variable_values_data.items():
                    if not isinstance(value_info, dict):
                        logger.warning(f"handle_variables_result: Unexpected variable value item type: {type(value_info)}.")
                        continue
                    item_text = f"  {variable_name}: {value_info.get('label', value_id)}"
                    item = QListWidgetItem(item_text)
                    # Added variable_display_name (variable_name) to item.data(Qt.UserRole)
                    item.setData(Qt.UserRole, {'variable_id': variable_id, 'value_id': value_id, 'value_name': value_info.get('label', value_id), 'variable_display_name': variable_name})
                    
                    # If this item is already selected (due to a previous selection), show it as selected in the UI too
                    if variable_name in self.selected_variable_values and \
                       self.selected_variable_values[variable_name]['variable_id'] == variable_id and \
                       self.selected_variable_values[variable_name]['value_id'] == value_id:
                        item.setSelected(True)

                    self.variables_list_widget.addItem(item)
            else:
                logger.warning(f"handle_variables_result: Unexpected variable values format: {type(variable_values_data)}. Variable: {variable_name}")
        self._update_add_run_button_state()

    def handle_variable_selection(self, clicked_item):
        """
        Handles selection/deselection of variable options.
        Ensures that only one option from the same variable (with the same display name) can be selected.

        Args:
            clicked_item (QListWidgetItem): The clicked item.
        """
        logger.info(f"handle_variable_selection called: '{clicked_item.text()}'")

        # Ignore header item clicks
        if clicked_item.text().strip().startswith("---"):
            clicked_item.setSelected(False) # Header should never be selectable
            logger.info("Header item clicked, ignoring selection.")
            return

        variable_data = clicked_item.data(Qt.UserRole)
        if not (variable_data and all(k in variable_data for k in ['variable_id', 'value_id', 'value_name', 'variable_display_name'])):
            logger.warning(f"handle_variable_selection: Missing or invalid variable selection data: {variable_data}")
            self.show_status_message(self.translator.get_string('invalid_variable_selection'), is_error=True)
            self.add_run_button.setEnabled(False)
            return

        clicked_variable_id = variable_data['variable_id']
        clicked_value_id = variable_data['value_id']
        clicked_value_name = variable_data['value_name']
        clicked_variable_display_name = variable_data['variable_display_name']

        # Determine if this click is intended to deselect an already active item
        is_deselection = (
            clicked_variable_display_name in self.selected_variable_values and
            self.selected_variable_values[clicked_variable_display_name]['variable_id'] == clicked_variable_id and
            self.selected_variable_values[clicked_variable_display_name]['value_id'] == clicked_value_id
        )

        # Clear all selections within this variable name group (both in UI and internal state)
        for i in range(self.variables_list_widget.count()):
            item = self.variables_list_widget.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data and item_data.get('variable_display_name') == clicked_variable_display_name:
                if item.isSelected():
                    item.setSelected(False) # Deselect in UI
                    logger.info(f"Cleared UI selection for variable name '{clicked_variable_display_name}': '{item.text()}'")
        
        # Always remove the entry for this variable name group from internal state
        if clicked_variable_display_name in self.selected_variable_values:
            del self.selected_variable_values[clicked_variable_display_name]
            logger.info(f"Cleared internal state for variable name '{clicked_variable_display_name}'.")

        # If the clicked item was not previously selected (i.e., user clicked a new item or an unselected one),
        # select it. If it was previously selected, we already deselected it above, so we don't re-select here.
        if not is_deselection:
            clicked_item.setSelected(True) # Select in UI
            self.selected_variable_values[clicked_variable_display_name] = { 
                'variable_id': clicked_variable_id, 
                'value_id': clicked_value_id, 
                'value_name': clicked_value_name 
            }
            logger.info(f"Set new selection for variable name '{clicked_variable_display_name}': '{clicked_item.text()}'")
        else:
            logger.info(f"User clicked an already active item ({clicked_item.text()}), effectively deselecting it from internal state for variable name '{clicked_variable_display_name}'.")

        self._update_add_run_button_state()
        logger.info(f"_update_add_run_button_state called. Current selected_variable_values: {self.selected_variable_values}")


    def _update_add_run_button_state(self):
        """
        Enables/disables the "Track Run" button.
        """
        logger.info(f"_update_add_run_button_state called. selected_game_data: {self.selected_game_data['id']}, selected_category_data: {self.selected_category_data['id']}")
        logger.info(f"available_subcategory_variables: {self.available_subcategory_variables}")
        logger.info(f"selected_variable_values (current selections): {self.selected_variable_values}")


        is_game_selected = self.selected_game_data['id'] is not None
        is_category_selected = self.selected_category_data['id'] is not None

        if not is_game_selected or not is_category_selected:
            self.add_run_button.setEnabled(False)
            logger.info("Game or category not selected, button disabled.")
            return

        if self.available_subcategory_variables:
            # Create a unique set of required variable names
            unique_variable_names_needed = {var_def['name'] for var_def in self.available_subcategory_variables}
            
            # Check if all required variable names have a selection in selected_variable_values
            all_required_variable_names_selected = True
            missing_vars_names = [] # New list to collect missing variable names
            for var_name in unique_variable_names_needed:
                if var_name not in self.selected_variable_values:
                    all_required_variable_names_selected = False
                    missing_vars_names.append(var_name)
            
            if not all_required_variable_names_selected:
                missing_str = ", ".join(sorted(missing_vars_names)) # Sort and join missing variable names
                self.show_status_message(self.translator.get_string('missing_variable_selection', missing_vars=missing_str), is_error=True)
                self.add_run_button.setEnabled(False)
                logger.info(f"Missing variable selection (by name): {missing_str}, button disabled.")
                return
            else:
                self.show_status_message("") # Clear status message if there was an error message before
        else:
            self.show_status_message("") # Clear status message if no variables and there was a previous error message

        is_run_already_tracked = False
        game_id = self.selected_game_data['id']
        if game_id in self.tracked_runs:
            game_data = self.tracked_runs[game_id]
            # Reconstruct variable_id:value_id pairs for API call and record key
            # This part is already handled correctly within `_create_category_item_widget` and `add_to_tracked`.
            # Here we just use the existing selected_variable_values for checking.
            current_selected_vars_for_key = {v['variable_id']: v['value_id'] for k, v in sorted(self.selected_variable_values.items())}
            current_tracked_key = f"{self.selected_category_data['id']}-{json.dumps(current_selected_vars_for_key, sort_keys=True)}"
            level_id = self.selected_level_data['id']

            if not level_id:
                if current_tracked_key in game_data.get('full_game_categories', {}):
                    is_run_already_tracked = True
            elif level_id in game_data.get('levels', {}) and current_tracked_key in game_data['levels'][level_id].get('categories', {}):
                is_run_already_tracked = True

        if is_run_already_tracked:
            self.show_status_message(self.translator.get_string('run_already_tracked', display_category_name=self.selected_category_data.get('name', '')), is_error=True) # Added default ''
            self.add_run_button.setEnabled(False)
            logger.info("Run already tracked, button disabled.")
        else:
            # Only clear if the status label text contains the `run_already_tracked` message, keep other valid messages.
            # This check can be a bit tricky. Simply, if the status label text starts with the `run_already_tracked` message.
            if self.status_label.text().startswith(self.translator.get_string('run_already_tracked', display_category_name="").split('{}')[0]):
                 self.show_status_message("") # Clear previous "already tracked" message
            self.add_run_button.setEnabled(True)
            logger.info("Button enabled.")

    def add_to_tracked(self):
        """
        Adds the selected run to tracked runs.
        """
        if not self.selected_category_data['id']:
            self.show_status_message(self.translator.get_string('track_category_missing'), is_error=True)
            return
        if not self.add_run_button.isEnabled():
            self.show_status_message(self.translator.get_string('add_run_hint_already_tracked'), is_error=True)
            return
        if not self.selected_game_data['id'] or not self.selected_game_data['name']:
            self.show_status_message(self.translator.get_string('game_not_selected'), is_error=True)
            return

        game_id = self.selected_game_data['id']
        if game_id not in self.tracked_runs:
            self.tracked_runs[game_id] = {
                'name': self.selected_game_data['name'],
                'icon_url': self.selected_game_data['icon_url'],
                'weblink': self.selected_game_data['weblink'],
                'full_game_categories': {},
                'levels': {},
                '_added_timestamp': time.time()
            }

        variable_query_params = ""
        display_variable_names = []
        # Create variable_id:value_id pairs for API call and record key
        actual_selected_variables_for_api_and_key = {} 
        # This is the variable values to be stored in `run_info['variables']` (new format)
        selected_variable_values_to_store_in_run_info = self.selected_variable_values.copy() 

        if selected_variable_values_to_store_in_run_info:
            for var_display_name in sorted(selected_variable_values_to_store_in_run_info.keys()):
                val_data = selected_variable_values_to_store_in_run_info[var_display_name]
                var_id = val_data['variable_id']
                val_id = val_data['value_id']
                variable_query_params += f"&var-{var_id}={val_id}"
                display_variable_names.append(val_data['value_name'])
                actual_selected_variables_for_api_and_key[var_id] = val_id


        display_category_name_full = self.selected_category_data['name']
        if self.selected_level_data['id']:
            display_category_name_full = f"{self.selected_level_data['name']}: {display_category_name_full}"
        if display_variable_names:
            display_variable_names.sort() # Sort display names
            display_category_name_full += f" ({', '.join(display_variable_names)})"

        # Tracked category key will now be sorted by variable IDs
        tracked_category_key = f"{self.selected_category_data['id']}-{json.dumps(actual_selected_variables_for_api_and_key, sort_keys=True)}"

        level_id = self.selected_level_data['id']
        category_id = self.selected_category_data['id']
        run_type = 'il' if level_id else 'full_game'
        
        url_template = "https://www.speedrun.com/api/v1/leaderboards/{game_id}/{path}?top=1&embed=players,segments{variables}"
        path = f"level/{level_id}/{category_id}" if level_id else f"category/{category_id}"
        api_url = url_template.format(game_id=game_id, path=path, variables=variable_query_params)

        self.add_worker = ApiWorker(api_url, app_instance=self)
        self.add_worker.finished.connect(
            lambda data, req_id, cat_id=category_id, cat_name=self.selected_category_data['name'],
                   gid=game_id, lid=level_id, rt=run_type, 
                   var_vals_to_store=selected_variable_values_to_store_in_run_info, # This is just the variable data
                   full_display_name=display_category_name_full, # This is the full display name
                   is_misc=self.selected_category_data['is_miscellaneous']:
                   self.handle_add_result(data, cat_id, cat_name, gid, lid, rt, var_vals_to_store, full_display_name, is_misc)
        )
        self.add_worker.error.connect(self.handle_api_error)
        self.add_worker.start()
        self.show_status_message(self.translator.get_string('record_tracking', display_category_name=display_category_name_full))
        self.add_run_button.setEnabled(False)

    def handle_add_result(self, leaderboard_data, category_id, category_base_name, game_id, level_id, run_type, selected_variable_values_to_store, full_display_name, is_miscellaneous):
        """
        Handles the result of adding a new run.
        selected_variable_values_to_store: This is the variable values to be stored, i.e., keyed by variable name.
        full_display_name: This is the full category/level/variable combination name to be shown in the UI.
        """
        try:
            if game_id not in self.tracked_runs:
                logger.warning(f"handle_add_result: Game {game_id} not found. Operation aborted.")
                self.show_status_message(self.translator.get_string('game_removed_during_api', game_id=game_id), is_error=True)
                self._update_add_run_button_state()
                return

            world_record = self._get_new_record_run_obj(leaderboard_data)
            if world_record:
                new_player_names, new_player_weblinks = self._extract_player_info(world_record, leaderboard_data)
                splits_data_api = leaderboard_data.get('data', {}).get('segments', [])
                if not isinstance(splits_data_api, list):
                    splits_data_api = []
                
                run_info = {
                    'name': category_base_name,
                    'display_name': full_display_name, # Use the full name passed directly
                    'current_record_time': world_record.get('times', {}).get('primary_t'),
                    'weblink': world_record.get('weblink'),
                    'current_runners': new_player_names,
                    'player_weblinks': new_player_weblinks,
                    'date_completed': world_record.get('date', _.get_string('not_available_abbr')),
                    'splits': splits_data_api,
                    'variables': selected_variable_values_to_store, # Store according to new structure
                    'is_new_record_broken': False,
                    'is_miscellaneous': is_miscellaneous
                }
                
                # Use variable_id:value_id pairs for API call and record key
                actual_selected_variables_for_api_and_key = {v['variable_id']: v['value_id'] for k, v in selected_variable_values_to_store.items()}
                tracked_category_key = f"{category_id}-{json.dumps(actual_selected_variables_for_api_and_key, sort_keys=True)}"

                if run_type == 'full_game':
                    self.tracked_runs[game_id]['full_game_categories'][tracked_category_key] = run_info
                elif run_type == 'il':
                    if level_id not in self.tracked_runs[game_id]['levels']:
                        self.tracked_runs[game_id]['levels'][level_id] = {
                            'name': self.selected_level_data['name'],
                            'categories': {}
                        }
                    self.tracked_runs[game_id]['levels'][level_id]['categories'][tracked_category_key] = run_info

                self.save_tracked_runs()
                self.update_tracked_list_ui()
                self.show_status_message(self.translator.get_string('record_tracked_success', display_category_name=run_info['display_name']))
                self._update_add_run_button_state()
            else:
                self.show_status_message(self.translator.get_string('no_world_record_found', display_category_name=full_display_name), is_error=True)
                self._update_add_run_button_state()
        except Exception as e:
            logger.error(f"Error in handle_add_result: {e}", exc_info=True)
            self.show_status_message(self.translator.get_string('error_adding_record_general', e=e), is_error=True)
            self._update_add_run_button_state()

    def _extract_player_info(self, run_obj, leaderboard_data):
        """
        Extracts player names and web links.
        """
        player_names, player_weblinks = [], []
        players_data_embed = leaderboard_data.get('data', {}).get('players', {}).get('data', [])
        player_id_map = {p_data['id']: p_data for p_data in players_data_embed if isinstance(p_data, dict) and p_data.get('id')}
        
        for run_player_id_obj in run_obj.get('players', []):
            if isinstance(run_player_id_obj, dict):
                if run_player_id_obj.get('rel') == 'user':
                    player_id_to_find = run_player_id_obj.get('id')
                    p_data = player_id_map.get(player_id_to_find)
                    if p_data:
                        player_names.append(p_data.get('names',{}).get('international', p_data.get('name', _.get_string('unknown_player'))))
                        player_weblinks.append(p_data.get('weblink'))
                    else:
                        player_names.append(_.get_string('unknown_player_id_missing'))
                        player_weblinks.append(None)
                elif run_player_id_obj.get('rel') == 'guest':
                    player_names.append(run_player_id_obj.get('name', _.get_string('unknown_player')))
                    player_weblinks.append(None)
        return player_names, player_weblinks

    @staticmethod
    def format_time(total_seconds_float):
        """
        Formats seconds into a readable time string.
        """
        if total_seconds_float is None:
            return _.get_string('not_available_abbr')
        try:
            total_seconds = float(total_seconds_float)
            if 0 <= total_seconds < 0.001: return "0s"
            
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            milliseconds = int((total_seconds - int(total_seconds)) * 1000)

            parts = []
            if hours > 0: parts.append(f"{hours}h")
            if minutes > 0 or hours > 0: parts.append(f"{minutes:02d}m")
            if seconds >= 0 and (total_seconds > 0 or milliseconds > 0): parts.append(f"{seconds:02d}s")
            if milliseconds > 0: parts.append(f"{milliseconds:03d}ms")
            
            return " ".join(parts) if parts else "0s"
        except (ValueError, TypeError):
            logger.error(f"format_time: Invalid time value '{total_seconds_float}'.", exc_info=True)
            return _.get_string('invalid_time')

    def update_tracked_list_ui(self):
        """
        Updates the UI display of tracked runs.
        """
        scroll_bar = self.tracked_list_widget.verticalScrollBar()
        old_scroll_position = scroll_bar.value() if scroll_bar else 0
        self.tracked_list_widget.clear()
        if not self.tracked_runs:
            if scroll_bar: scroll_bar.setValue(old_scroll_position)
            return

        key_func = lambda gid: self.tracked_runs[gid].get('name', '').lower() if self.current_sort_order == 'game_name_asc' else self.tracked_runs[gid].get('_added_timestamp', 0)
        reverse_sort = self.current_sort_order == 'added_date_desc'
        sorted_game_ids = sorted(self.tracked_runs.keys(), key=key_func, reverse=reverse_sort)

        for game_id in sorted_game_ids:
            game_data = self.tracked_runs.get(game_id)
            if not game_data: continue

            game_frame = QFrame()
            game_frame.setObjectName("GameFrame")
            game_frame_layout = QVBoxLayout(game_frame)
            game_frame_layout.setContentsMargins(10, 10, 10, 10)
            game_frame_layout.setSpacing(5)

            game_name_with_year = game_data.get('name', _.get_string('unknown_game'))
            game_weblink = game_data.get('weblink')

            game_header_layout = QHBoxLayout()
            game_header_layout.setContentsMargins(0, 0, 0, 0)
            game_header_layout.setSpacing(2)
            game_name_button = QPushButton(game_name_with_year)
            game_name_button.setObjectName("GameLinkButton")
            game_name_button.setCursor(Qt.PointingHandCursor)
            game_name_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            game_name_button.setFixedHeight(self.OPTIONS_BUTTON_SIZE)
            game_name_button.setFont(QFont("Roboto", self.GAME_HEADER_FONT_SIZE, QFont.Bold))
            game_name_button.setToolTip(_.get_string('open_speedrun_com_page', game_name=game_name_with_year))
            if game_weblink:
                game_name_button.clicked.connect(lambda _, link=game_weblink: webbrowser.open(link))
            else:
                game_name_button.setEnabled(False)

            options_button = QPushButton("⋮")
            options_button.setFixedSize(QSize(self.OPTIONS_BUTTON_SIZE, self.OPTIONS_BUTTON_SIZE))
            options_button.setObjectName("OptionsButton")
            options_button.setToolTip(_.get_string('options'))
            options_button.setFont(QFont("Roboto", self.theme.get("fonts", {}).get("options_button_size", 24)))
            options_button.clicked.connect(lambda _, data={'type': 'game_header', 'game_id': game_id}: self.show_options_menu(options_button, data))
            
            game_header_layout.addStretch(1)
            game_header_layout.addWidget(game_name_button, alignment=Qt.AlignVCenter)
            game_header_layout.addWidget(options_button, alignment=Qt.AlignVCenter)
            game_header_layout.addStretch(1)
            game_frame_layout.addLayout(game_header_layout)

            self._add_category_items_to_layout(game_id, game_data, game_frame_layout)

            game_frame.adjustSize()
            frame_list_item = QListWidgetItem()
            frame_list_item.setSizeHint(game_frame.sizeHint())
            frame_list_item.setFlags(frame_list_item.flags() & ~Qt.ItemIsSelectable)
            self.tracked_list_widget.addItem(frame_list_item)
            self.tracked_list_widget.setItemWidget(frame_list_item, game_frame)

        if scroll_bar: scroll_bar.setValue(min(old_scroll_position, scroll_bar.maximum()))
        
    def _create_category_item_widget(self, category_data, category_key, current_game_id, current_level_id=None, current_level_name=None, item_type='full_game'):
        """Creates a single category item widget for the tracked list."""
        category_display_name = category_data.get('display_name', category_data.get('name', _.get_string('unknown_category')))
        formatted_time = self.format_time(category_data.get('current_record_time'))
        runners = category_data.get('current_runners', [_.get_string('unknown_player')])
        runner_weblinks = category_data.get('player_weblinks', [None] * len(runners))
        weblink = category_data.get('weblink', '#')
        date_completed = category_data.get('date_completed', _.get_string('not_available_abbr'))
        splits_data_for_dialog = category_data.get('splits', [])
        
        # Get original_category_id and variable IDs from category_key
        original_category_id = category_key.split('-')[0] 

        # This is the stored 'variables' dictionary (can be old or new format)
        stored_variables_dict = category_data.get('variables', {}) 
        selected_variables_for_api = {} # This will be in {variable_id: value_id} format suitable for API

        if stored_variables_dict:
            # First, assume it's the new format: {'Variable Name': {'variable_id': ..., 'value_id': ..., ...}}
            # We check if all *values* in the dict are themselves dictionaries containing 'variable_id'
            is_potential_new_format = all(isinstance(v, dict) and 'variable_id' in v for v in stored_variables_dict.values())

            if is_potential_new_format:
                for var_data in stored_variables_dict.values():
                    if 'variable_id' in var_data and 'value_id' in var_data:
                        selected_variables_for_api[var_data['variable_id']] = var_data['value_id']
                    else:
                        logger.warning(f"_create_category_item_widget: Missing or corrupted variable data in new format (in value): {var_data}")
            elif isinstance(stored_variables_dict, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in stored_variables_dict.items()):
                # Assume old format: {variable_id: value_id}
                selected_variables_for_api = stored_variables_dict
            else:
                # If it's neither the clear new format nor the clear old format, log and fallback.
                logger.warning(f"_create_category_item_widget: Unexpected stored variables format: {stored_variables_dict}. Using empty dictionary.")
                selected_variables_for_api = {} # Fallback to empty to avoid errors
        
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(10)

        # ... (Stylesheet settings and widget creation remain as in original)
        font_family = self.theme.get("fonts",{}).get("default_family", "Roboto")
        base_font_size = self.BASE_ITEM_FONT_SIZE
        options_button_font_size = self.theme.get("fonts",{}).get("options_button_size", 24)

        # Dynamically set style based on the theme stylesheet for category_item_widget
        category_item_stylesheet = self.theme.get("stylesheets", {}).get("category_item_widget", "").format(
            default_font_family=font_family,
            base_item_font_size=base_font_size,
            options_button_size=self.OPTIONS_BUTTON_SIZE,
            options_button_font_size=options_button_font_size,
            new_wr_label_text=self.theme.get("colors", {}).get("new_wr_label_text", "#FFD700"),
            new_wr_category_name_color=self.theme.get("colors", {}).get("new_wr_category_name_color", "#FFD700"),
            new_wr_category_name_font_size=self.theme.get("fonts", {}).get("new_wr_category_name_font_size", 14)
        )
        item_widget.setStyleSheet(category_item_stylesheet)
        
        if category_data.get('is_new_record_broken', False):
            new_wr_label = QLabel(_.get_string('new_wr_label'))
            new_wr_label.setObjectName("new_wr_label")
            item_layout.addWidget(new_wr_label, alignment=Qt.AlignVCenter)

        category_name_actual_label = QLabel(category_display_name)
        category_name_actual_label.setObjectName("category_name_label")
        category_name_actual_label.setWordWrap(True)
        # Apply CSS class dynamically based on WR status
        if category_data.get('is_new_record_broken', False):
            category_name_actual_label.setProperty("cssClass", "new_wr_category_name")
        else:
            category_name_actual_label.setProperty("cssClass", "normal_category_name")
        # Font is set by stylesheet based on cssClass
        
        item_layout.addWidget(category_name_actual_label, 5, alignment=Qt.AlignVCenter)

        time_button = QPushButton(formatted_time)
        time_button.setObjectName("TimeButton")
        time_button.setCursor(Qt.PointingHandCursor)
        time_button.setFont(QFont(font_family, base_font_size))
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
                    runners_date_container_layout.addWidget(QLabel(" • "), alignment=Qt.AlignVCenter)
                runner_weblink = runner_weblinks[i] if i < len(runner_weblinks) else None
                if runner_weblink:
                    runner_button = QPushButton(runner_name)
                    runner_button.setObjectName("RunnerLinkButton") # Apply bold style from stylesheet
                    runner_button.setCursor(Qt.PointingHandCursor) # Change cursor
                    runner_button.clicked.connect(lambda _, link=runner_weblink: webbrowser.open(link))
                    runners_date_container_layout.addWidget(runner_button, alignment=Qt.AlignVCenter)
                else:
                    runner_label = QLabel(runner_name)
                    font = runner_label.font()
                    font.setBold(True) # Make runner name bold
                    runner_label.setFont(font)
                    runners_date_container_layout.addWidget(runner_label, alignment=Qt.AlignVCenter)
            else:
                break
        
        remaining_runners = len(runners) - self.MAX_DISPLAY_RUNNERS
        if remaining_runners > 0:
            if self.MAX_DISPLAY_RUNNERS > 0: runners_date_container_layout.addWidget(QLabel(" • "), alignment=Qt.AlignVCenter)
            more_button = QPushButton(_.get_string('more_runners_button', count=remaining_runners))
            more_button.setObjectName("MoreRunnersButton")
            more_button.setCursor(Qt.PointingHandCursor) # Change cursor to indicate clickable
            more_button.clicked.connect(lambda _, r_names=runners, r_links=runner_weblinks: self.show_all_runners_dialog(category_display_name, r_names, r_links))
            runners_date_container_layout.addWidget(more_button, alignment=Qt.AlignVCenter)

        runners_date_container_layout.addSpacing(10)
        date_label = QLabel(f"{date_completed}")
        date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        runners_date_container_layout.addWidget(date_label, alignment=Qt.AlignVCenter)
        item_layout.addLayout(runners_date_container_layout, 1)

        options_button = QPushButton("⋮")
        options_button.setFixedSize(QSize(self.OPTIONS_BUTTON_SIZE, self.OPTIONS_BUTTON_SIZE))
        options_button.setObjectName("OptionsButton")
        options_button.setFont(QFont("Roboto", options_button_font_size))
        options_button.setToolTip(_.get_string('options_button_tooltip'))
        options_button.clicked.connect(
            lambda _, data={
                'game_id': current_game_id, 'category_key': category_key, 'original_category_id': original_category_id,
                'level_id': current_level_id, 'type': item_type, 'weblink': weblink, 'splits': splits_data_for_dialog,
                'current_runners': runners, 'player_weblinks': runner_weblinks, 'category_name': category_display_name,
                'is_new_record_broken': category_data.get('is_new_record_broken', False),
                'selected_variables_for_this_run': selected_variables_for_api # Variables suitable for API
            }: self.show_options_menu(options_button, data)
        )
        item_layout.addWidget(options_button, alignment=Qt.AlignVCenter)

        item_widget.adjustSize()
        return item_widget
        
    def _add_category_items_to_layout(self, game_id, game_data, parent_layout):
        """Adds category widgets to the layout."""
        main_category_widgets, misc_category_widgets, il_category_widgets = [], [], []

        if game_data.get('full_game_categories'):
            sorted_fg_keys = sorted(game_data['full_game_categories'].keys(), key=lambda k: game_data['full_game_categories'][k].get('display_name', '').lower())
            for key in sorted_fg_keys:
                category_data = game_data['full_game_categories'].get(key)
                if category_data:
                    item_widget = self._create_category_item_widget(category_data, key, game_id, item_type='full_game')
                    # Check the 'is_miscellaneous' flag stored in category_data
                    if category_data.get('is_miscellaneous', False): 
                        misc_category_widgets.append(item_widget)
                    else:
                        main_category_widgets.append(item_widget)

        if game_data.get('levels'):
            sorted_level_ids = sorted(game_data['levels'].keys(), key=lambda lid: game_data['levels'][lid].get('name', '').lower())
            for level_id in sorted_level_ids:
                level_data = game_data['levels'].get(level_id)
                if level_data and level_data.get('categories'):
                    sorted_il_keys = sorted(level_data['categories'].keys(), key=lambda k: level_data['categories'][k].get('display_name', '').lower())
                    for key in sorted_il_keys:
                        category_data = level_data['categories'].get(key)
                        if category_data:
                            widget = self._create_category_item_widget(category_data, key, game_id, current_level_id=level_id, current_level_name=level_data.get('name'), item_type='il')
                            il_category_widgets.append(widget)

        for widget_list in [main_category_widgets, misc_category_widgets, il_category_widgets]:
            for widget in widget_list:
                parent_layout.addWidget(widget)

    def show_options_menu(self, button, data):
        """
        Displays the context menu.
        """
        menu = QMenu(self)
        item_type = data.get('type')

        if item_type == 'game_header':
            remove_game_action = menu.addAction(self.translator.get_string('options_menu_remove_game'))
            remove_game_action.triggered.connect(lambda: self.delete_tracked_game(data.get('game_id')))
        else:
            menu.addAction(self.translator.get_string('options_menu_view_splits')).triggered.connect(lambda: self.view_splits_details_from_data(data))
            menu.addAction(self.translator.get_string('options_menu_open_run_page')).triggered.connect(lambda: self._open_weblink(data.get('weblink'), self.translator.get_string('web_link_not_available', item_type="record")))
            menu.addAction(self.translator.get_string('options_menu_open_other_runs')).triggered.connect(lambda: self.show_other_runs_dialog(data))
            if data.get('is_new_record_broken', False):
                menu.addAction(self.translator.get_string('options_menu_mark_as_read')).triggered.connect(lambda: self.mark_run_as_read(data.get('game_id'), data.get('category_key'), data.get('level_id'), data.get('type')))
            
            player_weblinks = data.get('player_weblinks', [])
            current_runners = data.get('current_runners', [])
            if player_weblinks and current_runners:
                menu.addSeparator()
                for i, player_weblink in enumerate(player_weblinks):
                    if player_weblink and i < len(current_runners):
                        action = menu.addAction(self.translator.get_string('options_menu_open_player_profile', player_name=current_runners[i]))
                        action.triggered.connect(lambda _, link=player_weblink: self._open_weblink(link, self.translator.get_string('web_link_not_available', item_type="player")))
            
            menu.addSeparator()
            menu.addAction(self.translator.get_string('options_menu_remove_run')).triggered.connect(lambda: self.delete_tracked_run(data.get('game_id'), data.get('category_key'), data.get('level_id'), data.get('type')))

        menu.exec_(QCursor.pos())

    def show_other_runs_dialog(self, data):
        """Opens a dialog showing other runs."""
        game_id = data.get('game_id')
        original_category_id = data.get('original_category_id')
        level_id = data.get('level_id')
        category_name = data.get('category_name')
        # selected_variables should now be a directly usable dictionary for the API
        selected_variables = data.get('selected_variables_for_this_run', {}) 
        game_name = self.tracked_runs.get(game_id, {}).get('name', _.get_string("unknown_game"))
        dialog_title = f"{game_name} - {category_name}"
        AllRunsDialog(game_id, original_category_id, level_id, selected_variables, dialog_title, parent=self).exec_()

    def _open_weblink(self, url, error_message):
        """Opens a web link."""
        if url and url != '#':
            try: webbrowser.open(url)
            except Exception as e:
                logger.error(f"Error opening web link: {url} - {e}", exc_info=True)
                self.show_status_message(self.translator.get_string('web_link_open_failed'), is_error=True)
        else:
            self.show_status_message(error_message, is_error=True)

    def view_splits_details_from_data(self, data):
        """Shows segment details."""
        splits_data = data.get('splits', [])
        game_id = data.get('game_id')
        cat_name = data.get('category_name')
        game_name = self.tracked_runs.get(game_id, {}).get('name', _.get_string("unknown_game"))
        dialog_title = f"{game_name} - {cat_name}"
        SplitsDialog(splits_data, run_title=dialog_title, parent=self).exec_()

    def show_all_runners_dialog(self, run_display_name, all_runners, all_weblinks):
        """Shows all runners."""
        if not isinstance(all_runners, list) or not isinstance(all_weblinks, list):
            logger.error(f"show_all_runners_dialog: Invalid type. Runners: {type(all_runners)}, Weblinks: {type(all_weblinks)}")
            self.show_status_message(self.translator.get_string('error_fetching_runner_info'), is_error=True)
            return
        AllRunnersDialog(run_display_name, all_runners, all_weblinks, parent=self).exec_()

    def delete_tracked_run(self, game_id, category_key, level_id, run_type):
        """Deletes a tracked run."""
        if game_id not in self.tracked_runs: return
        game_entry = self.tracked_runs[game_id]
        deleted = False
        if run_type == 'full_game' and category_key in game_entry.get('full_game_categories', {}):
            del game_entry['full_game_categories'][category_key]
            deleted = True
        elif run_type == 'il' and level_id and level_id in game_entry.get('levels', {}) and category_key in game_entry['levels'][level_id].get('categories', {}):
            del game_entry['levels'][level_id]['categories'][category_key]
            if not game_entry['levels'][level_id].get('categories'): del game_entry['levels'][level_id]
            deleted = True
        
        if deleted:
            if not game_entry.get('full_game_categories') and not game_entry.get('levels'):
                del self.tracked_runs[game_id]
            self.save_tracked_runs()
            self.update_tracked_list_ui()
            self._update_add_run_button_state()
            self.show_status_message(self.translator.get_string('untrack_run_success'))
        else:
            self.show_status_message(self.translator.get_string('untrack_run_failed'), is_error=True)

    def delete_tracked_game(self, game_id):
        """Deletes a tracked game."""
        if game_id in self.tracked_runs:
            del self.tracked_runs[game_id]
            self.save_tracked_runs()
            self.update_tracked_list_ui()
            self._update_add_run_button_state()
            self.show_status_message(self.translator.get_string('game_removed_success'))
        else:
            self.show_status_message(self.translator.get_string('game_not_found_untrack', game_id=game_id), is_error=True)

    def check_for_new_records(self):
        """Checks for new records. Uses a flag to prevent consecutive clicks."""
        if self.is_checking_records:
            self.show_status_message(self.translator.get_string('check_already_running'), is_error=True)
            return

        if not self.tracked_runs:
            self.show_status_message(self.translator.get_string('no_records_to_track'), is_error=False)
            return

        self.is_checking_records = True
        self.ui_update_needed_after_check = False  # Reset flag on each new check

        self.refresh_button.setEnabled(False)
        self.timer.stop()

        # Gracefully stop any pending workers from a previous failed run
        for worker in self.active_check_workers:
            if worker.isRunning():
                worker.quit()
                worker.wait(100) # Short wait to allow termination

        self.active_check_workers = []
        self.pending_refresh_api_calls = 0
        self.total_runs_to_check = 0
        self.checked_runs_count = 0

        # Calculate total number of runs to check
        for game_id, game_data in self.tracked_runs.items():
            self.total_runs_to_check += len(game_data.get('full_game_categories', {}))
            for level_data_loop in game_data.get('levels', {}).values():
                self.total_runs_to_check += len(level_data_loop.get('categories', {}))
        
        self.update_progress_status()

        for game_id, game_data in self.tracked_runs.copy().items():
            for category_key, _ in game_data.get('full_game_categories', {}).copy().items():
                self._create_and_start_worker(game_id, category_key, None, 'full_game')
            for level_id, level_data_loop in game_data.get('levels', {}).copy().items():
                for category_key, _ in level_data_loop.get('categories', {}).copy().items():
                    self._create_and_start_worker(game_id, category_key, level_id, 'il')
        
        if self.pending_refresh_api_calls == 0:
            # Reset status if no workers were created
            self.refresh_button.setEnabled(True)
            self.timer.start()
            self.is_checking_records = False
            self.show_status_message(self.translator.get_string('check_complete'))

    def _create_and_start_worker(self, game_id, category_key, level_id, run_type):
        """Creates and starts a worker for record checking."""
        original_category_id = category_key.split('-')[0]
        variables_str = ""
        if '-' in category_key:
            try:
                variables_dict_raw = category_key.split('-', 1)[1]
                parsed_vars = json.loads(variables_dict_raw)
                for var_id, var_value_id in parsed_vars.items():
                    variables_str += f"&var-{var_id}={var_value_id}"
            except json.JSONDecodeError as e:
                logger.error(f"_create_and_start_worker: JSON parsing error: {category_key}: {e}", exc_info=True)
                self.on_worker_completed()
                return

        path = f"level/{level_id}/{original_category_id}" if run_type == 'il' else f"category/{original_category_id}"
        url = f"https://www.speedrun.com/api/v1/leaderboards/{game_id}/{path}?top=1&embed=players,segments{variables_str}"

        worker = ApiWorker(url, app_instance=self)
        worker.finished.connect(lambda data, req_id, g_id=game_id, c_key=category_key, l_id=level_id, rt=run_type: self.handle_record_check_result(data, g_id, c_key, l_id, rt))
        worker.error.connect(self.handle_api_error)
        worker.worker_completed.connect(self.on_worker_completed)
        self.active_check_workers.append(worker)
        self.pending_refresh_api_calls += 1
        worker.start()

    def handle_record_check_result(self, leaderboard_data, game_id, category_key, level_id, run_type):
        """Handles the record check result."""
        try:
            if game_id not in self.tracked_runs:
                logger.warning(f"handle_record_check_result: Game {game_id} not found.")
                return

            game_data = self.tracked_runs[game_id]
            current_tracked_run_data = None
            if run_type == 'full_game':
                current_tracked_run_data = game_data.get('full_game_categories', {}).get(category_key)
            elif run_type == 'il':
                current_tracked_run_data = game_data.get('levels', {}).get(level_id, {}).get('categories', {}).get(category_key)

            if not current_tracked_run_data:
                logger.warning(f"handle_record_check_result: Tracked data not found: {game_id}, {level_id}, {category_key}")
                return

            new_record_run_obj = self._get_new_record_run_obj(leaderboard_data)
            if new_record_run_obj:
                data_changed = False
                new_record_time_seconds = new_record_run_obj.get('times', {}).get('primary_t')
                new_runners, new_weblinks = self._extract_player_info(new_record_run_obj, leaderboard_data)

                # Check for runner or weblink changes
                if current_tracked_run_data.get('current_runners') != new_runners:
                    current_tracked_run_data['current_runners'] = new_runners
                    data_changed = True
                if current_tracked_run_data.get('player_weblinks') != new_weblinks:
                    current_tracked_run_data['player_weblinks'] = new_weblinks
                    data_changed = True
                
                # Check for new record
                old_record_time = current_tracked_run_data.get('current_record_time')
                if old_record_time is not None and new_record_time_seconds is not None and new_record_time_seconds < old_record_time:
                    run_identifier_for_msg = self._get_run_identifier_for_msg(game_data, current_tracked_run_data, level_id)
                    current_tracked_run_data['current_record_time'] = new_record_time_seconds
                    current_tracked_run_data['weblink'] = new_record_run_obj.get('weblink')
                    current_tracked_run_data['date_completed'] = new_record_run_obj.get('date', _.get_string('not_available_abbr'))
                    current_tracked_run_data['splits'] = leaderboard_data.get('data', {}).get('segments', [])
                    current_tracked_run_data['is_new_record_broken'] = True
                    self.has_unseen_new_wrs = True
                    data_changed = True

                    self.show_last_record_button.setVisible(True)
                    self.clear_new_wr_button.setVisible(True)
                    
                    new_broken_record_info = self._create_broken_record_info(game_data, current_tracked_run_data, game_data.get('levels', {}).get(level_id))
                    self.broken_records_history.append(new_broken_record_info)
                    self.show_status_message(self.translator.get_string('new_wr_detected', run_identifier=run_identifier_for_msg))

                if data_changed:
                    self.ui_update_needed_after_check = True
                    self.save_tracked_runs()

        except Exception as e:
            logger.error(f"Error within handle_record_check_result: {e}", exc_info=True)
            self.show_status_message(self.translator.get_string('api_error_general', error_message=e), is_error=True)

    def _get_new_record_run_obj(self, leaderboard_data):
        """Extracts the top run object from leaderboard data."""
        try:
            return leaderboard_data['data']['runs'][0]['run']
        except (KeyError, IndexError, TypeError):
            return None

    def _get_run_identifier_for_msg(self, game_data, category_data, level_id):
        """Creates a descriptive name for the run for status messages."""
        level_name = game_data.get('levels', {}).get(level_id, {}).get('name', '') if level_id else ''
        level_part = f"{level_name}: " if level_name else ""
        return f"'{level_part}{category_data.get('display_name', _.get_string('unknown_category'))}'"

    def _create_broken_record_info(self, game_data, category_data, level_data=None):
        """Creates an info dictionary for the broken records history."""
        return {
            'game_name': game_data.get('name', _.get_string('unknown_game')),
            'level_name': level_data.get('name') if level_data else None,
            'category_display_name': category_data.get('display_name', _.get_string('unknown_category')),
            'formatted_new_time': self.format_time(category_data.get('current_record_time')),
            'new_player_name': ', '.join(category_data.get('current_runners', [_.get_string('unknown_player')])),
            'new_run_date': f"({category_data.get('date_completed', _.get_string('not_available_abbr'))})",
            'weblink': category_data.get('weblink')
        }

    def handle_api_error(self, error_message):
        """Handles API errors and distinguishes them from bulk check errors."""
        sender_worker = self.sender()

        # If the error comes from one of the bulk check workers, just log it.
        # on_worker_completed will manage overall progress and final status.
        if sender_worker and sender_worker in self.active_check_workers:
            logger.error(f"API Error (during record check): {error_message}")
            return

        # If the error comes from a single action (search, add, details), handle it.
        context_key = 'api_error_general_prefix'
        if sender_worker and hasattr(sender_worker, 'url'):
            url = sender_worker.url
            if "games?name=" in url:
                context_key = 'api_error_search_context'
                self.search_button.setEnabled(True)
                self.search_button.setText(self.translator.get_string('search_button'))
            elif "/categories" in url or "/levels/" in url or (self.selected_game_data['id'] and f"/games/{self.selected_game_data['id']}" in url):
                context_key = 'api_error_category_level_context'
                self.on_category_variables_worker_completed() # Re-enable lists
            elif "leaderboards/" in url:
                context_key = 'api_error_record_check_context'
                self._update_add_run_button_state() # Re-evaluate add button state
        
        full_message = f"{self.translator.get_string('api_error_general_prefix')}: {self.translator.get_string(context_key)} {error_message}".strip()
        self.show_status_message(full_message, is_error=True)
        logger.error(f"{full_message}", exc_info=True)


    def on_worker_completed(self):
        """Callback function when an ApiWorker task completes. Only for the record checking loop."""
        # If a checking loop is not active, do nothing.
        if not self.is_checking_records:
            return

        self.checked_runs_count += 1
        self.update_progress_status()

        if self.pending_refresh_api_calls > 0:
            self.pending_refresh_api_calls -= 1
        
        if self.pending_refresh_api_calls <= 0:
            if self.ui_update_needed_after_check:
                self.update_tracked_list_ui()

            self.show_status_message(self.translator.get_string('check_complete'))
            
            # Reset the status flag at the very end
            self.is_checking_records = False
            
            # Re-enable UI elements in final state
            if self.refresh_button:
                self.refresh_button.setEnabled(True)
            if self.timer and not self.timer.isActive():
                self.timer.start()

    def update_progress_status(self, is_error=False):
        """
        Displays the current record checking progress in the status message.
        """
        if not self.is_checking_records:
            return
            
        message = self.translator.get_string('checking_for_new_records')
        if self.total_runs_to_check > 0:
            message = self.translator.get_string('checking_records_progress', checked=self.checked_runs_count, total=self.total_runs_to_check)
        
        color = self.theme.get('colors', {}).get('error' if is_error else 'on_surface', '#FF69B4' if is_error else '#FFFFFF')
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")


    def on_category_variables_worker_completed(self):
        """Completion handler for category and variable loading threads."""
        self.category_list_widget.setEnabled(True)
        self.variables_list_widget.setEnabled(True)

    def show_last_record_notification(self):
        """Displays the LastRecordDialog with the history of broken records."""
        LastRecordDialog(self.broken_records_history, parent=self).exec_()

    def mark_all_new_wrs_as_read(self):
        """Marks all new world records as "read"."""
        for game_data in self.tracked_runs.values():
            for category_data in game_data.get('full_game_categories', {}).values():
                category_data['is_new_record_broken'] = False
            for level_data in game_data.get('levels', {}).values():
                for category_data in level_data.get('categories', {}).values():
                    category_data['is_new_record_broken'] = False

        self.broken_records_history.clear()
        self.has_unseen_new_wrs = False
        self.save_tracked_runs()
        self.update_tracked_list_ui()
        self.show_last_record_button.setVisible(False)
        self.clear_new_wr_button.setVisible(False)
        self.show_status_message(self.translator.get_string('all_marked_as_read'))

    def mark_run_as_read(self, game_id, category_key, level_id, run_type):
        """Marks a specific 'New WR' run as read."""
        if game_id not in self.tracked_runs: return
        
        target_run_data = None
        if run_type == 'full_game':
            target_run_data = self.tracked_runs[game_id].get('full_game_categories', {}).get(category_key)
        elif run_type == 'il' and level_id:
            target_run_data = self.tracked_runs[game_id].get('levels', {}).get(level_id, {}).get('categories', {}).get(category_key)

        if target_run_data:
            if not target_run_data.get('is_new_record_broken', False):
                self.show_status_message(self.translator.get_string('run_already_marked_read'))
                return
            
            target_run_data['is_new_record_broken'] = False
            run_identifier = self._get_run_identifier_for_msg(self.tracked_runs[game_id], target_run_data, level_id)
            # Remove the specific broken record from history
            self.broken_records_history = [
                rec for rec in self.broken_records_history 
                if not (rec.get('game_name') == self.tracked_runs[game_id].get('name') and
                        rec.get('level_name') == (self.tracked_runs[game_id].get('levels', {}).get(level_id, {}).get('name') if level_id else None) and
                        rec.get('category_display_name') == target_run_data.get('display_name'))
            ]
            
            # Recalculate if there are any unseen WRs left
            self.has_unseen_new_wrs = any(
                c.get('is_new_record_broken') for g in self.tracked_runs.values() for c in g.get('full_game_categories', {}).values()
            ) or any(
                c.get('is_new_record_broken') for g in self.tracked_runs.values() for l in g.get('levels', {}).values() for c in l.get('categories', {}).values()
            )
            
            self.show_last_record_button.setVisible(self.has_unseen_new_wrs)
            self.clear_new_wr_button.setVisible(self.has_unseen_new_wrs)
            self.save_tracked_runs()
            self.update_tracked_list_ui()
            self.show_status_message(self.translator.get_string('run_marked_as_read'))
        else:
            self.show_status_message(self.translator.get_string('run_mark_read_failed', run_data="run data not found"), is_error=True)

    def show_status_message(self, message, is_error=False):
        """Displays a temporary status message."""
        # If a checking loop is active and the incoming message is not 'check_complete',
        # do not show temporary messages to preserve the progress message.
        if self.is_checking_records and message != self.translator.get_string('check_complete'):
            return

        color = self.theme.get('colors', {}).get('error' if is_error else 'success', '#FF69B4' if is_error else '#4CAF50')
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")
        
        # Make all status messages disappear after 5 seconds.
        QTimer.singleShot(5000, lambda: self.status_label.setText("") if self.status_label.text() == message else None)

    def closeEvent(self, event):
        """Event handler when the application is closed."""
        self.is_checking_records = False # Stop any pending loops
        for worker in self.active_check_workers:
            if worker.isRunning():
                worker.quit()
                worker.wait(500)
        self.save_tracked_runs()
        event.accept()

if __name__ == '__main__':
    if not (LANGUAGES and THEME):
        print("Error: 'Languages.json' or 'Theme.json' files not found or could not be loaded.")
        sys.exit(1)
        
    try:
        app = QApplication(sys.argv)
        # Initialize global translator
        settings = SettingsManager().load_settings()
        _.set_language(settings.get('language', 'en'))
        
        window = SpeedrunTrackerApp()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"A critical error occurred while starting the application: {e}", exc_info=True)
        # We need to ensure Translator is initialized to use _.get_string directly.
        # At this point, _ should already be initialized.
        print(_.get_string("critical_startup_error"))