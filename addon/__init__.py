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

import bpy
from bpy.types import Brush

EXE = "/home/vole/tourbox-blender/target/debug/tbelite"

known_modes = ("SCULPT",)
supported_events = ("MouseWheelUp", "MouseWheelDown")


def on_input_event(event: str):
    mode = "SCULPT"
    print(event)
    match event:
        case "MouseWheelUp":
            cycle_mode_brush(mode, -1)
        case "MouseWheelDown":
            cycle_mode_brush(mode, 1)


def thread_entry(file: IO):
    while True:
        data = file.readline().decode("utf-8").strip()
        if data in supported_events:
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


def tool_to_brush(mode: str, toollabel: str):
    "Hacky"
    brush = next(
        (brush for brush in get_mode_brushes(mode) if brush.name == brush_name), None
    )
    if brush is not None:
        return brush
    if mode == "SCULPT":
        return mode_label = f"Sculpt{}"
    raise Exception(f"Unknown Mode: {mode}")


def get_tools():
    return tuple(
        (tool.idname, tool.label)
        for tool in bpy.types.VIEW3D_PT_tools_active.tools_from_context(bpy.context)
        if hasattr(tool, "idname")
    )


def cycle_mode_brush(mode: str, delta: int):
    if mode not in known_modes:
        return
    tool_idname = get_active_tool()
    tools = get_tools()
    idx = next(i for i, (oidname, _) in enumerate(tools) if oidname == tool_idname)
    idx += delta
    idx %= len(tools)
    brush_name = tool_to_brush_name(mode, tools[idx][1])
    brush = next(
        (brush for brush in get_mode_brushes(mode) if brush.name == brush_name), None
    )
    if brush is None:
        print("Can't find brush", brush_name)
        return
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
