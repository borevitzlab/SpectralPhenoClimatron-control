from __future__ import print_function
from csv import DictWriter
import datetime
import logging
from os import path
import re
from telnetlib import Telnet
from time import sleep

from spcControl import (
    get_config,
    get_config_file,
)


TIMEOUT = 10
LOG = logging.getLogger("spcControl")


def _run(telnet, command, expected):
    """Do the leg work between this and the conviron."""
    LOG.debug("Sending command:  {0!s}".format(command.decode()))
    telnet.write(command)
    response = telnet.expect([expected,], timeout=TIMEOUT)
    LOG.debug("Received:  {0!s}".format(response[2].decode()))
    if response[0] < 0:  # No match found
        raise RuntimeError("Expected response was not received")
    return response


def _connect(config):
    """Boilerplate to connect to a conviron."""
    # Establish connection
    telnet = Telnet(config.get("Conviron", "Host"))
    response = telnet.expect([re.compile(b"login:"),], timeout=TIMEOUT)
    LOG.debug("Initial response is: {0!s}".format(response[2].decode()))
    if response[0] < 0:  # No match found
        raise RuntimeError("Login prompt was not received")
    # Username
    payload = bytes(config.get("Conviron", "User") + "\n", encoding="UTF8")
    telnet.write(payload)
    response = telnet.expect([re.compile(b"Password:"),], timeout=TIMEOUT)
    LOG.debug("Sent username: {0!s}".format(payload.decode()))
    LOG.debug("Received: {0!s}".format(response[2].decode()))
    if response[0] < 0:  # No match found
        raise RuntimeError("Password prompt was not received")
    # Password
    payload = bytes(config.get("Conviron", "Password") + "\n", encoding="UTF8")
    telnet.write(payload)
    response = telnet.expect([re.compile(b"#"),], timeout=TIMEOUT)
    LOG.debug("Send password: {0!s}".format(payload.decode()))
    LOG.debug("Received: {}".format(response[2].decode()))
    if response[0] < 0:  # No match found
        raise RuntimeError("Shell prompt was not received")
    return telnet


def communicate(line):
    """Communicate config values in csv line to a conviron."""
    config = get_config(get_config_file())
    cmd_str = "%s %s " % (config.get("Conviron", "SetCommand"),
                          config.get("Conviron", "DeviceID"))
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
        cmd = "%s %s %i %i\n" % (
            cmd_str,
            config.get("ConvironDataTypes", "Light1"),
            config.getint("ConvironDataIndicies", "Light1"),
            int(line[config.getint("ConvironCsvFields", "Light1")])
        )
        command_list.append(bytes(cmd, encoding="UTF8"))
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
    cmd_str = "%s %s " % (config.get("Conviron", "GetCommand"),
                          config.get("Conviron", "DeviceID"))
    # Establish connection
    telnet = _connect(config)
    # Get temp
    temp_cmd = bytes("%s %s\n" %
        (cmd_str, config.get("Logging", "TempSequence")),
        encoding="UTF8"
    )
    temp_resp = _run(telnet, temp_cmd, re.compile(b"# $"))
    # str should be:
    # '123 134 \r\n[PS1] # \r\n'
    # "<actual>SPACE<set>SPACE\r\n..."
    temp_str = temp_resp[2]
    temp, temp_set = temp_str.splitlines()[0].strip().split()
    temp = "{:0.1f}".format(float(temp)/10.0)
    temp_set = "{:0.1f}".format(float(temp_set)/10.0)
    # Get Rel Humidity
    rh_cmd = bytes("%s %s\n" %
        (cmd_str, config.get("Logging", "RHSequence")),
        encoding="UTF8"
    )
    rh_resp = _run(telnet, rh_cmd, re.compile(b"# $"))
    # str should be:
    # '52 73 \r\n[$PS1] # \r\n'
    # "<actual>SPACE<set>SPACE\r\n..."
    rh_str = rh_resp[2]
    rh, rh_set = rh_str.splitlines()[0].strip().split()
    rh = rh.decode()
    rh_set = rh_set.decode()
    # Get PAR
    par_cmd = bytes("%s %s\n" %
        (cmd_str, config.get("Logging", "PARSequence")),
        encoding="UTF8"
    )
    par_resp = _run(telnet, par_cmd, re.compile(b"# $"))
    # str should be:
    # '123 \r\n[PS1] # \r\n'
    # actual value only (set is always 0)
    par_str = par_resp[2]
    par = par_str.splitlines()[0].strip().decode()
    # We're done w/ the telnet handle, close it here to avoid timeout issues
    telnet.close()
    # Do the logging to a csv file
    now = datetime.datetime.now()
    date = now.strftime(config.get("Logging", "DateFmt"))
    time = now.strftime(config.get("Logging", "TimeFmt"))
    logfile = config.get("Logging", "LogFile")
    loghdr = config.get("Logging", "CSVLogHeader").strip().split(',')
    if path.exists(logfile):
        # don't clobber file, use append mode & don't write header
        lfh = open(logfile, "a", newline='')
        lcsv = DictWriter(lfh, loghdr)
    else:
        # new file, so create and write a header
        lfh = open(logfile, "w", newline='')
        lcsv = DictWriter(lfh, loghdr)
        lcsv.writeheader()
    lcsv.writerow({
        "Date": date,
        "Time": time,
        "Temp": temp,
        "SetTemp": temp_set,
        "RH": rh,
        "SetRH": rh_set,
        "PAR": par
    })
    # close things that need closing
    lfh.close()
