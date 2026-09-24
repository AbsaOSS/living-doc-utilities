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
R12 check 1: outside `living-doc-utilities`, no repository commits its own copy of a contract
schema. Checks git's index (not the filesystem) for `*-schema.json` / `*.schema.json` files
outside tests/ and any --allow directory; only this package allows its own shipped schemas.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

_PATTERNS = ("*-schema.json", "*.schema.json")


def find_vendored_schemas(root: Path, allow: Sequence[Path] = ()) -> list[str]:
    """Lists every git-tracked file under `root` matching `*-schema.json` or `*.schema.json`,
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
