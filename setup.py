from setuptools import setup, find_packages

setup(
    name='PyAutoload',
    version='0.1',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=['watchdog'],
    author='[Your Name]',
    author_email='[Your Email]',
    description='A Python autoloading library inspired by Zeitwerk.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='[Project URL]',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
