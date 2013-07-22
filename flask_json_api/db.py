# -*- coding: utf-8 -*-
"""
使用此模块需要 flask-sqlalchemy
"""

__all__ = ['get_instance', 'model_conv', 'validate_logic', 'validator']

import flask.ext.sqlalchemy
from sqlalchemy.orm import Query, validates as _orm_validates
from sqlalchemy.util import KeyedTuple

from conv import URLVarConverter
from werkzeug.exceptions import BadRequest


def get_instance(app):
    return flask.ext.sqlalchemy.SQLAlchemy(app)


# 此属性用来存放此模块用到的配置:
#   'exclude_columns': []      调用 as_dict() 时默认要排除的 column
flask.ext.sqlalchemy.Model.__api_args__ = None


# ===== as_dict ====================

def _model_as_dict(self, exclude=None, only=None):
    if exclude is None and only is None and self.__api_args__ is not None and 'exclude_columns' in self.__api_args__:
        exclude = self.__api_args__['exclude_columns']

    if exclude:
        # 若 exclude 和 only 同时被赋值，只考虑 exclude
        only = None
        if not isinstance(exclude, list):
            exclude = [exclude]
    elif only and not isinstance(only, list):
        only = [only]

    d = {}
    for column in self.__table__.columns:
        colname = column.name
        if (exclude and colname in exclude) or (only and colname not in only):
            continue
        d[colname] = getattr(self, colname)
    return d
flask.ext.sqlalchemy.Model.as_dict = _model_as_dict


def _query_as_dict(self, **kwargs):
    for row in self:
        yield row.as_dict(**kwargs)
Query.as_dict = _query_as_dict


# 包含 'join' 的 query 的返回值中，通常会包含 KeyedTuple
# 其实这个类型已经有一个类似的叫 _asdict() 的方法了，但是它的返回值不太符合需求
def _keyed_tuple_as_dict(self, **kwargs):
    result = {}
    for key, value in self._asdict().iteritems():
        if isinstance(value, flask.ext.sqlalchemy.Model):
            result.update(value.as_dict(**kwargs))
        else:
            result[key] = value
    return result
KeyedTuple.as_dict = _keyed_tuple_as_dict


# ===== simple validators ==========

validate_logic = {
    'min': lambda value, min: value is None or value >= min,
    'max': lambda value, max: value is None or value <= max,
    'min_length': lambda value, min: value is None or len(value) >= min,
}


def validator(columns, logic_name, *logic_args, **kwargs):
    if not isinstance(columns, list):
        columns = [columns]

    if isinstance(logic_name, str):
        logic = validate_logic[logic_name]
    else:
        logic = logic_name
        logic_name = 'lambda'

    @_orm_validates(*columns, **kwargs)
    def f(self, key, value):
        # 如果字段值为 None，不进行检查，由 sqlalchemy 根据字段的 nullable 属性确定是否合法
        if value is not None and not logic(value, *logic_args):
            args = []
            for arg in logic_args:
                args.append(str(arg))

            raise BadRequest(
                'db model validate failed: key={}, value={}, logic={}, arg={}'.format(
                    key, value, logic_name, ','.join(args)))
        return value

    return f



# ==================================

@URLVarConverter
def model_conv(id, model):
    instance = model.query.get(id)
    if instance is None:
        raise BadRequest('{}(id={})不存在，请求不合法'.format(model.__name__, id))
    return instance