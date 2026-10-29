# living_doc_utilities/github

Parent: ../../CONTEXT.md

## Purpose

Helpers for GitHub Actions and the GitHub API: action input and output, the rate limiter and the call decorators.

## How it fits

- Entry points: `utils.py::get_action_input`, `utils.py::set_action_output`, `rate_limiter.py::GithubRateLimiter`, `decorators.py::safe_call_decorator`, `decorators.py::debug_log_decorator`.
- Depends on: `utils.py` on the standard library only. `rate_limiter.py` and `decorators.py` on PyGithub and `requests` (the `github` extra); they are the only modules that import them.

## Invariants and gotchas

- `get_action_input(name)` reads `INPUT_` plus `name` upper-cased with `-` replaced by `_`. `set_action_output()` appends a `name=value\n` line to the file `GITHUB_OUTPUT` names. Consumers depend on both exactly.
- `safe_call_decorator` logs with `exc_info=True` and re-raises each of `ConnectionError`/`Timeout`, `GithubException`, `RequestException` and any other `Exception`, including one from the rate limiter's own lookup.
  - Keep the rate limiter call inside the `try`.
  - A swallowed or unlogged failure would hide a real error behind a `None` that a caller reads as "no data".
- `GithubRateLimiter` sleeps until the rate-limit reset when fewer than 5 calls remain; its reset math is a high-risk area.
