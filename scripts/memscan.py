# -*- coding: utf-8 -*-
"""read-only helpers for looking at the running game's memory (ctypes, no installs)"""
import ctypes, ctypes.wintypes as wt, re

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
PROCESS_QUERY_INFORMATION, PROCESS_VM_READ = 0x400, 0x10
MEM_COMMIT, PAGE_GUARD, PAGE_NOACCESS = 0x1000, 0x100, 0x01


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p), ('AllocationProtect', wt.DWORD),
                ('PartitionId', wt.WORD), ('RegionSize', ctypes.c_size_t), ('State', wt.DWORD), ('Protect', wt.DWORD), ('Type', wt.DWORD)]


class PE32(ctypes.Structure):
    _fields_ = [('dwSize', wt.DWORD), ('cntUsage', wt.DWORD), ('th32ProcessID', wt.DWORD), ('th32DefaultHeapID', ctypes.c_void_p),
                ('th32ModuleID', wt.DWORD), ('cntThreads', wt.DWORD), ('th32ParentProcessID', wt.DWORD), ('pcPriClassBase', wt.LONG),
                ('dwFlags', wt.DWORD), ('szExeFile', ctypes.c_wchar * 260)]


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Process32FirstW.argtypes = k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PE32)]
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.CloseHandle.argtypes = [wt.HANDLE]


def find_pid(prefix='planetarian'):
    snap = k32.CreateToolhelp32Snapshot(2, 0)
    pe = PE32(); pe.dwSize = ctypes.sizeof(PE32); pid = None
    ok = k32.Process32FirstW(snap, ctypes.byref(pe))
    while ok:
        if pe.szExeFile.lower().startswith(prefix):
            pid = pe.th32ProcessID; break
        ok = k32.Process32NextW(snap, ctypes.byref(pe))
    k32.CloseHandle(snap)
    return pid


class Proc:
    def __init__(self, pid):
        self.pid = pid
        self.h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not self.h:
            raise OSError('OpenProcess failed %d' % ctypes.get_last_error())

    def close(self):
        if self.h:
            k32.CloseHandle(self.h); self.h = None

    def alive(self):
        code = wt.DWORD()
        return bool(k32.GetExitCodeProcess(self.h, ctypes.byref(code))) and code.value == 259

    def regions(self, max_size=512 << 20):
        addr = 0; mbi = MBI()
        while k32.VirtualQueryEx(self.h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            base = mbi.BaseAddress or 0
            if mbi.State == MEM_COMMIT and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS)) and mbi.RegionSize <= max_size:
                yield base, mbi.RegionSize, mbi.Protect, mbi.Type
            addr = base + mbi.RegionSize
            if addr >= 0x7fffffffffff:
                break

    def read(self, addr, size):
        buf = ctypes.create_string_buffer(size); n = ctypes.c_size_t()
        if not k32.ReadProcessMemory(self.h, ctypes.c_void_p(addr), buf, size, ctypes.byref(n)):
            return b''
        return buf.raw[:n.value]

    def scan(self, pattern, writable_only=False):
        """pattern: compiled bytes regex. yields (addr, match, region_base, region_size, type)"""
        for base, size, prot, typ in self.regions():
            if writable_only and not (prot & 0xCC):
                continue
            data = self.read(base, size)
            if not data:
                continue
            for m in pattern.finditer(data):
                yield base + m.start(), m, base, size, typ


psapi = ctypes.WinDLL('psapi', use_last_error=True)
psapi.EnumProcessModules.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_void_p), wt.DWORD, ctypes.POINTER(wt.DWORD)]


def module_base(proc):
    """base address of the game's main exe module"""
    arr = (ctypes.c_void_p * 4)(); need = wt.DWORD()
    if not psapi.EnumProcessModules(proc.h, arr, ctypes.sizeof(arr), ctypes.byref(need)):
        raise OSError('EnumProcessModules failed %d' % ctypes.get_last_error())
    return arr[0]


def alloc_base(proc, addr):
    mbi = MBI()
    k32.VirtualQueryEx(proc.h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi))
    return mbi.AllocationBase


def region_of(proc, addr):
    """(base, size) of the committed region containing addr, or None"""
    mbi = MBI()
    if not k32.VirtualQueryEx(proc.h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)) or mbi.State != MEM_COMMIT:
        return None
    return (mbi.BaseAddress or 0), mbi.RegionSize
