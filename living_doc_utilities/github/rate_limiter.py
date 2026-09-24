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
This module contains a GitHub Rate Limiter class methods,
which acts as a rate limiter for GitHub API calls.
"""

import logging
import time
from datetime import datetime
from typing import Any, Callable, Optional

from github import Github

logger = logging.getLogger(__name__)


# Single method is fine: used as a callable class.
class GithubRateLimiter:
    """A callable class that rate-limits GitHub API calls."""

    def __init__(self, github_client: Github):
        self.__github_client: Github = github_client

    @property
    def github_client(self) -> Github:
        """Getter of the GitHub client."""
        return self.__github_client

    def __call__(self, method: Callable) -> Callable:
        """Wraps `method` so it respects the GitHub API rate limit."""

        def wrapped_method(*args, **kwargs) -> Optional[Any]:
            rate = self.github_client.get_rate_limit().rate
            remaining_calls = rate.remaining
            reset_time = rate.reset.timestamp()

            if remaining_calls < 5:
                logger.info("Rate limit almost reached. Sleeping until reset time.")
                sleep_time = reset_time - (now := time.time())
                max_iterations = 48  # caps this at 48 hours, preventing an infinite loop
                iteration = 0
                while sleep_time <= 0:
                    # A negative sleep_time means reset_time is in the past; nudge it forward by 1h until positive.
                    reset_time += 3600
                    sleep_time = reset_time - now
                    iteration += 1
                    if iteration >= max_iterations:
                        logger.warning("Reset time adjustment exceeded maximum iterations. Using default delay.")
                        sleep_time = 60
                        break

                total_sleep_time = sleep_time + 5
                hours, remainder = divmod(total_sleep_time, 3600)
                minutes, seconds = divmod(remainder, 60)

                logger.info(
                    "Sleeping for %s hours, %s minutes, and %s seconds until %s.",
                    int(hours),
                    int(minutes),
                    int(seconds),
                    datetime.fromtimestamp(reset_time).strftime("%Y-%m-%d %H:%M:%S"),
                )
                time.sleep(sleep_time + 5)

            return method(*args, **kwargs)

        return wrapped_method
