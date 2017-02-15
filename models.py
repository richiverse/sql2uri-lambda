"""Pynamodb is similar to most ORMs in nature"""
from datetime import datetime
from os import environ as env

import boto3
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    UTCDateTimeAttribute)

class Report(Model):
    class Meta:
        # STAGE env always available in Zappa
        table_name = 'Report-%(stage)s' % dict(
            stage=env['STAGE'])
        region = boto3.Session().region_name
        read_capacity_units = 1
        write_capacity_units = 1

    file_name = UnicodeAttribute(hash_key=True)
    file_description = UnicodeAttribute()
    backend_name = UnicodeAttribute()
    options = UnicodeAttribute()
    schedule = UnicodeAttribute(null=True)
    uri = UnicodeAttribute(default='gdrive')
    created_by = UnicodeAttribute(default='')
    registered_on = UTCDateTimeAttribute(default=datetime.utcnow)
    approved_by = UnicodeAttribute(null=True)
    approved_on = UTCDateTimeAttribute(null=True)
