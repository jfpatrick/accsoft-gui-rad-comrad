_BOOTSTRAP_RAN: bool = False


def setup_logging():
    """Sets the logging in Qt Designer according to the level passed in the environment variable."""

    global _BOOTSTRAP_RAN
    if not _BOOTSTRAP_RAN:
        _BOOTSTRAP_RAN = True
        # Only setup logging when application exists (we're in Qt designer)
        # otherwise, it's a launcher that imports it to setup plugin paths for Qt Designer subprocess
        import os
        from _comrad.log_config import install_logger_level
        install_logger_level(os.environ.get('COMRAD_DESIGNER_LOG_LEVEL', None))
