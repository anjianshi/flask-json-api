# -*- coding: utf-8 -*-
"""
use utils in this module, need wtforms_alchemy
"""

__all__ = ['FormValidateFailed', 'APIForm', 'ModelForm', 'ModelEditForm']

from flask import request, json
import datetime
from werkzeug.datastructures import MultiDict
import collections
from . import InvalidRequest

import wtforms
from wtforms_alchemy import model_form_factory


# =============================
#   自定义 Form 对象
# =============================


class FormValidateFailed(Exception):
    api_status = 400


class APIForm(wtforms.Form):
    def __init__(self, auto_validate=True, **kwargs):
        #    当表单用于修改某个已存在的 model 对象时，需要把这个对象通过 obj 参数传进来 ( TheForm(obj=xxx) )，
        # 不然 wtforms-components 的 unique validator 会检查失败
        #    这样做的另一个好处是：当 form 中某个可选字段未被赋值时，会自动从 model 实体中提取值并填充进去。
        # 这样就不用再费心判断这个字段到底是没赋值还是被有意设成空值的了
        #    注：wtforms-components 由 wtforms-alchemy 引入，用于完善 Field 和 validator 支持
        #
        #    貌似 wtforms-alchemy 对 obj 的处理还不够完善，创建实体时因为无法指定 obj ，导致验证总是会失败
        # 只好通过下面的代码，补上一个 self._obj 属性
        if not hasattr(self, '_obj'):
            if isinstance(self, ModelEditForm):
                raise ValueError("""当前表单是编辑实体用的表单，应传入对应的实体对象以避免 unique 检查失败。
                请通过命名参数的形式传递，即： TheForm(obj=instance) ，不要直接传递。
                如果确实不需要传入 obj 参数，请这样： TheForm(obj=None)""")
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
        """验证失败时自动抛出错误"""
        if not super(APIForm, self).validate():
            print(self.errors)
            raise FormValidateFailed()


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
        raise InvalidRequest('This function only accepts dict-like data structures.')

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


# 修改 StringField 的 process_formdata 在未传值时的行为。
# StringField ，在未传值的情况下默认会把字段值设成空字符串。导致
def _string_field_process_formdata(self, valuelist):
    if valuelist:
        self.data = valuelist[0]
wtforms.StringField.process_formdata = _string_field_process_formdata


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


# 提交表单时，有的字段是有意提交空值(url?a=&b=val)，有的字段是根本没提交(url?b=val)
# 通常，提交空值是想把数据库中的对应字段设为 null，不提交则是根本不想对字段值进行更改
# 而 WTForms 的 populate_obj 方法把第二种情况也当做第一种对待，结果提交表单时若省略某个字段，
# 数据库里的对应值就会被设为 null
# 这里的修正办法：通过检查字段的 raw_data 来判断到底是哪种情况，然后进行相应处理。
# todo: 但这个办法对使用了自己的 populate_obj 方法的 field (FormField, FieldList...)可能无效，需要测试一下
#
# 注释：
#   空值时，raw_data == ['']；没提交时，raw_data == []
#   另外有两种特殊情况：提交的表单完全为空，或是通过 obj 参数给表单赋值时，raw_data 为 None
def _populate_obj(self, obj, name):
    if name in obj.__table__.columns:  # 有时表单中会包含一些 model 里没有的辅助用的字段，这些字段的值不应写入 model 里
        if self.data or (isinstance(self.raw_data, list) and len(self.raw_data)):
            setattr(obj, name, self.data)
wtforms.Field.populate_obj = _populate_obj


# 修正时区。
# todo: 对时区的校正有待完善
def _DateTime_process_formdata(self, valuelist):
    if valuelist:
        date_str = ' '.join(valuelist)
        try:
            d = datetime.datetime.strptime(date_str, self.format)
            d2 = datetime.timedelta(hours=8)
            d = d - d2
            self.data = d
        except ValueError:
            self.data = None
            raise ValueError(self.gettext('Not a valid datetime value'))
wtforms.DateTimeField.process_formdata = _DateTime_process_formdata


# =================================
#    ModelForm
# =================================

ModelForm = model_form_factory(APIForm,
                               strip_string_fields=True)

ModelEditForm = model_form_factory(APIForm,
                                   strip_string_fields=True,
                                   all_fields_optional=True)