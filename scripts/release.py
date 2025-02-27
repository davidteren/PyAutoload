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
import traceback
from pathlib import Path


def run_command(command, capture_output=False):
    """Run a shell command and return the result."""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command.split(), capture_output=capture_output, text=True)
        if result.returncode != 0:
            print(f"Command failed with exit code {result.returncode}")
            if capture_output:
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
            sys.exit(1)
        return result
    except Exception as e:
        print(f"Error executing command: {command}")
        print(f"Exception: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


def clean_build_artifacts():
    """Clean up previous build artifacts."""
    print("Cleaning up previous build artifacts...")
    try:
        for directory in ["dist", "build", "*.egg-info"]:
            run_command(f"rm -rf {directory}")
    except Exception as e:
        print(f"Error cleaning build artifacts: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


def build_package():
    """Build the package distribution files."""
    print("Building package distribution files...")
    try:
        run_command("python -m build")
    except Exception as e:
        print(f"Error building package: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


def check_distribution():
    """Check the built distribution with twine."""
    print("Checking distribution files...")
    try:
        run_command("twine check dist/*")
    except Exception as e:
        print(f"Error checking distribution: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


def upload_to_pypi(test=False):
    """Upload the distribution to PyPI or TestPyPI."""
    try:
        if test:
            print("Uploading to TestPyPI...")
            run_command("twine upload --repository-url https://test.pypi.org/legacy/ dist/*")
        else:
            print("Uploading to PyPI...")
            run_command("twine upload dist/*")
    except Exception as e:
        print(f"Error uploading to {'TestPyPI' if test else 'PyPI'}: {str(e)}")
        print("Please check your credentials and network connection.")
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Release PyAutoload to PyPI")
    parser.add_argument("--test", action="store_true", help="Upload to TestPyPI instead of PyPI")
    args = parser.parse_args()

    try:
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

        # Check if dist directory contains files
        dist_files = list(Path("dist").glob("*"))
        if not dist_files:
            print("Error: No distribution files were created.")
            sys.exit(1)
        
        print(f"Created distribution files: {[f.name for f in dist_files]}")

        # Confirm before uploading
        if args.test:
            target = "TestPyPI"
        else:
            target = "PyPI"

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
            
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
