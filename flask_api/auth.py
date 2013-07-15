# -*- coding: utf-8 -*-

from functools import wraps

class AuthManager(object):
    __abstract__ = True

    def __init__(self, app):
        self.app = app
        app.before_request(self.prepare)

    def __call__(self, *verify_args, **verify_kwargs):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                self.prepare(*verify_args, **verify_kwargs)
                f(*args, **kwargs)
            return decorated_function;
        return decorator

    def prepare(self):
        """do something like: check if user is login, configure session, etc"""
        pass

    def login(self):
        pass

    def logout(self):
        pass

    def verify(self):
        """check if current user has auth to call this API
        raise a exception when failed"""
        pass


class UnauthorizedError(Exception):
    api_status = 401



ANONYMOUS_SIGN = 1
ADMIN_SIGN = 2
EMPLOYEE_SIGN = 4
CUSTOMER_SIGN = 8


class SessionAuthManager(AuthManager):
    sign = None
    customer_id = None

    def prepare(self):
        session.permanent = True

        if 'auth' in session and 'sign' in session['auth']:
            self.sign = session['auth']['sign']
            if self.sign == CUSTOMER_SIGN:
                self.customer_id = session['auth']['customer_id']

    def login(self, sign, customer_id=None):
        session['auth'] = {}
        session.modified = True

        self.sign = session['auth']['sign'] = sign
        self.customer_id = session['auth']['customer_id'] = 
            customer_id if self.sign == CUSTOMER_SIGN else None

    def logout(self):
        if 'auth' in session:
            del session['auth']
            session.modified = True
            self.sign = self.customer_id = None

    def verify(self, expect_sign):
        if sign is None or (expect_sign & self.sign) != self.sign:
            raise UnauthorizedError()