"""Pytest configuration: register the ``local_data`` marker.

Modules listed here need ignored local artifacts (``data/``, ``models/``, frozen reports) that
do not exist in CI. They are selected out with ``-m "not local_data"``; locally everything runs.
"""
import pytest

LOCAL_DATA_MODULES = {'test_baseline', 'test_stability', 'test_completed_experiment', 'test_api', 'test_null_reference'}


def pytest_configure(config):
    config.addinivalue_line('markers', 'local_data: needs ignored local data/models/reports (not available in CI)')


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.module.__name__.rsplit('.', 1)[-1] in LOCAL_DATA_MODULES:
            item.add_marker(pytest.mark.local_data)
