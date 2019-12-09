_BOOTSTRAP_RAN: bool = False

if not _BOOTSTRAP_RAN:
    _BOOTSTRAP_RAN = True

    import logging
    import os
    logging.basicConfig()
    from comrad.utils import install_logger_level
    install_logger_level(os.environ.get('COMRAD_DESIGNER_LOG_LEVEL', None))
