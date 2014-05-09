from configparser import ConfigParser
import logging
import logging.handlers
import sys
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib


def get_logger(name="spcControl"):
    config = get_config(get_config_file())
    # Formattter for both file & stream handlers
    fmt = logging.Formatter(config.get("Global", "LogFormat"))
    # Set up a file logger
    fhand = logging.FileHandler(config.get("Global", "Logfile"))
    fhand.setFormatter(fmt)
    if config.getboolean("Global", "Debug"):
        fhand.setLevel(logging.DEBUG)
    else:
        fhand.setLevel(logging.INFO)
    # Set up stream handler for errors
    shand = logging.StreamHandler()
    shand.setFormatter(fmt)
    shand.setLevel(logging.ERROR)
    # Email handler for errors
    email_fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    ehand = TlsSMTPHandler(
            ("smtp.gmail.com", 587),
            config.get("Global", "GmailUser"),
            config.get("Global", "EmailRecipient").strip().split(","),
            "spcControl Logging Message",
            credentials = (
                config.get("Global", "GmailUser"),
                config.get("Global", "GmailPass")
            ))
    ehand.setFormatter(email_fmt)
    ehand.setLevel(logging.ERROR)
    # Set up logger
    log = logging.getLogger("spcControl")
    log.addHandler(fhand)
    log.addHandler(shand)
    log.addHandler(ehand)
    log.setLevel(logging.DEBUG)
    return log


def get_config_file():
    try:
        config_file = sys.argv[2]
        with open(config_file) as fh:
            pass  # we can open it
    except (IndexError, IOError):
        config_file = "./chamber.ini"  # Default file name
    return config_file


def get_config(config_file):
    """Returns a ConfigParser which has read the given filename. If filename is
    not given, uses get_config_file()."""
    # If the config file is specified on the command line, use it

    parser = ConfigParser()
    try:
        parser.readfp(open(config_file))
    except AttributeError:
        parser.read_file(open(config_file))
    return parser



def email_error(subject, message, config_file=""):
    """Borrows heavily from http://kutuma.blogspot.com.au/2007/08/
    sending-emails-via-gmail-with-python.html
    """
    if not os.path.exists(config_file):
        config_file = get_config_file()
    config = get_config(config_file)
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


class TlsSMTPHandler(logging.handlers.SMTPHandler):
    """Shamelessly looted from:
    http://mynthon.net/howto/-/python/python%20-%20logging.SMTPHandler-how-to\
            -use-gmail-smtp-server.txt"
    """
    def emit(self, record):
        """Emit a record.
        Format the record and send it to the specified addressees.
        """
        try:
            import smtplib
            import string
            try:
                from email.utils import formatdate
            except ImportError:
                formatdate = self.date_time
            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP(self.mailhost, port)
            msg = self.format(record)
            msg = "From: {}\r\n".format(self.fromaddr)
            msg += "To: {}\r\n".format(",".join(self.toaddrs))
            msg += "Subject: {}\r\n".format(self.getSubject(record))
            msg += "Date: {}\r\n\r\n{}".format(formatdate(), msg)
            if self.username:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(self.username, self.password)
            smtp.sendmail(self.fromaddr, self.toaddrs, msg)
            smtp.quit()
        except (KeyboardInterrupt, SystemExit) as e:
            raise e
        except:
            LOG.warn("Could not log via email")


LOG = get_logger()
