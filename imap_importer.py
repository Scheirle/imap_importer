# -*- coding: utf-8 -*-
"""
Imap Importer
======================

A Pelican plugin, which imports articles, pages, comments, ... .

Author: Bernhard Scheirle
"""

from __future__ import unicode_literals

import logging
logger = logging.getLogger(__name__)
_log = "imap_importer: "

import os
import keyring
import getpass
import ssl, imaplib, email
import re

from pelican import signals

def natural_sort(l):
    """
    http://stackoverflow.com/questions/4836710/does-python-have-a-built-in-function-for-string-natural-sort
    """
    convert = lambda text: int(text) if text.isdigit() else text.lower() 
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(l, key = alphanum_key)

def number(path, metadata, content, settings):
    file_ext = settings['IMAP_IMPORTER']['FILE_FORMAT']
    file_list = natural_sort(os.listdir(path))
    if len(file_list) == 0:
        return "1." + file_ext
    i = -1
    while len(file_list) + i != -1:
        name = os.path.splitext(file_list[i])[0]
        try:
            num = int(name)
            return str(num + 1) + '.' + settings['IMAP_IMPORTER']['FILE_FORMAT']
        except:
            i -= 1
    return "1." + file_ext

IMAP_IMPORTER_DEFAULT_CONFIG = {
    'FOLDERS': [],
    'HOST': '',
    'USER': '',
    'TYPES' : {
        'comment' : {
            'PATH' : os.path.join('comments', '{slug}'),
            'FILENAME' : number,
        },
        'article' : {
            'PATH' : os.path.join('articles', '{category}'),
        },
        'page'    : {
            'PATH' : os.path.join('pages', '{category}'),
        },
    },
    'FILE_FORMAT' : 'md',
}

def merge_two_dicts(x, y):
    '''Given two dicts, merge them into a new dict as a shallow copy.'''
    z = x.copy()
    z.update(y)
    return z

def update_settings(pelican):
    settings = {}
    if 'IMAP_IMPORTER' in pelican.settings:
        settings = pelican.settings['IMAP_IMPORTER']

        if type(settings) is not dict:
            logger.warning("`IMAP_IMPORTER` should be a dict. Please update your configuration.")
            settings = {}
    pelican.settings['IMAP_IMPORTER'] = merge_two_dicts(IMAP_IMPORTER_DEFAULT_CONFIG, settings)

def get_password(user):
    print("Enter password for email account '" + user + "':")
    password = getpass.getpass()
    return password

def get_body(msg):
    maintype = msg.get_content_maintype()
    if maintype == 'multipart':
        for part in msg.get_payload():
            if part.get_content_maintype() == 'text':
                text = part.get_payload(decode=True).decode(part.get_content_charset())
                return text.strip()
    elif maintype == 'text':
        text = msg.get_payload(decode=True).decode(msg.get_content_charset())
        return text.strip()
    return None

def email_log(msg):
    return "email(" + msg['From'] + ", " + msg['Subject'] + ")"

