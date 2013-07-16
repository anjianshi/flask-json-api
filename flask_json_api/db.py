# -*- coding: utf-8 -*-
"""
use utils in this module, need flask-sqlalchemy

add as_dict() method, to resolve SQLAlchemy doesn't support translate model to dict, 
and then can't serialization it to json's problem

add a __api_args__ property help implement new feature

and other utils

"""

__all__ = ['get_instance', 'model_conv']

import flask.ext.sqlalchemy
from sqlalchemy.orm import Query
from sqlalchemy.util import KeyedTuple
from conv import RouteConverter


def get_instance(app):
    return flask.ext.sqlalchemy.SQLAlchemy(app)


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

# store custome args:
#'    exclude_columns': []      the columns should exclude when call as_dict()
flask.ext.sqlalchemy.Model.__api_args__ = None


def _query_as_dict(self, **kwargs):
    for row in self:
        yield row.as_dict(**kwargs)
Query.as_dict = _query_as_dict


# KeyedTuple is the return value of a query that has 'join' condition
# actually，it already has a method called _asdict(), but it's return value
# doesn't meet the requirements
def _keyed_tuple_as_dict(self, **kwargs):
    result = {}
    for key, value in self._asdict().iteritems():
        if isinstance(value, flask.ext.sqlalchemy.Model):
            result.update(value.as_dict(**kwargs))
        else:
            result[key] = value
    return result
KeyedTuple.as_dict = _keyed_tuple_as_dict


# ==================================

@RouteConverter
def model_conv(id, model):
    instance = model.query.get(id)
    if instance is None:
        raise InvalidRequest('{}(id={})不存在，请求不合法'.format(model.__name__, id))
    return instance