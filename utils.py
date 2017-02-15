from os import environ as env
from functools import partial
import random
import string

try:
    from jose import jwt
except ImportError:
    pass

try:
    encrypt = partial(jwt.encode, key=env['SQL_SECRET'], algorithm='HS256')
    decrypt = partial(jwt.decode, key=env['SQL_SECRET'], algorithms=['HS256'])
except TypeError:
    pass

def generate_secret(size=64):
    return ''.join(
        random.SystemRandom().choice(
        string.ascii_letters + string.digits)
        for _ in range(size)
    )
