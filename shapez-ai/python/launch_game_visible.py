"""
Launch shapez.exe explicitly on the user's interactive visible desktop (WinSta0\\Default).
Author: QXIK_mIJ
License: Apache License 2.0
"""

import ctypes
from ctypes import wintypes
import os
import sys

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('lpReserved', wintypes.LPWSTR),
        ('lpDesktop', wintypes.LPWSTR),
        ('lpTitle', wintypes.LPWSTR),
        ('dwX', wintypes.DWORD),
        ('dwY', wintypes.DWORD),
        ('dwXSize', wintypes.DWORD),
        ('dwYSize', wintypes.DWORD),
        ('dwXCountChars', wintypes.DWORD),
        ('dwYCountChars', wintypes.DWORD),
        ('dwFillAttribute', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('wShowWindow', wintypes.WORD),
        ('cbReserved2', wintypes.WORD),
        ('lpReserved2', ctypes.c_char_p),
        ('hStdInput', wintypes.HANDLE),
        ('hStdOutput', wintypes.HANDLE),
        ('hStdError', wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('hProcess', wintypes.HANDLE),
        ('hThread', wintypes.HANDLE),
        ('dwProcessId', wintypes.DWORD),
        ('dwThreadId', wintypes.DWORD),
    ]

def launch_visible():
    exe_path = r"C:\Users\mvas2\shapez-portable\shapez.exe"
    work_dir = r"C:\Users\mvas2\shapez-portable"

    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    si.lpDesktop = "WinSta0\\Default"

    pi = PROCESS_INFORMATION()

    cmd = f'"{exe_path}"'

    success = ctypes.windll.kernel32.CreateProcessW(
        None,
        cmd,
        None,
        None,
        False,
        0,
        None,
        work_dir,
        ctypes.byref(si),
        ctypes.byref(pi)
    )

    if success:
        print(f"[SUCCESS] Launched shapez.exe on WinSta0\\Default! PID: {pi.dwProcessId}")
        ctypes.windll.kernel32.CloseHandle(pi.hProcess)
        ctypes.windll.kernel32.CloseHandle(pi.hThread)
        return True
    else:
        err = ctypes.GetLastError()
        print(f"[ERROR] CreateProcessW failed with error code: {err}")
        return False

if __name__ == "__main__":
    launch_visible()
