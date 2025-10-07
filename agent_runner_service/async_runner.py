import asyncio
import threading
import concurrent.futures
import logging

logger = logging.getLogger(__name__)


class AsyncLoopThread:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        logger.info("AsyncLoopThread starting event loop")
        self.loop.run_forever()

    def run_coro(self, coro, timeout: float = 30):
        """Schedule coro on the background loop and wait for result with timeout."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise TimeoutError("Async task timed out")


# Singleton instance
_loop_thread = None


def get_loop_thread() -> AsyncLoopThread:
    global _loop_thread
    if _loop_thread is None:
        _loop_thread = AsyncLoopThread()
    return _loop_thread


def run_coro_sync(coro, timeout: float = 30):
    return get_loop_thread().run_coro(coro, timeout=timeout)
