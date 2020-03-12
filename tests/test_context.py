import pytest
from PyQt5.QtTest import QSignalSpy  # TODO: qtpy does not seem to expose QSignalSpy: https://github.com/spyder-ide/qtpy/issues/197
from comrad.data.context import CContext


@pytest.mark.parametrize('inherit_sel1,inherit_sel2,inherit_sel_match', [
    (True, True, True),
    (True, False, False),
    (False, True, False),
    (False, False, True),
])
@pytest.mark.parametrize('inherit_filter1,inherit_filter2,inherit_filter_match', [
    (True, True, True),
    (True, False, False),
    (False, True, False),
    (False, False, True),
])
@pytest.mark.parametrize('sel1,sel2,sel_match', [
    ('TEST.USER.1', 'TEST.USER.1', True),
    ('TEST.USER.1', 'TEST.USER.2', False),
    (None, 'TEST.USER.2', False),
    ('TEST.USER.1', None, False),
    (None, None, True),
])
@pytest.mark.parametrize('filter1,filter2,filter_match', [
    ({'key1': 'val1'}, {'key1': 'val1'}, True),
    ({'key1': 'val1'}, {'key2': 'val2'}, False),
    ({'key1': 'val1'}, {'key1': 'val1', 'key2': 'val2'}, False),
    ({'key1': 'val1'}, None, False),
    (None, {'key1': 'val1'}, False),
    (None, None, True),
])
@pytest.mark.parametrize('wild1,wild2,wild_match', [
    ({'key1': 'val1'}, {'key1': 'val1'}, True),
    ({'key1': 'val1'}, {'key2': 'val2'}, False),
    ({'key1': 'val1'}, {'key1': 'val1', 'key2': 'val2'}, False),
    ({'key1': 'val1'}, None, False),
    (None, {'key1': 'val1'}, False),
    (None, None, True),
])
def test_context_eq(sel1, sel2, sel_match, filter1, filter2, filter_match, wild1, wild2, wild_match,
                    inherit_filter1, inherit_filter2, inherit_filter_match, inherit_sel1, inherit_sel2,
                    inherit_sel_match):
    should_match = sel_match and filter_match and wild_match and inherit_filter_match and inherit_sel_match
    ctx1 = CContext(selector=sel1, data_filters=filter1, wildcards=wild1)
    ctx2 = CContext(selector=sel2, data_filters=filter2, wildcards=wild2)
    ctx1.inherit_parent_selector = inherit_sel1
    ctx2.inherit_parent_selector = inherit_sel2
    ctx1.inherit_parent_data_filters = inherit_filter1
    ctx2.inherit_parent_data_filters = inherit_filter2
    actually_match = ctx1 == ctx2
    reverse_match = ctx2 == ctx1
    assert should_match == actually_match
    assert should_match == reverse_match


@pytest.mark.parametrize('affected_prop,initial_val,new_val,expected_signal', [
    ('selector', None, 'TEST.USER.ALL', 'selectorChanged'),
    ('selector', 'LHC.USER.ALL', 'TEST.USER.ALL', 'selectorChanged'),
    ('selector', 'LHC.USER.ALL', None, 'selectorChanged'),
    ('data_filters', None, {'key1': 'val1'}, 'dataFiltersChanged'),
    ('data_filters', {}, {'key1': 'val1'}, 'dataFiltersChanged'),
    ('data_filters', {'key2': 'val2'}, {'key1': 'val1'}, 'dataFiltersChanged'),
    ('data_filters', {'key1': 'val1', 'key2': 'val2'}, {'key1': 'val1'}, 'dataFiltersChanged'),
    ('data_filters', {'key1': 'val1'}, {'key1': 'val1', 'key2': 'val2'}, 'dataFiltersChanged'),
    ('data_filters', {'key1': 'val1'}, None, 'dataFiltersChanged'),
    ('wildcards', None, {'key1': 'val1'}, 'wildcardsChanged'),
    ('wildcards', {}, {'key1': 'val1'}, 'wildcardsChanged'),
    ('wildcards', {'key2': 'val2'}, {'key1': 'val1'}, 'wildcardsChanged'),
    ('wildcards', {'key1': 'val1', 'key2': 'val2'}, {'key1': 'val1'}, 'wildcardsChanged'),
    ('wildcards', {'key1': 'val1'}, {'key1': 'val1', 'key2': 'val2'}, 'wildcardsChanged'),
    ('wildcards', {'key1': 'val1'}, None, 'wildcardsChanged'),
])
def test_signals_fire_on_attribute_update(affected_prop, initial_val, new_val, expected_signal):
    signals = {
        'selectorChanged': None,
        'dataFiltersChanged': None,
        'wildcardsChanged': None,
    }
    ctx = CContext(**{affected_prop: initial_val})
    for sig in signals:
        signals[sig] = QSignalSpy(getattr(ctx, sig))
    assert all(len(spy) == 0 for spy in signals.values())
    setattr(ctx, affected_prop, new_val)
    for sig, spy in signals.items():
        if sig == expected_signal:
            assert len(spy) == 1
            assert len(spy[0]) == 0
        else:
            assert len(spy) == 0


