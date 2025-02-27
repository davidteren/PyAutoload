"""
Tests for the FileWatcher class.
"""
import os
import time
import pytest
from pyautoload import FileWatcher


class TestFileWatcher:
    """Test suite for the FileWatcher class."""

    def test_file_watcher_initialization(self):
        """Test that the file watcher can be initialized with valid parameters."""
        watcher = FileWatcher(dirs=["dummy"])
        assert watcher is not None
        assert watcher.dirs == ["dummy"]

    def test_file_watcher_validation(self):
        """Test that the file watcher validates its parameters."""
        with pytest.raises(ValueError):
            FileWatcher(dirs=None)
        
        with pytest.raises(ValueError):
            FileWatcher(dirs=[])

    def test_file_watcher_callback(self, temp_dir):
        """Test that the file watcher calls the callback when files change."""
        # Skip this test until implementation is ready
        pytest.skip("Implementation not ready")
        
        # Create a test file
        test_file = os.path.join(temp_dir, "test_file.py")
        with open(test_file, "w") as f:
            f.write("# Test file")
        
        # Create a callback that sets a flag when called
        callback_called = False
        def callback(event):
            nonlocal callback_called
            callback_called = True
        
        # Start the watcher
        watcher = FileWatcher(dirs=[temp_dir])
        watcher.on_change(callback)
        watcher.start()
        
        try:
            # Modify the file
            time.sleep(0.1)  # Give the watcher time to start
            with open(test_file, "a") as f:
                f.write("\n# Modified")
            
            # Wait for the callback to be called
            time.sleep(0.2)
            assert callback_called, "Callback was not called when file changed"
        finally:
            watcher.stop()
            
    def test_file_watcher_filter(self, temp_dir):
        """Test that the file watcher can filter events."""
        # Skip this test until implementation is ready
        pytest.skip("Implementation not ready")
        
        # Create test files
        py_file = os.path.join(temp_dir, "test_file.py")
        with open(py_file, "w") as f:
            f.write("# Test Python file")
            
        txt_file = os.path.join(temp_dir, "test_file.txt")
        with open(txt_file, "w") as f:
            f.write("Test text file")
        
        # Create callbacks that set flags when called
        py_callback_called = False
        def py_callback(event):
            nonlocal py_callback_called
            py_callback_called = True
        
        # Start the watcher with a Python file filter
        watcher = FileWatcher(dirs=[temp_dir], patterns=["*.py"])
        watcher.on_change(py_callback)
        watcher.start()
        
        try:
            # Modify both files
            time.sleep(0.1)  # Give the watcher time to start
            
            with open(py_file, "a") as f:
                f.write("\n# Modified Python file")
            
            with open(txt_file, "a") as f:
                f.write("\nModified text file")
            
            # Wait for callbacks to be called
            time.sleep(0.2)
            assert py_callback_called, "Python callback was not called when Python file changed"
            
        finally:
            watcher.stop()
