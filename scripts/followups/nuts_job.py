"""Completion messages and retained process handles for the existing owned Job.

Native Windows only. Missing messages are not evidence that a limit was not
exceeded. Retained handles, rather than reusable PID values, bind exit codes.
Reference: Microsoft JOBOBJECT_ASSOCIATE_COMPLETION_PORT documentation.
"""
import ctypes as C
from ctypes import wintypes as W
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
import job_objects as native

class Association(C.Structure):
    _fields_=[('key',C.c_void_p),('port',W.HANDLE)]

class Memory(C.Structure):
    _fields_=[('cb',W.DWORD),('faults',W.DWORD)]+[(n,C.c_size_t) for n in (
        'peak_working','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private')]

create_port=native.api('CreateIoCompletionPort',W.HANDLE,[W.HANDLE,W.HANDLE,C.c_size_t,W.DWORD])
get_packet=native.api('GetQueuedCompletionStatus',W.BOOL,[W.HANDLE,C.POINTER(W.DWORD),C.POINTER(C.c_size_t),C.POINTER(C.c_void_p),W.DWORD])
psapi=C.WinDLL('psapi',use_last_error=True)
get_memory=psapi.GetProcessMemoryInfo
get_memory.argtypes=[W.HANDLE,C.POINTER(Memory),W.DWORD];get_memory.restype=W.BOOL
MESSAGES={1:'end_of_job_time',2:'end_of_process_time',3:'active_process_limit',4:'active_process_zero',
    6:'new_process',7:'exit_process',8:'abnormal_exit_process',9:'process_memory_limit',10:'job_memory_limit',
    11:'notification_limit',12:'job_cycle_time_limit',13:'silo_terminated'}

def handle_identity(handle):
    creation,ending,kernel,user=(W.FILETIME() for _ in range(4))
    native.check(native.process_times(handle,C.byref(creation),C.byref(ending),C.byref(kernel),C.byref(user)))
    return (creation.dwHighDateTime<<32)|creation.dwLowDateTime

class ObservedJob(native.Job):
    def __init__(self,name,commit_limit_bytes):
        self.port=None;self.retained={};self.capture_errors=[]
        super().__init__(name,commit_limit_bytes=commit_limit_bytes)
        try:
            self.port=native.check(create_port(W.HANDLE(-1),None,0,1))
            native.check(native.set_handle(self.port,1,0))
            association=Association(1,self.port)
            native.check(native.set_job(self.handle,7,C.byref(association),C.sizeof(association)))
        except BaseException:
            self.close();raise

    def launch_suspended(self,*args,**kwargs):
        primary=super().launch_suspended(*args,**kwargs)
        self.retain(primary['pid'])
        return primary

    def retain(self,pid):
        handle=native.open_process(0x101410,False,pid)
        if not handle:
            self.capture_errors.append(dict(pid=pid,error=C.get_last_error(),stage='open_handle'));return
        try:
            member=W.BOOL();native.check(native.in_job(handle,self.handle,C.byref(member)))
            if not member.value:
                self.capture_errors.append(dict(pid=pid,error='No longer an owned Job member'));return
            creation=handle_identity(handle);key=(pid,creation)
            if key not in self.retained:
                native.check(native.set_handle(handle,1,0));self.retained[key]=handle;handle=None
        finally:
            if handle:native.close(handle)

    def messages(self):
        result=[]
        for _ in range(10000):
            number=W.DWORD();key=C.c_size_t();value=C.c_void_p()
            ok=get_packet(self.port,C.byref(number),C.byref(key),C.byref(value),0)
            if not ok:
                error=C.get_last_error()
                if error==258 and value.value is None:break
                raise C.WinError(error)
            if key.value!=1:raise RuntimeError('Unknown Job completion key')
            result.append(dict(message=number.value,name=MESSAGES.get(number.value,'unknown'),
                message_value=value.value,observed_ns=time.time_ns(),delivery_guaranteed=False))
            if number.value==6 and value.value:self.retain(int(value.value))
        return result

    def observe(self):
        value=super().observe();messages=self.messages()
        for member in value['members']:self.retain(member['pid'])
        processes=[]
        for (pid,creation),handle in self.retained.items():
            item=dict(pid=pid,creation_filetime=creation,exit_code=None,private_bytes=None)
            state=native.wait(handle,0)
            if state==0:
                code=W.DWORD();native.check(native.exit_code(handle,C.byref(code)))
                item.update(state='exited',exit_code=code.value)
            elif state==258:
                item['state']='running';memory=Memory();memory.cb=C.sizeof(memory)
                if get_memory(handle,C.byref(memory),C.sizeof(memory)):
                    item.update(private_bytes=memory.private,working_set_bytes=memory.working,
                        peak_working_set_bytes=memory.peak_working,peak_pagefile_bytes=memory.peak_pagefile)
                else:item['memory_error']=C.get_last_error()
            else:raise C.WinError(C.get_last_error())
            processes.append(item)
        value.update(completion_messages=messages,retained_process_handles=processes,
            process_capture_errors=self.capture_errors.copy(),
            private_commit_scope='PROCESS_MEMORY_COUNTERS_EX.PrivateUsage on retained owned process handles; distinct from RSS and Job peak commitment',
            exit_code_scope='Only handles captured while owned; fast unseen process exit codes may be unavailable')
        self.capture_errors.clear();return value

    def close(self):
        super().close()
        for handle in self.retained.values():native.close(handle)
        self.retained.clear()
        if self.port:native.close(self.port);self.port=None
