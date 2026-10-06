"""Native Windows 10+ owned cohorts, atomically assigned at process creation.

No breakaway flags, time limits, inherited job handles, PID-based termination,
or fallback to an unowned Popen. Job absence is a kernel observation, not a PID
or JSON inference. Only CreateProcess descendants are covered (not WMI launch).
"""
import ctypes as C
from ctypes import wintypes as W
import os
from pathlib import Path
import subprocess
import sys
import time

if sys.platform != 'win32':
    raise RuntimeError('Native Windows Job Objects required')

K = C.WinDLL('kernel32', use_last_error=True)
SIZE = C.c_size_t
LL = C.c_longlong
HANDLE = W.HANDLE


class Limits(C.Structure):
    _fields_ = [('process_time', LL), ('job_time', LL), ('flags', W.DWORD),
                ('min_working', SIZE), ('max_working', SIZE), ('active_limit', W.DWORD),
                ('affinity', SIZE), ('priority', W.DWORD), ('scheduling', W.DWORD)]


class IO(C.Structure):
    _fields_ = [(n, C.c_ulonglong) for n in ('reads', 'writes', 'other', 'read_bytes', 'write_bytes', 'other_bytes')]


class Extended(C.Structure):
    _fields_ = [('basic', Limits), ('io', IO), ('process_memory', SIZE),
                ('job_memory', SIZE), ('peak_process_memory', SIZE), ('peak_job_memory', SIZE)]


class Accounting(C.Structure):
    _fields_ = [('user_time', LL), ('kernel_time', LL), ('period_user', LL), ('period_kernel', LL),
                ('page_faults', W.DWORD), ('total', W.DWORD), ('active', W.DWORD), ('terminated', W.DWORD)]


class Startup(C.Structure):
    _fields_ = [('cb', W.DWORD), ('reserved', W.LPWSTR), ('desktop', W.LPWSTR), ('title', W.LPWSTR),
                ('x', W.DWORD), ('y', W.DWORD), ('xsize', W.DWORD), ('ysize', W.DWORD),
                ('xchars', W.DWORD), ('ychars', W.DWORD), ('fill', W.DWORD), ('flags', W.DWORD),
                ('show', W.WORD), ('reserved_size', W.WORD), ('reserved_pointer', C.c_void_p),
                ('stdin', HANDLE), ('stdout', HANDLE), ('stderr', HANDLE)]


class StartupEx(C.Structure):
    _fields_ = [('startup', Startup), ('attributes', C.c_void_p)]


class ProcessInfo(C.Structure):
    _fields_ = [('process', HANDLE), ('thread', HANDLE), ('pid', W.DWORD), ('tid', W.DWORD)]


def api(name, result, args):
    f = getattr(K, name); f.restype = result; f.argtypes = args
    return f


create_job = api('CreateJobObjectW', HANDLE, [C.c_void_p, W.LPCWSTR])
open_job = api('OpenJobObjectW', HANDLE, [W.DWORD, W.BOOL, W.LPCWSTR])
close = api('CloseHandle', W.BOOL, [HANDLE])
set_job = api('SetInformationJobObject', W.BOOL, [HANDLE, C.c_int, C.c_void_p, W.DWORD])
query_job = api('QueryInformationJobObject', W.BOOL, [HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p])
terminate_job = api('TerminateJobObject', W.BOOL, [HANDLE, W.UINT])
initialize = api('InitializeProcThreadAttributeList', W.BOOL, [C.c_void_p, W.DWORD, W.DWORD, C.POINTER(SIZE)])
update = api('UpdateProcThreadAttribute', W.BOOL, [C.c_void_p, W.DWORD, SIZE, C.c_void_p, SIZE, C.c_void_p, C.c_void_p])
delete = api('DeleteProcThreadAttributeList', None, [C.c_void_p])
create_process = api('CreateProcessW', W.BOOL, [W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p,
    W.BOOL, W.DWORD, C.c_void_p, W.LPCWSTR, C.POINTER(StartupEx), C.POINTER(ProcessInfo)])
