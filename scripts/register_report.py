#! /usr/bin/env python2
"""This script serves as a client example of registering a report.
Your credentials are encrypted prior to transport and your api gateway key
is used to encrypt and validate you as a user on the other end.
"""
from functools import partial
from os import path, environ as env
import sys
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import requests

from utils import encrypt

def prompt_user_for_credentials():
    return dict(
        file_name=raw_input('file_name: '),
        file_description=raw_input('file_description: '),
        backend_name=raw_input('backend_name: The backend registered in the sql-lambda '),
        sql=raw_input('sql: '),
        params=raw_input('params[None]: ') or None,
        uri=raw_input('uri[gdrive]: ') or 'gdrive',
    )

def register_report(config):
    try:
        response = requests.post(
            '{app_endpoint}/sql2uri/register/{report}'
            .format(app_endpoint=env['APP_ENDPOINT'],
                    report=config['file_name']),
            json=dict(**config),
            headers={"x-api-token": env['API_ID']}
        )
    except Exception as err:
        print(err)
    return True

def main():
    config = prompt_user_for_credentials()

    config['options'] = encrypt(
        dict(sql=config['sql'],
             params=config['params']), key=env['SQL_SECRET']
    )
    del config['sql']
    del config['params']
    if register_report(config):
        print(
            "http GET $APP_ENDPOINT/sql2uri/view/{report} "
            "x-api-key:$API_KEY".format(report=config['file_name'])
        )

if __name__ == '__main__':
    main()
