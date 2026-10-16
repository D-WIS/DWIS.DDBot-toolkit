"""Repository-wide selection of optional external-runtime reference tests."""

import os

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-reference",
        action="store_true",
        help="Run reference tests; missing SDKs, restore errors, and build failures are fatal.",
    )


def pytest_collection_modifyitems(config, items):
    if (
        config.getoption("--run-reference")
        or os.environ.get("MANIFEST_CREATION_REFERENCE") == "require"
    ):
        return
    skip = pytest.mark.skip(reason="Reference tests are opt-in; use --run-reference.")
    for item in items:
        if item.get_closest_marker("reference") is not None:
            item.add_marker(skip)
