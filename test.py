#!/home/bruce/dev/dali/bin/python3
import sys
import logging
import asyncio
from dali.command import DaliCommand
from dali.tridonic import TridonicDali
from dali.gear import DaliGear
import functools
import signal

async def test(driver):

    await driver.commission()
    await asyncio.sleep(1)

    # try:
        # print("Scanning for devices")
        # devices = await driver.scan_for_gear()
        # print(devices)




        # print("Doing some lighting excercises")
        # g = DaliGear(driver, 0)
        # pol = await g.query_fade()
        # print("Fade = ", pol)

        # await g.off()
    
    # finally:
    #     await driver.send_cmd(0, DaliCommand.Off)
    #     await driver.send_cmd(1, DaliCommand.Off)


def ask_exit(signame, loop, device):
    print("got signal %s: exit" % signame)
    device.close()
    loop.stop()


async def main():
    main_loop = asyncio.get_running_loop()
    d = TridonicDali(main_loop)
    d.open()

    for signame in {'SIGINT', 'SIGTERM'}:
        main_loop.add_signal_handler(
            getattr(signal, signame),
            functools.partial(ask_exit, signame, main_loop, d))

    await test(d)


if __name__ == "__main__":
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logging.root.setLevel(logging.DEBUG)
    logging.root.addHandler(handler)


    asyncio.run(main())
