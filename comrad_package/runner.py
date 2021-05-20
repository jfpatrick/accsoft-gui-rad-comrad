# This provides a public stable interface that can be used by deployed ComRAD applications
# (their generated __main__.py file is expected to rely on this interface)

# flake8: noqa: E401,E403
from _comrad.launcher import create_args_parser as build_cli, process_args as run_with_args, parse_args, DeployedArgs
