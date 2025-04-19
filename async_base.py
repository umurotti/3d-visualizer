from concurrent.futures import ThreadPoolExecutor
import atexit
import requests

class AsyncPostClient:
    _executor = ThreadPoolExecutor(max_workers=8)

    @staticmethod
    def fire_and_forget_post(url, json=None, timeout=1):
        def task():
            try:
                requests.post(url, json=json, timeout=timeout)
            except requests.exceptions.RequestException as e:
                print(f"[WARN] Async POST failed: {e}")
        AsyncPostClient._executor.submit(task)

    @staticmethod
    @atexit.register
    def shutdown_executor():
        AsyncPostClient._executor.shutdown(wait=False)
