#
# Copyright 2025 ABSA Group Limited
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
docs/contracts.md, R12 check 1 - "No vendored schemas": outside `living-doc-utilities`, no
repository commits its own copy of a contract schema. This is a filename check only, run from
every component's own `make qa`: `python -m living_doc_utilities.contracts.check_no_vendored_schemas
[--allow <dir> ...]`, from the root of the repository being checked. It fails on any file
*committed to git* whose name matches `*-schema.json` or `*.schema.json`, outside `tests/`
and any `--allow`ed directory - the generic filename pattern also catches a schema under a
retired contract name, which a check keyed to today's six names would miss. Checking git's
index rather than walking the filesystem is what keeps this from tripping over a local
virtualenv or build directory that happens to hold a same-named file but was never committed.

Only `living-doc-utilities` itself passes `--allow living_doc_utilities/contracts/schemas`,
for its own generated, shipped schemas.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

_PATTERNS = ("*-schema.json", "*.schema.json")


def find_vendored_schemas(root: Path, allow: Sequence[Path] = ()) -> list[str]:
    """
    Lists every git-tracked file under `root` matching `*-schema.json` or `*.schema.json`,
    excluding anything under a `tests` directory or one of `allow`.

    @param root: the repository root to check (must be inside a git working tree).
    @param allow: directories, relative to `root`, allowed to hold schema-shaped files.
    @return: offending paths, relative to `root`, sorted; empty when the tree is clean.
    """
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", *_PATTERNS],
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    allow_dirs = [Path(a) for a in allow]

    offenders = []
    for relative in tracked.split("\0"):
        if not relative:
            continue
        parts = Path(relative).parts
        if "tests" in parts[:-1]:
            continue
        if any(Path(relative).is_relative_to(a) for a in allow_dirs):
            continue
        offenders.append(relative)
    return sorted(offenders)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for `python -m living_doc_utilities.contracts.check_no_vendored_schemas`."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path("."), help="repository root to check (default: the current directory)"
    )
    parser.add_argument(
        "--allow",
        type=Path,
        action="append",
        default=[],
        metavar="DIR",
        help="a directory, relative to --root, allowed to hold schema-shaped files; repeatable",
    )
    args = parser.parse_args(argv)

    offenders = find_vendored_schemas(args.root, args.allow)
    if offenders:
        print("vendored schema file(s) committed outside an allowed location:", file=sys.stderr)
        for offender in offenders:
            print(f"  {offender}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
