from telnetlib import Telnet
from spcControl import (
        get_config,
        get_config_file
        )


def communicate(line):
    config = get_config(get_config_file())

    # # We do the login manually # #
    # Establish connection
    telnet = Telnet(config.get("Heliospectra", "MasterHost"),
            port=config.getint("Heliospectra", "MasterPort"))
    response = telnet.read_until(b">")
    if config.getboolean("Global", "Debug") > 0:
        print("Intial response is:", response.decode())

    wavelengths = [s.strip() for s in
            config.get("Heliospectra", "Wavelengths").split(",")]

    intensities = []
    for wl in sorted(wavelengths):
        intensity = float(line[config.getint("HeliospectraCsvFields", wl)])
        # Solarcalc gives percentages, telnet wants value in 0-255
        intensity = int(round(
            intensity * config.getfloat("Heliospectra", "Multiplier")
            ))
        intensities.append((wl, intensity))

    intensities = sorted(intensities)
    if config.getboolean("Global", "Debug"):
        print("Intensity list is:", intensities)

    set_cmd = config.get("Heliospectra", "SetallWlCommand")

    command_line = bytes("%s %s\n" % (
                set_cmd,
                " ".join("%i" % itn for _, itn in intensities)
                ),
            encoding="UTF8"
            )

    if config.getboolean("Global", "Debug"):
        print("Running:", command_line.decode())
    telnet.write(command_line)

    response = telnet.read_some()
    if config.getboolean("Global", "Debug"):
        print("Response is:", response.decode())

    # Close telnet session
    telnet.close()
