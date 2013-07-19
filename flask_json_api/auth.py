# -*- coding: utf-8 -*-

from functools import wraps
from flask import session
from werkzeug.exceptions import Unauthorized


class AuthManager(object):
    __abstract__ = True

    def __init__(self, app):
        self.app = app

        @app.before_request
        def auth_prepare():
            self.prepare()

    def __call__(self, *verify_args, **verify_kwargs):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                self.verify(*verify_args, **verify_kwargs)
                return f(*args, **kwargs)
            return decorated_function
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


class SessionAuthManager(AuthManager):
    """AuthManager 的 session 实现
    sign 指当前访客的身份类型。它是由用户定义的，每种身份类型需对应一个数字
    若某个 API handler 允许多种身份的人访问，可把这个多个身份类型的值按位运算，传给此对象
    """

    def __init__(self, app):
        self.sign = None
        self.extra_data = None

        super(SessionAuthManager, self).__init__(app)

    def prepare(self):
        session.permanent = True

        if 'auth' in session and 'sign' in session['auth']:
            self.sign = session['auth']['sign']
            self.extra_data = session['auth']['extra_data']
        else:
            self.sign = self.extra_data = None

    def login(self, sign, extra_data=None):
        session['auth'] = {}
        session.modified = True

        self.sign = session['auth']['sign'] = sign
        self.extra_data = session['auth']['extra_data'] = extra_data

    def logout(self):
        if 'auth' in session:
            del session['auth']
            session.modified = True
            self.sign = self.extra_data = None

    def verify(self, expect_sign):
        """若要使所有访客都能访问此 API，可把 expect_sign 设为 None，或者不对此 API 应用 auth 装饰器(不推荐，容易疏忽犯错)"""
        if expect_sign is None:
            return

        if self.sign is None or (expect_sign & self.sign) != self.sign:
            raise Unauthorized()