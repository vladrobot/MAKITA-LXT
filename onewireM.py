#convert C code https://github.com/raspberrypi/pico-examples/blob/master/pio/onewire/onewire_library/onewire_library.c
#crc8 from https://github.com/robert-hh/Onewire_DS18X20/blob/master/onewire.py
from machine import Pin
import rp2, array

@rp2.asm_pio(sideset_init=(rp2.PIO.OUT_HIGH,), set_init=(rp2.PIO.OUT_HIGH,), side_pindir=True, in_shiftdir=rp2.PIO.SHIFT_RIGHT, out_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, autopull=True)
def Makita1WPIO():
    set(pins,0)         .side(0)
    set(x,23)           .side(1) [4] #5
    label("loop_a")
    nop()               .side(1) [6] #8
    nop()                        [7] #8
    nop()                        [7] #8 
    jmp(x_dec,"loop_a")          [7] #8 24x31=744 + 5 = 749 (750)
    set(x,7)            .side(0) [6] #7
    label("loop_b")
    jmp(x_dec,"loop_b")          [7] #8x8=64 + 7 = 71 (70)
    mov(isr,pins)                    #1
    push()                       [7] #8
    set(x,24)                    [7] #8
    label("loop_c")
    nop()                        [7] #8
    nop()                        [7] #8
    nop()                        [7] #8
    jmp(x_dec,"loop_c")          [7] #8 32x25=800 + 7 + 71 + 1 + 1 + 8 + 8  =  (889)
    wrap_target()
    label("start")                   
    out(y,8)                         # first byte Delay for send 1 or read
    label("fetch_bit")
    out(x,1)            .side(0)     #1 
    jmp(not_x, "send_0").side(1) [3] #4
    # send bit 1 and read bit
    nop()                        [5] #6
    mov(x,y)            .side(0) [7] #8 4+6+1 = 11 
    in_(pins,1)                  [5] #6
    label("loop_e")
    nop()                        [6] #7 
    jmp(x_dec,"loop_e")          [6] #7 14x8=112 + 8 + 6 = 126 (127 or 184) 14x12=168 + 8 + 6 = 182
    jmp(not_osre,"fetch_bit")        
    jmp("start")
    # send bit 0
    label("send_0")
    set(x,5)            .side(1) [2] #3
    label("loop_d")
    nop()                        [7] #8
    jmp(x_dec,"loop_d")          [7] #8 16x6=96 + 3 + 4 = 103 (104)
    in_(null,1)         .side(0) [3] #5
    set(x,3)                         #1
    label("loop_f")
    jmp(x_dec,"loop_f")          [6] #7 7x4=28 + 5 + 1 = 34
    jmp(not_osre,"fetch_bit")
    wrap() # Reset - (750us; Wait(read) - 70; Pause - 410),  HI - 11us, LOW - 104us, Slot - 138us

class MAKITA:
    CMD_SEARCHROM = 0xf0
    CMD_READROM = 0x33
    CMD_MATCHROM = 0x55
    CMD_SKIPROM = 0xcc

    def __init__(self, sm_id, count_freq, pin, bits_per_word = 8):
        self._sm = rp2.StateMachine(sm_id, Makita1WPIO, count_freq, \
                    sideset_base=Pin(pin), in_base=Pin(pin), set_base=Pin(pin),\
                    push_thresh=bits_per_word, pull_thresh=bits_per_word)
        self.sm_id = sm_id
        self.count_freq = count_freq
        self.pin = pin
        self.bits_per_word = bits_per_word
        self.crctab1 = (b"\x00\x5E\xBC\xE2\x61\x3F\xDD\x83"
                        b"\xC2\x9C\x7E\x20\xA3\xFD\x1F\x41")
        self.crctab2 = (b"\x00\x9D\x23\xBE\x46\xDB\x65\xF8"
                        b"\x8C\x11\xAF\x32\xCA\x57\xE9\x74")

    
    def send(self, data):
        #self._sm.put(bytes([data]))
        self._sm.put(bytes([0x07,data]))
        while self._sm.tx_fifo() !=0:
            pass
        self._sm.get()
       
    def crc8(self, data): # Compute CRC, based on tables
        crc = 0
        for i in range(len(data)):
           crc ^= data[i] ## just re-using crc as intermediate
           crc = (self.crctab1[crc & 0x0f] ^
                  self.crctab2[(crc >> 4) & 0x0f])
        return crc
    
    def checksum(self, data):
        db = list(data.to_bytes(8,"big"))
        crc = db.pop(0)
        db.reverse()
        print(db)
        if self.crc8(db) == crc:
            return True
        return False
    
    def reset(self):
        if self._sm.active() != True:
            self._sm.active(1)
        else:
            self._sm.restart()
        if (self._sm.get() & 1) == 0:
            return True
        return False
    
    def read(self):
        self._sm.put(bytes([0x0B,0xFF]))
        #self._sm.put(bytes([0xFF]))
        while self._sm.tx_fifo() !=0:
            pass
        return self._sm.get() >> 24
    
    def romsearch(self, command, romcodes=[],maxdevs=0):
        romcode = 0
        next_branch_point = -1
        num_found = 0
        finished = False
        if self._sm.active() == True:
            self._sm.active(0)
        self.__init__(self.sm_id, self.count_freq, self.pin, 1) # set driver to 1-bit mode
        
        while (finished == False) and (maxdevs == 0 or num_found < maxdevs):
            finished = True
            branch_point = next_branch_point
            if self.reset() != True:
                num_found = 0     # no slaves present
                finished = true
                break
            for i in range(8):  # send search command as single bits
                self.send(command >> i)
            
            for index in range(64): #determine romcode bits 0..63 (see ref)
                a = self.read()
                b = self.read()
                if (a == 0) and (b == 0): # (a, b) = (0, 0)
                    if index == branch_point:
                        self.send(1)
                        romcode |= (1 << index)
                    else:
                        if ((index > branch_point) or (romcode & (1 << index)) == 0):
                            self.send(0)
                            finished = false
                            romcode &= ~(1 << index)
                            next_branch_point = index
                        else:                 # index < branch_point or romcode[index] = 1
                            self.send(1)
                elif (a != 0) and (b != 0):  # (a, b) = (1, 1) error (e.g. device disconnected)
                    num_found = -2             # function will return -1
                    finished = true
                    break                     # terminate for loop
                else:
                    if a == 0: # (a, b) = (0, 1) or (1, 0)
                        self.send(0)
                        romcode &= ~(1 << index)
                    else:
                        self.send(1)
                        romcode |= (1 << index)
            # end of for loop
            if romcode != 0:
                #romcodes[num_found] = romcode  #store the romcode
                romcodes.append(romcode)
            num_found += 1
        # end of while loop
        if self._sm.active() == True:
            self._sm.active(0)
        self.__init__(self.sm_id, self.count_freq, self.pin, 8) # restore 8-bit mode
        return num_found, romcodes