resume_thread = api('ResumeThread', W.DWORD, [HANDLE])
wait = api('WaitForSingleObject', W.DWORD, [HANDLE, W.DWORD])
exit_code = api('GetExitCodeProcess', W.BOOL, [HANDLE, C.POINTER(W.DWORD)])
open_process = api('OpenProcess', HANDLE, [W.DWORD, W.BOOL, W.DWORD])
in_job = api('IsProcessInJob', W.BOOL, [HANDLE, HANDLE, C.POINTER(W.BOOL)])
process_times = api('GetProcessTimes', W.BOOL, [HANDLE, C.POINTER(W.FILETIME), C.POINTER(W.FILETIME),
    C.POINTER(W.FILETIME), C.POINTER(W.FILETIME)])
set_handle = api('SetHandleInformation', W.BOOL, [HANDLE, W.DWORD, W.DWORD])


def check(value):
    if not value: raise C.WinError(C.get_last_error())
    return value


def identity(pid, job_handle=None):
    h = check(open_process(0x1000, False, int(pid)))
    try:
        creation, ending, kernel, user = (W.FILETIME() for _ in range(4))
        check(process_times(h, C.byref(creation), C.byref(ending), C.byref(kernel), C.byref(user)))
        member = W.BOOL()
        if job_handle is not None: check(in_job(h, job_handle, C.byref(member)))
        return dict(pid=int(pid), creation_filetime=(creation.dwHighDateTime << 32) | creation.dwLowDateTime,
                    member_of_owned_job=bool(member.value) if job_handle is not None else None)
    finally: close(h)


