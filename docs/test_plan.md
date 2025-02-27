# PyAutoload Test Plan

This document outlines a comprehensive test plan for the PyAutoload library, focusing on testing the integration with Python's import system and ensuring reliability in real-world scenarios.

## Test-Driven Development Approach

We will follow a strict TDD approach:

1. Write failing tests first
2. Implement the minimum code required to pass tests
3. Refactor for clarity and performance
4. Repeat for each component and feature

## Test Hierarchy

### 1. Unit Tests

Test individual components in isolation:

#### 1.1 Inflector Tests

- Test basic camelization
- Test custom inflections
- Test edge cases (numbers, special characters)

#### 1.2 Module Registry Tests

- Test registration of modules
- Test lookup functionality
- Test dependency tracking
- Test concurrency handling

#### 1.3 File Scanner Tests

- Test directory traversal
- Test file path to module name conversion
- Test handling of packages vs. modules
- Test ignored directories and files

#### 1.4 Import Hook Tests

- Test finder functionality
- Test loader functionality
- Test module spec creation
- Test integration with sys.meta_path

### 2. Integration Tests

Test components working together:

#### 2.1 Basic Import Tests

- Test importing simple modules
- Test importing packages
- Test nested packages
- Test relative imports

#### 2.2 Eager Loading Tests

- Test loading all modules
- Test loading specific namespaces
- Test handling of import errors
- Test loading order

#### 2.3 Reloading Tests

- Test file change detection
- Test module reloading
- Test handling of dependent modules
- Test concurrency during reloading

### 3. System Tests

Test the complete system with realistic scenarios:

#### 3.1 Project Structure Tests

- Test with different project structures
- Test with nested namespaces
- Test with circular dependencies
- Test with non-standard naming

#### 3.2 Performance Tests

- Test import time compared to standard imports
- Test memory usage
- Test scalability with large projects
- Test concurrent import scenarios

#### 3.3 Compatibility Tests

- Test with different Python versions
- Test with different operating systems
- Test with popular frameworks
- Test with various import patterns

## Test Fixtures

We will create comprehensive test fixtures:

### 1. Sample Project Structure

```
sample_app/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── user.py
│   └── product.py
├── controllers/
│   ├── __init__.py
│   ├── users_controller.py
│   └── products_controller.py
└── services/
    ├── __init__.py
    ├── authentication.py
    └── authorization.py
```

### 2. Edge Case Fixtures

- Circular dependency examples
- Non-standard naming examples
- Import error examples
- Thread safety test cases

### 3. Mock Import System

Create a controlled environment for testing import hooks:

```python
class MockMetaPath:
    def __init__(self):
        self.finders = []
        
    def find_spec(self, fullname, path=None, target=None):
        for finder in self.finders:
            spec = finder.find_spec(fullname, path, target)
            if spec is not None:
                return spec
        return None
```

## Test Implementation

### 1. Example Unit Test: Inflector

```python
def test_camelize():
    inflector = Inflector()
    assert inflector.camelize("user") == "User"
    assert inflector.camelize("users_controller") == "UsersController"
    assert inflector.camelize("html_parser") == "HtmlParser"
    
def test_custom_inflections():
    inflector = Inflector()
    inflector.inflect({
        "html_parser": "HTMLParser",
        "json_api": "JSONAPI"
    })
    assert inflector.camelize("html_parser") == "HTMLParser"
    assert inflector.camelize("json_api") == "JSONAPI"
```

### 2. Example Integration Test: Module Loading

```python
def test_module_loading(sample_project):
    # Set up autoloader with sample project
    loader = AutoLoader(base_path=sample_project, top_level="sample_app")
    loader.setup()
    
    # Test importing a module
    import sample_app.models.user
    assert hasattr(sample_app.models.user, "User")
    
    # Test importing a controller
    import sample_app.controllers.users_controller
    assert hasattr(sample_app.controllers.users_controller, "UsersController")
```

### 3. Example System Test: Reloading

```python
def test_module_reloading(sample_project):
    # Set up autoloader with reloading enabled
    loader = AutoLoader(base_path=sample_project, top_level="sample_app")
    loader.setup()
    loader.enable_reloading()
    
    # Import a module
    import sample_app.models.user
    original_user = sample_app.models.user.User
    
    # Modify the module file
    user_path = os.path.join(sample_project, "models", "user.py")
    with open(user_path, "a") as f:
        f.write("\nclass NewClass:\n    pass\n")
    
    # Trigger reloading
    time.sleep(0.1)  # Give the file watcher time to detect changes
    loader.reload()
    
    # Check that the module was reloaded
    import sample_app.models.user
    assert hasattr(sample_app.models.user, "NewClass")
    assert sample_app.models.user.User is not original_user
```

## Test Coverage Goals

We aim for:

- **90%+ line coverage** for core functionality
- **100% coverage** for critical components:
  - Import hooks
  - Module registry
  - Reloading mechanism
- **Edge case coverage** for:
  - Thread safety
  - Error handling
  - Compatibility issues

## Test Automation

We'll set up:

1. **Continuous Integration** via GitHub Actions
2. **Automated test runs** on multiple Python versions
3. **Coverage reporting** in CI
4. **Benchmark tracking** for performance tests

## Test Categories

Our test suite will be organized into categories:

### 1. Fast Tests

- Unit tests and simple integration tests
- Run on every commit
- Should complete in under 10 seconds

### 2. Standard Tests

- Full integration tests
- Run on pull requests
- Should complete in under 2 minutes

### 3. Extended Tests

- System tests, compatibility tests, and benchmarks
- Run before releases
- May take several minutes to complete

## Testing Tools

We'll use:

- **pytest** as the primary test framework
- **pytest-cov** for coverage reporting
- **pytest-benchmark** for performance testing
- **pytest-mock** for mocking
- **pytest-xdist** for parallel test execution

## Mocking Strategy

For testing import hooks without affecting the global import system:

```python
@contextmanager
def isolated_meta_path():
    """Context manager that isolates sys.meta_path changes."""
    original_meta_path = sys.meta_path.copy()
    try:
        yield
    finally:
        sys.meta_path = original_meta_path

def test_finder_integration():
    with isolated_meta_path():
        finder = PyAutoloadFinder(base_paths=["sample"])
        # Test finder functionality
        sys.meta_path.insert(0, finder)
        # ... test imports
```

## Test Implementation Schedule

1. **Week 1**: Core unit tests for Inflector, Registry
2. **Week 2**: Unit tests for Scanner, Import Hooks
3. **Week 3**: Integration tests for basic importing
4. **Week 4**: Integration tests for eager loading
5. **Week 5**: Integration tests for reloading
6. **Week 6**: System tests for real-world scenarios
7. **Week 7**: Performance and compatibility tests
8. **Week 8**: Documentation tests and examples
