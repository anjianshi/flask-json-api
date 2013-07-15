# -*- coding: utf-8 -*-

__version__ = 0.1
__all__ = ['APIManager', 'ExceptionHandler', 'ExceptionWrap', 'ResponseFormatter', 'APIJSONEncoder']

from functools import wraps
from flask import make_response, json
import decimal


class APIManager(object):
    def __init__(self):
        self.app = None

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
        self.decorators = None

        # default decorators
        self.exception_handler = None
        self.response_formatter = None


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
    """the exception that has property "api_status", will be treat
    "api_status" means http status, it's value like 404, 500, etc

    if an exception need to be treat, but is not raised by API handler itself(eg. raised by 3rd library ), 
    and you can't change it to have the "api_status" property, you can call "register_exception" method, 
    register the exception into ExceptionHandler, then it will known how to handle it

    after all, only exceptions that is the instance of Exception(or it's sub-class), will be treat
    """

    def __init__(self):
        self.registered_exceptions = []

    def __call__(self, f):
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                if e.api_status:
                    return make_response(e.message, e.api_status)
                else:
                    for registered_exception in self.registered_exceptions:
                        if isinstance(e, registered_exception.exception_class):
                            return make_response(registered_exception.message,
                                                 registered_exception.api_status)

                    # can't understand this exception, raise it again
                    raise e
        return decorated_function

    def register_exception(self, *args, **kwargs):
        self.registered_exceptions.append(ExceptionWrap(*args, **kwargs))


class ExceptionWrap(object):
    def __init__(self, exception_class, api_status=500, message=''):
        self.exception_class = exception_class
        self.api_status = api_status
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
        # support Decimal （already known "sqlalchemy db join query" sometimes include values of this type）
        if isinstance(o, decimal.Decimal):
            return float(o)

        # support generator
        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)

        return json.JSONEncoder.default(self, o)