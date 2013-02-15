from __future__ import print_function
from telnetlib import Telnet
from conviron import get_config
import datetime
from time import sleep

config = get_config()


def communicate(line):
    cmd_str = "%s %s " % (
            config.get("Conviron", "SetCommand"),
            config.get("Conviron", "DeviceID")
            )

    # # We do the login manually # #
    # Establish connection
    telnet = Telnet(config.get("Heliospectra","MasterHost"),
            port=config.getint("Heliospectra", "MasterPort"))
    response = telnet.read_until(b">")
    if config.getboolean("Global", "Debug") > 0:
        print(response.decode())

    wavelengths = [s.strip() for s in
            config.get("Heliospectra","Wavelengths").split(",")]

    intensities = []
    for wl in wavelengths:
        intensity = float(line[config.getint("HeliospectraCsvFields", wl)])
        # Solarcalc gives percentages, telnet wants value in 0-255
        intensity = int(round(intensity * 2.55))
        intensities[wl] = intensity

    if config.getboolean("Global", "Debug"):
        print(intensities)

    set_cmd = config.get("Heliospecta", "SetWlsRelPowerCommand")

    command_line = bytes("%s %s\n" % (
                set_cmd,
                " ".join("%i" for intensity in intensities.values())
                ),
            encoding="UTF8"
            )

    if config.getboolean("Global", "Debug"):
        print(commandline.decode())

    response = telnet.read_some()
    if config.getboolean("Global", "Debug"):
        print(response.decode())

    # Close telnet session
    telnet.close()
