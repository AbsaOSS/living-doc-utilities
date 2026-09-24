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
Decorators for debug-logging method calls and for rate-limited calls that log and re-raise
every failure. Needs the `github` extra (`pip install living-doc-utilities[github]`).
"""

import logging
from functools import wraps
from typing import Any, Callable, Optional

from github import GithubException
from requests import RequestException, Timeout

from living_doc_utilities.github.rate_limiter import GithubRateLimiter

logger = logging.getLogger(__name__)


def debug_log_decorator(method: Callable) -> Callable:
    """Adds debug logging around a method call."""

    @wraps(method)
    def wrapped(*args, **kwargs) -> Optional[Any]:
        logger.debug("Calling method %s with args: %s and kwargs: %s.", method.__name__, args, kwargs)
        result = method(*args, **kwargs)
        logger.debug("Method %s returned %s.", method.__name__, result)
        return result

    return wrapped


def safe_call_decorator(rate_limiter: GithubRateLimiter) -> Callable:
    """Decorator factory: wraps `method` in `rate_limiter`, logging and re-raising every
    failure - never returning `None`, so a caller can tell "no data" from "fetch failed"."""

    def decorator(method: Callable) -> Callable:
        rate_limited_method = rate_limiter(method)

        # Keep the log decorator first, to log the correct method name.
        @debug_log_decorator
        @wraps(method)
        def wrapped(*args, **kwargs) -> Optional[Any]:
            # The rate-limit lookup runs inside the try, so a failure there is logged like any other.
            try:
                return rate_limited_method(*args, **kwargs)
            except (ConnectionError, Timeout) as e:
                logger.error("Network error calling %s: %s.", method.__name__, e, exc_info=True)
                raise
            except GithubException as e:
                logger.error("GitHub API error calling %s: %s.", method.__name__, e, exc_info=True)
                raise
            except RequestException as e:
                logger.error("HTTP error calling %s: %s.", method.__name__, e, exc_info=True)
                raise
            except Exception as e:
                logger.error(
                    "Unexpected error of type %s occurred in %s: %s.",
                    type(e).__name__,
                    method.__name__,
                    e,
                    exc_info=True,
                )
                raise

        return wrapped

    return decorator
