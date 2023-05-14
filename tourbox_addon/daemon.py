from functools import partial
from os import kill
from signal import SIGINT
from subprocess import PIPE, Popen
from threading import Thread
from typing import IO

import bpy

from tourbox_addon import EXE
from tourbox_addon.events import on_input_event


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


def thread_entry(file: IO):
    while True:
        data = file.readline().decode("utf-8").strip()
        if data != "Unknown" and data.strip():
            # Hack to get back to a "safe" blender thread, hopefully. But nothing is certain
            bpy.app.timers.register(partial(on_input_event, data), first_interval=0)
