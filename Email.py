import sys, os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import Encoders
import yaml
import argparse


class Postman:
    def __init__(self, username, password, from_addr, mail_server,use_tls):
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.mail_server = mail_server
        self.use_tls = use_tls
        
    def __enter__(self):
        self.server = smtplib.SMTP(self.mail_server)
        self.server.ehlo()
        if self.use_tls:
            self.server.starttls()
            self.server.login(self.username, self.password)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.server.quit()

    def send(self, to, subject, msg, attach=None):
        msg_mime = MIMEMultipart('mixed')
        msg_mime.attach(MIMEText(msg, 'html'))
        msg_mime['Subject'] = subject
        msg_mime['From'] = self.from_addr
        msg_mime['To'] = to
        if attach:
            for fn in attach:
                file = MIMEBase('application',"octet-stream")
                file.set_payload( open( fn, "rb").read() )
                Encoders.encode_base64(file)
                file.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(fn))
                msg_mime.attach(file)
        self.server.sendmail(self.from_addr, to, msg_mime.as_string())

    def close(self):
        self.server.quit()

class Templater:
    def render(self, name_file, args):
        temp_file = open(name_file, 'r')
        temp_render = temp_file.read()
        for arg in args:
            temp_render = temp_render.replace("{{%s}}" % arg, args[arg])
        temp_file.close()
        return temp_render


class Send():

    def __init__(self, conf):
        self.tls = conf['mail']['tls']
        self.username = conf['mail']['username']
        self.password = conf['mail']['password']
        self.from_addr = conf['mail']['from_addr']
        self.mail_server = conf['mail']['mail_server']
        self.postman = Postman(username=self.username, password=self.password,
                       from_addr=self.from_addr, mail_server=self.mail_server,
                       use_tls=self.tls)
        self.templater = Templater()
    
    def send_msg(self, to, subject, msg, attach=None):
        if self.postman:
            with self.postman as p:
                p.send(to, subject, msg, attach)

    def render_template(self, name_file, args):
        if self.templater:
            return self.templater.render(name_file, args)
        else:
            return None


def help_parser():
    parser = argparse.ArgumentParser(description='Send template based email with attachments.')
    parser.add_argument('--to', type=str, nargs='?', required=True,
                        help='destination email address')
    parser.add_argument('--subject', type=str, nargs='?', required=True,
                        help='mail subject line')
    parser.add_argument('--msg', type=str, nargs='?',
                        help='message body')
    parser.add_argument('--msg_data', type=str, nargs='*',
                        help='data for message template, key=value pairs passed at the command line')
    parser.add_argument('--msg_data_file', type=str, nargs='?',
                        help='data for message template, this can be set in the config yaml')
    parser.add_argument('--msg_template', type=str, nargs='?',
                        help='message template location, this can be set in the config yaml')
    parser.add_argument('--attachments', type=str, nargs='*',
                        help='message body')
    parser.add_argument('--config',  type=str, nargs='?',
                        help='optional alternative config yaml, defualts to mail.yaml')

    args = parser.parse_args()
    return vars(args)

def main():

    cli = help_parser()
    conf = yaml.load(open('mail.yaml',"r")) if not cli['config'] else yaml.load(open(cli['config'],"r"))

    attachments = None if not cli['attachments'] else cli['attachments']
    if cli['msg_data_file']:
        mail_data_file = conf['mail']['mail_data'] if not cli['msg_data'] else cli['msg_data']
        mail_data = yaml.load(open(mail_data_file,"r"))
    else:
         mail_data = {}
         for each in cli['msg_data']:
             k, v = each.split("=")
             mail_data[k] = v
         print mail_data
    mail_template = conf['mail']['template'] if not cli['msg_template'] else cli['msg_template']
    subject = cli['subject']
    mail_to = cli['to']

    send=Send(conf=conf)
    send.send_msg(mail_to, subject, send.render_template(mail_template,
                                                        mail_data ), attachments)

if __name__ == "__main__":
    main()
    
                                        
