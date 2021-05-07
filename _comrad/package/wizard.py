from __future__ import print_function, unicode_literals
import logging
import functools
import questionary
from dataclasses import dataclass
from typing import List, Optional, Union, Set, cast
from packaging.requirements import Requirement, InvalidRequirement
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.completion.word_completer import WordCompleter
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.filters import IsDone, Filter
from prompt_toolkit.styles import BaseStyle, Style
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.layout import (FormattedTextControl, Layout, HSplit, VSplit, BufferControl, D,
                                   ConditionalContainer, ScrollOffsets)
from questionary.prompts import AVAILABLE_PROMPTS
from questionary.prompts.common import Separator, merge_styles
from questionary.constants import (DEFAULT_QUESTION_PREFIX, DEFAULT_STYLE, INDICATOR_SELECTED, INDICATOR_UNSELECTED,
                                   SELECTED_POINTER, DEFAULT_KBI_MESSAGE)
from questionary.question import Question
from .phonebook import suggest_maintainer_info
from .spec import PackageSpec


logger = logging.getLogger(__name__)


CUSTOM_PROMPT_TYPE = 'comrad_custom_list'


def confirm_spec_interactive(inferred_spec: PackageSpec,
                             implicitly_disabled_requirements: Set[Requirement],
                             mandatory: Optional[Set[Requirement]],
                             force_phonebook: bool):

    # Skip resolving user information, if it was already cached
    if force_phonebook or (inferred_spec.maintainer is None and inferred_spec.maintainer_email is None):
        suggested_maintainer, suggested_email = suggest_maintainer_info(default_maintainer=inferred_spec.maintainer,
                                                                        default_email=inferred_spec.maintainer_email,
                                                                        force=force_phonebook)
    else:
        logger.debug('Not contacting phonebook, using maintainer information from cache')
        suggested_maintainer, suggested_email = inferred_spec.maintainer, inferred_spec.maintainer_email

    questionary.print(text='\n'
                           'Input or confirm package details\n'
                           '================================',
                      style='fg:#44ff44 italic')
    mandatory_reqs = mandatory or set()
    optional_reqs = [RequirementItem(req=req, checked=True) for req in inferred_spec.install_requires
                     if req not in mandatory_reqs]
    optional_reqs.extend([RequirementItem(req=req, checked=False, implied=True)
                          for req in implicitly_disabled_requirements])
    optional_choices = sorted(optional_reqs, key=line_sort)
    forced_reqs = {RequirementItem(req=req, checked=True, forced=True) for req in mandatory_reqs}
    mandatory_choices = sorted(forced_reqs, key=line_sort)

    suggested_dependencies: List[Union[RequirementItem, Separator]] = []
    suggested_dependencies.extend(optional_choices)
    suggested_dependencies.append(Separator('Always included:'))
    suggested_dependencies.extend(mandatory_choices)

    try:
        answers = questionary.unsafe_prompt(
            questions=[{
                'type': 'input',
                'name': 'name',
                'message': 'Package name',
                'default': inferred_spec.name,
            }, {
                'type': 'input',
                'name': 'version',
                'message': 'Package version',
                'default': inferred_spec.version,
            }, {
                'type': CUSTOM_PROMPT_TYPE,
                'name': 'install_requires',
                'message': 'Runtime dependencies',
                'choices': suggested_dependencies,
            }, {
                'type': 'input',
                'name': 'description',
                'message': 'Package description',
                'default': inferred_spec.description or '',
            }, {
                'type': 'input',
                'name': 'maintainer',
                'message': 'Package maintainer',
                'default': suggested_maintainer or '',
            }, {
                'type': 'input',
                'name': 'maintainer_email',
                'message': "Maintainer's email",
                'default': suggested_email or '',
            }],
            style=Style([('qmark', 'fg:#5f819d'),  # token in front of the question
                         ('question', 'bold'),  # question text
                         ('answer', 'fg:#ff9d00 bold'),  # submitted answer text behind the question
                         ('pointer', 'fg:#ff9d00 bold'),  # pointer used in select and checkbox prompts
                         ('selected', ''),  # style for a selected item of a checkbox
                         ('separator', 'fg:#6c6c6c'),  # separator in lists
                         ('instruction', 'fg:#0ef4e5'),  # user instructions for select, rawselect, checkbox
                         ('text', ''),  # any other text
                         ('instruction', ''),  # user instructions for select, rawselect, checkbox
                         ('error', 'fg:#ff0000 bold'),
                         ('hint', 'fg:#6c6c6c')]),
        )
    except KeyboardInterrupt:
        print(f'\n'
              f'{DEFAULT_KBI_MESSAGE}'
              f'\n')
        # Re-raise instead of getting swallowed, like questionary.prompt() does
        raise

    # Reuse the mapping logic that sits in that method
    inferred_spec.update_from_dict(answers)