class Job:
    def __init__(self, name, commit_limit_bytes=None, existing=False):
        if not name.startswith('Local\\ParallelBayes-'): raise ValueError('Owned job namespace required')
        self.name = name; self.handle = None; self.process = None
        self.handle = check(open_job(4, False, name) if existing else create_job(None, name))
        if not existing and C.get_last_error() == 183:
            self.close(); raise FileExistsError('Job name collision')
        try:
            check(set_handle(self.handle, 1, 0))
            if not existing:
                limits = Extended(); limits.basic.flags = 0x2000
                if commit_limit_bytes is not None:
                    if type(commit_limit_bytes) is not int or commit_limit_bytes < 1: raise ValueError('Positive commit limit required')
                    limits.basic.flags |= 0x200; limits.job_memory = commit_limit_bytes
                check(set_job(self.handle, 9, C.byref(limits), C.sizeof(limits)))
        except BaseException:
            self.close(); raise

    def launch_suspended(self, argv, cwd, stdout, stderr, environment=None):
        """JOB_LIST removes the unowned creation/assignment race.

        HANDLE_LIST inherits only NUL/stdout/stderr, never the job or host lock.
        Returned child has not executed user code; caller journals then resumes.
        """
        import msvcrt
        if self.process is not None: raise RuntimeError('One primary launch per owned job')
        length = SIZE(); initialize(None, 2, 0, C.byref(length))
        buffer = C.create_string_buffer(length.value)
        check(initialize(buffer, 2, 0, C.byref(length)))
        info = ProcessInfo()
        handles = []
        try:
            with open('NUL', 'rb') as stdin:
                handles = [msvcrt.get_osfhandle(f.fileno()) for f in (stdin, stdout, stderr)]
                for h in handles: check(set_handle(h, 1, 1))
                handle_list = (HANDLE * 3)(*handles)
                job_list = (HANDLE * 1)(self.handle)
                check(update(buffer, 0, 0x20002, handle_list, C.sizeof(handle_list), None, None))
                check(update(buffer, 0, 0x2000D, job_list, C.sizeof(job_list), None, None))
                startup = StartupEx(); startup.startup.cb = C.sizeof(startup)
                startup.startup.flags = 0x100; startup.startup.stdin, startup.startup.stdout, startup.startup.stderr = handles
                startup.attributes = C.cast(buffer, C.c_void_p)
                env = dict(os.environ if environment is None else environment)
                env_buffer = C.create_unicode_buffer('\0'.join(k+'='+str(v) for k,v in sorted(env.items(), key=lambda kv:kv[0].upper()))+'\0\0')
                command = C.create_unicode_buffer(subprocess.list2cmdline([str(a) for a in argv]))
                check(create_process(None, command, None, None, True,
                    0x00080000 | 0x00000400 | 0x00000004 | 0x08000000,
                    env_buffer, str(Path(cwd).resolve()), C.byref(startup), C.byref(info)))
                self.process = info
        finally:
            for h in handles: set_handle(h, 1, 0)
            delete(buffer)
        record = identity(info.pid, self.handle)
        if not record['member_of_owned_job']:
            self.terminate(); raise RuntimeError('Atomic job assignment failed')
        return record

    def resume(self):
        if resume_thread(self.process.thread) == 0xFFFFFFFF: raise C.WinError(C.get_last_error())
        close(self.process.thread); self.process.thread = None

    def poll(self):
        if wait(self.process.process, 0) == 258: return None
        result = W.DWORD(); check(exit_code(self.process.process, C.byref(result)))
        return result.value

    def observe(self):
        accounting = Accounting(); limits = Extended()
        check(query_job(self.handle, 1, C.byref(accounting), C.sizeof(accounting), None))
        check(query_job(self.handle, 9, C.byref(limits), C.sizeof(limits), None))
        size = 8192
        while True:
            buf = C.create_string_buffer(size)
            if query_job(self.handle, 3, buf, size, None): break
            if C.get_last_error() != 234: raise C.WinError(C.get_last_error())
            size *= 2
        count = W.DWORD.from_buffer(buf, 4).value
        pids = list((SIZE * count).from_buffer(buf, 8))
        members = []
        import psutil
        rss = 0
        for pid in pids:
            try:
                item = identity(pid, self.handle)
                if not item['member_of_owned_job']: raise RuntimeError('Job PID identity changed during observation')
                process = psutil.Process(pid)
                item.update(rss_bytes=process.memory_info().rss, command=process.cmdline(),
                            parent_pid=process.ppid())
                rss += item['rss_bytes']; members.append(item)
            except (psutil.NoSuchProcess, ProcessLookupError):
                continue
            except OSError as exc:
                if getattr(exc, 'winerror', None) == 87: continue
                raise
        return dict(job_name=self.name, active_processes=accounting.active,
                    total_processes=accounting.total, members=members, sampled_rss_bytes=rss,
                    job_cpu_seconds=(accounting.user_time+accounting.kernel_time)/10**7,
                    kernel_peak_job_commit_bytes=limits.peak_job_memory,
                    hard_job_commit_limit_bytes=limits.job_memory,
                    rss_scope='Sampled sum of resident pages, shared pages may count repeatedly; polling peak can miss spikes',
                    commit_scope='Kernel job commitment, distinct from RSS and CUDA device allocation')

    def terminate(self, code=0xE001):
        check(terminate_job(self.handle, code))

    def close(self):
        if self.process is not None:
            for name in ('thread', 'process'):
                h = getattr(self.process, name)
                if h: close(h); setattr(self.process, name, None)
        if self.handle:
            close(self.handle); self.handle = None

    def __enter__(self): return self
    def __exit__(self, *args): self.close()


def observe_named_job(name):
    """Unknown/access-denied is not death; observers never retain job handles."""
    try:
        with Job(name, existing=True) as job:
            return dict(state='present', **job.observe())
    except OSError as exc:
        if getattr(exc, 'winerror', None) == 2:
            return dict(state='absent', job_name=name,
                        proof='OpenJobObjectW ERROR_FILE_NOT_FOUND; owned noninherited last-handle kill policy')
        raise
