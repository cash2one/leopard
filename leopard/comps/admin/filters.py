import datetime

from sqlalchemy import cast, Date

from flask.ext.admin.contrib.sqla import tools
from flask.ext.admin.contrib.sqla.filters import BaseSQLAFilter
from flask.ext.admin.model import filters


class Base(BaseSQLAFilter):

    def __init__(self, column, name, options=None, data_type=None):

        super(BaseSQLAFilter, self).__init__(name, options, data_type)

        self.column = column


class FilterEqual(Base):
    def apply(self, query, value):
        return query.filter(self.column == value)

    def operation(self):
        return '等于'

    def __str__(self):
        return self.name


class FilterNotEqual(Base):
    def apply(self, query, value):
        return query.filter(self.column != value)

    def operation(self):
        return '不等于'

    def __str__(self):
        return self.name


class FilterLike(Base):
    def apply(self, query, value):
        stmt = tools.parse_like_term(value)
        return query.filter(self.column.ilike(stmt))

    def operation(self):
        return '包含'

    def __str__(self):
        return self.name


class FilterNotLike(Base):
    def apply(self, query, value):
        stmt = tools.parse_like_term(value)
        return query.filter(~self.column.ilike(stmt))

    def operation(self):
        return '不包含'

    def __str__(self):
        return self.name


class FilterGreater(Base):
    def apply(self, query, value):
        return query.filter(self.column > value)

    def operation(self):
        return '大于'

    def __str__(self):
        return self.name


class FilterSmaller(Base):
    def apply(self, query, value):
        return query.filter(self.column < value)

    def operation(self):
        return '小于'

    def __str__(self):
        return self.name


class FilterDatetimeLike(Base):

    def apply(self, query, value):
        value = value.split('-')
        today = datetime.date(int(value[0]), int(value[1]), int(value[2][0:2]))
        return query.filter(cast(self.column, Date) == today)

    def operation(self):
        return '等于'

    def __str__(self):
        return self.name


class FilterDatetimeNotLike(Base):

    def apply(self, query, value):
        value = value.split('-')
        today = datetime.date(int(value[0]), int(value[1]), int(value[2][0:2]))
        return query.filter(cast(self.column, Date) != today)

    def operation(self):
        return '不等于'

    def __str__(self):
        return self.name


# Customized type filters
class BooleanEqualFilter(FilterEqual, filters.BaseBooleanFilter):
    pass


class BooleanNotEqualFilter(FilterNotEqual, filters.BaseBooleanFilter):
    pass


class FilterConverter(filters.BaseFilterConverter):
    strings = (FilterEqual, FilterNotEqual, FilterLike, FilterNotLike)
    numeric = (FilterEqual, FilterNotEqual, FilterGreater, FilterSmaller)
    datetime_filter = (FilterDatetimeLike, FilterDatetimeNotLike,
                       FilterGreater, FilterSmaller)
    bool = (BooleanEqualFilter, BooleanNotEqualFilter)
    enum = (FilterEqual, FilterNotEqual)

    def convert(self, type_name, column, name, **kwargs):
        if type_name in self.converters:
            return self.converters[type_name](column, name, **kwargs)

        return None

    @filters.convert('String', 'Unicode', 'Text', 'UnicodeText')
    def conv_string(self, column, name, **kwargs):
        return [f(column, name, **kwargs) for f in self.strings]

    @filters.convert('Boolean')
    def conv_bool(self, column, name, **kwargs):
        return [f(column, name, **kwargs) for f in self.bool]

    @filters.convert('Integer', 'SmallInteger', 'Numeric', 'Float',
                     'BigInteger')
    def conv_int(self, column, name, **kwargs):
        return [f(column, name, **kwargs) for f in self.numeric]

    @filters.convert('Date')
    def conv_date(self, column, name, **kwargs):
        return [f(column, name, data_type='datepicker', **kwargs) for f
                in self.numeric]

    @filters.convert('DateTime')
    def conv_datetime(self, column, name, **kwargs):
        return [f(column, name, data_type='datetimepicker', **kwargs) for f
                in self.datetime_filter]

    @filters.convert('Enum', 'ENUM')
    def conv_enum(self, column, name, options=None, **kwargs):
        if not options:
            options = [
                (v, v)
                for v in column.type.enums
            ]
        return [f(column, name, options, **kwargs) for f in self.enum]
