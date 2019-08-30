# This file is run automatically because the containing directory is added to the PYTHONPATH
import os

# Setup hooks to replace PyJapc with Papc
def replace_pyjapc(fgen):
    import importlib

    module_name, function_name = fgen.rsplit(':', 1)
    mod = importlib.import_module(module_name)
    system_func = getattr(mod, function_name)

    from papc.interfaces.pyjapc import SimulatedPyJapc
    return SimulatedPyJapc.from_simulation_factory(system_func)


fgen = os.environ.get('PYJAPC_SIMULATION_INIT', None)
if fgen:
    import pyjapc
    # # Note: We try to minimise the pollution of the PyJapc namespace by pushing
    # # as much of the patching as possible into replace_pyjapc.
    pyjapc.PyJapc = replace_pyjapc(fgen)
    print(f'Replacing PyJAPC with a mocked version: {fgen}')

# Clean up the PyJapc namespace from our simulation activities.
del replace_pyjapc
del fgen
