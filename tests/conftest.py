"""pytest configuration: markers for the real-Xano integration suite.

Markers are registered in ``pytest.ini`` and applied here from the class hierarchy of
``test_integration_xano.py``, so new live tests are marked without per-test decorators:

- ``integration``: every test that may call a real Xano workspace;
- ``writes``: scenarios that persist data (``XANO_TEST_ALLOW_WRITES=true``);
- ``concurrency``: race scenarios (``XANO_TEST_CONCURRENCY=true``).

Examples: ``pytest -m "not integration"`` (offline only), ``pytest -m integration -ra``.
"""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if item.module is None or item.module.__name__.rpartition(".")[2] != "test_integration_xano":
            continue
        item.add_marker(pytest.mark.integration)
        test_class = getattr(item, "cls", None)
        if test_class is None:
            continue
        lineage = {klass.__name__ for klass in test_class.__mro__}
        if "XanoLiveWriteTestCase" in lineage:
            item.add_marker(pytest.mark.writes)
        if "Concurrency" in test_class.__name__:
            item.add_marker(pytest.mark.concurrency)
