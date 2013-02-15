try:
    from ConfigParser import ConfigParser
except ImportError:
    # Python 3.x
    from configparser import ConfigParser
import sys
import os


CONFIG_FILE = "./conviron.ini"  # Default file name
def get_config():
    """Returns a ConfigParser which has read the given filename. If filename is
    not given, uses CONFIG_FILE."""
    # If the config file is specified on the command line, use it
    if len(sys.argv) > 1:
        if os.path.isfile(sys.argv[1]):
            config_file = sys.argv[1]
        else:
            print("Incorrect commandline.\n"
                "Format is `python -m conviron <ini_file_path>`")
            sys.exit(1)
    else:
        config_file = CONFIG_FILE

    parser = ConfigParser()
    try:
        parser.readfp(open(config_file))
    except AttributeError:
        parser.read_file(open(config_file))
    return parser
