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

"""Tests for GithubRateLimiter, the callable that throttles calls against the GitHub API rate limit."""

import time


def test_exceeds_max_iterations(rate_limiter, mock_rate_limiter, mocker):
    """When the reset time can't be pushed past now within the iteration cap, a default delay is used."""
    mock_time = mocker.patch("living_doc_utilities.github.rate_limiter.time")
    mock_time.time.return_value = 200000000
    mock_time.sleep = mocker.Mock()

    mock_logger = mocker.patch("living_doc_utilities.github.rate_limiter.logger")

    mock_rate_limiter.rate.remaining = 0
    mock_rate_limiter.rate.reset.timestamp.return_value = 1000

    @rate_limiter
    def dummy_func():
        return "ok"

    result = dummy_func()

    assert result == "ok"
    mock_logger.warning.assert_called()
    warning_call = mock_logger.warning.call_args[0][0]
    assert "maximum iterations" in warning_call
    mock_time.sleep.assert_called_with(65)  # 60 + 5 seconds buffer


def test_rate_limiter_extended_sleep_remaining_1(mocker, rate_limiter, mock_rate_limiter):
    """When only one call remains before the rate limit resets, the wrapped call sleeps before it runs."""
    mock_sleep = mocker.patch("time.sleep", return_value=None)
    mock_rate_limiter.rate.remaining = 1
    mock_rate_limiter.rate.reset.timestamp.return_value = time.time() + 3600

    method_mock = mocker.Mock()
    wrapped_method = rate_limiter(method_mock)

    wrapped_method()

    method_mock.assert_called_once()
    mock_sleep.assert_called_once()


def test_rate_limiter_extended_sleep_remaining_10(mocker, rate_limiter):
    """When enough calls remain before the rate limit resets, the wrapped call runs without sleeping."""
    mock_sleep = mocker.patch("time.sleep", return_value=None)

    method_mock = mocker.Mock()
    wrapped_method = rate_limiter(method_mock)

    wrapped_method()

    method_mock.assert_called_once()
    mock_sleep.assert_not_called()


def test_rate_limiter_extended_sleep_remaining_1_negative_reset_time(mocker, rate_limiter, mock_rate_limiter):
    """When calls are low and the recorded reset time is already past, the call still sleeps after it is advanced."""
    mock_sleep = mocker.patch("time.sleep", return_value=None)
    mock_rate_limiter.rate.remaining = 1
    mock_rate_limiter.rate.reset.timestamp = mocker.Mock(return_value=time.time() - 1000)

    method_mock = mocker.Mock()
    wrapped_method = rate_limiter(method_mock)

    wrapped_method()

    method_mock.assert_called_once()
    mock_sleep.assert_called_once()
