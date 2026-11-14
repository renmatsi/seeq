"""Barra de título própria, mantendo a janela no gerenciamento do Windows."""

import os


def install(root, drag_widgets):
    if os.name != 'nt':
        return False

    import ctypes as ct
    from ctypes import wintypes as wt

    user = ct.WinDLL('user32', use_last_error=True)
    controls = ct.WinDLL('comctl32', use_last_error=True)
    long_ptr = ct.c_ssize_t
    uintptr = ct.c_size_t
    callback = ct.WINFUNCTYPE(long_ptr, wt.HWND, wt.UINT, uintptr, long_ptr, uintptr, uintptr)

    def api(dll, name, result, *args):
        proc = getattr(dll, name)
        proc.restype, proc.argtypes = result, args
        return proc

    ancestor = api(user, 'GetAncestor', wt.HWND, wt.HWND, wt.UINT)
    window_rect = api(user, 'GetWindowRect', wt.BOOL, wt.HWND, ct.POINTER(wt.RECT))
    zoomed = api(user, 'IsZoomed', wt.BOOL, wt.HWND)
    position = api(user, 'SetWindowPos', wt.BOOL, wt.HWND, wt.HWND, ct.c_int, ct.c_int, ct.c_int, ct.c_int, wt.UINT)
    send = api(user, 'SendMessageW', long_ptr, wt.HWND, wt.UINT, uintptr, long_ptr)
    release = api(user, 'ReleaseCapture', wt.BOOL)
    monitor = api(user, 'MonitorFromWindow', wt.HANDLE, wt.HWND, wt.DWORD)

    class MonitorInfo(ct.Structure):
        _fields_ = [('size', wt.DWORD), ('monitor', wt.RECT), ('work', wt.RECT), ('flags', wt.DWORD)]

    monitor_info = api(user, 'GetMonitorInfoW', wt.BOOL, wt.HANDLE, ct.POINTER(MonitorInfo))
    subclass = api(controls, 'SetWindowSubclass', wt.BOOL, wt.HWND, callback, uintptr, uintptr)
    remove = api(controls, 'RemoveWindowSubclass', wt.BOOL, wt.HWND, callback, uintptr)
    default = api(controls, 'DefSubclassProc', long_ptr, wt.HWND, wt.UINT, uintptr, long_ptr)

    root.update_idletasks()
    hwnd = ancestor(root.winfo_id(), 2)
    if not hwnd:
        return False

    @callback
    def procedure(handle, message, wparam, lparam, subclass_id, ref):
        if message == 0x0083:  # WM_NCCALCSIZE
            if wparam and zoomed(handle):
                info = MonitorInfo(size=ct.sizeof(MonitorInfo))
                if monitor_info(monitor(handle, 2), ct.byref(info)):
                    rect = ct.cast(lparam, ct.POINTER(wt.RECT))[0]
                    rect.left, rect.top = info.work.left, info.work.top
                    rect.right, rect.bottom = info.work.right, info.work.bottom
            return 0
        if message == 0x0084 and not zoomed(handle):  # WM_NCHITTEST
            x = ct.c_short(lparam & 0xffff).value
            y = ct.c_short((lparam >> 16) & 0xffff).value
            rect = wt.RECT()
            if window_rect(handle, ct.byref(rect)):
                edge = 6
                left, right = x < rect.left + edge, x >= rect.right - edge
                top, bottom = y < rect.top + edge, y >= rect.bottom - edge
                if top:
                    return 13 if left else 14 if right else 12
                if bottom:
                    return 16 if left else 17 if right else 15
                if left or right:
                    return 10 if left else 11
        if message == 0x0082:  # WM_NCDESTROY
            remove(handle, procedure, subclass_id)
        return default(handle, message, wparam, lparam)

    if not subclass(hwnd, procedure, 1, 0):
        return False
    root._caption_callback = procedure
    position(hwnd, None, 0, 0, 0, 0, 0x37)  # Recalcula a moldura sem mover a janela.

    try:
        dwm = ct.WinDLL('dwmapi')
        attribute = api(dwm, 'DwmSetWindowAttribute', ct.c_long, wt.HWND, wt.DWORD, ct.c_void_p, wt.DWORD)
        for key, value in ((33, 2), (34, 0xfffffffe)):
            data = wt.DWORD(value)
            attribute(hwnd, key, ct.byref(data), ct.sizeof(data))
    except (OSError, AttributeError):
        pass

    def drag(event):
        release()
        point = (event.x_root & 0xffff) | ((event.y_root & 0xffff) << 16)
        send(hwnd, 0x00A1, 2, point)
        return 'break'

    for widget in drag_widgets:
        widget.bind('<ButtonPress-1>', drag)
    return True
