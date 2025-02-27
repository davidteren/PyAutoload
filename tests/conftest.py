"""
PyAutoload test fixtures and configuration.
"""
import os
import sys
import tempfile
import shutil
import pytest

# Add the source directory to the path so tests can import the package
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, src_path)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_project(temp_dir):
    """
    Create a sample project structure for testing autoloading.
    
    Directory structure:
    /sample_app
      /__init__.py
      /models
        /__init__.py
        /user.py
      /controllers
        /__init__.py
        /users_controller.py
      /services
        /__init__.py
        /user_service.py
        /auth
          /__init__.py
          /authentication_service.py
    """
    project_path = os.path.join(temp_dir, "sample_app")
    os.makedirs(project_path)
    
    # Create __init__.py
    with open(os.path.join(project_path, "__init__.py"), "w") as f:
        f.write("")
    
    # Create models directory
    models_path = os.path.join(project_path, "models")
    os.makedirs(models_path)
    with open(os.path.join(models_path, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(models_path, "user.py"), "w") as f:
        f.write("class User:\n    pass\n")
    
    # Create controllers directory
    controllers_path = os.path.join(project_path, "controllers")
    os.makedirs(controllers_path)
    with open(os.path.join(controllers_path, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(controllers_path, "users_controller.py"), "w") as f:
        f.write("class UsersController:\n    pass\n")
    
    # Create services directory
    services_path = os.path.join(project_path, "services")
    os.makedirs(services_path)
    with open(os.path.join(services_path, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(services_path, "user_service.py"), "w") as f:
        f.write("class UserService:\n    pass\n")
    
    # Create nested auth directory
    auth_path = os.path.join(services_path, "auth")
    os.makedirs(auth_path)
    with open(os.path.join(auth_path, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(auth_path, "authentication_service.py"), "w") as f:
        f.write("class AuthenticationService:\n    pass\n")
    
    return project_path
