from telnetlib import Telnet
from spcControl import (
        get_config,
        get_config_file
        )


def communicate(line):
    config = get_config(get_config_file())
    helio_mode = config.get("Heliospectra", "Mode")
    helio_csv = helio_mode + "CsvFields"

    # # We do the login manually # #
    # Establish connection
    telnet = Telnet(config.get(helio_mode, "MasterHost"),
            port=config.getint(helio_mode, "MasterPort"))
    response = telnet.read_until(b">")
    if config.getboolean("Global", "Debug") > 0:
        print("Intial response is:", response.decode())

    wavelengths = [s.strip() for s in
            config.get(helio_mode, "Wavelengths").split(",")]

    intensities = []
    for wl in wavelengths:
        intensity = float(line[config.getint(helio_csv, wl)])
        # Solarcalc gives percentages, telnet wants value in 0-255
        intensity = int(round(
            intensity * config.getfloat(helio_mode, "Multiplier")
            ))
        intensities.append((wl, intensity))

    intensities = sorted(intensities)
    if config.getboolean("Global", "Debug"):
        print("Intensity list is:", intensities)

    set_cmd = config.get(helio_mode, "SetallWlCommand")

    command_line = bytes("%s %s\n" % (
                set_cmd,
                " ".join("%i" % intens for _, intens in intensities)
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
