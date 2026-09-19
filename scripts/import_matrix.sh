#!/usr/bin/env bash
#
# Import matrix: build the wheel, then install it into three clean virtual environments and
# prove which modules need which extra (pyproject.toml, [project.optional-dependencies]):
#
#   none    - `pip install <wheel>`          every module imports EXCEPT github.rate_limiter and
#                                            github.decorators; the HTML sanitiser is callable
#                                            only once the `html` extra is installed
#   github  - `pip install <wheel>[github]`  additionally github.rate_limiter, github.decorators
#   html    - `pip install <wheel>[html]`    additionally sanitize_html_fragment and
#                                            convert_html_to_markdown work
#
# Each environment must also pass `pip check`. The modules are imported from the installed
# wheel (not the source tree), so a dependency missing from pyproject.toml fails here.
# Run it with `make import-matrix`; CI runs the same target.

set -euo pipefail

PYTHON="${PYTHON:-python3}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

VERSION="$(sed -n 's/^version = "\(.*\)"$/\1/p' "$ROOT/pyproject.toml" | head -n 1)"
[[ -n "$VERSION" ]] || { echo "::error::cannot read the version from pyproject.toml" >&2; exit 1; }

echo "== Building the wheel (version $VERSION)"
# Build from a copy of the sources (tracked and untracked, minus anything git-ignored): setuptools
# builds in-tree, which would leave build/ and *.egg-info in the repository and reuse a stale
# build/lib that still holds a module deleted from the source tree.
"$PYTHON" - "$ROOT" "$WORK/src" <<'PY'
import shutil
import subprocess
import sys
from pathlib import Path

root, destination = Path(sys.argv[1]), Path(sys.argv[2])
listing = subprocess.run(
    ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
    cwd=root, check=True, capture_output=True, text=True,
).stdout
for name in filter(None, listing.split("\0")):
    source = root / name
    if source.is_file():
        (destination / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination / name)
PY
"$PYTHON" -m build --wheel --outdir "$WORK/dist" "$WORK/src" > "$WORK/build.log" 2>&1 || { cat "$WORK/build.log"; exit 1; }

shopt -s nullglob
wheels=("$WORK"/dist/living_doc_utilities-"$VERSION"-*.whl)
if [[ ${#wheels[@]} -ne 1 ]]; then
  echo "::error::expected exactly one living_doc_utilities-$VERSION-*.whl, found: $(ls "$WORK/dist")" >&2
  exit 1
fi
WHEEL="${wheels[0]}"
echo "Built $(basename "$WHEEL")"

"$PYTHON" - "$WHEEL" <<'PY'
import sys
import zipfile

names = zipfile.ZipFile(sys.argv[1]).namelist()
retired = [
    n for n in names if n.startswith(("living_doc_utilities/model/", "living_doc_utilities/factory/", "living_doc_utilities/exporter/"))
] + [n for n in names if n == "living_doc_utilities/decorators.py"]
assert not retired, f"the wheel still packages retired modules: {retired}"
assert any(n.startswith("living_doc_utilities/contracts/schemas/") and n.endswith(".json") for n in names), (
    "the wheel does not package the contract schemas"
)
PY

check_environment() {
  local mode="$1" spec="$WHEEL"
  [[ "$mode" == "none" ]] || spec="$WHEEL[$mode]"
  local venv="$WORK/venv-$mode"

  echo "== Environment '$mode': pip install ${spec##*/}"
  "$PYTHON" -m venv "$venv"
  "$venv/bin/python" -m pip install --quiet --disable-pip-version-check "$spec"
  "$venv/bin/python" -m pip check
  # Run away from the repository so the source tree can never shadow the installed wheel;
  # -I also ignores PYTHON* variables and the current directory.
  (cd "$WORK" && "$venv/bin/python" -I - "$mode" "$VERSION" <<'PY'
import importlib
import importlib.metadata
import importlib.util
import pkgutil
import sys

mode, expected_version = sys.argv[1], sys.argv[2]
extras = {"none": set(), "github": {"github"}, "html": {"html"}}[mode]

import living_doc_utilities as package

assert "site-packages" in package.__file__, f"not the installed wheel: {package.__file__}"
assert importlib.metadata.version("living-doc-utilities") == expected_version

# Module -> (extra it needs, top-level module that is missing without it).
NEEDS_EXTRA = {
    "living_doc_utilities.github.rate_limiter": ("github", "github"),
    "living_doc_utilities.github.decorators": ("github", "github"),
}

for retired in ("model", "factory", "exporter", "decorators"):
    assert importlib.util.find_spec(f"living_doc_utilities.{retired}") is None, retired

names = sorted(m.name for m in pkgutil.walk_packages(package.__path__, "living_doc_utilities."))
assert "living_doc_utilities.contracts.io" in names and "living_doc_utilities.authoring.normalize" in names
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
PY
  )
}

for mode in none github html; do
  check_environment "$mode"
done
echo "== Import matrix passed"
