import pytest
import sys
import os

#  this is for the configuration test for the project

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



def pytest_configure(config):
    # Configure custom markers
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "browser: mark test as requiring browser (Playwright)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
