# tests

Parent: ../CONTEXT.md

## Purpose

The pytest suite, mirroring the package: `contracts/`, `authoring/` (with `golden/`), `github/`, `inputs/` and `docs/` (the documentation checks), plus `test_logging_config.py` and the shared `fixtures/`.

## Conventions

- Use `pytest` with `pytest-mock` (`mocker`), never `unittest`.
- Give every test, test class and test module a one-line docstring stating the behavior it locks; Pylint's docstring checks are on for `tests/`. The rules that are off: [Rules switched off for tests](../DEVELOPER.md#rules-switched-off-for-tests)
- Test behavior: return values, raised exceptions, log messages.
- Set `INPUT_*` and `GITHUB_OUTPUT` with `monkeypatch.setenv` (files under `tmp_path`), or patch `get_action_input`. Never patch `os.getenv` or `builtins.open`, never rely on the ambient environment, and never call an external service or the real GitHub API.
- Bind PyGithub mocks with `spec=`. Use the shared fixtures before adding setup: `conftest.py` for logging, `github/conftest.py` for GitHub.
- For a decorator that wraps a failing call, cover the success path and assert that it logs and re-raises (`pytest.raises`), never that it returns `None`.
- The GitHub surface is mocked at the `Github` object, with no `responses`. If a change adds raw `requests` calls, add `responses` to `requirements-dev.txt` and stub there, so there stays one HTTP-mocking convention.

## Where each fake comes from

| What you need to fake | Pattern used in this repo | Where to copy it from |
|---|---|---|
| GitHub client (`github.Github`) | `mocker.Mock(spec=Github)`, stub `.get_rate_limit()` on the return value | `tests/github/conftest.py::rate_limiter` |
| `Rate` / rate-limit object | `mocker.Mock(spec=Rate)`, set `.remaining` / `.reset.timestamp.return_value` | `tests/github/conftest.py::mock_rate_limiter` |
| Rate limiter under test | `rate_limiter` fixture (`GithubRateLimiter` wrapping a `spec=Github` mock) | `tests/github/conftest.py`; `tests/github/test_rate_limiter.py` |
| `time` inside the rate limiter (sleep / clock) | `mocker.patch("living_doc_utilities.github.rate_limiter.time")`, then `.time.return_value` / `.sleep` | `tests/github/test_rate_limiter.py` |
| `INPUT_*` action inputs | `monkeypatch.setenv("INPUT_NAME", ...)`, or `mocker.patch("living_doc_utilities.inputs.action_inputs.get_action_input", return_value=...)` | `tests/github/test_utils.py`; `tests/inputs/test_action_inputs.py` |
| A concrete `BaseActionInputs` | a small `TestActionInputs(BaseActionInputs)` in the test module, implementing `_validate` / `_print_effective_configuration` | `tests/inputs/test_action_inputs.py` |
| `GITHUB_OUTPUT` file write | `monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "out.txt"))`, then assert on the file's bytes | `tests/github/test_utils.py` |
| Logging assertions | `mocker.patch("living_doc_utilities.<module>.logger.error")` / `.debug`, assert `call_args[0]` is the format string + args | `tests/github/test_decorators.py`; `tests/github/test_utils.py` |
| `logging.basicConfig` | `mock_logging_setup` fixture (`mocker.patch("logging.basicConfig")`) + `caplog` | `tests/conftest.py`; `tests/test_logging_config.py` |
| GitHub / HTTP exceptions | raise a real `github.GithubException(status, data, headers)` / `requests.RequestException` from the wrapped function, then `pytest.raises` | `tests/github/test_decorators.py` |
| A `contracts/` model instance | a `tests/contracts/factories.py` builder (`factories.user_story(entity_id=..., **overrides)`), never the pydantic class by hand | `tests/contracts/factories.py`; any `tests/contracts/test_*.py` |
| A `contracts/` cross-field validator failure | `pytest.raises(ValidationError, match="<the raise message>")` around a factory call with an overridden field | `tests/contracts/test_doc_entities.py::test_feature_with_authored_state_origin_fails` |
| A generated-schema shape claim (map typing, enum, `field_occupancy` keys) | load the committed `contracts/schemas/<id>-schema.json` and assert on the dict, or `jsonschema.validate(instance=data, schema=schema)` for pass/fail cases; never a pydantic-only assertion | `tests/contracts/test_schema_export.py` |
