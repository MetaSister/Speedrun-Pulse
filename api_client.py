# api_client.py
# Bu dosya, speedrun.com API'si ile etkileşimi yöneten QThread worker'larını içerir.

import requests
import json
import time
from PyQt5.QtCore import QThread, pyqtSignal

from config import RETRY_MAX_ATTEMPTS, RETRY_INITIAL_DELAY, REQUEST_TIMEOUT
from localization import _

class BaseApiWorker(QThread):
    """
    Yeniden deneme mekanizması içeren temel API worker sınıfı.
    """
    error = pyqtSignal(str, object)
    worker_completed = pyqtSignal()

    def __init__(self, max_retries=RETRY_MAX_ATTEMPTS, initial_retry_delay=RETRY_INITIAL_DELAY, request_timeout=REQUEST_TIMEOUT):
        super().__init__()
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.request_timeout = request_timeout
        self.last_exception_type = None

    def _request_with_retries(self, url):
        """
        Bir URL'ye üstel backoff ile yeniden deneme yaparak istek gönderir.
        """
        self.last_exception_type = None
        retryable_status_codes = [420, 429, 500, 502, 503, 504]

        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, timeout=self.request_timeout)
                response.raise_for_status()  # HTTP hata kodları için bir exception fırlatır
                return response
            except requests.exceptions.Timeout:
                self.last_exception_type = "Timeout"
            except requests.exceptions.ConnectionError:
                self.last_exception_type = "ConnectionError"
            except requests.exceptions.HTTPError as e:
                self.last_exception_type = "HTTPError"
                if e.response.status_code in retryable_status_codes:
                    pass  # Yeniden denenebilir hata, döngü devam etsin
                else:
                    error_msg = _.get_string('http_error', status_code=e.response.status_code, url=url)
                    self.error.emit(error_msg, e)
                    return None
            except requests.exceptions.RequestException as e:
                self.last_exception_type = "RequestException"
                error_msg = _.get_string('general_request_error', error=e, url=url)
                self.error.emit(error_msg, e)
                return None

            if attempt < self.max_retries - 1:
                delay = self.initial_retry_delay * (2 ** attempt)
                time.sleep(delay)
        
        error_message = _.get_string('max_retries_exceeded', url=url, max_retries=self.max_retries)
        if self.last_exception_type:
             error_message += f" Last error type: {self.last_exception_type}."
        self.error.emit(error_message, None)
        return None

class ApiWorker(BaseApiWorker):
    """
    Belirli bir API isteğini işleyen ve sonucu JSON olarak döndüren worker.
    """
    finished = pyqtSignal(object, object)

    def __init__(self, url, request_id=None, **kwargs):
        super().__init__(**kwargs)
        self.url = url
        self.request_id = request_id
        self.run_context = None # Record kontrolü gibi özel context'ler için

    def run(self):
        """
        Worker'ın ana çalışma fonksiyonu.
        """
        try:
            response = self._request_with_retries(self.url)
            if response:
                try:
                    result = response.json()
                    self.finished.emit(result, self.request_id)
                except json.JSONDecodeError as e:
                    error_msg = _.get_string('json_decode_error', url=self.url)
                    self.error.emit(error_msg, e)
        except Exception as e:
            error_msg = _.get_string('unexpected_api_worker_error', error=e)
            self.error.emit(error_msg, e)
        finally:
            self.worker_completed.emit()