@dataclass
class RequirementItem:
    req: Requirement
    checked: bool
    implied: bool = False
    forced: bool = False

    def __hash__(self):
        return hash(self.req)


def line_sort(choice: RequirementItem) -> str:
    return str(choice.req).lower()


class ImplicitRequirementError(Exception):
    pass


class ExistingRequirementError(Exception):
    pass


class ExtensibleInquirerControl(FormattedTextControl):
    # Inspired by questionary.prompts.common.InquirerControl

    def __init__(self, choices: List[Union[RequirementItem, Separator]], **kwargs):
        self.pointer_index = -1
        self.selected_options: Set[Requirement] = set()
        self.answered = False
        self.aborting = False
        self.choices: List[Union[RequirementItem, Separator]] = []
        self._init_choices(choices)
        super().__init__(self._get_choice_tokens, **kwargs)
        self.is_entering_arbitrary_token = False
        self.arbitrary_token_error: Optional[str] = None

    def add_choice(self, choice: str):
        req = Requirement(choice)  # Keep this to throw an exception if input is invalid

        for item in self.choices:
            if isinstance(item, Separator):
                continue
            if item.forced and item.req.name == req.name:
                raise ImplicitRequirementError
            elif not item.forced and str(req) == str(item.req):
                raise ExistingRequirementError

        for idx, item in enumerate(self.choices):
            if isinstance(item, Separator):
                sep_idx = idx
                break
        else:
            sep_idx = len(self.choices) - 1
        # Insert before the first separator (which separates mandatory options)
        self.choices.insert(sep_idx, RequirementItem(req=req, checked=True))
        self.selected_options.add(req)

        # Resort by name
        new_choices = sorted(cast(List[RequirementItem], self.choices[:sep_idx + 1]), key=line_sort)
        self.choices[:sep_idx + 1] = new_choices

    @property
    def line_count(self) -> int:
        return len(self.choices)

    def get_selected_values(self) -> List[Requirement]:
        return [c.req for c in self.choices if not isinstance(c, Separator) and (c.forced or c.req in self.selected_options)]

    def _init_choices(self, choices: List[Union[RequirementItem, Separator]]):
        searching_first_choice = True
        for i, c in enumerate(choices):
            self.choices.append(c)
            if not isinstance(c, Separator):
                if c.checked and not c.forced:
                    self.selected_options.add(c.req)
                if searching_first_choice and not c.forced:  # Find the first (available) choice
                    self.pointer_index = i
                    searching_first_choice = False

    def toggle_focused_choice(self):
        try:
            pointed_choice = self.choices[self.pointer_index]
        except IndexError:
            return
        self._toggle_line(pointed_choice)

    def toggle_all(self):
        all_selected = True
        for choice in self.choices:
            if isinstance(choice, Separator):
                continue
            if choice.req not in self.selected_options and not choice.forced:
                self.selected_options.add(choice.req)
                all_selected = False
        if all_selected:
            self.selected_options.clear()

    def _toggle_line(self, line: RequirementItem):
        if line.req in self.selected_options:
            self.selected_options.remove(line.req)
        else:
            self.selected_options.add(line.req)

    def _get_choice_tokens(self):
        """Override parent logic to append requirement spec in parenthesis after the name."""
        tokens = []
        for index, choice in enumerate(self.choices):
            if isinstance(choice, Separator):
                tokens.append(('class:separator', f'  {choice.title!s}\n'))
                continue
            selected = (choice.req in self.selected_options)
            pointed_at = (index == self.pointer_index)

            if pointed_at:
                tokens.append(('class:pointer', f' {SELECTED_POINTER} '))
            else:
                tokens.append(('class:text', '   '))

            if choice.forced:
                tokens.append(('class:text', f'📦 {str(choice.req).strip()}'))
            else:
                tokens.append(('class:text', f'{INDICATOR_SELECTED if selected else INDICATOR_UNSELECTED} '))
                tokens.append(('class:text', str(choice.req).strip()))

                if pointed_at:
                    tokens.append(('[SetCursorPosition]', ''))

                if choice.implied:
                    tokens.append(('class:hint', ' (implicitly shipped with comrad)'))
            tokens.append(('class:text', '\n'))
        tokens.pop()  # Remove last newline.
        return tokens


