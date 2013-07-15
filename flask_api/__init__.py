# -*- coding: utf-8 -*-

__version__ = 0.1
__all__ = ['APIManager', 'ExceptionHandler', 'RegisteredException', 'ResponseFormatter', 'APIJSONEncoder']

from functools import wraps
from flask import make_response, json


class APIManager(object):
    app = None

    # decorators that will be applied to API handler
    # front weill be applied earlier
    # 
    # for performance, decorators will be applied when API handlers register,
    # rather than when API handler be called.
    # so change this property won't affect API handlers that already registered
    #
    # after all decorators be applied, the origin function will be returned (not the decorated one, just origin)
    # so, you can call that function as well as it hasn't be decorated. no exception handle, no response format...
    # and if you want a decorator be effictive all the time(regardless call like an API handler or normal function),
    # you should add it manually, dont't add it in this decorators list
    # example: auth decorator is the one should add manually
    decorators = None

    # default decorators
    exception_handler = None
    response_formatter = None

    def init_app(self, app_or_blueprint):
        self.app = app_or_blueprint

        self.exception_handler = ExceptionHandler()
        self.response_formatter = ResponseFormatter()

        self.decorators = [
            self.response_formatter,
            self.exception_handler
        ]

    def __call__(self, *args, **kwargs):
        return self.register(*args, **kwargs)

    def register(self, rule):
        """ register new API handler """
        def decorator(f):
            def decorated_function(*args, **kwargs):
                return f(*args, **kwargs)

            for decorator in self.decorators:
                decorated_function = decorator(decorated_function)
            decorated_function = wraps(f)(decorated_function)

            self.app.add_url_rule(rule, None, decorated_function)

            return f
        return decorator


# ==============================

class ExceptionHandler(object):
    def __init__(self):
        self.registered_exceptions = [
            # todo: add pre registered exceptions
        ]

    def __call__(self, f):
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                # notice: only exceptions that is the instance of the sub-class of Exception, will be handle
                for registered_exception in self.registered_exceptions:
                    if isinstance(e, registered_exception.exception_class):
                        return make_response(registered_exception.message,
                                             registered_exception.http_status)

                # if no registered_exception matched, raise the exception again
                raise e
        return decorated_function

    def register_exception(*args, **kwargs):
        self.registered_exceptions.append(_RegisteredException(*args, **kwargs))


class RegisteredException(object):
    def __init__(self, exception_class, http_status=500, message=''):
        self.exception_class = exception_class
        self.http_status = http_status
        self.message = message


# ================================

class ResponseFormatter(object):
    """format API handler's return value to JSON or JSONP
    if there's a query param called "callback"(eg.  http://url?callback=xxx), format to JSONP
    else JSON
    """
    def __init__(self, json_encoder_cls=None):
        self.json_encoder_cls = json_encoder_cls or APIJSONEncoder

    def __call__(self, f):
        def decorated_function(*args, **kwargs):
            json_str = json.dumps(f(*args, **kwargs), cls=self.json_encoder_cls)
            callback = request.args.get('callback', False)
            if callback:
                return str(callback) + '(' + json_str + ')', 200, {'Content-Type': 'application/javascript'}
            else:
                return json_str, 200, {'Content-Type': 'application/json'}
        return decorated_function


class APIJSONEncoder(json.JSONEncoder):
    def default(self, o):
        # support Decimal （already known "db join query" sometimes include values of this type）
        if isinstance(o, Decimal):
            return float(o)

        # support generator
        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)

        return json.JSONEncoder.default(self, o)