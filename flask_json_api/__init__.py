# -*- coding: utf-8 -*-

__version__ = 0.1
__all__ = ['APIManager', 'ExceptionHandler', 'ExceptionWrap', 'InvalidRequest', 'ResponseFormatter', 'APIJSONEncoder']

from functools import wraps
from flask import make_response, json, request


class APIManager(object):
    def __init__(self, app_or_blueprint=None):
        if app_or_blueprint:
            self.init_app(app_or_blueprint)
        else:
            self.app = None

        self.response_formatter = ResponseFormatter()
        self.exception_handler = ExceptionHandler()
        
        # 要对 API handler 应用的装饰器的列表。排序靠前的会先被调用
        #
        # 修改装饰器列表不会对已经注册了的 API handler 产生影响。
        # 因为装饰器被设计成在 API handler 刚注册时就应用于其上,
        # 而不是每次调用 API handler 时都读取这个列表并应用一次。（这样做是出于性能考虑)
        #
        # APIManager 把装饰好了的 API handler 交给 flask app 之后，会把 *原始* 的 API handler 当做返回值返回。
        # 就是说，这个函数再被 APIManager 装饰了之后，没有任何变化。
        # 这样做的好处是：
        #     一个 API handler 可以像调用普通函数那样调用另一个 API handler，
        #     不会有重复的 exception_handler 和 response_formatter 等步骤。
        # 不过也要注意，若想让某个装饰器在任何时候都起作用（例如 auth 装饰器就需要这样），
        # 就不能把它加到 APIManager 的装饰器列表里面去，只能让它作为一个普通的装饰器， 手动添加到 API handler 前
        self.decorators = [
            self.response_formatter,
            self.exception_handler
        ]

    def init_app(self, app_or_blueprint):
        self.app = app_or_blueprint

    def __call__(self, rule, **rule_kwargs):
        """注册新 API handler"""
        def decorator(f):
            def decorated_function(*args, **kwargs):
                return f(*args, **kwargs)

            for decorator in self.decorators:
                decorated_function = decorator(decorated_function)
            decorated_function = wraps(f)(decorated_function)

            self.app.add_url_rule(rule, None, decorated_function, **rule_kwargs)

            return f
        return decorator


# ==============================

class ExceptionHandler(object):
    """ExceptionHandler 只处理与 HTTPException 或与其兼容的 exception 对象（至少要包含 code 字段）
    exception 对象的 code 和 description 字段
    """

    def __init__(self):
        self.registered_exceptions = []

    def __call__(self, f):
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                if hasattr(e, 'api_status'):
                    return make_response(e.message, e.api_status)
                else:
                    for wrapper in self.registered_exceptions:
                        if isinstance(e, wrapper.exception_class):
                            return make_response(wrapper.message if wrapper.message is not None else e.message,
                                                 wrapper.api_status)

                    # can't understand this exception, raise it again
                    raise e
        return decorated_function

    def register_exception(self, *args, **kwargs):
        """若需要 ExceptionHandler 处理一个没有 api_status 属性 exception 对象(例如它来自第三方类库)，
        可以调用此方法，把它提交给 ExceptionHandler，并指明对应的 api_status
        这样 ExceptionHandler 就知道该如何处理它了
        （你也可以自己构造一个 ExceptionWrapper 对象，插入到 ExceptionHandler 的 registered_exceptions 属性里）

        另外，此方法还有一个用途：给指定类型的 exception 对象设定默认 message"""
        self.registered_exceptions.append(ExceptionWrapper(*args, **kwargs))


class ExceptionWrapper(object):
    def __init__(self, exception_class, api_status=500, message=None):
        self.exception_class = exception_class
        self.api_status = api_status
        self.message = message


class InvalidRequest(Exception):
    """当用户请求不合法时，统一抛出此异常(如：json 格式错误，表单值)"""
    api_status = 400


# ================================

class ResponseFormatter(object):
    """把 API handler 的返回值转换成 JSON
    如果用户的请求参数中包含 "callback"(例如：http://url?callback=xxx)，则把返回值格式化成 JSONP
    """

    def __init__(self):
        # 用户可以创建自定义的 formatter，以处理默认的 json_encoder 无法处理的数据类型
        #
        # 创建 formatter 时，如果需要，可以给它指定一个数据类型。这样，json_encoder 就只会在要处理的值与指定类型是同一分类或是其子类时，
        # 调用 formatter
        #
        # 如果没有给 formatter 指定数据类型，则每处理一个值，都会调用它。适用于一个 formatter 要处理多种数据类型的情况。
        #
        # 不过要注意，在这种情况下，如果 formatter 发现一个值不应由它来处理，它必须抛出一个 TypeError 异常，
        # 这样系统才能了解情况，并把值传给下一个 formatter。
        # 否则，无论 formatter 返回什么(包括 None)，系统都会认为这个值就是正确的计算结果，并将其返回
        self.formatters = []
        self.flask_json_encoder = json.JSONEncoder()

    def __call__(self, f):
        def decorated_function(*args, **kwargs):
            json_str = json.dumps(f(*args, **kwargs), default=self._default)
            callback = request.args.get('callback', False)
            if callback:
                return str(callback) + '(' + json_str + ')', 200, {'Content-Type': 'application/javascript'}
            else:
                return json_str, 200, {'Content-Type': 'application/json'}
        return decorated_function

    def _default(self, o):
        for formatter in self.formatters:
            if isinstance(formatter, tuple):
                if isinstance(o, formatter[0]):
                    return formatter[1](o)
            else:
                try:
                    return formatter(o)
                except TypeError:
                    pass
        return self.flask_json_encoder.default(o)

    def register(self, formatter, target_class=None):
        if target_class:
            self.formatters.append((target_class, formatter))
        else:
            self.formatters.append(formatter)