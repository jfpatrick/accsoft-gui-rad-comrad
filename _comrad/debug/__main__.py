# This is a module that should be available for debugging in PyCharm, but is not shipped in production
# (this it's only useful with "editable" pip installations).
#
# The reason is that PyCharm Python debug configuration cannot work with console_script or gui_script entrypoints.
# Instead, it is asking for either a Python script file, or a module.
#
# To debug using this approach:
# 1. Make sure your local comrad package is installed in "editable" mode (pip install -e ...)
# 2. In configuration switch "Target to run" from "Script path" to "Module name"
# 3. Specify "_comrad.debug" as the "Module name"
# 4. In "Parameters" enter "run <any additional comrad run arguments> <application file>"
# 5. Make sure that virtual environment, working directory and everything else is set according to your needs


if __name__ == '__main__':
    from ..launcher import run
    run()
