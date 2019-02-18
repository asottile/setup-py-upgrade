[![Build Status](https://travis-ci.org/asottile/setup-py-upgrade.svg?branch=master)](https://travis-ci.org/asottile/setup-py-upgrade)

setup-py-upgrade
================

upgrade a setup.py to declarative metadata

## installation

`pip install setup-py-upgrade`

## cli

Consult the help for the latest usage:

```console
$ setup-py-upgrade --help
usage: setup-py-upgrade [-h] directory

positional arguments:
  directory

optional arguments:
  -h, --help  show this help message and exit
```

pass the root directory of the repository you'd like to convert

the script overwrites `setup.py` and `setup.cfg` when run

## sample output

```console
$ setup-py-upgrade ../pre-commit
../pre-commit/setup.py and ../pre-commit/setup.cfg written!
$ tail -n999 ../pre-commit/setup.{py,cfg}
==> ../pre-commit/setup.py <==
from setuptools import setup
setup()

==> ../pre-commit/setup.cfg <==
[metadata]
name = pre_commit
description = A framework for managing and maintaining multi-language pre-commit hooks.
long_description = file: README.md
long_description_content_type = text/markdown
url = https://github.com/pre-commit/pre-commit
version = 1.14.2
author = Anthony Sottile
author_email = asottile@umich.edu
classifiers =
    License :: OSI Approved :: MIT License
    Programming Language :: Python :: 2
    Programming Language :: Python :: 2.7
    Programming Language :: Python :: 3
    Programming Language :: Python :: 3.6
    Programming Language :: Python :: 3.7
    Programming Language :: Python :: Implementation :: CPython
    Programming Language :: Python :: Implementation :: PyPy

[options]
packages = find:
install_requires =
    aspy.yaml
    cfgv>=1.4.0
    identify>=1.0.0
    importlib-metadata
    nodeenv>=0.11.1
    pyyaml
    six
    toml
    virtualenv
    futures; python_version<"3.2"
    importlib-resources; python_version<"3.7"

[options.packages.find]
exclude =
    tests*
    testing*

[options.entry_points]
console_scripts =
    pre-commit = pre_commit.main:main
    pre-commit-validate-config = pre_commit.clientlib:validate_config_main
    pre-commit-validate-manifest = pre_commit.clientlib:validate_manifest_main

[options.package_data]
pre_commit.resources =
    *.tar.gz
    empty_template_*
    hook-tmpl

[bdist_wheel]
universal = True
```

## what versions of setuptools / pip does the output work with?

- `pip>=1.5` (when installing from a wheel)
    - released 2014-01-02
- `setuptools>=30.3` (when building from source)
    - released 2016-12-08
- `virtualenv>=15.2` (to get a sufficient setuptools via `--no-download`)
   - released 2018-03-21

## what is not supported

declarative metadata does not support `ext_modules` or setuptools plugins --
those must stay in `setup.py`.  If you're converting a project which uses one
of those, you'll see a message like:

```console
$ setup-py-upgrade ../future-breakpoint/
ext_modules= is not supported in setup.cfg
```

To convert those, temporarily remove the offending constructs from `setup.py`,
then run `setup-py-upgrade`, then paste them back into the file.
