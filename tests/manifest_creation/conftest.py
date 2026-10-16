"""Build the C# oracle once per test session, outside the source tree."""

import pytest

from .support import build_reference


@pytest.fixture(scope="session")
def reference_harness(tmp_path_factory):
    return build_reference(tmp_path_factory.mktemp("manifest-reference-build"))
