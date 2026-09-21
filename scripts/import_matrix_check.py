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
    # Build from a copy: an in-tree build would leave build/ and *.egg-info behind and reuse a stale build/lib.
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
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    retired = [name for name in names if name.startswith(RETIRED_DIRS) or name == RETIRED_FILE]
    assert not retired, f"the wheel still packages retired modules: {retired}"
    assert any(
        name.startswith(f"{PACKAGE}/contracts/schemas/") and name.endswith(".json") for name in names
    ), "the wheel does not package the contract schemas"


def check_env(mode: str, expected_version: str) -> None:
    extras = EXTRAS[mode]

    import living_doc_utilities as package

    assert "site-packages" in str(package.__file__), f"not the installed wheel: {package.__file__}"
    assert importlib.metadata.version("living-doc-utilities") == expected_version

    names = sorted(module.name for module in pkgutil.walk_packages(package.__path__, f"{PACKAGE}."))
    assert f"{PACKAGE}.contracts.io" in names and f"{PACKAGE}.authoring.normalize" in names
    for name in names:
        if name in NEEDS_EXTRA and NEEDS_EXTRA[name][0] not in extras:
            extra, missing = NEEDS_EXTRA[name]
            try:
                importlib.import_module(name)
            except ModuleNotFoundError as error:
                assert error.name == missing, f"{name} failed on {error.name!r}, expected {missing!r}"
            else:
                raise AssertionError(f"{name} imported without the '{extra}' extra")
        else:
            importlib.import_module(name)

    from living_doc_utilities.authoring.html_to_markdown import convert_html_to_markdown
    from living_doc_utilities.authoring.url_policy import safe_href, sanitize_html_fragment
    from living_doc_utilities.contracts.schema_export import load_schema

    assert safe_href("https://example.com/a") == "https://example.com/a"  # needs no extra
    assert load_schema("doc-entities-v1.0.0")  # the schemas are packaged as package data

    for call in (lambda: sanitize_html_fragment("<p>x</p>"), lambda: convert_html_to_markdown("<p>x</p>")):
        if "html" in extras:
            call()
        else:
            try:
                call()
            except ModuleNotFoundError as error:
                assert error.name == "nh3", error.name
            else:
                raise AssertionError("the HTML sanitiser ran without the 'html' extra")

    print(f"   {len(names)} modules checked: OK ({mode})")


COMMANDS: dict[str, Callable[..., None]] = {
    "version": version,
    "copy-sources": copy_sources,
    "check-wheel": check_wheel,
    "check-env": check_env,
}

if __name__ == "__main__":
    COMMANDS[sys.argv[1]](*sys.argv[2:])
