"""
This file is run automatically because the containing directory is added to the PYTHONPATH
"""
import os
import logging


# Setup hooks to replace PyJapc with Papc
def _replace_pyjapc(generator_path):
    import importlib

    module_name, function_name = generator_path.rsplit(':', 1)
    mod = importlib.import_module(module_name)
    system_func = getattr(mod, function_name)

    from papc.interfaces.pyjapc import SimulatedPyJapc
    return SimulatedPyJapc.from_simulation_factory(system_func, strict=False)


_GENERATOR_PATH = os.environ.get('PYJAPC_SIMULATION_INIT', None)
if _GENERATOR_PATH:
    import pyjapc
    # # Note: We try to minimise the pollution of the PyJapc namespace by pushing
    # # as much of the patching as possible into replace_pyjapc.
    pyjapc.PyJapc = _replace_pyjapc(_GENERATOR_PATH)

    # To disable papc warnings that are not really useful, we instal a filter to suppress them
    class PapcFilter(logging.Filter):

        def filter(self, record: logging.LogRecord) -> bool:
            return 'not supported in simulation mode' not in record.getMessage()

    logging.getLogger('papc.interfaces').addFilter(PapcFilter())


# Clean up the PyJapc namespace from our simulation activities.
del _replace_pyjapc
del _GENERATOR_PATH
