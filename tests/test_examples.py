import pytest
from comrad.examples import examples


all_examples = examples.find_runnable()


@pytest.mark.parametrize('example_path', all_examples, ids=list(map(str, all_examples)))
def test_run_examples(example_path):
    mod = examples.module(basedir=example_path, name='test_example')
    title, desc, entrypoint, fgen, args = examples.read(module=mod, basedir=example_path)
    assert title is not None and len(title) > 0
    assert desc is not None and len(desc) > 0
    assert entrypoint is not None and len(entrypoint) > 0
    files = examples.get_files(example_path)
    assert len(files) > 0
    cmd_args, cmd_env = examples.make_cmd(entrypoint=entrypoint,
                                          example_path=example_path,
                                          japc_generator=fgen,
                                          extra_args=args)
    import subprocess
    proc = subprocess.Popen(cmd_args, env=cmd_env, stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=False)
    try:
        proc.wait(timeout=1.5)
    except subprocess.TimeoutExpired:
        proc.kill()

    out, errs = proc.communicate()
    stdout = out.decode('utf-8')
    stderr = errs.decode('utf-8')

    if fgen is not None:
        # Check only when we are expecting PAPC to mock things...
        err_msg = f'PAPC mocking ({fgen}) has failed:\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}'
        assert stdout is None or 'cmmnbuild_dep_manager' not in stdout, err_msg
        assert stderr is None or 'cmmnbuild_dep_manager' not in stderr, err_msg

    assert 'Error in sitecustomize' not in stderr and 'Cannot open file:' not in stderr, f'Application failed to load correctly:\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}'


@pytest.mark.skip
def test_find_runnable():
    pass


@pytest.mark.skip
def test_module():
    pass


@pytest.mark.skip
def test_read():
    pass


@pytest.mark.skip
def test_get_files():
    pass


@pytest.mark.skip
def test_make_cmd():
    pass


@pytest.mark.skip
def test_disable_implicit_plugin():
    pass


@pytest.mark.skip
def test_module_id():
    pass
