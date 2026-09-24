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

"""Tests for the debug-log and rate-limit-aware safe-call decorators."""

import pytest
from github import GithubException
from requests import RequestException, Timeout

from living_doc_utilities.github.decorators import debug_log_decorator, safe_call_decorator


def sample_function(x, y):
    return x + y


def test_debug_log_decorator(mocker):
    """A decorated call returns the wrapped function's result while logging the call and its return value."""
    mock_log_debug = mocker.patch("living_doc_utilities.github.decorators.logger.debug")

    decorated_function = debug_log_decorator(sample_function)
    expected_call = [
        mocker.call("Calling method %s with args: %s and kwargs: %s.", "sample_function", (3, 4), {}),
        mocker.call("Method %s returned %s.", "sample_function", 7),
    ]

    actual = decorated_function(3, 4)

    assert 7 == actual
    assert mock_log_debug.call_args_list == expected_call


def test_safe_call_decorator_success(rate_limiter):
    """A wrapped call that succeeds returns the underlying result unchanged."""

    @safe_call_decorator(rate_limiter)
    def sample_method(x, y):
        return x + y

    actual = sample_method(2, 3)

    assert 5 == actual


def test_safe_call_decorator_none_result_is_not_an_error(rate_limiter, mocker):
    """A wrapped call returning None is passed through as a valid result, not logged as an error."""
    mock_log_error = mocker.patch("living_doc_utilities.github.decorators.logger.error")

    @safe_call_decorator(rate_limiter)
    def sample_method():
        return None

    actual = sample_method()

    assert actual is None
    mock_log_error.assert_not_called()


@pytest.mark.parametrize(
    "error, expected_message",
    [
        pytest.param(ConnectionError("Test connection error"), "Network error calling %s: %s.", id="connection-error"),
        pytest.param(Timeout("Test timeout"), "Network error calling %s: %s.", id="timeout"),
        pytest.param(
            GithubException(
                404,
                {"message": "Not Found", "documentation_url": "https://developer.github.com/v3"},
                {"X-RateLimit-Limit": "60", "X-RateLimit-Remaining": "0"},
            ),
            "GitHub API error calling %s: %s.",
            id="github-exception",
        ),
        pytest.param(RequestException("Test HTTP error"), "HTTP error calling %s: %s.", id="request-exception"),
    ],
)
def test_safe_call_decorator_logs_and_reraises(rate_limiter, mocker, error, expected_message):
    """Connection, timeout, GitHub API, and HTTP errors are each logged with a type-specific message and re-raised."""
    mock_log_error = mocker.patch("living_doc_utilities.github.decorators.logger.error")

    @safe_call_decorator(rate_limiter)
    def sample_method():
        raise error

    with pytest.raises(type(error)) as excinfo:
        sample_method()

    args, kwargs = mock_log_error.call_args
    assert excinfo.value is error
    assert 1 == mock_log_error.call_count
    assert expected_message == args[0]
    assert "sample_method" == args[1]
    assert args[2] is error
    assert kwargs["exc_info"]


def test_safe_call_decorator_github_api_error_message(rate_limiter, mocker):
    """A GitHub API error is logged with a GitHub-specific message and the original exception before re-raising."""
    mock_log_error = mocker.patch("living_doc_utilities.github.decorators.logger.error")
    error = GithubException(
        404,
        {"message": "Not Found", "documentation_url": "https://developer.github.com/v3"},
        {"X-RateLimit-Limit": "60", "X-RateLimit-Remaining": "0"},
    )

    @safe_call_decorator(rate_limiter)
    def sample_method():
        raise error

    with pytest.raises(GithubException) as excinfo:
        sample_method()

    args, kwargs = mock_log_error.call_args
    assert excinfo.value is error
    assert 1 == mock_log_error.call_count
    assert "GitHub API error calling %s: %s." == args[0]
    assert "sample_method" == args[1]
    assert args[2] is error
    assert '404 {"message": "Not Found", "documentation_url": "https://developer.github.com/v3"}' == str(args[2])
    assert kwargs["exc_info"]


def test_safe_call_decorator_exception(rate_limiter, mocker):
    """An exception of an unrecognized type is logged with a generic message naming its type before re-raising."""
    mock_log_error = mocker.patch("living_doc_utilities.github.decorators.logger.error")

    @safe_call_decorator(rate_limiter)
    def sample_method(x, y):
        return x / y

    with pytest.raises(ZeroDivisionError) as excinfo:
        sample_method(2, 0)

    args, kwargs = mock_log_error.call_args
    assert 1 == mock_log_error.call_count
    assert "Unexpected error of type %s occurred in %s: %s." == args[0]
    assert "ZeroDivisionError" == args[1]
    assert "sample_method" == args[2]
    assert args[3] is excinfo.value
    assert kwargs["exc_info"]


def test_safe_call_decorator_logs_and_reraises_rate_limit_lookup_failure(rate_limiter, mocker):
    """A failure while checking the rate limit is logged and re-raised without ever invoking the wrapped call."""
    mock_log_error = mocker.patch("living_doc_utilities.github.decorators.logger.error")
    error = GithubException(401, {"message": "Bad credentials"}, {})
    rate_limiter.github_client.get_rate_limit.side_effect = error
    wrapped_call = mocker.Mock(__name__="sample_method")

    with pytest.raises(GithubException) as excinfo:
        safe_call_decorator(rate_limiter)(wrapped_call)()

    args, kwargs = mock_log_error.call_args
    assert excinfo.value is error
    assert 1 == mock_log_error.call_count
    assert "GitHub API error calling %s: %s." == args[0]
    assert "sample_method" == args[1]
    assert kwargs["exc_info"]
    wrapped_call.assert_not_called()
