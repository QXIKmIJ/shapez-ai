"""
Position the shapez window on Display 1 or Display 2.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import ctypes
from ctypes import wintypes
import sys
import psutil

def move_shapez(monitor=1):
    hdesk = ctypes.windll.user32.OpenDesktopW('Default', 0, False, 0x0040 | 0x0001)
    ctypes.windll.user32.SetThreadDesktop(hdesk)

    shapez_pids = set(p.pid for p in psutil.process_iter(['name', 'pid']) if 'shapez' in (p.info['name'] or '').lower())
    
    target_hwnd = None
    def cb(hwnd, lp):
        nonlocal target_hwnd
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in shapez_pids:
            buf = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
            if buf.value.lower() == 'shapez':
                target_hwnd = hwnd
                return False
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    ctypes.windll.user32.EnumDesktopWindows(hdesk, WNDENUMPROC(cb), 0)

    if not target_hwnd:
        print("[ERROR] Could not find shapez window handle.")
        return False

    if monitor == 2:
        # Display 2 is (2560, 121, 4480, 1321)
        x, y, w, h = 2650, 180, 1400, 950
    else:
        # Display 1 is (0, 0, 2560, 1440)
        x, y, w, h = 460, 180, 1500, 950

    # SW_RESTORE = 9, SWP_SHOWWINDOW = 0x0040
    ctypes.windll.user32.ShowWindow(target_hwnd, 9)
    ctypes.windll.user32.SetWindowPos(target_hwnd, -1, x, y, w, h, 0x0040)
    ctypes.windll.user32.SetWindowPos(target_hwnd, -2, x, y, w, h, 0x0040)
    ctypes.windll.user32.SetForegroundWindow(target_hwnd)
    ctypes.windll.user32.BringWindowToTop(target_hwnd)
    print(f"[SUCCESS] Moved shapez (HWND {target_hwnd}) to Monitor {monitor} at ({x}, {y}, {w}x{h}) and focused!")
    return True

if __name__ == "__main__":
    mon = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    move_shapez(mon)
