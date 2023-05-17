from abc import ABC, abstractproperty
from dataclasses import field
from typing import Literal, Callable

from attr import dataclass

from bpy.types import Context
from tourbox_addon.brush import get_active_brush, set_active_brush
from tourbox_addon.data import modify_store
from tourbox_addon.util import default_context


DialPrefix = Literal["MouseWheel", "TallDial", "FlatWheel"]

__dial_bindings: dict()


@default_context
def bind_active_brush_button(ctx: Context, button: str):
    brush = get_active_brush()
    with modify_store() as store:
        newbrush = store.overwrite_brush(ctx.mode, button, brush)
    set_active_brush(newbrush)


@dataclass
class ModeProfile(ABC):
    button_states: dict = field(init=False, default_factory=dict)

    @abstractproperty
    def tall_dial(self, clockwise: bool):
        raise NotImplementedError()

    def flat_wheel(self, clockwise: bool):
        raise NotImplementedError()

    @abstractproperty
    def mouse_wheel(self, downwards: bool):
        raise NotImplementedError()

    def button_press(self, prefix: str):
        self.button_states[prefix] = True

    def button_release(self, prefix: str):
        self.button_states[prefix] = False



def on_input_event(event: str):
    pass
