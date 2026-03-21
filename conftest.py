"""Root conftest for pytest configuration."""


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")
