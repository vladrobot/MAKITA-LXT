from machine import Pin
import array, time
from onewireM import MAKITA
import binascii

ARDUINO_OBI_VERSION_MAJOR = 0 #Major version number (X.x.x)
ARDUINO_OBI_VERSION_MINOR = 2 #Minor version number (x.X.x)
ARDUINO_OBI_VERSION_PATCH = 1 #Patch version number (x.x.X)

machine.freq(125000000)
makita = MAKITA(0, 1000000, 21)
en = Pin(20, Pin.OUT)
en.value(1)


def cmd_and_read_33(cmd, cmd_len, rsp_len):
    rsp = []
    makita.reset()
    makita.send(0x33)

    for i in range(8):
        time.sleep(0.00009)
        rsp.append(makita.read())
    
    for i in range(cmd_len):
        time.sleep(0.00009)
        makita.send(cmd[i])

    for i in range(8,rsp_len):
        time.sleep(0.00009)
        rsp.append(makita.read())
    return rsp

def cmd_and_read_cc(cmd, cmd_len, rsp_len):
    rsp = []
    makita.reset()
    makita.send(0xcc)

    for i in range(cmd_len):
        time.sleep(0.00009)
        makita.send(cmd[i])
        
    for i in range(rsp_len):
        time.sleep(0.00009)
        rsp.append(makita.read())
    return rsp

def send_usb(rsp, rsp_len):
    for i in range(rsp_len):
        #print("send , rsp_len", rsp[i].to_bytes(1,"big"), rsp_len)
        cdc.write(rsp[i].to_bytes(1,"big"))
    

def read_usb():
    data = []
    rsp = []
    RX_BUF = []
    rb = cdc.read(1)
    if rb == None:
        return
    RX_BUF.append(rb[0])
    while rb != None:
        rb = cdc.read(1)
        if rb != None:
            RX_BUF.append(rb[0])
    #print("rx_buf",RX_BUF)
    RX_BUF = bytes(RX_BUF)
    if len(RX_BUF) >= 4:
        start = RX_BUF[0]
        if start == 0x01:
            len_cmd = RX_BUF[1]
            rsp_len = RX_BUF[2]
            cmd = RX_BUF[3];
            if len_cmd > 0:
                #print(RX_BUF.hex())
                for i in range(len_cmd):
                    data.append(RX_BUF[i+4])
                #print("data",data)
        else:
            return

        if cmd != 0x01:
            en.value(0)
            time.sleep(0.4)
   
        if cmd == 0x01:
            rsp.append(0x01)
            rsp.append(ARDUINO_OBI_VERSION_MAJOR)
            rsp.append(ARDUINO_OBI_VERSION_MINOR)
            rsp.append(ARDUINO_OBI_VERSION_PATCH)
        elif cmd == 0x31:
            makita.reset()
            makita.send(0xcc)
            time.sleep(0.00009)
            makita.send(0x99)
            time.sleep(0.00009)
            makita.reset()
            makita.send(0x31)
            time.sleep(0.00009)
            rsp.append(makita.read())
            time.sleep(0.00009)
            rsp.append(makita.read())
            rsp.reverse()
        elif cmd == 0x32:
            makita.reset()
            makita.send(0xcc)
            time.sleep(0.00009)
            makita.send(0x99)
            time.sleep(0.0004)
            makita.reset()
            makita.write(0x32)
            time.sleep(0.00009)
            rsp.append(makita.read())
            time.sleep(0.00009)
            rsp.append(makita.read())
            rsp.reverse()
            time.sleep(0.00009)
        elif cmd == 0x33:
            rsp = cmd_and_read_33(data, len_cmd, rsp_len)
        elif cmd == 0xCC:
            rsp = cmd_and_read_cc(data, len_cmd, rsp_len)
        else:
            rsp_len = 0
        rsp.insert(0,cmd)
        rsp.insert(1,rsp_len)
        #print(bytearray(rsp).hex())
        send_usb(rsp, rsp_len+2)
        en.value(1)

while True:
    read_usb()
    time.sleep(0.01)