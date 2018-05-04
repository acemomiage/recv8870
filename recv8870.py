#!/usr/bin/env python
#coding: utf-8

import time
import serial as ser
import multiprocessing as mp
import signal
import socket
import os
import sys
import shutil

DEV_PATH       = '/dev/usb-clamp'
SOCKET_PATH    = '/tmp/'
SOCKET_NAME    = 'pmeasure.sock'
SOCKET_TIMEOUT = 5
PID_FILE       = '/var/run/recv8870.pid'
QUEUE_SIZE     = 20
QUEUE_REDUCE   = 10
QUEUE_MAX_SIZE = QUEUE_SIZE + 10

class ReadFromSerial(object):
    def __init__(self):
        pass

    def start(self, queue, flag):
        try:
            s = ser.Serial(DEV_PATH,
                           19200,
                           timeout=10,
                           parity=ser.PARITY_EVEN,
                           rtscts=1)
            while True:
                # print("Queue Size:" + str(queue.qsize()))
                if queue.qsize() > QUEUE_SIZE:
                    queue = self.queue_reduce(queue)
                if flag.is_set():
                    break
                msg = s.readline()
                v   = str(msg.strip())[2:-2]
                queue.put(v)
        finally:
            s.close()

    def queue_reduce(self, queue):
        # print("In queue reduce")
        buf = []
        for i in range(queue.qsize()):
            buf.append(queue.get())
            # print(buf)
        for i in range(QUEUE_SIZE - QUEUE_REDUCE):
            queue.put(buf[i])
        return(queue)

class SendBackSocket(object):
    def __init__(self):
        pass

    def start(self, queue, flag):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(SOCKET_TIMEOUT)
        s.bind(SOCKET_PATH + SOCKET_NAME)
        shutil.chown(SOCKET_PATH + SOCKET_NAME, group='plugdev')
        os.chmod(SOCKET_PATH + SOCKET_NAME, 0o0664)
        s.listen(1)
        try:
            while True:
                try:
                    if flag.is_set():
                        break
                    conn, addr = s.accept()
                    # sys.stdout.write("Connected.\n")
                    msg = queue.get()
                    conn.send(msg.encode())
                    # sys.stdout.write("Disconnected\n")
                    conn.close()
                except OSError as emsg:
                    pass
        finally:
                s.close()
                os.remove(SOCKET_PATH + SOCKET_NAME)

def main_routine():
    flag = mp.Event()
    queue = mp.Queue(QUEUE_MAX_SIZE)
    
    read_p = ReadFromSerial()
    send_p = SendBackSocket()
    p01  = mp.Process(target=read_p.start, args=(queue, flag))
    p02  = mp.Process(target=send_p.start, args=(queue, flag))

    processes = [ p01, p02]

    for p in processes:
        p.start()

    def signalHandler(signal, handler):
        flag.set()

    signal.signal(signal.SIGINT,  signalHandler)
    signal.signal(signal.SIGTERM, signalHandler)

    while True:
        alive_flag = False
        for p in processes:
            if p.is_alive():
                alive_flag = True
                break
        if alive_flag:
            time.sleep(1)
            continue
        break
    os.remove(PID_FILE)

def daemonize():
    pid = os.fork()
    if pid > 0:  # parent process
        pid_file = open(PID_FILE, 'w')
        pid_file.write(str(pid)+"\n")
        pid_file.close()
        sys.exit()
    if pid == 0: # child process
        main_routine()
    
if __name__ == '__main__':
#    while True:
    daemonize()
    
