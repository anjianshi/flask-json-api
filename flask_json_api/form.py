# -*- coding: utf-8 -*-
"""
使用此模块需要 wtforms_alchemy
"""

__all__ = ['APIForm', 'ModelForm', 'ModelEditForm']

from flask import request, current_app
import datetime
from werkzeug.datastructures import MultiDict
import collections
from werkzeug.exceptions import BadRequest

import wtforms
from wtforms_alchemy import model_form_factory


# =============================
#   自定义 wtforms Form 对象
# =============================

class APIForm(wtforms.Form):
    def __init__(self, auto_validate=True, **kwargs):
        # 当表单用于修改某个已存在的 model 对象时，需要把这个对象通过 obj 参数传进来 ( TheForm(obj=xxx) )，
        # 不然 wtforms-components 的 unique validator 会检查失败
        #
        # 这样做的另一个好处是：当 form 中某个可选字段未被赋值时，会自动从 model 实体中提取值并填充进去。
        # 这样就不用再费心判断这个字段到底是没赋值还是被有意设成空值的了
        #
        # 注：wtforms-components 由 wtforms-alchemy 引入，用于完善 Field 和 validator 支持
        #
        # 貌似 wtforms-alchemy 对 obj 的处理还不够完善，创建实体时因为无法指定 obj ，导致验证总是会失败
        # 只好通过下面的代码，补上一个 self._obj 属性
        if not hasattr(self, '_obj'):
            self._obj = None

        if request.get_json() is not None:
            # 解决 WTForms 不支持 json 形式的表单值的问题
            formdata = MultiDict(_flatten_json(request.json))
        else:
            formdata = request.form
        super(APIForm, self).__init__(formdata, **kwargs)

        if auto_validate:
            self.validate()

    def validate(self):
        """验证失败时自动报错"""
        if not super(APIForm, self).validate():
            if current_app.confit['DEBUG']:
                print('Form validate failed：')
                print(self.errors)
            raise BadRequest('Form validate failed')


# 用于解决 WTForms 不支持 json 形式的表单值的问题
def _flatten_json(json, parent_key='', separator='-'):
    """Flattens given JSON dict to cope with WTForms dict structure.

    :param json: json to be converted into flat WTForms style dict
    :param parent_key: this argument is used internally be recursive calls
    :param separator: default separator

    Examples::

        flatten_json({'a': {'b': 'c'}})
        >>> {'a-b': 'c'}
    """
    if not isinstance(json, collections.Mapping):
        raise BadRequest('This function only accepts dict-like data structures.')

    items = []
    for key, value in json.items():
        new_key = parent_key + separator + key if parent_key else key
        if isinstance(value, collections.MutableMapping):
            items.extend(_flatten_json(value, new_key, separator).items())
        elif isinstance(value, list):
            items.extend(_flatten_json_list(value, new_key, separator))
        else:
            value = _format_value(value)
            items.append((new_key, value))
    return dict(items)


def _flatten_json_list(json, parent_key='', separator='-'):
    items = []
    i = 0
    for item in json:
        new_key = parent_key + separator + str(i)
        if isinstance(item, list):
            items.extend(_flatten_json_list(item, new_key, separator))
        elif isinstance(item, dict):
            items.extend(_flatten_json(item, new_key, separator).items())
        else:
            item = _format_value(item)
            items.append((new_key, item))
        i += 1
    return items


def _format_value(value):
    """wtforms 有些 field 只能处理字符串格式的值，无法处理 python/json 类型的值

    此函数把这些无法被处理的值转换成每种字段对应的字符串形式"""
    if value is None:
        return ''
    if isinstance(value, datetime.datetime):
        return value.isoformat().split(".").pop(0)
    if isinstance(value, int) or isinstance(value, float):
        # 若不把数字类型转换为 str ，InputValidator() 会把 0 值视为未赋值，导致验证失败
        return str(value)
    return value


# ======================================
#    自定义 WTForms-alchemy ModelForm
# ======================================

ModelForm = model_form_factory(APIForm, strip_string_fields=True)


class _APIEditForm(APIForm):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, '_obj'):
            raise ValueError("""当前表单是编辑实体用的表单，应传入对应的实体对象以避免 unique 检查失败。
                请通过命名参数的形式传递，即： TheForm(obj=instance) ，不要直接传递。
                如果确实不需要传入 obj 参数，请这样： TheForm(obj=None)""")
        super(_APIEditForm, self).__init__(*args, **kwargs)


ModelEditForm = model_form_factory(_APIEditForm,
                                   strip_string_fields=True,
                                   all_fields_optional=True)