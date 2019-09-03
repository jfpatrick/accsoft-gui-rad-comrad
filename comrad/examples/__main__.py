"""
Entry point for the ComRAD Examples browser when launched with python -m
"""

import signal
import argparse
from comrad import __version__
from .browser import populate_parser, run_browser


# Notify the kernel that we are not going to handle SIGINT
signal.signal(signal.SIGINT, signal.SIG_DFL)


def _run():
    """Run the examples browser."""
    # TODO: Parse entry points from setup.py
    parser = argparse.ArgumentParser(prog='python -m comrad.examples',
                                     description='Interactive ComRAD example browser')
    populate_parser(parser)
    parser.add_argument('-V', '--version',
                        action='version',
                        version=f'comrad {__version__}')
    args = parser.parse_args()
    run_browser(args)


if __name__ == '__main__':
    _run()
