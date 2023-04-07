# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "tourbox-controller",
    "author": ".",
    "description": "",
    "blender": (2, 80, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Generic",
}

from functools import partial
from os import kill
from signal import SIGINT
from subprocess import Popen, PIPE
from threading import Thread
from typing import IO
from typing import Generic
from time import time
from dataclasses import dataclass, field
import pickle

import bpy
from bpy.types import Brush
from math import inf

T = Generic()

EXE = "/home/squirrel/tourbox-blender/target/debug/tbelite"
PICKLECONFIG = "/home/squirrel/.config/tourbox-blender.pickle"
SWATCH_TIMEOUT = 1  # second(s)

TallDialPressed = False
FlatWheelPressed = False


@dataclass(slots=True)
class BrushSwatch:
    mode: str
    buttons: tuple[str]
    timeout: float = field(init=False, default=inf)
    __storage: dict = field(init=False, default_factory=dict)

    def tap(self, button: str):
        if bpy.context.mode != self.mode:
            return
        if "Press" in button:
            self.__press(button)
        elif "Release" in button:
            self.__release(button)

    def __release(self, button: str):
        button = button.replace("Release", "")
        if time() - self.timeout >= SWATCH_TIMEOUT:
            brush = get_mode_active_brush(self.mode)
            self.__storage[button] = brush.name
            print(f"Set '{button}' to '{brush.name}'")
            self.timeout = inf

    def __press(self, button: str):
        self.timeout = time()
        button = button.replace("Press", "")
        brush = self.__storage.get(button, None)
        if brush is None or brush not in bpy.data.brushes:
            return
        brush = bpy.data.brushes[brush]
        set_mode_brush(self.mode, brush)
        print(f"Used '{button}' to switch to '{brush.name}'")


try:
    with open(PICKLECONFIG, "rb") as fo:
        SWATCHES = pickle.load(fo)
except Exception as e:
    print(e)
    SWATCHES = (
        BrushSwatch(
            "SCULPT",
            (
                "DpadLeft",
                "DpadRight",
                "DpadUp",
                "DpadDown",
                "BottomRightClickerLeft",
                "BottomRightClickerRight",
                "SideThumb",
                "LongBarButton",
            ),
        ),
    )

def on_input_event(event: str):
    mode = bpy.context.mode
    for swatch in SWATCHES:
        swatch.tap(event)
    with open(PICKLECONFIG, "wb") as fo:
        pickle.dump(SWATCHES, file=fo)
    if mode not in known_modes:
        return
    print(event)
    known_modes[mode](event)


def edit_on_input_event(event: str):
    match event:
        case "LogoButtonLeftPress":
            bpy.ops.object.mode_set(mode="OBJECT", toggle=False)
        case "LogoButtonRightPress":
            bpy.ops.object.mode_set(mode="SCULPT", toggle=False)


def object_on_input_event(event: str):
    match event:
        case "LogoButtonLeftPress":
            bpy.ops.object.mode_set(mode="EDIT", toggle=False)
        case "LogoButtonRightPress":
            bpy.ops.object.mode_set(mode="SCULPT", toggle=False)


def sculpt_on_input_event(event: str):
    global TallDialPressed, FlatWheelPressed

    mode = "SCULPT"

    match event:
        case "MouseWheelUp":
            cycle_mode_brush(mode, -1)
        case "MouseWheelDown":
            cycle_mode_brush(mode, 1)
        case "TallDialPress":
            TallDialPressed = True
        case "TallDialRelease":
            TallDialPressed = False
        case "FlatWheelPress":
            FlatWheelPressed = True
        case "FlatWheelRelease":
            FlatWheelPressed = False
        case "ButtonNearTallDialPress":
            brush = get_mode_active_brush(mode)
            brush.direction = ({"SUBTRACT", "ADD"} - {brush.direction}).pop()
        case "LogoButtonLeftPress":
            bpy.ops.object.mode_set(mode="OBJECT", toggle=False)
        case "LongBarButtonPress":
            brush = (
                bpy.context.tool_settings.unified_paint_settings
                if bpy.context.tool_settings.unified_paint_settings.use_unified_size
                else get_mode_active_brush(mode)
            )
            brush.use_locked_size = ({"VIEW", "SCENE"} - {brush.use_locked_size}).pop()
        case "TallDialRight" | "TallDialLeft" | "FlatWheelRight" | "FlatWheelLeft":
            direction = 1 if "Right" in event else -1
            unified_settings = bpy.context.tool_settings.unified_paint_settings
            brush = get_mode_active_brush(mode)
            if "TallDial" in event:
                scroll_value_T(
                    unified_settings if unified_settings.use_unified_size else brush,
                    "size",
                    0,
                    500,
                    (2 if TallDialPressed else 20) * direction,
                )
            else:
                # Unified strength is broken in Blender currently
                # https://projects.blender.org/blender/blender/issues/99172
                # So it should always be left disabled
                scroll_value_T(
                    unified_settings
                    if unified_settings.use_unified_strength
                    else brush,
                    "strength",
                    0,
                    1,
                    (0.02 if FlatWheelPressed else 0.08) * direction,
                )


