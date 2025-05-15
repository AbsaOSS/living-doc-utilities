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
This module contains an Action Inputs class methods,
which are essential for running the GH action.
"""
import logging
from abc import ABC, abstractmethod

from living_doc_utilities.constants import GITHUB_TOKEN
from living_doc_utilities.github.utils import get_action_input

logger = logging.getLogger(__name__)


class BaseActionInputs(ABC):
    """
    A class representing all the action inputs. It is responsible for loading, managing
    and validating the inputs required for running the GH Action.
    """

    @staticmethod
    def get_github_token() -> str:
        """
        Getter of the GitHub authorization token.
        @return: The GitHub authorization token.
        """
        return get_action_input(GITHUB_TOKEN)

    def validate_user_configuration(self) -> bool:
        """
        Checks that all the user configurations defined are correct.
        @return: True if the configuration is correct, False otherwise.
        """
        logger.debug("User configuration validation started")
        repository_error_count = self._validate()
        if repository_error_count > 0:
            logger.debug("User configuration validation failed.")
            return False

        logger.debug("User configuration validation successfully completed.")
        return True

    @abstractmethod
    def _validate(self) -> int:
        raise NotImplementedError

    def print_effective_configuration(self) -> None:
        """
        Prints the effective configuration of the action inputs.
        """
        logger.info("Effective configuration:")
        logger.info("GitHub token: %s", self.get_github_token())
        self._print_effective_configuration()

    @abstractmethod
    def _print_effective_configuration(self) -> None:
        raise NotImplementedError
