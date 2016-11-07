# Copyright (C) 2016 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import ctypes
import logging
import struct

from lib.common.defines import (
    KERNEL32, GENERIC_READ, GENERIC_WRITE, FILE_SHARE_READ, FILE_SHARE_WRITE,
    OPEN_EXISTING
)
from lib.common.rand import random_string

log = logging.getLogger(__name__)

# Random name for the zer0m0n driver.
driver_name = random_string(16)

CTL_CODE_BASE = 0x222000

class Ioctl(object):
    actions = [
        "addpid",
        "cmdpipe",
        "channel",
        "dumpmem",
    ]

    def invoke(self, action, value):
        if action not in self.actions:
            raise RuntimeError("Invalid ioctl action: %s" % action)

        device_handle = KERNEL32.CreateFileA(
            "\\\\.\\%s" % driver_name, GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None
        ) % 2**32

        if device_handle == 0xffffffff:
            # Only report an error if the error is not "name not found",
            # indicating that no kernel analysis is currently taking place.
            if KERNEL32.GetLastError() != 2:
                log.warning(
                    "Error opening handle to driver (%s): %d!",
                    driver_name, KERNEL32.GetLastError()
                )
            return False

        out = ctypes.create_string_buffer(0x1000)
        length = ctypes.c_uint()

        ret = KERNEL32.DeviceIoControl(
            device_handle, CTL_CODE_BASE + self.actions.index(action) * 4,
            value, len(value), out, ctypes.sizeof(out),
            ctypes.byref(length), None
        )
        KERNEL32.CloseHandle(device_handle)

        if not ret:
            log.warning(
                "Error performing ioctl (%d): %d!",
                self.actions.index(action), KERNEL32.GetLastError()
            )
            return False

        return out.raw[:length.value]

    def addpid(self, pid):
        return self.invoke("addpid", struct.pack("I", pid))

    def cmdpipe(self, pipe):
        return self.invoke("cmdpipe", "\x00".join(pipe + "\x00"))

    def channel(self, pipe):
        return self.invoke("channel", "\x00".join(pipe + "\x00"))

    def dumpmem(self, pid):
        return self.invoke("dumpmem", struct.pack("I", pid))

ioctl = Ioctl()
