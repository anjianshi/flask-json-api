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

    def __call__(self, var_name, *conv_args, **conv_kwargs):
        """
        var_name can be a sting, assign which variable in url should be converted;
        or a tuple, assign both variable name and the argument name when pass to API handler

        conv_args and conv_kwargs will pass to self.converter after var_value
        """
        if isinstance(var_name, tuple):
            from_, to = var_name
        else:
            from_ = to = var_name

        def decorator(f):
            @wraps(f)
            def decorated_function(**kwargs):
                var_value = kwargs.pop(from_)
                kwargs[to] = self.converter(var_value, *conv_args, **conv_kwargs)
                return f(**kwargs)
            return decorated_function
        return decorator