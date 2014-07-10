from __future__ import print_function
import logging
from telnetlib import Telnet

from spcControl import (
        get_config,
        get_config_file,
        )


LOG = logging.getLogger("spcControl")


def communicate(line):
    config = get_config(get_config_file())
    helio_mode = config.get("Heliospectra", "Mode")
    helio_csv = helio_mode + "CsvFields"
    # # We do the login manually # #
    # Establish connection
    telnet = Telnet(config.get(helio_mode, "MasterHost"),
            port=config.getint(helio_mode, "MasterPort"))
    response = telnet.read_until(b">")
    LOG.debug("Intial response is: {0!s}".format(response.decode()))

    wavelengths = [s.strip() for s in
            config.get(helio_mode, "Wavelengths").split(",")]
    # Build list of wl:intensity pairs to send
    intensities = []
    for wl in wavelengths:
        intensity = float(line[config.getint(helio_csv, wl)])
        # Solarcalc gives percentages, telnet wants value in 0-255
        intensity = int(round(
            intensity * config.getfloat(helio_mode, "Multiplier")
            ))
        intensities.append((wl, intensity))
    # And order them
    intensities = sorted(intensities)
    LOG.debug("Intensity list is: {0!s}".format(intensities))

    set_cmd = config.get(helio_mode, "SetallWlCommand")

    command_line = bytes("%s %s\n" % (
                set_cmd,
                " ".join("%i" % intens for _, intens in intensities)
                ),
            encoding="UTF8"
            )

    LOG.debug("Running: {0!s}".format(command_line.decode()))
    telnet.write(command_line)

    response = telnet.read_some()
    LOG.debug("Response is: {0!s}".format(response.decode()))

    # Close telnet session
    telnet.close()