@pytest.mark.parametrize('affected_prop,initial_val,new_val', [
    ('selector', None, None),
    ('selector', 'LHC.USER.ALL', 'LHC.USER.ALL'),
    ('data_filters', None, None),
    ('data_filters', {}, {}),
    ('data_filters', {'key1': 'val1'}, {'key1': 'val1'}),
    ('data_filters', {'key1': 'val1', 'key2': 'val2'}, {'key1': 'val1', 'key2': 'val2'}),
    ('wildcards', None, None),
    ('wildcards', {}, {}),
    ('wildcards', {'key1': 'val1'}, {'key1': 'val1'}),
    ('wildcards', {'key1': 'val1', 'key2': 'val2'}, {'key1': 'val1', 'key2': 'val2'}),
])
def test_signals_dont_fire_on_same_attribute_update(affected_prop, initial_val, new_val):
    signals = ['selectorChanged', 'dataFiltersChanged', 'wildcardsChanged']
    ctx = CContext(**{affected_prop: initial_val})
    spies = []
    for sig in signals:
        spies.append(QSignalSpy(getattr(ctx, sig)))
    assert all(len(spy) == 0 for spy in spies)
    setattr(ctx, affected_prop, new_val)
    assert all(len(spy) == 0 for spy in spies)


@pytest.mark.parametrize('wildcards,par_wildcards,expected_wildcards', [
    (None, None, None),
    ({}, None, None),
    (None, {}, None),
    ({}, {}, None),
    ({'key1': 'val1'}, None, {'key1': 'val1'}),
    ({'key1': 'val1'}, {}, {'key1': 'val1'}),
    (None, {'key1': 'val1'}, {'key1': 'val1'}),
    ({}, {'key1': 'val1'}, {'key1': 'val1'}),
    ({'key1': 'val1'}, {'key2': 'val2'}, {'key1': 'val1', 'key2': 'val2'}),
    ({'key1': 'val1'}, {'key1': 'CHANGED'}, {'key1': 'val1'}),
    ({'key1': 'val1'}, {'key1': 'CHANGED', 'key2': 'val2'}, {'key1': 'val1', 'key2': 'val2'}),
    ({'key1': 'val1', 'key2': 'val2'}, {'key1': 'CHANGED'}, {'key1': 'val1', 'key2': 'val2'}),
])
@pytest.mark.parametrize('par_inherit_sel', [True, False])
@pytest.mark.parametrize('par_inherit_filter', [True, False])
@pytest.mark.parametrize('sel,par_sel,inherit_sel,expected_sel', [
    (None, None, True, None),
    ('TEST.USER.ALL', None, True, 'TEST.USER.ALL'),
    (None, 'TEST.USER.ALL', True, 'TEST.USER.ALL'),
    ('TEST.USER.ALL', 'TEST.USER.ALL', True, 'TEST.USER.ALL'),
    ('TEST.USER.ALL', 'CHANGED', True, 'TEST.USER.ALL'),
    ('', None, True, None),
    (None, '', True, None),
    ('', '', True, None),
    ('', 'TEST.USER.ALL', True, 'TEST.USER.ALL'),
    ('TEST.USER.ALL', '', True, 'TEST.USER.ALL'),
    (None, None, False, None),
    ('TEST.USER.ALL', None, False, 'TEST.USER.ALL'),
    (None, 'TEST.USER.ALL', False, None),
    ('TEST.USER.ALL', 'TEST.USER.ALL', False, 'TEST.USER.ALL'),
    ('TEST.USER.ALL', 'CHANGED', False, 'TEST.USER.ALL'),
    ('', None, False, None),
    (None, '', False, None),
    ('', '', False, None),
    ('', 'TEST.USER.ALL', False, None),
    ('TEST.USER.ALL', '', False, 'TEST.USER.ALL'),
])
@pytest.mark.parametrize('filter,par_filter,inherit_filter,expected_filter', [
    (None, None, True, None),
    ({}, None, True, None),
    (None, {}, True, None),
    ({}, {}, True, None),
    ({'key1': 'val1'}, None, True, {'key1': 'val1'}),
    ({'key1': 'val1'}, {}, True, {'key1': 'val1'}),
    (None, {'key1': 'val1'}, True, {'key1': 'val1'}),
    ({}, {'key1': 'val1'}, True, {'key1': 'val1'}),
    ({'key1': 'val1'}, {'key2': 'val2'}, True, {'key1': 'val1', 'key2': 'val2'}),
    ({'key1': 'val1'}, {'key1': 'CHANGED'}, True, {'key1': 'val1'}),
    ({'key1': 'val1'}, {'key1': 'CHANGED', 'key2': 'val2'}, True, {'key1': 'val1', 'key2': 'val2'}),
    ({'key1': 'val1', 'key2': 'val2'}, {'key1': 'CHANGED'}, True, {'key1': 'val1', 'key2': 'val2'}),
    (None, None, False, None),
    ({}, None, False, None),
    (None, {}, False, None),
    ({}, {}, False, None),
    ({'key1': 'val1'}, None, False, {'key1': 'val1'}),
    ({'key1': 'val1'}, {}, False, {'key1': 'val1'}),
    (None, {'key1': 'val1'}, False, None),
    ({}, {'key1': 'val1'}, False, None),
    ({'key1': 'val1'}, {'key2': 'val2'}, False, {'key1': 'val1'}),
    ({'key1': 'val1'}, {'key1': 'CHANGED'}, False, {'key1': 'val1'}),
    ({'key1': 'val1'}, {'key1': 'CHANGED', 'key2': 'val2'}, False, {'key1': 'val1'}),
    ({'key1': 'val1', 'key2': 'val2'}, {'key1': 'CHANGED'}, False, {'key1': 'val1', 'key2': 'val2'}),
])
def test_merged(wildcards, par_wildcards, expected_wildcards, par_inherit_filter, par_inherit_sel, sel,
                par_sel, inherit_sel, expected_sel, filter, par_filter, inherit_filter, expected_filter):
    child_ctx = CContext(selector=sel, data_filters=filter, wildcards=wildcards)
    child_ctx.inherit_parent_data_filters = inherit_filter
    child_ctx.inherit_parent_selector = inherit_sel
    par_ctx = CContext(selector=par_sel, data_filters=par_filter, wildcards=par_wildcards)
    par_ctx.inherit_parent_selector = par_inherit_sel
    par_ctx.inherit_parent_data_filters = par_inherit_filter
    merged_ctx = child_ctx.merged(par_ctx)
    assert merged_ctx.inherit_parent_data_filters == child_ctx.inherit_parent_data_filters
    assert merged_ctx.inherit_parent_selector == child_ctx.inherit_parent_selector
    assert merged_ctx.selector == expected_sel
    assert merged_ctx.data_filters == expected_filter
    assert merged_ctx.wildcards == expected_wildcards
    assert id(merged_ctx) != id(child_ctx)
    assert id(merged_ctx) != id(par_ctx)


