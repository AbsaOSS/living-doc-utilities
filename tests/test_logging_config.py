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

"""Tests for setup_logging, the project's logging configuration entry point."""

import logging
import sys
from logging import StreamHandler

from living_doc_utilities.logging_config import setup_logging


def validate_logging_config(mock_logging_setup, caplog, expected_level, expected_message):
    """Assert that logging was configured with the expected level, format, stdout handler, and log message."""
    mock_logging_setup.assert_called_once()

    call_args = mock_logging_setup.call_args[1]
    assert call_args["level"] == expected_level
    assert call_args["format"] == "%(asctime)s - %(levelname)s - %(message)s"
    assert call_args["datefmt"] == "%Y-%m-%d %H:%M:%S"

    handlers = call_args["handlers"]
    assert len(handlers) == 1
    assert isinstance(handlers[0], StreamHandler)
    assert handlers[0].stream is sys.stdout

    assert expected_message in caplog.text


def test_setup_logging_default_logging_level(mock_logging_setup, caplog, monkeypatch):
    """`setup_logging` configures the INFO level and logs a setup confirmation message when called with no args."""
    monkeypatch.delenv("INPUT_VERBOSE_LOGGING", raising=False)
    monkeypatch.delenv("RUNNER_DEBUG", raising=False)
    with caplog.at_level(logging.INFO):
        setup_logging()

    validate_logging_config(mock_logging_setup, caplog, logging.INFO, "Logging configuration set up.")


def test_setup_logging_verbose_logging_enabled(mock_logging_setup, caplog, monkeypatch):
    """Setting INPUT_VERBOSE_LOGGING enables debug-level logging and logs that verbose logging is enabled."""
    monkeypatch.setenv("INPUT_VERBOSE_LOGGING", "true")

    with caplog.at_level(logging.DEBUG):
        setup_logging()

    validate_logging_config(mock_logging_setup, caplog, logging.DEBUG, "Verbose logging enabled.")


def test_setup_logging_debug_mode_enabled_by_ci(mock_logging_setup, caplog, monkeypatch):
    """Setting RUNNER_DEBUG enables debug-level logging and logs that debug mode was enabled by the CI runner."""
    monkeypatch.setenv("RUNNER_DEBUG", "1")

    with caplog.at_level(logging.DEBUG):
        setup_logging()

    validate_logging_config(mock_logging_setup, caplog, logging.DEBUG, "Debug mode enabled by CI runner.")
