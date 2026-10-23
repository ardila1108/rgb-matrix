"""Only send a frame to the panel when it really changed."""


class FrameGate:
    """Say whether a frame needs sending.

    A static screen then costs nothing: no new frame, no buffer swap. A brightness
    change counts as a change, because the panel library applies brightness when
    the pixels are written.
    """

    def __init__(self):
        self._last = None
        self._brightness = None

    def changed(self, image, brightness):
        data = image.tobytes()
        if data == self._last and brightness == self._brightness:
            return False
        self._last, self._brightness = data, brightness
        return True
