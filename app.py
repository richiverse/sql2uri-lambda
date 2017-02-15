#! /usr/bin/env python2
"""
sql2uri service takes your sql and runs it against a backend you registered
in the sql-lambda service and outputs it to gdrive.
"""

from os import environ as env
from json import dumps, loads

import boto3
from flask import Flask, jsonify, request
from pynamodb.exceptions import (
    UpdateError,
    ScanError,
    QueryError,
    DeleteError,
    DoesNotExist,
)
import requests

from models import Report
from middleware import list_routes
from utils import decrypt

app = Flask(__name__)

def raise_if_not_exists(model):
    if not model.exists():
        raise DoesNotExist()

def handle_request(method, **kwargs):
    try:
        response = method(**kwargs)
    except Exception as err:
        raise(err)
    return response

def run_sql(backend, options):
    url = '{sql_endpoint}/sql/view/{backend}'.format(
        sql_endpoint=env['SQL_ENDPOINT'],
        backend=backend,
    )
    params = dict(options=options, key=env['SQL_SECRET'])

    return handle_request(
        requests.get,
        url=url,
        params=params,
        headers={'x-api-key': env['SQL_KEY']},
    )

def save_to_uri(report, data, uri='gdrive'):
    url = '{uri_endpoint}/{uri}/write'.format(
        uri_endpoint=env['%s_ENDPOINT' % uri.upper()],
        uri=uri,
    )
    data = dict(
        file_name=report,
        data=data,
        folder_id=env['GDRIVE_PARENT_FOLDER_ID'],
    )
    return handle_request(
        requests.post,
        url=url,
        json=data,
        headers={'x-api-key': env['%s_KEY' % uri.upper()]},
    )
@app.route('/sql2uri')
def list_api_routes():
    return jsonify(list_routes(app))

@app.route('/sql2uri/list_reports')
def list_reports():
    raise_if_not_exists(Report)
    results = [dict(
        file_name=item.file_name,
        file_description=item.file_description
        )
        for item in Report.scan()
    ]
    return jsonify(results)

@app.route('/sql2uri/info/<report>')
def report_info(report):
    results = [dict(
        file_name=item.file_name,
        file_description=item.file_description,
        backend_name=item.backend_name,
        options=item.options,
        schedule=item.schedule,
        uri=item.uri,
        created_by=item.created_by,
        registered_on=item.registered_on,
        approved_by=item.approved_by,
        approved_on=item.approved_on
        )
        for item in Report.query(
            'file_name', file_name__eq=report)
    ]
    results = results[0]
    results['decrypted_options'] = decrypt(results['options'], key=env['SQL_SECRET'])
    return jsonify(results)

@app.route('/sql2uri/register/<report>', methods=['POST'])
def register_report(report):
    """Register your report.

    options MUST be encrypted .
    uri Default is gdrive.
    """
    json = request.json

    file_name = json['file_name']
    file_description = json['file_description']
    backend_name = json['backend_name']
    options = json['options']
    uri = json.get('uri', 'gdrive')

    if not Report.exists():
        Report.create_table(wait=True)

    new_report = Report(
        file_name=file_name,
        file_description=file_description,
        backend_name=backend_name,
        options=options,
        uri=uri
    )
    new_report.save()
    return jsonify(
        "http POST $APP_ENDPOINT:5002/sql/view/%(report)s "
        "x-api-key:$API_ID "
        % dict(report=report)
    )

@app.route('/sql2uri/view/<report>')
def view_report(report=None, event=None):
    """ Run all your reports on demand.

    Deploy to gdrive and this is also configurable.
    """
    report = report if report else event['report']
    args = loads(report_info(report).data)
    data = loads(run_sql(
        args['backend_name'],
        args['options'],
        ).json()
    )
    saved = save_to_uri(
        report=report,
        data=data,
        uri=args['uri'],
    )
    print(saved, str(dir(saved)))
    return saved.json()

@app.route('/sql2uri/schedule/<report>', methods=['PATCH'])
def schedule_report(report):
    """Schedules your report based on schedule parameter.

    If schedule is not provided or schedule is not valid, raises error.
    1. First you must create a rule
    2. Define a scheduled event source for a rate/cron of schedule
    3. Must use lambda function as target with a json blob of {'schedule': 'rate'}
    4. rule details such as name and description
    client.put_targets(Rule=get_scheduled_event_name,Targets=[{Id, Arn, Input}])

    """
    raise NotImplented
    json = request.json
    schedule = json.get('schedule')

    info_url = (
        'http://docs.aws.amazon.com/lambda/latest/dg/'
        'tutorial-scheduled-events-schedule-expressions.html'
    )
    if not schedule:
        raise ValueError(
            'Invalid Rate or Cron String: See\n%s\n for details:'
            % info_url
        )

    events = boto3.client('events')
    rule = [dict(
        name=report,
        function='app.view_report',
        function_kwargs=dict(report=report),
        expression=schedule,
        description='{} scheduled for {}'.format(report, schedule),
    )]
    try:
        Report.update_item(
            'schedule',
            value=schedule,
            action='put',
            file_name__eq=report)
        return "%s applied to %s" % (schedule, report)
    except UpdateError as err:
        raise(err)

@app.route('/sql2uri/unschedule/<report>', methods=['DELETE'])
def unschedule_report(report):
    """TODO: This requires update to ddb + boto call to cloudwatch secudler"""
    Report.update_item(
        'schedule',
        action='delete',
        file_name__eq=report
    )
    return "Unscheduled %s" % report

if __name__ == '__main__':
    DEBUG = False if env['STAGE'] == 'prod' else True
    app.run(debug=DEBUG, port=5002)
