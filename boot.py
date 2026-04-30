import time
import usb.device
from usb.device.cdc import CDCInterface

cdc = CDCInterface()
cdc.init(baudrate=115200, bits=8, parity="N", stop=1, timeout=0)  # zero timeout makes this non-blocking, suitable for os.dupterm()
usb.device.get().init(cdc, builtin_driver=True)
while not cdc.is_open():
    time.sleep_ms(100)


