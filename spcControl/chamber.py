from telnetlib import Telnet
from spcControl import (get_config, get_config_file)
from time import sleep
import re
from csv import DictWriter
import datetime
from os import path


TIMEOUT = 10


def _run(telnet, command, expected):
    """Do the leg work between this and the conviron."""
    config = get_config(get_config_file())
    if config.getboolean("Global", "Debug"):
        print("Sending command: ", command.decode())
    telnet.write(command)
    response = telnet.expect([expected,], timeout=TIMEOUT)
    if config.getboolean("Global", "Debug"):
        print("Received: ", response[2].decode())
    if response[0] < 0:  # No match found
        raise RuntimeError("Expected response was not received")
    return response


def _connect(config):
    """Boilerplate to connect to a conviron."""
    cmd_str = "%s %s " % (
            config.get("Conviron", "SetCommand"),
            config.get("Conviron", "DeviceID")
            )
    # # We do the login manually # #
    # Establish connection
    telnet = Telnet(config.get("Conviron", "Host"))
    response = telnet.expect([re.compile(b"login:"),], timeout=TIMEOUT)
    if config.getboolean("Global", "Debug") > 0:
        print("Initial response is:", response[2].decode())
    if response[0] < 0:  # No match found
        raise RuntimeError("Login prompt was not received")
    # Username
    payload = bytes(config.get("Conviron", "User") + "\n", encoding="UTF8")
    telnet.write(payload)
    response = telnet.expect([re.compile(b"Password:"),], timeout=TIMEOUT)
    if config.getboolean("Global", "Debug") > 0:
        print("Sent username:", payload.decode())
        print("Received:", response[2].decode())
    if response[0] < 0:  # No match found
        raise RuntimeError("Password prompt was not received")
    # Password
    payload = bytes(config.get("Conviron", "Password") + "\n", encoding="UTF8")
    telnet.write(payload)
    response = telnet.expect([re.compile(b"#"),], timeout=TIMEOUT)
    if config.getboolean("Global", "Debug") > 0:
        print("Send password:", payload.decode())
        print("Received:", response[2].decode())
    if response[0] < 0:  # No match found
        raise RuntimeError("Shell prompt was not received")
    return telnet


def communicate(line):
    """Communicate config values in csv line to a conviron."""
    config = get_config(get_config_file())
    cmd_str = "%s %s " % (
            config.get("Conviron", "SetCommand"),
            config.get("Conviron", "DeviceID")
            )
    # Establish connection
    telnet = _connect(config)
    # Make list for the "Set" part of the communication
    # Append init commands to command list
    command_list = []
    for params in config.get("Conviron", "InitSequence").split(","):
        command_list.append(bytes(cmd_str + params + "\n", encoding="UTF8"))
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
    for command in command_list:
        _run(telnet, command, re.compile(b"#"))
    sleep(2)
    # Clear write flag
    write_flag_command = bytes(
            cmd_str + config.get("Conviron", "ClearWriteFlagCommand") + "\n",
            encoding="UTF8"
            )
    _run(telnet, write_flag_command, re.compile(b"#"))
    sleep(2)
    # Make list of Reload command sequences
    command_list = []
    for params in config.get("Conviron", "ReloadSequence").split(","):
        command_list.append(bytes(cmd_str + params + "\n", encoding="UTF8"))
    # Append teardown commands to command list
    for params in config.get("Conviron", "TearDownSequence").split(","):
        command_list.append(bytes(cmd_str + params + "\n", encoding="UTF8"))
    # Run Reload command sequence
    for command in command_list:
        _run(telnet, command, re.compile(b"#"))
    sleep(2)
    # Clear write flag
    clear_write_flag_cmd = bytes(
            cmd_str + config.get("Conviron", "ClearWriteFlagCommand") + "\n",
            encoding="UTF8"
            )
    _run(telnet, clear_write_flag_cmd, re.compile(b"#"))
    sleep(2)
    # Clear Busy flag
    clear_busy_flag_cmd = bytes(
            cmd_str + config.get("Conviron", "ClearBusyFlagCommand") + "\n",
            encoding="UTF8"
            )
    _run(telnet, clear_busy_flag_cmd, re.compile(b"#"))
    sleep(2)
    # Close telnet session
    telnet.close()


def log():
    """Get values back from convirons"""
    config = get_config(get_config_file())
    cmd_str = "%s %s " % (
            config.get("Conviron", "GetCommand"),
            config.get("Conviron", "DeviceID")
            )
    # Establish connection
    telnet = _connect(config)
    # Get temp
    temp_cmd = bytes("%s %s\n" % (
        cmd_str,
        config.get("Logging", "TempSequence")),
        encoding="UTF8")
    temp_resp = _run(telnet, temp_cmd, re.compile(b"# (.+)$"))
    print (temp_resp)
    temp = temp_resp.groups()[1]
    print (temp)
    sleep(1)
    # Get Rel Humidity
    rh_cmd = bytes("%s %s\n" % (
        cmd_str,
        config.get("Logging", "RHSequence")),
        encoding="UTF8")
    rh_resp = _run(telnet, rh_cmd, re.compile(b"# (.+)$"))
    print (rh_resp)
    rh = rh_resp.groups()[1]
    print (rh)
    sleep(1)
    # Get PAR
    par_cmd = bytes("%s %s\n" % (
        cmd_str,
        config.get("Logging", "PARSequence")),
        encoding="UTF8")
    par_resp = _run(telnet, par_cmd, re.compile(b"# (.+)$"))
    print (par_resp)
    par = par_resp.groups()[1]
    print (par)
    sleep(1)
    # Do the logging to a csv file
    now = datetime.datetime.now()
    date = now.strftime(config.get("Logging", "DateFmt"))
    time = now.strftime(config.get("Logging", "TimeFmt"))
    logfile = config.get("Logging", "LogFile")
    loghdr = config.get("Logging", "CSVLogHeader").strip().split(',')
    if path.exists(logfile):
        # don't clobber file, use append mode & don't write header
        lfh = open(logfile, "a")
        lcsv = DictWriter(lfh, loghdr)
    else:
        # new file, so create and write a header
        lfh = open(logfile, "w")
        lcsv = DictWriter(lfh, loghdr)
        lcsv.writeheader()
    lcsv.writerow({
        "Date": date,
        "Time": time,
        "Temp": temp,
        "RH": rh,
        "PAR": par
        })
    # close things that need closing
    lfh.close()
    telnet.close()
