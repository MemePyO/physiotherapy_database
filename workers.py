"""Lightweight background task runner for long-running operations.

Keeps the Tk UI responsive by running work on a worker thread and reporting
completion back to the Tk thread via ``after()``.
"""

import threading


class BackgroundTask:
    """Run a callable on a worker thread and call back on the Tk thread."""

    def __init__(self, owner, work, on_done=None, on_error=None, on_progress=None):
        self.owner = owner
        self.work = work  # callable(progress_callback) -> result
        self.on_done = on_done  # callable(result)
        self.on_error = on_error  # callable(exception)
        self.on_progress = on_progress  # callable(message)
        self._thread = None
        self.cancelled = False

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            result = self.work(self._progress)
            if not self.cancelled:
                self._schedule(lambda: self.on_done(result) if self.on_done else None)
        except Exception as e:
            if not self.cancelled:
                err = e
                self._schedule(lambda err=err: self.on_error(err) if self.on_error else None)

    def _progress(self, message):
        if self.on_progress:
            self._schedule(lambda: self.on_progress(message))

    def _schedule(self, fn):
        try:
            self.owner.after(0, fn)
        except Exception:
            pass

    def cancel(self):
        self.cancelled = True

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()
