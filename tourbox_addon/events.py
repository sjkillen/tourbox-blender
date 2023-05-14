


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
