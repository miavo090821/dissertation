import pytest
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pytest_configure(config):
    # Configure custom markers.
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "browser: mark test as requiring browser (Playwright)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    # Modify test collection based on markers.
    # Skip browser tests by default unless explicitly enabled
    if not os.environ.get('RUN_BROWSER_TESTS'):
        skip_browser = pytest.mark.skip(reason="Browser tests disabled")
        for item in items:
            if "browser" in item.keywords:
                item.add_marker(skip_browser)