def scroll_value_T(target, attr: str, minv: T, maxv: T, step: T):
    incremented = getattr(target, attr) + step
    clamped = min(max(incremented, minv), maxv)
    setattr(target, attr, clamped)


def thread_entry(file: IO):
    while True:
        data = file.readline().decode("utf-8").strip()
        if data != "Unknown" and data.strip():
            # Hack to get back to a "safe" blender thread, hopefully. But nothing is certain
            bpy.app.timers.register(partial(on_input_event, data), first_interval=0)


def set_mode_brush(mode: str, brush: Brush):
    if mode == "SCULPT":
        bpy.context.tool_settings.sculpt.brush = brush
    else:
        raise Exception(f"Unknown Mode: {mode}")


def get_mode_active_brush(mode: str):
    if mode == "SCULPT":
        return bpy.context.tool_settings.sculpt.brush
    raise Exception(f"Unknown Mode: {mode}")


def get_mode_brushes(mode: str):
    if mode == "SCULPT":
        return (brush for brush in bpy.data.brushes if brush.use_paint_sculpt)
    raise Exception(f"Unknown Mode: {mode}")


def get_active_tool():
    return bpy.context.workspace.tools.from_space_view3d_mode(
        bpy.context.mode, create=False
    ).idname


def lookup_brush(mode: str, brush_name: str) -> str | None:
    return next(
        (brush for brush in get_mode_brushes(mode) if brush.name == brush_name), None
    )


class MissingBrush(Exception):
    pass


def tool_to_brush(mode: str, toollabel: str):
    """Hackily convert tool label to brushname
    The tools have an operator associated with them to switch to the correct brush, but they raise errors when called here
    """
    brush = lookup_brush(mode, toollabel)
    if brush is not None:
        return brush
    if mode == "SCULPT":
        mode_label = f"Sculpt{toollabel}"
    else:
        raise Exception(f"Unknown Mode: {mode}")
    brush = lookup_brush(mode, mode_label)
    if brush is not None:
        return brush
    for suffix in ("/Deflate", "/Contrast", "/Deepen", "/Peaks", "/Magnify"):
        brush = lookup_brush(mode, f"{toollabel}{suffix}")
        if brush is not None:
            return brush
    raise MissingBrush(f"Failed to convert tool '{toollabel}' to a brush")


def get_tools():
    return tuple(
        (tool.idname, tool.label)
        for tool in bpy.types.VIEW3D_PT_tools_active.tools_from_context(bpy.context)
        if hasattr(tool, "idname")
    )


def cycle_mode_brush(mode: str, delta: int):
    "This function barely works, but it works enough"
    if mode not in known_modes:
        return
    tool_idname = get_active_tool()
    tools = get_tools()
    idx = next(i for i, (oidname, _) in enumerate(tools) if oidname == tool_idname)
    idx += delta
    idx %= len(tools)
    try:
        brush = tool_to_brush(mode, tools[idx][1])
    except MissingBrush:
        brush = tool_to_brush(mode, tools[0][1])
    set_mode_brush(mode, brush)


daemon = None


def start_daemon():
    global daemon
    if daemon is not None:
        return
    daemon = Popen([EXE], stdout=PIPE)
    t = Thread(target=thread_entry, args=(daemon.stdout,))
    t.start()


def stop_daemon():
    global daemon
    if daemon is None:
        return
    kill(daemon.pid, SIGINT)
    daemon = None


def register():
    start_daemon()


def unregister():
    stop_daemon()


known_modes = {
    "SCULPT": sculpt_on_input_event,
    "EDIT_MESH": edit_on_input_event,
    "OBJECT": object_on_input_event,
}
