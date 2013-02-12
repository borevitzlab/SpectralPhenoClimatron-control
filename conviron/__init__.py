from configparser import ConfigParser

CONFIG_FILE = "./conviron.ini"  # Default file name


def get_config(filename):
    """Returns a ConfigParser which has read the given filename. If filename is
    not given, uses CONFIG_FILE."""
    if not filename:
        filename = CONFIG_FILE
    return ConfigParser.read_file(open(filename))
