import asyncio


class DaliException(Exception):
    """Dali Exception"""

class FramingException(DaliException):
    """Thrown when waiting for a response and a framing error occurrs"""


class DaliCommand:
    Off = 0x00
    Up = 0x01
    Down = 0x02
    StepUp = 0x03
    StepDown = 0x04
    RecallMaxLevel = 0x05
    RecallMinLevel = 0x06
    StepDownAndOff = 0x07
    OnAndStepUp = 0x08
    EnableDAPCSequence = 0x09
    GoToLastActiveLevel = 0x0a
    ContinuousUp = 0x0b
    ContinuousDown = 0x0c
    GoToScene = 0x10
    Reset = 0x20
    StoreActualLevelInDTR0 = 0x21
    SavePersistentVariables = 0x22
    SetOperatingMode = 0x23
    ResetMemoryBank = 0x24
    IdentifyDevice = 0x25
    SetMaxLevel = 0x2a
    SetMinLevel = 0x2b
    SetSystemFailureLevel = 0x2c
    SetPowerOnLevel = 0x2d
    SetFadeTime = 0x2e
    SetFadeRate = 0x2f
    SetExtendedFadeTime = 0x30
    SetScene = 0x40
    RemoveFromScene = 0x50
    AddToGroup = 0x60
    RemoveFromGroup = 0x70
    SetShortAddress = 0x80
    EnableWriteMemory = 0x81
    QueryStatus = 0x90
    QueryControlGearPresent = 0x91
    QueryLampFailure = 0x92
    QueryLampPowerOn = 0x93
    QueryLimitError = 0x94
    QueryResetState = 0x95
    QueryMissingShortAddress = 0x96
    QueryVersionNumber = 0x97
    QueryContentDTR0 = 0x98
    QueryDeviceType = 0x99
    QueryPhysicalMinimum = 0x9a
    QueryPowerFailure = 0x9b
    QueryContentDTR1 = 0x9c
    QueryContentDTR2 = 0x9d
    QueryOperatingMode = 0x9e
    QueryLightSourceType = 0x9f
    QueryActualLevel = 0xa0
    QueryMaxLevel = 0xa1
    QueryMinLevel = 0xa2
    QueryPowerOnLevel = 0xa3
    QuerySystemFailureLevel = 0xa4
    QueryFadeTimeFadeRate = 0xa5
    QueryManufacturerSpecificMode = 0xa6
    QueryNextDeviceType = 0xa7
    QueryExtendedFadeTime = 0xa8
    QueryControlGearFailure = 0xaa
    QuerySceneLevel = 0xb0
    QueryGroupsZeroToSeven = 0xc0
    QueryGroupsEightToFifteen = 0xc1
    QueryRandomAddressH = 0xc2
    QueryRandomAddressM = 0xc3
    QueryRandomAddressL = 0xc4
    ReadMemoryLocation = 0xc5

    # Special Commands
    Terminate = 0xa1
    Initialise = 0xA5
    Randomise = 0xa7
    Compare = 0xa9
    Withdraw = 0xab
    Ping = 0xad
    SearchAddrH = 0xb1
    SearchAddrM = 0xb3
    SearchAddrL = 0xb5
    ProgramShortAddress = 0xb7
    VerifyShortAddress = 0xb9
    QueryShortAddress = 0xbb
    EnableDeviceType = 0xc1
    SetDTR0 = 0xa3
    SetDTR1 = 0xc3
    SetDTR2 = 0xc5
    WriteMemoryLocation = 0xc7
    WriteMemoryLocationNoReply = 0xc9

    cmd_names = {
        0x00: "Off",
        0x01: "Up",
        0x02: "On",
        0x03: "StepUp",
        0x04: "StepDown",
        0x05: "RecallMaxLevel",
        0x06: "RecallMinLevel",
        0x07: "StepDownAndOff",
        0x08: "OnAndStepUp",
        0x09: "EnableDAPCSequence",
        0x0a: "GoToLastActiveLevel",
        0x0b: "ContinuousUp",
        0x0c: "ContinuousDown",
        0x10: "GoToScene",
        0x20: "Reset",
        0x21: "StoreActualLevelInDTR0",
        0x22: "SavePersistentVariables",
        0x23: "SetOperatingMode",
        0x24: "ResetMemoryBank",
        0x25: "IdentifyDevice",
        0x2a: "SetMaxLevel",
        0x2b: "SetMinLevel",
        0x2c: "SetSystemFailureLevel",
        0x2d: "SetPowerOnLevel",
        0x2e: "SetFadeTime",
        0x2f: "SetFadeRate",
        0x30: "SetExtendedFadeTime",
        0x40: "SetScene",
        0x50: "RemoveFromScene",
        0x60: "AddToGroup",
        0x70: "RemoveFromGroup",
        0x80: "SetShortAddress",
        0x81: "EnableWriteMemory",
        0x90: "QueryStatus",
        0x91: "QueryControlGearPresent",
        0x92: "QueryLampFailure",
        0x93: "QueryLampPowerOn",
        0x94: "QueryLimitError",
        0x95: "QueryResetState",
        0x96: "QueryMissingShortAddress",
        0x97: "QueryVersionNumber",
        0x98: "QueryContentDTR0",
        0x99: "QueryDeviceType",
        0x9a: "QueryPhysicalMinimum",
        0x9b: "QueryPowerFailure",
        0x9c: "QueryContentDTR1",
        0x9d: "QueryContentDTR2",
        0x9e: "QueryOperatingMode",
        0x9f: "QueryLightSourceType",
        0xa0: "QueryActualLevel",
        0xa1: "QueryMaxLevel",
        0xa2: "QueryMinLevel",
        0xa3: "QueryPowerOnLevel",
        0xa4: "QuerySystemFailureLevel",
        0xa5: "QueryFadeTimeFadeRate",
        0xa6: "QueryManufacturerSpecificMode",
        0xa7: "QueryNextDeviceType",
        0xa8: "QueryExtendedFadeTime",
        0xaa: "QueryControlGearFailure",
        0xb0: "QuerySceneLevel",
        0xc0: "QueryGroupsZeroToSeven",
        0xc1: "QueryGroupsEightToFifteen",
        0xc2: "QueryRandomAddressH",
        0xc3: "QueryRandomAddressM",
        0xc4: "QueryRandomAddressL",
        0xc5: "ReadMemoryLocation",

        0xa1: "Terminate",
        0xA5: "Initialise",
        0xa7: "Randomise",
        0xa9: "Compare",
        0xab: "Withdraw",
        0xad: "Ping",
        0xb1: "SearchAddrH",
        0xb3: "SearchAddrM",
        0xb5: "SearchAddrL",
        0xb7: "ProgramShortAddress",
        0xb9: "VerifyShortAddress",
        0xbb: "QueryShortAddress",
        0xc1: "EnableDeviceType",
        0xa3: "SetDTR0",
        0xc3: "SetDTR1",
        0xc5: "SetDTR2",
        0xc7: "WriteMemoryLocation",
        0xc9: "WriteMemoryLocationNoReply",
    }


    TYPE_16BIT = 16
    TYPE_24BIT = 24
    TYPE_DA24CONF = 25  # Seems to be a standard 24 bit one, but Tridonic treats it differently.
    

    def __init__(self, seq, data, type) -> None:
        self.seq = seq
        self.data = data
        self.type = type
        self.evt = asyncio.Event()
        self.result = None


    def resolve(self, result):
        self.result = result
        self.evt.set()

    async def wait(self): 
        # TODO timeout?
        await self.evt.wait()
        if isinstance(self.result, Exception):
            raise self.result
        return self.result
