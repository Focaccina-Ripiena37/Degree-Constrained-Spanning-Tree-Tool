# app/progress.py - Gestisce il progresso e i timeout dell'applicazione

"""
Progress tracking and timeout handling utilities for DCST Tool.

This module provides classes and functions to:
1. Track and display progress of long-running operations
2. Handle operation timeouts
3. Manage cancellable operations
"""

# Standard library imports
import threading
import time
import logging
import signal
import sys
from functools import wraps

# Third-party library imports
import tkinter as tk
from tkinter import ttk

# ===== Progress Tracking Functionality =====

class ProgressBar:
    """Visual progress bar using tkinter."""
    
    def __init__(self, root, max_value):
        """
        Initialize a progress bar.
        
        Args:
            root: Tkinter root or frame
            max_value: Maximum value for the progress bar
        """
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=20)
        self.progress["maximum"] = max_value
        self.value = 0

    def update(self, value):
        """Update progress bar to a specific value."""
        self.value = value
        self.progress["value"] = self.value
        self.progress.update_idletasks()

    def increment(self, step=1):
        """Increment progress bar by specified step."""
        self.value += step
        self.update(self.value)


class ProgressTracker:
    """Track progress of long-running algorithms."""
    
    def __init__(self, total_steps=100, name="Operation"):
        """
        Initialize a progress tracker.
        
        Args:
            total_steps: Total number of steps in the operation
            name: Name of the operation being tracked
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.name = name
        self.start_time = None
        self.cancelled = False
    
    def start(self):
        """Start tracking progress."""
        self.start_time = time.time()
        self.current_step = 0
        self.cancelled = False
        logging.info(f"Starting {self.name} (0/{self.total_steps})")
        
    def update(self, step=None, message=None):
        """
        Update progress.
        
        Args:
            step: Current step (if None, increment by 1)
            message: Optional message to log with the update
        """
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1
            
        percentage = (self.current_step / self.total_steps) * 100
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        log_msg = f"{self.name} progress: {percentage:.1f}% ({self.current_step}/{self.total_steps})"
        if message:
            log_msg += f" - {message}"
        
        logging.info(log_msg)
        
        # Log every 10% progress or each minute for long-running tasks
        if self.current_step % max(1, self.total_steps // 10) == 0 or elapsed > 60:
            logging.info(f"{self.name} has been running for {elapsed:.1f} seconds")
    
    def finish(self):
        """Mark operation as finished."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        logging.info(f"Finished {self.name} in {elapsed:.2f} seconds")
        
    def is_cancelled(self):
        """Check if operation was cancelled."""
        return self.cancelled
    
    def cancel(self):
        """Cancel the operation."""
        self.cancelled = True
        logging.info(f"{self.name} was cancelled")


# ===== Timeout Handling Functionality =====

class TimeoutError(Exception):
    """Exception raised when a function times out."""
    pass


def timeout(seconds):
    """
    Function decorator that raises TimeoutError when a function takes longer than 'seconds' to complete.
    Works on Unix/Linux/Mac with signal module.
    
    Args:
        seconds: Timeout duration in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def handler(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")
            
            # Set the timeout handler
            original_handler = signal.getsignal(signal.SIGALRM)
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
            finally:
                # Reset the alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)
            return result
        return wrapper if sys.platform != 'win32' else func  # Signal approach doesn't work on Windows
    return decorator


class ThreadWithTimeout(threading.Thread):
    """Thread class with a timeout and a result."""
    
    def __init__(self, target, args=(), kwargs=None, timeout=None):
        """
        Initialize a thread with timeout capability.
        
        Args:
            target: Function to execute
            args: Arguments to pass to target
            kwargs: Keyword arguments to pass to target
            timeout: Maximum execution time in seconds
        """
        super().__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.timeout = timeout
        self.result = None
        self.exception = None
        self._is_cancelled = False
    
    def run(self):
        """Execute the target function and capture its result or exception."""
        try:
            if not self._is_cancelled:
                self.result = self.target(*self.args, **self.kwargs)
        except Exception as e:
            self.exception = e
            logging.error(f"Error in thread: {e}")
    
    def cancel(self):
        """Mark the thread as cancelled."""
        self._is_cancelled = True
    
    def run_with_timeout(self):
        """
        Run the thread with timeout and return the result or raise exception.
        
        Returns:
            Result of the target function
            
        Raises:
            TimeoutError: If execution exceeds the timeout
            Exception: Any exception raised by the target function
        """
        self.start()
        self.join(self.timeout)
        
        if self.is_alive():
            self.cancel()
            self.join(0.1)  # Give a small amount of time to clean up
            if self.is_alive():
                logging.warning("Thread could not be cancelled gracefully")
            raise TimeoutError(f"Operation timed out after {self.timeout} seconds")
        
        if self.exception:
            raise self.exception
        
        return self.result


def run_with_timeout(func, args=(), kwargs=None, timeout=30):
    """
    Run a function with a timeout.
    Works on all platforms using threading.
    
    Args:
        func: Function to execute
        args: Arguments to pass to function
        kwargs: Keyword arguments to pass to function
        timeout: Maximum execution time in seconds
        
    Returns:
        Result of the function
        
    Raises:
        TimeoutError: If execution exceeds the timeout
    """
    kwargs = kwargs or {}
    thread = ThreadWithTimeout(target=func, args=args, kwargs=kwargs, timeout=timeout)
    return thread.run_with_timeout()
