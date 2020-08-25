import sys
from setuptools import setup, find_packages

from pydantic_odm import __version__

is_wheel = 'bdist_wheel' in sys.argv

excluded = []


with open("README.md", "r") as fh:
    long_description = fh.read()


def exclude_package(pkg):
    for exclude in excluded:
        if pkg.startswith(exclude):
            return True
    return False


def create_package_list(base_package):
    return ([base_package] +
            [base_package + '.' + pkg
             for pkg
             in find_packages(base_package)
             if not exclude_package(pkg)])


setup(
    # Metadata
    name='pydantic-odm',
    version=__version__,
    author='Ivan Galin',
    author_email='gin.voglgorad@gmail.com',
    url='https://github.com/i8enn/pydantic-odm/',
    download_url='',
    description='Small async ODM for MongoDB based on Motor and Pydantic',
    long_description=long_description,
    long_description_content_type="text/markdown",
    license='MIT',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Unix',
        'Operating System :: POSIX :: Linux',
        'Environment :: Console',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet',
    ],
    packages=create_package_list('pydantic_odm'),
    install_requires=[
        'pydantic>=1.1',
        'motor>=2.0',
    ],
    python_requires='>=3.6',
    zip_safe=False
)
