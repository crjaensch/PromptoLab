# thread_manager.py
import logging
from typing import Callable, Any, Dict, Optional
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Qt

logging.debug('thread_manager module imported.')

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    
    Since QRunnable doesn't inherit from QObject and can't directly use signals,
    this class provides the signals we need for worker communication.
    """
    finished = Signal(object)  # Signal emitted when the worker completes with a result
    error = Signal(str)       # Signal emitted when an error occurs
    progress = Signal(int)    # Signal emitted to report progress
    cancelled = Signal()      # Signal emitted when the worker is cancelled

class BaseRunnable(QRunnable):
    """
    Base class for all runnables that provides common functionality.
    """
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self._is_cancelled = False
        
    def run(self):
        """
        Abstract method that must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement run()")
    
    def cancel(self):
        """
        Set the cancellation flag. Workers should check this flag
        periodically and stop execution if it's set.
        """
        self._is_cancelled = True
        
    def is_cancelled(self):
        """
        Check if this worker has been cancelled.
        """
        return self._is_cancelled

class ThreadManager:
    """
    Manages a global thread pool for the application.
    
    This class provides a centralized interface for submitting tasks to
    a thread pool and managing thread execution.
    """
    _instance = None
    
    @classmethod
    def instance(cls):
        """
        Get the singleton instance of the ThreadManager.
        """
        if cls._instance is None:
            cls._instance = ThreadManager()
        return cls._instance
    
    def __init__(self):
        """
        Initialize the thread manager with the global thread pool.
        """
        self.thread_pool = QThreadPool.globalInstance()
        self.active_runnables = []  # Keep track of active runnables for cleanup
        logging.debug(f"ThreadManager initialized with {self.thread_pool.maxThreadCount()} threads")
    
    def start_runnable(self, runnable: BaseRunnable, priority: int = 0):
        """
        Submit a runnable to the thread pool.
        
        Args:
            runnable: The BaseRunnable to execute
            priority: The priority of the task (higher values = higher priority)
        """
        # Keep track of the runnable for cleanup
        self.active_runnables.append(runnable)
        
        # Connect cleanup to finished and error signals
        runnable.signals.finished.connect(lambda _: self._cleanup_runnable(runnable))
        runnable.signals.error.connect(lambda _: self._cleanup_runnable(runnable))
        runnable.signals.cancelled.connect(lambda: self._cleanup_runnable(runnable))
        
        # Set the priority and start the runnable
        runnable.setAutoDelete(False)  # We'll handle deletion ourselves
        self.thread_pool.start(runnable, priority)
    
    def _cleanup_runnable(self, runnable):
        """
        Remove a runnable from the active list when it's done.
        """
        if runnable in self.active_runnables:
            self.active_runnables.remove(runnable)
    
    def cancel_all(self):
        """
        Cancel all active runnables.
        """
        for runnable in self.active_runnables.copy():
            runnable.cancel()
    
    def wait_for_all(self, msecs: int = -1):
        """
        Wait for all tasks to complete.
        
        Args:
            msecs: Maximum time to wait in milliseconds, or -1 to wait indefinitely
        
        Returns:
            True if all tasks completed, False if timed out
        """
        return self.thread_pool.waitForDone(msecs)
    
    def cleanup(self):
        """
        Clean up the thread manager by cancelling all active runnables
        and waiting for them to finish.
        """
        self.cancel_all()
        self.wait_for_all(3000)  # Wait up to 3 seconds for tasks to finish