def _smart_dependency_list(message: str,
                           choices: List[Union[RequirementItem, Separator]],
                           qmark: str = DEFAULT_QUESTION_PREFIX,
                           style: Optional[BaseStyle] = None) -> Question:
    if style:
        style = merge_styles([DEFAULT_STYLE, style])
    else:
        style = DEFAULT_STYLE
    new_item_buffer = Buffer(history=InMemoryHistory(),
                             completer=WordCompleter(words=['accwidgets', 'pyrbac', 'pyjapc', 'pytimber',
                                                            'JPype1', 'pyqtgraph', 'PyQt5', 'QtPy', 'qtawesome',
                                                            'matplotlib', 'numpy', 'scipy', 'pyccda', 'dataclasses',
                                                            'papc', 'psutil', 'requests', 'PyYAML', 'pandas',
                                                            'jpype1', 'nicejapc', 'pjlsa', 'pybt', 'pyfgc',
                                                            'pylogbook', 'pyphonebook', 'pyrda3', 'stubgenj']))

    ic = ExtensibleInquirerControl(choices)

    class IsTypingNewModule(Filter):

        def __call__(self):
            return ic.is_entering_arbitrary_token

        def __repr__(self):
            return 'IsTypingNewModule()'

    class HasError(Filter):

        def __call__(self):
            return ic.arbitrary_token_error is not None

        def __repr__(self):
            return 'HasError()'

    def get_prompt_tokens():
        tokens = []

        tokens.append(('class:qmark', qmark))
        tokens.append(('class:question', f' {message!s} '))
        if not ic.aborting:
            if ic.answered:
                selected_values = ic.get_selected_values()
                selected_count = len(selected_values)
                tokens.append(('class:answer', f'({selected_count} package{"" if selected_count == 1 else "s"} included)'))
                for selected_req in selected_values:
                    tokens.append(('class:answer', f'\n    📦 {str(selected_req).strip()}'))
            else:
                instruction = ('\n (<a> to add new list item, <up>, <down> to move,'
                               ' <space> to select, <t> to toggle all)' if not IsTypingNewModule()()
                               else '\n (<escape> to cancel entering new list item,'
                                    ' <enter> to confirm new item)')
                tokens.append(('class:instruction', instruction))
        return tokens

    def get_arbitrary_input_tokens():
        tokens = []
        tokens.append(('class:text', '\nEnter package spec here in PEP-508 format (e.g. my_pkg or my_pkg==2.0):'))
        return tokens

    def get_error_tokens():
        tokens = []
        tokens.append(('class:error', f'\n{ic.arbitrary_token_error}'))
        return tokens

    layout = Layout(HSplit([
        Window(content=FormattedTextControl(get_prompt_tokens, focusable=False),
               dont_extend_height=True),
        ConditionalContainer(Window(ic,
                                    width=D.exact(43),
                                    height=D(min=3),
                                    scroll_offsets=ScrollOffsets(top=1, bottom=1),
                                    dont_extend_height=True),
                             filter=(~IsDone() & ~IsTypingNewModule())),
        ConditionalContainer(
            HSplit([
                ConditionalContainer(Window(content=FormattedTextControl(get_error_tokens, focusable=False),
                                            height=D.exact(2),
                                            dont_extend_height=True),
                                     filter=HasError()),
                Window(content=FormattedTextControl(get_arbitrary_input_tokens, focusable=False),
                       height=D.exact(2),
                       dont_extend_height=True),
                VSplit([
                    Window(content=FormattedTextControl([('class:text', '> ')], focusable=False),
                           width=D.exact(2),
                           dont_extend_height=True),
                    Window(content=BufferControl(buffer=new_item_buffer),
                           height=D.exact(1),
                           dont_extend_height=True),
                ]),
            ]),
            filter=(~IsDone() & IsTypingNewModule()),
        ),
    ]))

    kb = KeyBindings()

    @kb.add(Keys.ControlC, eager=True)
    def interrupt(event):
        ic.aborting = True
        event.app.exit(exception=KeyboardInterrupt, style='class:aborting')

    @kb.add(' ', eager=True, filter=~IsTypingNewModule())
    def select(_):
        ic.toggle_focused_choice()

    @kb.add('t', eager=True, filter=~IsTypingNewModule())
    def toggle(_):
        ic.toggle_all()

    @kb.add('a', eager=True, filter=~IsTypingNewModule())
    def add(event):
        new_item_buffer.reset(append_to_history=True)
        ic.is_entering_arbitrary_token = True
        ic.arbitrary_token_error = None

    @kb.add(Keys.Escape, eager=True, filter=IsTypingNewModule())
    def cancel_add(event):
        ic.is_entering_arbitrary_token = False
        ic.arbitrary_token_error = None

    def _move_cursor(*_, index_step: int):
        def _move() -> Union[RequirementItem, Separator]:
            new_index = ((ic.pointer_index + index_step) % ic.line_count)
            ic.pointer_index = new_index
            current_choice = ic.choices[new_index]
            return current_choice
        curr = _move()
        while isinstance(curr, Separator) or curr.forced:
            curr = _move()

    kb.add(Keys.Down, eager=True, filter=~IsTypingNewModule())(functools.partial(_move_cursor, index_step=1))

    kb.add(Keys.Up, eager=True, filter=~IsTypingNewModule())(functools.partial(_move_cursor, index_step=-1))

    def _finish_manual_entry():
        try:
            ic.add_choice(new_item_buffer.text)
        except InvalidRequirement:
            ic.arbitrary_token_error = f'Cannot parse library name "{new_item_buffer.text}", please use PEP-508 format.'
        except ExistingRequirementError:
            ic.arbitrary_token_error = f'Requirement "{new_item_buffer.text}" already exists in the list.'
        except ImplicitRequirementError:
            ic.arbitrary_token_error = f'Requirement "{Requirement(new_item_buffer.text).name}" is implicitly ' \
                                       'included with fixed version.'
        else:
            ic.is_entering_arbitrary_token = False

    @kb.add(Keys.Enter, eager=True)
    def set_answer(event):
        if IsTypingNewModule()():
            _finish_manual_entry()
        else:
            ic.answered = True
            event.app.exit(result=ic.get_selected_values())

    return Question(Application(layout=layout,
                                key_bindings=kb,
                                mouse_support=True,
                                style=style))


# Custom implementation of the control (to be detected when using prompt() or unsafe_prompt())
AVAILABLE_PROMPTS[CUSTOM_PROMPT_TYPE] = _smart_dependency_list
