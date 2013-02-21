from configparser import ConfigParser
import sys
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

CONFIG_FILE = "./conviron.ini"  # Default file name


def get_config(filename=None):
    """Returns a ConfigParser which has read the given filename. If filename is
    not given, uses CONFIG_FILE."""
    # If the config file is specified on the command line, use it
    if filename is not None:
        config_file = filename
    elif len(sys.argv) > 1:
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

config = get_config()


def email_error(subject, message):
    """Borrows heavily from http://kutuma.blogspot.com.au/2007/08/
    sending-emails-via-gmail-with-python.html
    """
    try:
        msg = MIMEMultipart()
        msg["From"] = config.get("Global", "GmailUser")
        msg["To"] = config.get("Global", "EmailRecipient")
        msg["Subject"] = subject
        msg.attach(MIMEText(message))

        gmail = smtplib.SMTP("smtp.gmail.com", 587)
        gmail.ehlo()
        gmail.starttls()
        gmail.ehlo()
        gmail.login(
                config.get("Global", "GmailUser"),
                config.get("Global", "GmailPass")
            )
        gmail.sendmail(
                config.get("Global", "GmailUser"),
                config.get("Global", "EmailRecipient"),
                msg.as_string()
                )
        gmail.close()
    except:
        pass

