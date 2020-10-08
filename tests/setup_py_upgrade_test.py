import pytest

from setup_py_upgrade import main


def test_basic(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'setup(name="foo")\n',
    )
    main((str(tmpdir),))
    setup_py = tmpdir.join('setup.py').read()
    setup_cfg = tmpdir.join('setup.cfg').read()
    assert setup_py == 'from setuptools import setup\nsetup()\n'
    assert setup_cfg == '[metadata]\nname = foo\n'


def test_non_from_import_setuptools(tmpdir):
    tmpdir.join('setup.py').write(
        'import setuptools\n'
        'setuptools.setup(name="foo")\n',
    )
    main((str(tmpdir),))
    setup_cfg = tmpdir.join('setup.cfg').read()
    assert setup_cfg == '[metadata]\nname = foo\n'


def test_reads_file(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'with open("README.md") as f:\n'
        '    readme = f.read()\n'
        'setup(name="foo", long_description=readme)',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        'long_description = file: README.md\n'
    )


def test_unrelated_with_statement(tmpdir):  # only added for test coverage
    tmpdir.join('setup.py').write(
        'import contextlib\n'
        'from setuptools import setup\n'
        'with contextlib.suppress(ImportError):\n'
        '    import dne\n'
        'setup(name="foo")\n',
    )
    main((str(tmpdir),))
    setup_cfg = tmpdir.join('setup.cfg').read()
    assert setup_cfg == '[metadata]\nname = foo\n'


def test_option_key(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'setup(name="foo", install_requires=["astpretty", "six"])\n',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        '\n'
        '[options]\n'
        'install_requires =\n'
        '    astpretty\n'
        '    six\n'
    )


def test_unsupported_argument(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import Extension, setup\n'
        'setup(name="foo", ext_modules=[Extension("_x", ["_x.c"])])\n',
    )
    with pytest.raises(SystemExit) as excinfo:
        main((str(tmpdir),))
    msg, = excinfo.value.args
    assert msg == 'ext_modules= is not supported in setup.cfg'


def test_intentionally_not_parsable(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'from foo import __version__\n'
        'setup(name="foo", version=__version__)\n',
    )
    with pytest.raises(NotImplementedError) as excinfo:
        main((str(tmpdir),))
    msg, = excinfo.value.args
    assert msg == 'unparsable: version='


def test_find_packages(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import find_packages, setup\n'
        'setup(name="foo", packages=find_packages(exclude=("tests*",)))\n',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        '\n'
        '[options]\n'
        'packages = find:\n'
        '\n'
        '[options.packages.find]\n'
        'exclude = tests*\n'
    )


def test_package_dir(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'setup(name="foo", package_dir={"": "src", "pkg1": "pkg1"})\n',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        '\n'
        '[options]\n'
        'package_dir =\n'
        '    =src\n'
        '    pkg1=pkg1\n'
    )


def test_project_urls(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'setup(\n'
        '    name="foo",\n'
        '    project_urls={"homepage": "https://example.com"},\n'
        ')\n',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        'project_urls =\n'
        '    homepage=https://example.com\n'
    )


def test_project_urls_multiple(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'setup(\n'
        '    name="foo",\n'
        '    project_urls={\n'
        '        "homepage": "https://example.com",\n'
        '        "issues": "https://example.com/issues",\n'
        '    },\n'
        ')\n',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        'project_urls =\n'
        '    homepage=https://example.com\n'
        '    issues=https://example.com/issues\n'
    )


def test_entry_points(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'setup(name="foo", entry_points={"console_scripts": ["a=a:main"]})\n',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        '\n'
        '[options.entry_points]\n'
        'console_scripts =\n'
        '    a=a:main\n'
    )


def test_extras_to_requirements_rewrite(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'setup(\n'
        '    name="foo",\n'
        "    extras_require={':python_version==\"2.7\"': ['typing']}\n"
        ')\n',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        '\n'
        '[options]\n'
        'install_requires = typing;python_version=="2.7"\n'
    )


def test_normal_extras(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'setup(\n'
        '    name="foo",\n'
        "    extras_require={'lint': ['pre-commit']},\n"
        ')\n',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        '\n'
        '[options.extras_require]\n'
        'lint = pre-commit\n'
    )


def test_empty_string_package_data(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'setup(name="foo", package_data={"": ["*.pyi"]})\n',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        '\n'
        '[options.package_data]\n'
        '* =\n'
        '    *.pyi\n'
    )


def test_empty_string_exclude_package_data(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'setup(name="foo", exclude_package_data={"": ["*.tar.gz"]})\n',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        '\n'
        '[options.exclude_package_data]\n'
        '* =\n'
        '    *.tar.gz\n'
    )


def test_package_data_multiple_entries(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'setup(name="foo", package_data={"resources": ["*.json", "*.pyi"]})\n',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        '\n'
        '[options.package_data]\n'
        'resources =\n'
        '    *.json\n'
        '    *.pyi\n'
    )


def test_updates_existing_setup_cfg(tmpdir):
    tmpdir.join('setup.py').write(
        'from setuptools import setup\n'
        'setup(name="foo")\n',
    )
    tmpdir.join('setup.cfg').write(
        '[metadata]\n'
        'license_file = LICENSE\n'
        '\n'
        '[bdist_wheel]\n'
        'universal = 1\n',
    )
    main((str(tmpdir),))
    assert tmpdir.join('setup.cfg').read() == (
        '[metadata]\n'
        'name = foo\n'
        'license_file = LICENSE\n'
        '\n'
        '[bdist_wheel]\n'
        'universal = 1\n'
    )