def test_merged_with_none():
    child_ctx = CContext(selector='TEST.USER.ALL')
    merged_ctx = child_ctx.merged(None)
    assert id(merged_ctx) != id(child_ctx)  # Different obj reference
    assert merged_ctx == child_ctx


@pytest.mark.parametrize('inherit_sel', [True, False])
@pytest.mark.parametrize('inherit_filter', [True, False])
@pytest.mark.parametrize('sel,new_sel,expected_sel,replace_sel', [
    (None, None, None, True),
    (None, '', None, True),
    (None, 'CHANGED', 'CHANGED', True),
    ('', None, None, True),
    ('', '', None, True),
    ('', 'CHANGED', 'CHANGED', True),
    ('TEST.USER.ALL', None, None, True),
    ('TEST.USER.ALL', '', None, True),
    ('TEST.USER.ALL', 'CHANGED', 'CHANGED', True),
    ('TEST.USER.ALL', None, 'TEST.USER.ALL', False),
    ('', None, None, False),
    (None, None, None, False),
])
@pytest.mark.parametrize('wildcards,new_wildcards,expected_wildcards,replace_wildcards', [
    (None, None, None, True),
    (None, {}, None, True),
    (None, {'key1': 'val1'}, {'key1': 'val1'}, True),
    ({}, None, None, True),
    ({}, {}, None, True),
    ({}, {'key1': 'val1'}, {'key1': 'val1'}, True),
    ({'key1': 'val1'}, None, None, True),
    ({'key1': 'val1'}, {}, None, True),
    ({'key1': 'val1'}, {'key2': 'val2'}, {'key2': 'val2'}, True),
    ({'key1': 'val1'}, {'key1': 'CHANGED'}, {'key1': 'CHANGED'}, True),
    ({'key1': 'val1'}, {'key1': 'CHANGED', 'key2': 'val2'}, {'key1': 'CHANGED', 'key2': 'val2'}, True),
    ({'key1': 'val1', 'key2': 'val2'}, {'key1': 'CHANGED'}, {'key1': 'CHANGED'}, True),
    ({'key1': 'val1'}, None, {'key1': 'val1'}, False),
    ({}, None, None, False),
    (None, None, None, False),
])
@pytest.mark.parametrize('filter,new_filter,expected_filter,replace_filter', [
    (None, None, None, True),
    (None, {}, None, True),
    (None, {'key1': 'val1'}, {'key1': 'val1'}, True),
    ({}, None, None, True),
    ({}, {}, None, True),
    ({}, {'key1': 'val1'}, {'key1': 'val1'}, True),
    ({'key1': 'val1'}, None, None, True),
    ({'key1': 'val1'}, {}, None, True),
    ({'key1': 'val1'}, {'key2': 'val2'}, {'key2': 'val2'}, True),
    ({'key1': 'val1'}, {'key1': 'CHANGED'}, {'key1': 'CHANGED'}, True),
    ({'key1': 'val1'}, {'key1': 'CHANGED', 'key2': 'val2'}, {'key1': 'CHANGED', 'key2': 'val2'}, True),
    ({'key1': 'val1', 'key2': 'val2'}, {'key1': 'CHANGED'}, {'key1': 'CHANGED'}, True),
    ({'key1': 'val1'}, None, {'key1': 'val1'}, False),
    ({}, None, None, False),
    (None, None, None, False),
])
def test_from_existing_replacing(sel, new_sel, expected_sel,
                                 wildcards, new_wildcards, expected_wildcards,
                                 filter, new_filter, expected_filter,
                                 inherit_sel, inherit_filter,
                                 replace_sel, replace_filter, replace_wildcards):
    orig_ctx = CContext(selector=sel, data_filters=filter, wildcards=wildcards)
    orig_ctx.inherit_parent_selector = inherit_sel
    orig_ctx.inherit_parent_data_filters = inherit_filter

    kwargs = {}
    if replace_sel:
        kwargs['selector'] = new_sel
    if replace_filter:
        kwargs['data_filters'] = new_filter
    if replace_wildcards:
        kwargs['wildcards'] = new_wildcards

    new_ctx = CContext.from_existing_replacing(orig_ctx, **kwargs)
    assert new_ctx.selector == expected_sel
    assert new_ctx.data_filters == expected_filter
    assert new_ctx.wildcards == expected_wildcards
    assert new_ctx.inherit_parent_selector == inherit_sel
    assert new_ctx.inherit_parent_data_filters == inherit_filter
    assert id(new_ctx) != id(orig_ctx)
