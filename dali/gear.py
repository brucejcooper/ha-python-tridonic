from .dali_alliance_db import DaliAllianceProductDB
from .command import DaliCommand
from typing import NamedTuple

class Fade(NamedTuple):
    """
    Fade rate
    1: 358 steps/sec
    2. 253 steps/sec
    3. 179 steps/sec
    4. 127
    5. 89 
    6. 63
    7. 45 
    8. 32
    9. 22
    10. 16
    11. 11.2
    12. 7.9
    13. 5.6
    14. 4.0
    15. 2.8
    """

    """
    Fade Time
    0: < 0.7sec
    1: 0.7
    2. 1
    3. 1.4
    4. 2 
    5. 2.8
    6. 4
    7. 5.6
    8. 8
    9. 11.3 
    10. 16
    11. 22.6
    12. 32
    13. 45.2
    14. 64
    15. 90.5 seconds

    """
    time: int
    rate: int


class GearType:
    gear_types = {
        0: "fluorescent lamp",
        1: "emergency lighting",
        2: "HID lamp",
        3: "low voltage halogen lamp",
        4: "incandescent lamp dimmer",
        5: "dc-controlled dimmer",
        6: "LED lamp",
        7: "Relay",
        8: "Colour",
    }

    def __init__(self, code):
        self.code = code


    def __repr__(self) -> str:
        return "{}({})".format(GearType.gear_types.get(self.code, "Unknown"), self.code)


class GearInfo(NamedTuple):
    last_mem_bank: int
    gtin: str
    firmware_version: str
    serial: str
    hardware_version: str
    dali_version: int

    @property
    def unique_id(self):
        """DALI defines the combination of GTIN and serial number to be globally unique and immutable"""

        return "{}-{}".format(self.gtin, self.serial)


class DaliGear:
    def __init__(self, driver, address):
        self.driver = driver
        self.address = address
        self.device_type = None
        self.info = None
        self.level = None
        self.dalidb_record = None

    async def _send_cmd(self, cmd):
        return await self.driver.send_cmd(self.address, cmd)

    async def fetch_deviceinfo(self):
        dt = await self.driver.send_cmd(self.address, DaliCommand.QueryDeviceType)
        if dt is None:
            self.device_type = None
        else:
            self.device_type = GearType(dt)

        if self.device_type is not None:
            # Read information on the bank 0 of the device
            # See https://infosys.beckhoff.com/english.php?content=../content/1033/tcplclib_tc3_dali/6940982539.html&id= for details on the memory banks
            # Returns the content of the memory location stored in DTR0 that is located within the memory bank listed in DTR1
            buf = await self.driver.read_memory(self.address, 0, 2, 20)

            '''
            Example DALI data (from index 02 onwards. )
            LMB GTIN        VER  SER Major  SER MI HWV  DALI VERSION
            01 07ee4bb3b889 0707 00001a5838 920269 0300 08 

            GTIN can be looked up by screen scraping 

            '''
            g0 = await self._send_cmd(DaliCommand.QueryGroupsZeroToSeven)
            g1 = await self._send_cmd(DaliCommand.QueryGroupsEightToFifteen)
            self.groups = g1 << 8 | g0

            self.min_level = await self._send_cmd(DaliCommand.QueryMaxLevel)
            self.max_level = await self._send_cmd(DaliCommand.QueryMinLevel)

            
            gtin = int.from_bytes(buf[1:7], "big")

            self.info = GearInfo(
                last_mem_bank = buf[0],
                gtin = gtin,
                firmware_version = "{}.{}".format(buf[7],buf[8]),
                serial = "{:02x}{:02x}{:02x}{:02x}{:02x}.{:02x}{:02x}{:02x}".format(buf[13],buf[12],buf[11],buf[10],buf[9],buf[16],buf[15],buf[14]),
                hardware_version = "{}.{}".format(buf[17], buf[18]),
                dali_version = buf[19]
            )

            with DaliAllianceProductDB() as db:
                self.dalidb_record = await db.fetch(gtin)

            await self.get_level()            

    async def get_level(self):
        self.level = await self._send_cmd(DaliCommand.QueryActualLevel)
        return self.level

    async def on(self):
        # For the LED ballasts I'm using, Sending the ON command doesn't seem to work.  Instead, we recall the last active level (could also be recall Max level)
        await self._send_cmd(DaliCommand.GoToLastActiveLevel)
        self.level = await self.get_level()

    async def max(self):
        # For the LED ballasts I'm using, Sending the ON command doesn't seem to work.  Instead, we recall the last active level (could also be recall Max level)
        await self._send_cmd(DaliCommand.RecallMaxLevel)
        self.level = await self.get_level()

    async def min(self):
        # For the LED ballasts I'm using, Sending the ON command doesn't seem to work.  Instead, we recall the last active level (could also be recall Max level)
        await self._send_cmd(DaliCommand.RecallMinLevel)
        self.level = await self.get_level()


    async def query_fade(self):
        fade_and_rate =  await self._send_cmd(DaliCommand.QueryFadeTimeFadeRate)
        return Fade(time = fade_and_rate >> 4, rate = fade_and_rate & 0x0F)


    async def off(self):
        await self._send_cmd(DaliCommand.Off)
        self.level = 0 # Or so we can assume

    async def brighten(self):
        await self._send_cmd(DaliCommand.Up)
        self.level = await self.get_level()

    async def dim(self):
        await self._send_cmd(DaliCommand.Down)
        self.level = await self.get_level()

    async def query_power_on_level(self):
        return await self._send_cmd(DaliCommand.QueryPowerOnLevel)

    async def set_power_on_level(self, level):
        await self.driver.send_special_cmd(DaliCommand.SetDTR0, level)
        # Command must be sent twice within 100ms.
        await self._send_cmd(DaliCommand.SetPowerOnLevel)
        await self._send_cmd(DaliCommand.SetPowerOnLevel)


    async def toggle(self):
        level = await self.get_level()
        if level == 0:
            await self.on()
        else:
            await self.off()


    def __repr__(self):
        return "DaliDevice({} ({}) Lvl {}, {} {} Groups {:016b})".format(self.address, self.device_type, self.level, self.info, self.dalidb_record, self.groups)
