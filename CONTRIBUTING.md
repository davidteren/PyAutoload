# Contributing to PyAutoload

First off, thank you for considering contributing to PyAutoload! We appreciate your time and effort to make this project better.

## Code of Conduct

By participating in this project, you agree to abide by our code of conduct. Please treat all community members with respect.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report for PyAutoload.

Before creating bug reports, please check [the issue list](https://github.com/user/pyautoload/issues) as you might find that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title** for the issue to identify the problem.
* **Describe the exact steps which reproduce the problem** in as many details as possible.
* **Provide specific examples to demonstrate the steps**. Include links to files or GitHub projects, or copy/pasteable snippets, which you use in those examples.
* **Describe the behavior you observed after following the steps** and point out what exactly is the problem with that behavior.
* **Explain which behavior you expected to see instead and why.**
* **Include screenshots or animated GIFs** if applicable.
* **If you're reporting that PyAutoload crashed**, include a stack trace.
* **If the problem is related to performance or memory**, include a CPU profile capture with your report.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for PyAutoload, including completely new features and minor improvements to existing functionality.

* **Use a clear and descriptive title** for the issue to identify the suggestion.
* **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
* **Provide specific examples to demonstrate the steps** or how the enhancement would be used.
* **Describe the current behavior** and **explain which behavior you expected to see instead** and why.
* **Explain why this enhancement would be useful** to most PyAutoload users.

### Pull Requests

* Fill in the required template
* Do not include issue numbers in the PR title
* Include screenshots and animated GIFs in your pull request whenever possible.
* Follow the Python styleguides (PEP 8)
* Include tests for any new functionality or bug fixes
* Document new code appropriately
* End all files with a newline

## Development Workflow

1. Fork and clone the repository
2. Create a new branch: `git checkout -b my-branch-name`
3. Install development dependencies: `pip install -e ".[dev]"`
4. Make your changes
5. Run the tests: `pytest`
6. Push to your fork and submit a pull request

## Testing

We use pytest for testing. Please make sure any new functionality includes appropriate tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pyautoload
```

## Styleguides

### Git Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

### Python Styleguide

All Python code should adhere to [PEP 8](https://www.python.org/dev/peps/pep-0008/).

### Documentation Styleguide

* Use [Google style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) for documenting code.
* Use Markdown for documentation files.

## Additional Notes

### Issue and Pull Request Labels

This section lists the labels we use to help us track and manage issues and pull requests.

* **bug** - Issues that are bugs
* **documentation** - Issues related to documentation
* **enhancement** - Issues that are feature requests
* **good first issue** - Good for newcomers
* **help wanted** - Extra attention is needed
* **question** - Further information is requested
