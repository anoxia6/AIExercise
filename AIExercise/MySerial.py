import serial
import time
from threading import Lock

class Myserial:
    def __init__(self, portfile):
        self.res = None
        self.serial = serial.Serial(portfile, int(9600), timeout=0.004, parity=serial.PARITY_NONE, stopbits=1)
        time.sleep(1)

    def write(self, data):
        lock = Lock()
        lock.acquire()
        try:
            self.serial.write(str(data).encode())
            # print(data)
            self.serial.flush()
            self.res = self.serial.readline()
            for i in range(10):
                if(self.res[-2:] == b'\r\n'):
                    break;
                else:
                    self.res = self.res + self.serial.readline()
            # print(self.res)
            self.serial.flush()
            
        except ZeroDivisionError as e:
            print('except:', e)
        finally:
            # print("serial.write_finally\n")
            lock.release()
            pass

    def read(self):
        return self.res
    
    def close(self):
        self.serial.close()
    
    def open(self):
        self.serial.open()
        
if __name__ == '__main__':
    serial = Myserial('/dev/ttyS9')
    while True:
        serial.write('2')
        print(serial.read())
        time.sleep(1)