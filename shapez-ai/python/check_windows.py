import ctypes
import ctypes.wintypes

monitors = []
def cb(hmon, hdc, lprect, lparam):
    r = lprect.contents
    monitors.append((r.left, r.top, r.right, r.bottom))
    return True

MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HMONITOR, ctypes.wintypes.HDC, ctypes.POINTER(ctypes.wintypes.RECT), ctypes.wintypes.LPARAM)
ctypes.windll.user32.EnumDisplayMonitors(0, 0, MONITORENUMPROC(cb), 0)
print('Active Displays:', monitors)
