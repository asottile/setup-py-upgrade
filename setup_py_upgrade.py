import argparse
import ast
import configparser
import io
import os.path
from typing import Any
from typing import Dict
from typing import Sequence

METADATA_KEYS = frozenset((
    'name', 'version', 'url', 'download_url', 'project_urls', 'author',
    'author_email', 'maintainer', 'maintainer_email', 'classifiers',
    'license', 'license_file', 'description', 'long_description',
    'long_description_content_type', 'keywords', 'platforms', 'provides',
    'requires', 'obsoletes',
))
OPTIONS_AS_SECTIONS = (
    'entry_points', 'extras_require', 'package_data', 'exclude_package_data',
)
OPTIONS_KEYS = frozenset((
    'zip_safe', 'setup_requires', 'install_requires', 'python_requires',
    'use_2to3', 'use_2to3_fixers', 'use_2to3_exclude_fixers',
    'convert_2to3_doctests', 'scripts', 'eager_resources', 'dependency_links',
    'tests_require', 'include_package_data', 'packages', 'package_dir',
    'namespace_packages', 'py_modules', 'data_files',

    # need special processing (as sections)
    *OPTIONS_AS_SECTIONS,
))
FIND_PACKAGES_ARGS = ('where', 'exclude', 'include')


def is_setuptools_attr_call(node: ast.Call, attr: str) -> bool:
    return (
        # X(
        (isinstance(node.func, ast.Name) and node.func.id == attr) or
        # setuptools.X(
        (
            isinstance(node.func, ast.Attribute) and
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == 'setuptools' and
            node.func.attr == attr
        )
    )


class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.sections: Dict[str, Dict[str, Any]] = {}
        self.sections['metadata'] = {}
        self.sections['options'] = {}

        self._files: Dict[str, str] = {}

    def visit_With(self, node: ast.With) -> None:
        # with open("filename", ...) as fvar:
        #     varname = fvar.read()
        if (
                # with open(...)
                len(node.items) == 1 and
                isinstance(node.items[0].context_expr, ast.Call) and
                isinstance(node.items[0].context_expr.func, ast.Name) and
                node.items[0].context_expr.func.id == 'open' and
                # "filename"
                len(node.items[0].context_expr.args) > 0 and
                isinstance(node.items[0].context_expr.args[0], ast.Str) and
                # as fvar
                isinstance(node.items[0].optional_vars, ast.Name) and
                # varname =
                len(node.body) == 1 and
                isinstance(node.body[0], ast.Assign) and
                len(node.body[0].targets) == 1 and
                isinstance(node.body[0].targets[0], ast.Name) and
                # fvar.read()
                isinstance(node.body[0].value, ast.Call) and
                isinstance(node.body[0].value.func, ast.Attribute) and
                # .read()
                node.body[0].value.func.attr == 'read' and
                # fvar.
                isinstance(node.body[0].value.func.value, ast.Name) and
                (
                    node.body[0].value.func.value.id ==
                    node.items[0].optional_vars.id
                )
        ):
            varname = node.body[0].targets[0].id
            filename = node.items[0].context_expr.args[0].s
            self._files[varname] = filename
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if is_setuptools_attr_call(node, 'setup'):
            for kwd in node.keywords:
                if kwd.arg in METADATA_KEYS:
                    section = 'metadata'
                elif kwd.arg in OPTIONS_KEYS:
                    section = 'options'
                else:
                    raise SystemExit(
                        f'{kwd.arg}= is not supported in setup.cfg',
                    )

                if isinstance(kwd.value, ast.Name):
                    value = f'file: {self._files[kwd.value.id]}'
                elif (
                        isinstance(kwd.value, ast.Call) and
                        is_setuptools_attr_call(kwd.value, 'find_packages')
                ):
                    find_section = {
                        k: ast.literal_eval(v)
                        for k, v in zip(FIND_PACKAGES_ARGS, kwd.value.args)
                    }
                    find_section.update({
                        kwd.arg: ast.literal_eval(kwd.value)
                        for kwd in kwd.value.keywords
                    })
                    self.sections['options.packages.find'] = find_section
                    value = 'find:'
                else:
                    try:
                        value = ast.literal_eval(kwd.value)
                    except ValueError:
                        raise NotImplementedError(f'unparsable {kwd.arg}')

                self.sections[section][kwd.arg] = value

        self.generic_visit(node)


def _list_as_str(lst: Sequence[str]) -> str:
    if len(lst) == 1:
        return lst[0]
    else:
        return '\n' + '\n'.join(lst)


def reformat_lists(section: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: _list_as_str(v) if isinstance(v, (list, tuple)) else v
        for k, v in section.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    args = parser.parse_args()

    setup_py = os.path.join(args.directory, 'setup.py')
    with open(setup_py, 'rb') as setup_py_f:
        tree = ast.parse(setup_py_f.read(), filename=setup_py)

    visitor = Visitor()
    visitor.visit(tree)

    for option_section in OPTIONS_AS_SECTIONS:
        if option_section in visitor.sections['options']:
            section = visitor.sections['options'].pop(option_section)
            visitor.sections[f'options.{option_section}'] = section

    for k in tuple(visitor.sections.get('options.extras_require', {})):
        if k.startswith(':'):
            deps = visitor.sections['options.extras_require'].pop(k)
            ir = visitor.sections['options'].setdefault('install_requires', [])
            for dep in deps:
                ir.append(f'{dep}; {k[1:]}')

    sections = {k: reformat_lists(v) for k, v in visitor.sections.items() if v}
    if sections.get('options', {}).get('package_dir'):
        sections['options']['package_dir'] = _list_as_str([
            f'{k}={v}' for k, v in sections['options']['package_dir'].items()
        ])

    # always want these to start with a newline
    for section in ('entry_points', 'package_data'):
        for k, v in dict(sections.get(f'options.{section}', {})).items():
            if '\n' not in v:
                if k == '':
                    sections[f'options.{section}'].pop(k)
                    k = '*'
                sections[f'options.{section}'][k] = f'\n{v}'

    cfg = configparser.ConfigParser()
    cfg.update(sections)

    setup_cfg = os.path.join(args.directory, 'setup.cfg')
    if os.path.exists(setup_cfg):
        orig = configparser.ConfigParser()
        orig.read(setup_cfg)

        for section_name, section in orig.items():
            for k, v in section.items():
                # a shame `setdefault(...)` doesn't work
                if not cfg.has_section(section_name):
                    cfg.add_section(section_name)
                cfg[section_name][k] = v

    with open(setup_py, 'w') as f:
        f.write('from setuptools import setup\nsetup()\n')

    sio = io.StringIO()
    cfg.write(sio)
    with open(setup_cfg, 'w') as f:
        contents = sio.getvalue().strip() + '\n'
        contents = contents.replace('\t', '    ')
        contents = contents.replace(' \n', '\n')
        f.write(contents)

    print(f'{setup_py} and {setup_cfg} written!')
    return 0


if __name__ == '__main__':
    exit(main())
