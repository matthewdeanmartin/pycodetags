"""Keep process-wide configuration from leaking between otherwise independent tests."""

import pytest

from pycodetags.app_config import CodeTagsConfig


@pytest.fixture(autouse=True)
def isolate_config():
    previous = CodeTagsConfig.instance
    CodeTagsConfig.set_instance(None)
    yield
    CodeTagsConfig.set_instance(previous)
