import logging

logger = logging.getLogger(__name__)


def test_logging(level='error'):
    """
    Test that logging works as excepted.
    """
    method = getattr(logger, level)
    method('Test logging for %s', __name__)
