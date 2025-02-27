#!/usr/bin/env python3
"""
Release script for PyAutoload.

This script helps with the release process by:
1. Building the distribution packages
2. Testing the packages locally
3. Uploading to PyPI

Usage:
    python scripts/release.py [--test]

Options:
    --test  Upload to TestPyPI instead of PyPI
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, capture_output=False):
    """Run a shell command and return the result."""
    print(f"Running: {command}")
    result = subprocess.run(command.split(), capture_output=capture_output, text=True)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        if capture_output:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        sys.exit(1)
    return result


def clean_build_artifacts():
    """Clean up previous build artifacts."""
    print("Cleaning up previous build artifacts...")
    for directory in ["dist", "build", "*.egg-info"]:
        run_command(f"rm -rf {directory}")


def build_package():
    """Build the package distribution files."""
    print("Building package distribution files...")
    run_command("python -m build")


def check_distribution():
    """Check the built distribution with twine."""
    print("Checking distribution files...")
    run_command("twine check dist/*")


def upload_to_pypi(test=False):
    """Upload the distribution to PyPI or TestPyPI."""
    if test:
        print("Uploading to TestPyPI...")
        run_command("twine upload --repository-url https://test.pypi.org/legacy/ dist/*")
    else:
        print("Uploading to PyPI...")
        run_command("twine upload dist/*")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Release PyAutoload to PyPI")
    parser.add_argument("--test", action="store_true", help="Upload to TestPyPI instead of PyPI")
    args = parser.parse_args()

    # Ensure we're in the project root directory
    os.chdir(Path(__file__).parent.parent)

    # Check for required tools
    for tool in ["twine", "build"]:
        try:
            run_command(f"{tool} --version", capture_output=True)
        except Exception:
            print(f"Error: {tool} is not installed. Please install it with 'pip install {tool}'")
            sys.exit(1)

    # Prepare and build
    clean_build_artifacts()
    build_package()
    check_distribution()

    # Confirm before uploading
    target = "TestPyPI" if args.test else "PyPI"
    confirm = input(f"\nReady to upload to {target}. Continue? [y/N] ")
    if confirm.lower() != 'y':
        print("Upload canceled.")
        return

    # Upload
    upload_to_pypi(args.test)
    print("Upload completed successfully!")

    if args.test:
        print("\nTo install from TestPyPI:")
        print("pip install --index-url https://test.pypi.org/simple/ PyAutoload")
    else:
        print("\nTo install from PyPI:")
        print("pip install PyAutoload")


if __name__ == "__main__":
    main()
