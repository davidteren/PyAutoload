"""
Tests for the Inflector class.
"""
import pytest
from pyautoload import Inflector


class TestInflector:
    """Test suite for the Inflector class."""

    def test_camelize(self):
        """Test that the inflector can camelize strings correctly."""
        inflector = Inflector()
        
        # Test basic camelization
        assert inflector.camelize("user") == "User"
        assert inflector.camelize("users_controller") == "UsersController"
        
        # Test handling of digits
        assert inflector.camelize("point_3d_value") == "Point3dValue"
        
        # Test acronyms (defaults to simple camelization)
        assert inflector.camelize("html_parser") == "HtmlParser"
        
    def test_custom_inflections(self):
        """Test that the inflector can handle custom inflections."""
        inflector = Inflector()
        
        # Add custom inflections
        inflector.inflect({
            "html_parser": "HTMLParser",
            "csv_controller": "CSVController",
            "mysql_adapter": "MySQLAdapter"
        })
        
        # Test custom inflections
        assert inflector.camelize("html_parser") == "HTMLParser"
        assert inflector.camelize("csv_controller") == "CSVController"
        assert inflector.camelize("mysql_adapter") == "MySQLAdapter"
        
        # Test regular camelization still works
        assert inflector.camelize("users_controller") == "UsersController"
