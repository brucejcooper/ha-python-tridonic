from .gear import DaliGear
from .command import DaliCommand, DaliException, FramingException
from typing import List, Awaitable
import asyncio


class ClashException(DaliException):
    pass


class SearchAddressSender:
    """When transmitting new values for search address, only transmit the ones that change"""
    
    def __init__(self, drv):
        self.drv = drv
        self.lastH = None
        self.lastM = None
        self.lastL = None

    async def send(self, addr):
        l = addr & 0xFF
        m = (addr >> 8) & 0xFF
        h = (addr >> 16) & 0xFF

        if l != self.lastL:
            await self.drv.send_special_cmd(DaliCommand.SearchAddrL, l)
            self.lastL = l
        if m != self.lastM:
            await self.drv.send_special_cmd(DaliCommand.SearchAddrM, m)
            self.lastM = m
        if h != self.lastH:
            await self.drv.send_special_cmd(DaliCommand.SearchAddrH, h)
            self.lastH = h







class DaliDriver:
    def __init__(self) -> None:
        pass

    async def _send(self, data: int, type=DaliCommand.TYPE_16BIT, repeat=1):
        raise Exception("Not Implemented")

    async def send_direct_arc_power(self, address: int, level):
        return await self._send((address << 9) | level)

    async def send_cmd(self, address: int, cmd: int, repeat=1):
        return await self._send((address << 9 ) | (0x01 << 8) | cmd, repeat=repeat)

    async def send_special_cmd(self, special_cmd: int, param: int = 0, repeat=1):
        return await self._send((special_cmd << 8) | param, repeat=repeat)
    

    async def broadcast(self, cmd, repeat=1):
        await self._send(0xFF << 8 | cmd, repeat=repeat)

    async def start_quiescent(self):
        await self._send(0xFFFE1D, type=DaliCommand.TYPE_DA24CONF, repeat=2)

    async def stop_quiescent(self):
        await self._send(0xFFFE1E, type=DaliCommand.TYPE_DA24CONF, repeat=2)


    async def scan_for_gear(self) -> Awaitable[List[DaliGear]]:
        devices = []
        for address in range(0,64):
            gear = DaliGear(self, address)
            await gear.fetch_deviceinfo()

            if gear.device_type:
                devices.append(gear)
        return devices



    async def compare(self, search, address_sender):
        """
        Compares the supplied search value with items on the bus. 
        Returns: 
          int: how many devices (0, 1, or 2 to represent more than 1) devices with the search address equal 
               to or lower than the supplied value
        """
        # print("Compare 0x{:06x}".format(search))
        await address_sender.send(search)
        try:
            found = await self.send_special_cmd(DaliCommand.Compare)
            if found == 0xFF:
                # Precisely one device is equal to or less than high
                return 1
            elif found == None:
                # No devices found under
                return 0
            else:
                raise Exception("Illegal Response from search command")

        except FramingException as ex:
            # This means there are multiple devices equal or under high
            return 2


    async def search_for_device(self, start=0):
        """Performs a binary search of the address search space, finding the participating gear with
           the lowest search address
        """
        low = start
        high = 0xFFFFFF

        sender = SearchAddressSender(self)
        while True:
            mid = int((low+high)/2) # Start in the middle
            res = await self.compare(mid, sender)

            if low == high:
                if res == 1:
                    return mid
                elif res == 2:
                    # There is a search address clash.
                    raise ClashException()
                else:
                    # No devices found at all.
                    return None

            if res == 0:
                # zero devices below or equal to mid
                low = mid+1
            else:
                # 1 or more devices below or equal to mid, but we don't know which
                high = mid

        



    async def commission(self):
        # Terminate any outstanding initialise.
        await self.send_special_cmd(DaliCommand.Terminate, 0)
        try:

            # TODO start quiescent mode (24 bit command.)

            # Put devices in initialisation mode. 
            await self.send_special_cmd(DaliCommand.Initialise, repeat=2)


            # Clear out any existing short addresses
            await self.send_special_cmd(DaliCommand.SetDTR0, 0xFF)
            await self.broadcast(DaliCommand.SetShortAddress, repeat=2)

            # Reset operating mode
            await self.send_special_cmd(DaliCommand.SetDTR0, 128)
            await self.broadcast(DaliCommand.SetOperatingMode, repeat=2)

            # Remove devices from groups
            for group in range(16):
                await self.broadcast(DaliCommand.RemoveFromGroup | group, repeat=2)

            # Randomise the search addresses for all devices. 
            await self.send_special_cmd(DaliCommand.Randomise, repeat=2)
            await asyncio.sleep(0.1)  

            
            finished = False
            search_floor = 0

            available_short_addresses = list(range(64))

            while not finished:
                # We know that there are no more devices less than search floor, so pass that in as a starting point.
                # TODO strictly, we could make this faster, as we know which segments of the search have stuff in and which don't.
                try:
                    found = await self.search_for_device(search_floor)

                    if found:
                        short_addr = available_short_addresses.pop(0)
                        print("Found device at search address {:06x}. Assigning address {}".format(found, short_addr))
                        shifted = (short_addr << 1) | 0x01
                        await self.send_special_cmd(DaliCommand.ProgramShortAddress, shifted)
                        queried_short_addr = await self.send_special_cmd(DaliCommand.QueryShortAddress)

                        if queried_short_addr == shifted:
                            # Good, the device took the address
                            await self.send_special_cmd(DaliCommand.Withdraw)
                        else:
                            raise DaliException("Short Address did not stick (Returned {:02x} instead of {:02x})".format(queried_short_addr, shifted))
                        search_floor = found + 1
                    else:
                        # print("No more devices found")
                        finished = True
                except ClashException:
                    # Two devices managed to settle on the same search address.  Re-randomise any gear that hasn't already been allocated
                    search_floor = 0
        finally:
            # Make sure we've terminated our commission process
            await self.send_special_cmd(DaliCommand.Terminate, 0)
                



