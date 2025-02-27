"""
Integration tests for PyAutoload.

These tests verify that all components work together correctly.
"""
import os
import sys
import pytest
import importlib
from contextlib import contextmanager
from pyautoload import AutoLoader


@contextmanager
def isolated_meta_path():
    """Context manager that isolates sys.meta_path changes."""
    original_meta_path = sys.meta_path.copy()
    try:
        yield
    finally:
        sys.meta_path = original_meta_path


@contextmanager
def isolated_modules():
    """Context manager that preserves the state of sys.modules."""
    original_modules = sys.modules.copy()
    try:
        yield
    finally:
        # Restore only the modules that were there originally
        # to avoid affecting other tests
        for key in list(sys.modules.keys()):
            if key not in original_modules:
                del sys.modules[key]
            else:
                sys.modules[key] = original_modules[key]


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project structure for testing."""
    # Create the project structure
    app_dir = tmp_path / "sample_app"
    app_dir.mkdir()
    
    # Create __init__.py
    init_py = app_dir / "__init__.py"
    init_py.write_text("# Sample app")
    
    # Create models directory and files
    models_dir = app_dir / "models"
    models_dir.mkdir()
    
    models_init = models_dir / "__init__.py"
    models_init.write_text("# Models package")
    
    user_py = models_dir / "user.py"
    user_py.write_text("""
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        
    def __str__(self):
        return f"{self.name} <{self.email}>"
""")
    
    product_py = models_dir / "product.py"
    product_py.write_text("""
class Product:
    def __init__(self, name, price):
        self.name = name
        self.price = price
        
    def __str__(self):
        return f"{self.name} (${self.price})"
""")
    
    # Create controllers directory and files
    controllers_dir = app_dir / "controllers"
    controllers_dir.mkdir()
    
    controllers_init = controllers_dir / "__init__.py"
    controllers_init.write_text("# Controllers package")
    
    users_controller_py = controllers_dir / "users_controller.py"
    users_controller_py.write_text("""
from sample_app.models.user import User

class UsersController:
    def __init__(self):
        self.users = []
        
    def create_user(self, name, email):
        user = User(name, email)
        self.users.append(user)
        return user
        
    def get_users(self):
        return self.users
""")
    
    products_controller_py = controllers_dir / "products_controller.py"
    products_controller_py.write_text("""
from sample_app.models.product import Product

class ProductsController:
    def __init__(self):
        self.products = []
        
    def create_product(self, name, price):
        product = Product(name, price)
        self.products.append(product)
        return product
        
    def get_products(self):
        return self.products
""")
    
    return str(tmp_path)


class TestIntegration:
    """Integration tests for PyAutoload."""
    
    def test_basic_autoloading(self, sample_project):
        """Test basic autoloading of modules."""
        with isolated_meta_path(), isolated_modules():
            # Initialize autoloader
            loader = AutoLoader(
                base_path=os.path.join(sample_project, "sample_app"),
                top_level="sample_app"
            )
            
            # Set up autoloading
            loader.setup()
            
            try:
                # Import a model
                import sample_app.models.user
                assert hasattr(sample_app.models.user, "User")
                
                # Create a user
                user = sample_app.models.user.User("Test User", "test@example.com")
                assert user.name == "Test User"
                assert user.email == "test@example.com"
                
                # Import a controller
                import sample_app.controllers.users_controller
                assert hasattr(sample_app.controllers.users_controller, "UsersController")
                
                # Create a controller
                controller = sample_app.controllers.users_controller.UsersController()
                assert hasattr(controller, "create_user")
                
                # Test controller functionality
                new_user = controller.create_user("New User", "new@example.com")
                assert new_user.name == "New User"
                assert new_user.email == "new@example.com"
                assert len(controller.get_users()) == 1
            finally:
                # Clean up
                if loader.watcher:
                    loader.watcher.stop()
    
    def test_eager_loading(self, sample_project):
        """Test eager loading of all modules."""
        with isolated_meta_path(), isolated_modules():
            # Initialize autoloader
            loader = AutoLoader(
                base_path=os.path.join(sample_project, "sample_app"),
                top_level="sample_app"
            )
            
            # Set up autoloading and eager load
            loader.setup()
            loader.eager_load()
            
            try:
                # All modules should be loaded
                assert "sample_app.models.user" in sys.modules
                assert "sample_app.models.product" in sys.modules
                assert "sample_app.controllers.users_controller" in sys.modules
                assert "sample_app.controllers.products_controller" in sys.modules
                
                # Verify functionality
                user_class = sys.modules["sample_app.models.user"].User
                product_class = sys.modules["sample_app.models.product"].Product
                
                assert user_class.__name__ == "User"
                assert product_class.__name__ == "Product"
            finally:
                # Clean up
                if loader.watcher:
                    loader.watcher.stop()
    
    def test_module_reloading(self, sample_project):
        """Test reloading of modules when files change."""
        with isolated_meta_path(), isolated_modules():
            # Initialize autoloader
            loader = AutoLoader(
                base_path=os.path.join(sample_project, "sample_app"),
                top_level="sample_app"
            )
            
            # Set up autoloading
            loader.setup()
            
            try:
                # Import a module
                import sample_app.models.user
                original_user = sample_app.models.user.User
                
                # Modify the module file
                user_path = os.path.join(sample_project, "sample_app", "models", "user.py")
                with open(user_path, "a") as f:
                    f.write("\nclass Admin(User):\n    pass\n")
                
                # Reload the module
                loader.reload_module("sample_app.models.user")
                
                # Re-import to get the updated module
                importlib.reload(sys.modules["sample_app.models.user"])
                
                # Check that the new class is available
                assert hasattr(sample_app.models.user, "Admin")
                assert issubclass(sample_app.models.user.Admin, sample_app.models.user.User)
            finally:
                # Clean up
                if loader.watcher:
                    loader.watcher.stop()
    
    def test_multiple_root_paths(self, tmp_path):
        """Test autoloading with multiple root paths."""
        with isolated_meta_path(), isolated_modules():
            # Create two separate app directories
            app1_dir = tmp_path / "app1"
            app1_dir.mkdir()
            (app1_dir / "__init__.py").write_text("# App 1")
            (app1_dir / "module1.py").write_text("class Module1:\n    pass")
            
            app2_dir = tmp_path / "app2"
            app2_dir.mkdir()
            (app2_dir / "__init__.py").write_text("# App 2")
            (app2_dir / "module2.py").write_text("class Module2:\n    pass")
            
            # Initialize autoloader with both roots
            loader = AutoLoader(
                root_paths=[str(app1_dir), str(app2_dir)]
            )
            
            # Set up autoloading
            loader.setup()
            
            try:
                # Import modules from both apps
                import app1.module1
                import app2.module2
                
                assert hasattr(app1.module1, "Module1")
                assert hasattr(app2.module2, "Module2")
            finally:
                # Clean up
                if loader.watcher:
                    loader.watcher.stop()
