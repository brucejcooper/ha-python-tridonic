
import asyncio
import hid
import struct
import threading
from .driver import DaliDriver
from .command import DaliCommand, FramingException

class TridonicDali(DaliDriver):

    def __init__(self, evt_loop = None) -> None:
        DaliDriver.__init__(self)
        self.next_sequence = 1
        self.hid = None
        self.message_directions = dict()
        self.message_directions[0x11] = "external"
        self.message_directions[0x12] = "received"
        self.message_directions[0x13] = "sent"

        self.message_types = dict()
        self.message_types[0x71] = "no response"
        self.message_types[0x72] = "response"
        self.message_types[0x73] = "tx complete"
        self.message_types[0x74] = "broadcast received"
        self.message_types[0x77] = "framing error"

        self.outstanding_commands = dict()

        if evt_loop is None:
            self.evt_loop = asyncio.get_event_loop()
        else:
            self.evt_loop = evt_loop

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def open(self):
        vendor = 0x17b5
        product = 0x0020
        self.hid =  hid.Device(vendor, product)
        self.read_loop_running = True
        self.read_thread = threading.Thread(target = self.read_loop, daemon=True)
        self.read_thread.start()

    def message_received(self, args):
        (dr, ty, ad, cm, sn) = args

        processed = False
        if dr == 0x12:
            if sn != 0:
                awaitable = self.outstanding_commands[sn]
                if awaitable is not None:
                    if ty == 0x72: # Completed
                        awaitable.resolve(cm)
                        del self.outstanding_commands[sn]

                        processed = True
                    elif ty == 0x71: # No Reponse
                        awaitable.resolve(None)
                        del self.outstanding_commands[sn]
                        processed = True
                    elif ty == 0x77:
                        awaitable.resolve(FramingException("Framing Error"))
                        processed = True
                    elif ty == 0x73: # Transmit completed
                        processed = True # Ignore tx complete for commands that we initiated.
            elif ty == 0x71:
                self.last_command.resolve(None)
                processed = True
        
        if not processed:
            print("{} {} [{:02x}] cmd {} seq {}".format(
                self.message_directions.get(dr, dr), 
                self.message_types.get(ty, "{:02x}".format(ty)), 
                ad, 
                DaliCommand.cmd_names.get(cm, "0x{:02x}".format(cm)), 
                sn))

    def read_loop(self):
        while self.read_loop_running:
            ret = self.receive(1000)
            if ret is not None:
                self.evt_loop.call_soon_threadsafe(self.message_received, ret)

    def close(self):
        self.read_loop_running = False
        self.hid.close()  # This will cause any active call to read to throw an exception.
        if self.read_thread is not None:
            self.read_thread.join() # This could wait up to 100ms due to the timeout nature of the reading thread.
        self.hid = None


    def get_seq(self):
        newseq = self.next_sequence
        self.next_sequence = self.next_sequence + 1  # Note: Not thread safe
        if self.next_sequence > 255:
            self.next_sequence = 1 # Sequence 0 is reserved for external entities
        return newseq

    async def _send(self, cmd: int, type=DaliCommand.TYPE_16BIT, repeat=1):
        """Data expected by DALI USB:
        dr sn rp ty ?? ec ad cm .. .. .. .. .. .. .. ..
        12 1d 00 03 00 00 ff 08 00 00 00 00 00 00 00 00

        dr: direction
            0x12 = USB side
        rp: 0x20 for repeat twice, 0x00 otherwise.
        sn: seqnum
        ty: type
            0x03 = 16bit
            0x04 = 24bit
            0x06 = DA24 Conf (???)
        ec: ecommand (first byte for 24 bit ones)
        ad: address
        cm: command


        example command for START QUIESCENT Command
        12 01 20 06 00 ff fe 1d 00 00 00 00 00 00 00 00...
        """

        seq = self.get_seq()
        data = bytearray(64) # Transmitted packets are 64 bytes wide, but most of them (all but the first 8) are 0x00
        data[0] = 0x12 # USB side command
        data[1] = seq
        if repeat == 2:
            data[2] = 0x20
        if type == DaliCommand.TYPE_16BIT:
            data[3] = 0x03 # 16 bit
        elif type == DaliCommand.TYPE_24BIT:
            data[3] = 0x04 # 16 bit
        elif type == DaliCommand.TYPE_DA24CONF:
            data[3] = 0x06 # 16 bit
        else:
            raise Exception("Illegal type")
        data[5] = (cmd >> 16) & 0xFF
        data[6] = (cmd >> 8) & 0xFF
        data[7] = cmd & 0xFF
        # print("SND {}".format(bytes(data)))

        if self.hid is None:
            raise Exception("Device not open")
        self.hid.write(bytes(data))

        awaitable = DaliCommand(seq, data, type)
        self.outstanding_commands[awaitable.seq] = awaitable
        self.last_command = awaitable
        return await awaitable.wait()



    async def read_memory(self, address, bank, offset, num):
        await self.send_special_cmd(DaliCommand.SetDTR1, bank)  # Set memory bank
        await self.send_special_cmd(DaliCommand.SetDTR0, offset)  # Set location 

        buf = bytearray()

        for i in range(num):
            b =  await self.send_cmd(address, DaliCommand.ReadMemoryLocation)
            if b is None:
                raise Exception("got no response when querying memory")
            buf.append(b)
        return bytes(buf)



    def receive(self, timeout=None):
        if self.hid is None:
            raise Exception("Device not open")
        try:
            data = self.hid.read(16, timeout)
        except Exception as ex:
            print("EXCEPTION READING: ", ex)
            return None
        if data is None or len(data) == 0:
            return None

        """Raw data received from DALI USB:
        dr ty ?? ec ad cm st st sn .. .. .. .. .. .. ..
        11 73 00 00 ff 93 ff ff 00 00 00 00 00 00 00 00

        dr: direction
            0x11 = DALI side
            0x12 = USB side
        ty: type
            0x71 = transfer no response
            0x72 = transfer response
            0x73 = transfer complete
            0x74 = broadcast received (?)
            0x76 = ?
            0x77 = framing error
        ec: ecommand
        ad: address
        cm: command
            also serves as response code for 72
        st: status
            internal status code, value unknown
        sn: seqnum
        """

        dr = data[0]
        ty = data[1]
        ec = data[3]
        ad = data[4]
        cm = data[5]
        st = struct.unpack('H', data[6:8])[0]
        sn = data[8]
        return (dr, ty, ad, cm, sn)
