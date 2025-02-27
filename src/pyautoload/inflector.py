"""
Module that provides inflection functionality for PyAutoload.
"""


class Inflector:
    """
    Handles conversion between file names and module/class names.
    
    This class is responsible for converting:
    - Snake case file names to CamelCase class/module names
    - Supporting custom inflections for special cases like acronyms
    """
    
    def __init__(self):
        """Initialize a new Inflector with empty custom inflections."""
        self.custom_inflections = {}
    
    def camelize(self, basename, _=None):
        """
        Convert a snake_case basename to CamelCase.
        
        Args:
            basename (str): The basename to camelize (e.g., "users_controller")
            _ (any, optional): Placeholder parameter for compatibility with Zeitwerk
            
        Returns:
            str: The camelized name (e.g., "UsersController")
        """
        # Check for custom inflections first
        if basename in self.custom_inflections:
            return self.custom_inflections[basename]
        
        # Otherwise, perform standard camelization
        return ''.join(x.capitalize() or '_' for x in basename.split('_'))
    
    def inflect(self, inflections):
        """
        Add custom inflections to the inflector.
        
        Args:
            inflections (dict): A dictionary mapping from snake_case to CamelCase
                               Example: {"html_parser": "HTMLParser"}
        """
        self.custom_inflections.update(inflections)
