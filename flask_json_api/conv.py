# -*- coding: utf-8 -*-

__all__ = ['URLVarConverter']

from functools import wraps


class URLVarConverter(object):
    """
    generate URL variable converter
    this is different from Flask's route converter, it's use as a decorator

    example:
    @URLVarConverter
    def sum_conv(value, another_num):
        return value + another_num

    @api('/<num>')
    @sum_conv(('num', 'computed_num'), 10)
    def get_sum(computed_num):
        return computed_num
    """

    def __init__(self, f):
        self.converter = f

    def __call__(self, orig_var_name, target_var_name, *conv_args, **conv_kwargs):
        """
        if 'target_var_name' set to None, will set it's value same as 'orig_var_name'

        conv_args and conv_kwargs will pass to self.converter after var_value
        """
        if target_var_name is None:
            target_var_name = orig_var_name

        def decorator(f):
            @wraps(f)
            def decorated_function(**kwargs):
                var_value = kwargs.pop(orig_var_name)
                kwargs[target_var_name] = self.converter(var_value, *conv_args, **conv_kwargs)
                return f(**kwargs)
            return decorated_function
        return decorator