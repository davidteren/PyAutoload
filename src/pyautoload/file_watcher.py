"""
Module that provides file watching functionality for PyAutoload.
"""
import os
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


class FileWatcher:
    """
    Watches for file changes in specified directories.
    
    This class uses the watchdog library to monitor file changes
    and trigger callbacks when files are modified, created, or deleted.
    """
    
    def __init__(self, dirs, patterns=None):
        """
        Initialize a new FileWatcher.
        
        Args:
            dirs (list): A list of directories to watch
            patterns (list, optional): A list of patterns to match (e.g., ["*.py"])
        
        Raises:
            ValueError: If dirs is None or empty
        """
        if not dirs:
            raise ValueError("dirs must be a non-empty list of directories")
        
        self.dirs = dirs
        self.patterns = patterns or ["*.py"]
        self.observer = None
        self.handlers = []
        self.callbacks = []
    
    def on_change(self, callback):
        """
        Register a callback to be called when files change.
        
        Args:
            callback (callable): A function to call when files change
                                The function should accept an event parameter
        """
        self.callbacks.append(callback)
    
    def _on_any_event(self, event):
        """
        Handle watchdog events.
        
        Args:
            event (watchdog.events.FileSystemEvent): The event to handle
        """
        for callback in self.callbacks:
            callback(event)
    
    def start(self):
        """
        Start watching for file changes.
        """
        if self.observer:
            return
        
        self.observer = Observer()
        
        # Create event handler
        event_handler = PatternMatchingEventHandler(
            patterns=self.patterns,
            ignore_directories=True,
            case_sensitive=False
        )
        event_handler.on_any_event = self._on_any_event
        self.handlers.append(event_handler)
        
        # Schedule the observer
        for directory in self.dirs:
            if os.path.isdir(directory):
                self.observer.schedule(event_handler, directory, recursive=True)
        
        # Start the observer
        self.observer.start()
    
    def stop(self):
        """
        Stop watching for file changes.
        """
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
