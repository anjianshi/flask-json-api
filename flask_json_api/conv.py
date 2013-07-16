# -*- coding: utf-8 -*-

__all__ = ['RouteConverter']

from functools import wraps


class RouteConverter(object):
    """
    generate route converter
    this is different from Flask's route converter, it's use as a decorator

    example:
    @RouteConverter
    def sum_conv(value, another_num):
        return value + another_num

    @api('/<num>')
    @sum_conv(('num', 'computed_num'), 10)
    def get_sum(computed_num):
        return computed_num
    """

    def __init__(self, f):
        self.converter = f

    def __call__(self, from_, to, *conv_args, **conv_kwargs):
        """
        if 'to' set to None, will set it's value same as 'from_'

        conv_args and conv_kwargs will pass to self.converter after var_value
        """
        if to is None:
            to = from_

        def decorator(f):
            @wraps(f)
            def decorated_function(**kwargs):
                var_value = kwargs.pop(from_)
                kwargs[to] = self.converter(var_value, *conv_args, **conv_kwargs)
                return f(**kwargs)
            return decorated_function
        return decorator