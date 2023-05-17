from functools import cache, partial, reduce
from math import inf
import re
from time import time
from typing import Literal
import bpy

from bpy.types import Context
from tourbox_addon.brush import (
    ActiveBrush,
    get_active_brush,
    get_paint,
    set_active_brush,
)
from tourbox_addon.data import modify_store
from tourbox_addon.util import default_context


DialPrefix = Literal["MouseWheel", "TallDial", "FlatWheel"]
BRUSH_SET_BUTTONS = (
    "DpadLeft",
    "DpadRight",
    "DpadUp",
    "DpadDown",
    "BottomRightClickerLeft",
    "BottomRightClickerRight",
    "SideThumb",
    "LongBarButton",
)
WHEEL_DIRS = ("Right", "Down", "Up", "Left")


_ModeProfile__button_states = dict()
_BrushModeProfile__timeout = inf
TIMEOUT = 1.0


@default_context
def bind_active_brush_button(ctx: Context, button: str):
    brush = get_active_brush()
    with modify_store() as store:
        newbrush = store.overwrite_brush(ctx.mode, button, brush)
    set_active_brush(ctx, newbrush)


class ModeProfile:
    def __init__(self) -> None:
        self.brush = ActiveBrush(bpy.context)

    def tall_dial(self, pressed: bool, direction: int):
        pass

    def flat_wheel(self, pressed: bool, direction: int):
        pass

    def mouse_wheel(self, pressed: bool, direction: int):
        pass

    def button_press(self, prefix: str):
        print("pressed", prefix)
        __button_states[prefix] = True

        if prefix == "LogoButtonRight":
            if bpy.context.mode != "SCULPT":
                bpy.ops.object.mode_set(mode="SCULPT")
        elif prefix == "LogoButtonLeft":
            if bpy.context.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            else:
                bpy.ops.object.mode_set(mode="EDIT")

    def button_release(self, prefix: str):
        print("released", prefix)
        __button_states[prefix] = False

    def button_state(self, prefix: str) -> bool:
        return __button_states.get(prefix, False)


class BrushModeProfile(ModeProfile):
    def tall_dial(self, pressed: bool, direction: int):
        self.brush.size += (2 if pressed else 20) * direction

    def flat_wheel(self, pressed: bool, direction: int):
        self.brush.strength += (0.2 if not pressed else 0.008) * direction
        self.brush.flow += (0.2 if not pressed else 0.008) * direction

    def mouse_wheel(self, pressed: bool, direction: int):
        pass

    def button_press(self, prefix: str):
        global __timeout
        super().button_press(prefix)
        if prefix == "ButtonNearTallDial":
            self.brush.direction = not self.brush.direction
        elif prefix in BRUSH_SET_BUTTONS:
            __timeout = time()
            with modify_store() as store:
                newbrush = store.get_brush(bpy.context.mode, prefix)
                if newbrush is not None:
                    set_active_brush(bpy.context, newbrush)

    def button_release(self, prefix: str):
        global __timeout
        super().button_release(prefix)
        if prefix in BRUSH_SET_BUTTONS:
            if time() - __timeout >= TIMEOUT:
                bind_active_brush_button(bpy.context, prefix)
            __timeout = inf


def get_profile() -> ModeProfile:
    if get_paint() is not None:
        return BrushModeProfile()
    return ModeProfile()


def on_input_event(event: str):
    profile = get_profile()
    if "Press" in event:
        profile.button_press(event.replace("Press", ""))
    elif "Release" in event:
        profile.button_release(event.replace("Release", ""))
    expr = "|".join(WHEEL_DIRS)
    prefix = re.sub(expr, "", event)
    pressed = profile.button_state(prefix)
    direction = 1 if ("Right" in event or "Down" in event) else -1
    if prefix == "TallDial":
        profile.tall_dial(pressed, direction)
    elif prefix == "FlatWheel":
        profile.flat_wheel(pressed, direction)
    elif prefix == "MouseWheel":
        profile.mouse_wheel(pressed, direction)