def process_email(settings, msg):
    """
        returns 
    """
    if 'X-PELICAN-IMAP-IMPORTER' in msg and msg['X-PELICAN-IMAP-IMPORTER'] == 'processed-debug4':
        logger.debug(_log + "Skipping already processed " + email_log(msg))
        return False

    logger.info(_log + "Processing " + email_log(msg))
    body = get_body(msg)
    if body is None:
        logger.warning(_log + "Coudn't extract body of " + email_log(msg))
        return False

    metadata = {}
    content = ''

    state = 0
    for line in body.splitlines():
        if state == 0:
            if line.strip().upper() == '-----BEGIN IMPORT BLOCK-----':
                state = 1
        elif state == 1:
            if line.strip().upper() == '-----BEGIN CONTENT BLOCK-----':
                state = 2
                continue
            if line.strip() == '':
                continue

            key_value = line.split(':', 1)
            if len(key_value) != 2:
                logger.warning(_log + "invalid syntax in " + email_log(msg))
                logger.warning(_log + "ignoring metadata: " + str(key_value))
            else:
                key = key_value[0].strip().lower()
                value = key_value[1].strip()
                metadata[key] = value
        elif state == 2:
            if line.strip().upper() == '-----END CONTENT/IMPORT BLOCK-----':
                state = 3
                break
            content += line + "\r\n"

    if state != 3:
        logger.info(_log + "No or no valid import/content block in " + email_log(msg))
        return False

    if 'type' not in metadata:
        logger.warning(_log + "Metadata 'type' is missing in " + email_log(msg))
        return False

    metadata['type'] = metadata['type'].lower()
    types = settings['IMAP_IMPORTER']['TYPES']
    if metadata['type'] not in types:
        logger.warning(_log + "Type '" + metadata['type'] + "' is not set in IMAP_IMPORTER.TYPES. " + email_log(msg))
        return False

    path = None
    try:
        path = types[metadata['type']]['PATH'].format(**metadata)
    except KeyError as e:
        logger.warning(_log + "Type '" + metadata['type'] + "' requires a specific metadata(" + str(e) + ") which is missing in " + email_log(msg))
        return False

    path = os.path.join(settings['PATH'], path)
    try:
        os.makedirs(path, exist_ok=True)
    except:
        logger.warning(_log + "Couldn't create directory '" + path + "'.")
        return False

    filename = None
    if 'FILENAME' in types[metadata['type']]:
        filename = types[metadata['type']]['FILENAME'](path, metadata, content, settings)
    elif 'filename' in metadata:
        filename = metadata['filename']
    else:
        logger.warning(_log + "Type '" + metadata['type'] + "' has no filename function set, therefore the email requires a specific metadata(filename) which is missing in " + email_log(msg))
        return False
    file_path = os.path.join(path, filename)
    if os.path.isfile(file_path):
        logger.warning(_log + "File at '" + file_path + "' does already exists. Would be overriden by " + email_log(msg))
        return False

    with open(file_path, 'w') as f:
        print(content, file=f)
        logger.info(_log + "Created new file of type '" + metadata['type'] + "': " + file_path)
        return True

    return False
    """
    -----BEGIN IMPORT BLOCK-----
    type: comment
    slug: 
    -----BEGIN CONTENT BLOCK-----
    date: 2015-11-20T21:52+08:00
    author: testauth

    awesome
    -----END CONTENT/IMPORT BLOCK-----
    """

def run(pelican):
    update_settings(pelican)

    host = pelican.settings['IMAP_IMPORTER']['HOST']
    user = pelican.settings['IMAP_IMPORTER']['USER']
    folders = pelican.settings['IMAP_IMPORTER']['FOLDERS']

    new_password = False
    password = keyring.get_password('PELICAN_IMAP_IMPORTER', user)
    if password is None:
        password = get_password(user)
        new_password = True

    host = pelican.settings['IMAP_IMPORTER']['HOST']

    # Connect
    imap = None
    try:
        imap = imaplib.IMAP4(host)
        context = ssl.create_default_context()
        imap.starttls(context)
    except Exception as e:
        logger.critical(_log + "Couldn't connect to '" + host + "'")
        logger.critical(_log + str(e))
        exit()

    # Login
    try_again = True
    fail_counter = 0
    while try_again:
        try:
            imap.login(user, password)
            try_again = False
        except imaplib.IMAP4_SSL.error as e:
            fail_counter += 1
            logger.warning(_log + "Authentication failed!")
            logger.warning(_log + "Make sure that the user name and password are correct")
            if fail_counter > 3:
                exit()
            password = get_password(user)
            new_password = True

    # successful login
    if new_password:
        keyring.set_password('PELICAN_IMAP_IMPORTER', user, password)
    
    for folder in folders:
        imap.select(folder)
        typ, data = imap.search(None, 'ALL')
        for num in data[0].split():
            typ, data = imap.fetch(num, '(RFC822)')
            #imap.append('INBOX.Server.Comments', None, None, message=data[0][1])
            msg = email.message_from_bytes(data[0][1])
            if process_email(pelican.settings, msg):
                del msg['X-PELICAN-IMAP-IMPORTER']
                msg['X-PELICAN-IMAP-IMPORTER'] = 'processed-debug4'
                imap.store(num, '+FLAGS', '\\Deleted') # delete email
                imap.append(folder, '\\Seen', None, message=msg.as_bytes())
        imap.expunge()
    imap.logout()

def register():
    signals.initialized.connect(run)
