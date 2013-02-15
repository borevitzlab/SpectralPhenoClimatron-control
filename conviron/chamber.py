from telnetlib import Telnet
from conviron import get_config
import datetime
from time import sleep

config = get_config()


def _run(telnet, commands):
    response = b''
    for command in commands:
        if config.getboolean("Global", "Debug"):
            print("Sending command: ", command.decode())
        telnet.write(command)
        this_response = telnet.read_some()
        if config.getboolean("Global", "Debug"):
            print("Received: ", this_response.decode())
    return response


def communicate(line):
    cmd_str = "%s %s " % (
            config.get("Conviron", "SetCommand"),
            config.get("Conviron", "DeviceID")
            )

    # # We do the login manually # #
    # Establish connection
    telnet = Telnet(config.get("Conviron", "Host"))
    response = telnet.read_until(b"login: ")
    if config.getboolean("Global", "Debug") > 0:
        print("Initial response is:", response.decode())

    # Username
    payload = bytes(config.get("Conviron", "User") + "\n", encoding="UTF8")
    telnet.write(payload)
    response = telnet.read_until(b"Password: ")
    if config.getboolean("Global", "Debug") > 0:
        print("Sent username:", payload.decode())
        print("Received:", response.decode())

    # Password
    payload = bytes(config.get("Conviron", "Password") + "\n", encoding="UTF8")
    telnet.write(payload)
    response = telnet.read_until(b"#")
    if config.getboolean("Global", "Debug") > 0:
        print("Send password:", payload.decode())
        print("Received:", response.decode())

    # Make list for the "Set" part of the communication
    # Append init commands to command list
    command_list = [
            bytes(cmd_str + params + "\n", encoding="UTF8")
            for params in config.get("Conviron", "InitSequence").split(",")
            ]
    # Append temp command to list
    command_list.append(bytes("%s %s %i %i\n" % (
        cmd_str,
        config.get("ConvironDataTypes", "Temperature"),
        config.getint("ConvironDataIndicies", "Temperature"),
        int(float(line[config.getint("GlobalCsvFields", "Temperature")]) * 10)
        ), encoding="UTF8"))
    # Append humidity command to list
    command_list.append(bytes("%s %s %i %i\n" % (
        cmd_str,
        config.get("ConvironDataTypes", "Humidity"),
        config.getint("ConvironDataIndicies", "Humidity"),
        int(line[config.getint("GlobalCsvFields", "Humidity")])
        ), encoding="UTF8"))
    if config.getboolean("Conviron", "UseInternalLights"):
        # Append light1 command to list
        command_list.append(bytes("%s %s %i %i\n" % (
            cmd_str,
            config.get("ConvironDataTypes", "Light1"),
            config.getint("ConvironDataIndicies", "Light1"),
            int(line[config.getint("ConvironCsvFields", "Light1")])
            ), encoding="UTF8"))
    # Append teardown commands to command list
    for params in config.get("Conviron", "TearDownSequence").split(","):
        command_list.append(bytes(cmd_str + params + "\n", encoding="UTF8"))
    # Run set commands sequence
    _run(telnet, command_list)
    sleep(2)

    # Clear write flag
    _run(telnet, [bytes(cmd_str +
        config.get("Conviron", "ClearWriteFlagCommand") +
        "\n", encoding="UTF8")
        ])
    sleep(2)

    # Make list of Reload command sequences
    command_list = [
            bytes(cmd_str + params + "\n", encoding="UTF8")
            for params in config.get("Conviron", "ReloadSequence").split(",")
            ]
    # Append teardown commands to command list
    for params in config.get("Conviron", "TearDownSequence").split(","):
        command_list.append(bytes(cmd_str + params + "\n", encoding="UTF8"))
    # Run Reload command sequence
    _run(telnet, command_list)
    sleep(2)

    # Clear write flag
    _run(telnet, [bytes(cmd_str +
        config.get("Conviron", "ClearWriteFlagCommand") +
        "\n", encoding="UTF8")
        ])
    sleep(2)

    # Clear Busy flag
    _run(telnet, [bytes(cmd_str +
        config.get("Conviron", "ClearBusyFlagCommand") +
        "\n", encoding="UTF8")
        ])
    sleep(2)

    # Close telnet session
    telnet.close()
