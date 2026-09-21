#
# Copyright 2026 ABSA Group Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
The checks behind `import_matrix.bat`: `version`, `copy-sources`, `check-wheel`, and `check-env`, which
runs with `python -I` inside the virtual environment under test.
"""

import importlib
import importlib.metadata
import pkgutil
import re
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Callable
from pathlib import Path

PACKAGE = "living_doc_utilities"
RETIRED_DIRS = (f"{PACKAGE}/model/", f"{PACKAGE}/factory/", f"{PACKAGE}/exporter/")
RETIRED_FILE = f"{PACKAGE}/decorators.py"

EXTRAS: dict[str, set[str]] = {"none": set(), "github": {"github"}, "html": {"html"}}
# Module -> (extra it needs, top-level module that is missing without it).
NEEDS_EXTRA: dict[str, tuple[str, str]] = {
    f"{PACKAGE}.github.rate_limiter": ("github", "github"),
    f"{PACKAGE}.github.decorators": ("github", "github"),
}


def version(root: str) -> None:
    match = re.search(r'^version = "(.*)"$', (Path(root) / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)
    if match is None:
        sys.exit("::error::cannot read the version from pyproject.toml")
    print(match.group(1))


def copy_sources(root: str, destination: str) -> None:
    """Copies the tracked and untracked sources (minus git-ignored) so the wheel is built from a copy: an
    in-tree build would leave build/ and *.egg-info behind and reuse a stale build/lib."""
    source_root, target_root = Path(root), Path(destination)
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=source_root,
        check=True,
        capture_output=True,
        encoding="utf-8",
    ).stdout
    for name in filter(None, listing.split("\0")):
        source = source_root / name
        if source.is_file():
            (target_root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target_root / name)


def check_wheel(wheel: str) -> None:
    """The wheel packages the contract schemas and none of the retired modules."""
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    retired = [name for name in names if name.startswith(RETIRED_DIRS) or name == RETIRED_FILE]
    assert not retired, f"the wheel still packages retired modules: {retired}"
    assert any(
        name.startswith(f"{PACKAGE}/contracts/schemas/") and name.endswith(".json") for name in names
    ), "the wheel does not package the contract schemas"


def _import_module(name: str, extras: set[str]) -> None:
    if name not in NEEDS_EXTRA or NEEDS_EXTRA[name][0] in extras:
        importlib.import_module(name)
        return
    extra, missing = NEEDS_EXTRA[name]
    try:
        importlib.import_module(name)
    except ModuleNotFoundError as error:
        assert error.name == missing, f"{name} failed on {error.name!r}, expected {missing!r}"
    else:
        raise AssertionError(f"{name} imported without the '{extra}' extra")


def _check_extras_behaviour(extras: set[str]) -> None:
    url_policy = importlib.import_module(f"{PACKAGE}.authoring.url_policy")
    html_to_markdown = importlib.import_module(f"{PACKAGE}.authoring.html_to_markdown")
    schema_export = importlib.import_module(f"{PACKAGE}.contracts.schema_export")

    assert url_policy.safe_href("https://example.com/a") == "https://example.com/a"  # needs no extra
    assert schema_export.load_schema("doc-entities-v1.0.0")  # the schemas are packaged as package data

    sanitiser_calls = (
        lambda: url_policy.sanitize_html_fragment("<p>x</p>"),
        lambda: html_to_markdown.convert_html_to_markdown("<p>x</p>"),
    )
    for call in sanitiser_calls:
        if "html" in extras:
            call()
        else:
            try:
                call()
            except ModuleNotFoundError as error:
                assert error.name == "nh3", error.name
            else:
                raise AssertionError("the HTML sanitiser ran without the 'html' extra")


def check_env(mode: str, expected_version: str) -> None:
    """Every module imports from the installed wheel, needing only this environment's extras."""
    extras = EXTRAS[mode]
    package = importlib.import_module(PACKAGE)

    assert "site-packages" in str(package.__file__), f"not the installed wheel: {package.__file__}"
    assert importlib.metadata.version("living-doc-utilities") == expected_version

    names = sorted(module.name for module in pkgutil.walk_packages(package.__path__, f"{PACKAGE}."))
    assert f"{PACKAGE}.contracts.io" in names and f"{PACKAGE}.authoring.normalize" in names
    for name in names:
        _import_module(name, extras)
    _check_extras_behaviour(extras)

    print(f"   {len(names)} modules checked: OK ({mode})")


COMMANDS: dict[str, Callable[..., None]] = {
    "version": version,
    "copy-sources": copy_sources,
    "check-wheel": check_wheel,
    "check-env": check_env,
}

if __name__ == "__main__":
    COMMANDS[sys.argv[1]](*sys.argv[2:])
