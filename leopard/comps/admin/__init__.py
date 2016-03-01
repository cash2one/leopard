from copy import deepcopy
from flask import request, redirect, url_for, flash, make_response
from flask.ext import admin
from flask.ext.admin import expose
from flask.ext.admin.base import AdminViewMeta, BaseView as origin_BaseView
from flask.ext.admin.babel import gettext
from flask.ext.admin.form import FormOpts
from flask.ext.admin.form import BaseForm as OriginBaseform
from flask.ext.admin._compat import string_types, with_metaclass
from flask.ext.admin.model.helpers import get_mdict_item_or_list
from flask.ext.admin.contrib.sqla import tools
from flask.ext.admin.contrib.sqla import ModelView as OriginModelview
from flask.ext.admin.helpers import get_form_data, is_form_submitted
from flask.ext.admin.actions import action
from flask.ext.restful.reqparse import RequestParser
from wtforms.ext.i18n.form import Form
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from leopard.comps.excel import export_xls
from leopard.core.config import get_config
from leopard.helpers import get_current_user, get_columns_by_model
from . import filters
from . import typefmt

translations_cache = {}

page_size_parser = RequestParser()
page_size_parser.add_argument('page_size', type=int, default=20)


def dict_merge(a, b):
    if not isinstance(b, dict):
        return b
    result = deepcopy(a)
    for k, v in b.items():
        if k in result and isinstance(result[k], dict):
                result[k] = dict_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


class BaseForm(OriginBaseform, Form):

    LANGUAGES = ['zh']


class BaseViewMetaclass(AdminViewMeta):
    config_cache = {}

    def __new__(cls, name, bases, attrs):
        module = attrs['__module__']
        if module not in cls.config_cache:
            try:
                cls.config_cache[module] = get_config(module) or {}
            except OSError:
                cls.config_cache[module] = {}
        try:
            config_attrs = cls.config_cache[module][name]
        except KeyError:
            config_attrs = {}
        return super(BaseViewMetaclass, cls).__new__(
            cls, name, bases, dict_merge(config_attrs, attrs))


class BaseView(with_metaclass(BaseViewMetaclass, origin_BaseView)):
    def __init__(self, name=None, category=None, endpoint=None, url=None,
                 static_folder=None, static_url_path=None, icon=None):
        self.icon = icon
        super(BaseView, self).__init__(name, category, endpoint, url,
                                       static_folder, static_url_path)


class ModelViewMetaclass(AdminViewMeta):
    config_cache = {}

    def __new__(cls, name, bases, attrs):
        module = attrs['__module__']
        if module not in cls.config_cache:
            try:
                cls.config_cache[module] = get_config(module) or {}
            except OSError:
                cls.config_cache[module] = {}
        try:
            config_attrs = cls.config_cache[module][name]
        except KeyError:
            config_attrs = {}
        return super(ModelViewMetaclass, cls).__new__(
            cls, name, bases, dict_merge(config_attrs, attrs))


class ModelView(with_metaclass(ModelViewMetaclass, OriginModelview)):
    filter_converter = filters.FilterConverter()
    column_type_formatters = dict(typefmt.BASE_FORMATTERS)

    form_base_class = BaseForm
    form_readonly_columns = []

    read_template = 'admin/model/read.html'

    get_match_all_query = None      #符合条件的所有查询值

    def __init__(self, model, session,
                 name=None, category=None, endpoint=None, url=None, icon=None):
        self.icon = icon
        super(ModelView, self).__init__(model, session, name,
                                        category, endpoint, url)

    def _refresh_cache(self):
        self._read_form_class = self.get_read_form()
        super(ModelView, self)._refresh_cache()

    def validate_form_on_submit(self, form):
        if not is_form_submitted():
            return False

        for f in form:
            if f.name in self.form_readonly_columns:
                form._fields.pop(f.name)

        return form.validate()

    def get_read_form(self):
        return self.get_form()

    def read_form(self, obj=None):
        return self._read_form_class(get_form_data(), obj=obj)

    @expose('/read/', methods=('GET', ))
    def read_view(self):
        return_url = request.args.get('url') or url_for('.index_view')

        if not self.can_read:
            return redirect(return_url)

        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)

        model = self.get_one(id)

        if model is None:
            return redirect(return_url)

        form = self.read_form(obj=model)

        form_leopard = FormOpts(widget_args=self.form_widget_args)

        return self.render(self.read_template,
                           model=model,
                           get_value=self.get_list_value,
                           form=form,
                           form_leopard=form_leopard,
                           return_url=return_url)

    def edit_form(self, obj=None):
        form = super(ModelView, self).edit_form(obj=obj)

        for f in form:
            if f.name in self.form_readonly_columns:
                f.readonly = True
        return form

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        """
            Edit model view
        """
        return_url = request.args.get('url') or url_for('.index_view')

        if not self.can_edit:
            return redirect(return_url)

        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)

        model = self.get_one(id)

        if model is None:
            return redirect(return_url)

        form = self.edit_form(obj=model)

        if self.validate_form_on_submit(form):
            if self.update_model(form, model):
                if '_continue_editing' in request.form:
                    flash(gettext('Model was successfully saved.'))
                    return redirect(request.url)
                else:
                    return redirect(return_url)

        form_leopard = FormOpts(widget_args=self.form_widget_args,
                                form_rules=self._form_create_rules)

        return self.render(self.edit_template,
                           model=model,
                           get_value=self.get_list_value,
                           form=form,
                           form_leopard=form_leopard,
                           return_url=return_url)

    def get_list(self, page, sort_column, sort_desc, search, filters,
                 execute=True):
        self.page_size = page_size_parser.parse_args()['page_size']

        joins = set()

        query = self.get_query()
        count_query = self.get_count_query()

        # Apply search criteria
        if self._search_supported and search:
            # Apply search-related joins
            if self._search_joins:
                for jn in self._search_joins.values():
                    query = query.join(jn)
                    count_query = count_query.join(jn)

                joins = set(self._search_joins.keys())

            # Apply terms
            terms = search.split(' ')

            for term in terms:
                if not term:
                    continue

                stmt = tools.parse_like_term(term)
                filter_stmt = [c.ilike(stmt) for c in self._search_fields]
                query = query.filter(or_(*filter_stmt))
                count_query = count_query.filter(or_(*filter_stmt))

        # Apply filters
        if filters and self._filters:
            for idx, value in filters:
                flt = self._filters[idx]
                if not value:
                    continue
                # Figure out joins
                tbl = flt.column.table.name

                join_tables = self._filter_joins.get(tbl, [])

                for table in join_tables:
                    if table.name not in joins:
                        query = query.join(table)
                        count_query = count_query.join(table)
                        joins.add(table.name)

                # Apply filter
                query = flt.apply(query, value)
                count_query = flt.apply(count_query, value)

        # Calculate number of rows
        count = count_query.scalar()

        # Auto join
        for j in self._auto_joins:
            query = query.options(joinedload(j))

        # Sorting
        if sort_column is not None:
            if sort_column in self._sortable_columns:
                sort_field = self._sortable_columns[sort_column]

                query, joins = self._order_by(query, joins, sort_field,
                                              sort_desc)
        else:
            order = self._get_default_order()

            if order:
                query, joins = self._order_by(query, joins, order[0], order[1])

        if self.get_match_all_query:
            self.get_match_all_query = None
        self.get_match_all_query = query

        # Pagination
        if page is not None:
            query = query.offset(page * self.page_size)

        query = query.limit(self.page_size)

        # Execute if needed
        if execute:
            query = query.all()

        return count, query

    def scaffold_filters(self, data):
        if isinstance(data, tuple):
            name, lable = data
        else:
            name = data
            lable = ''
        join_tables = []
        if isinstance(name, string_types):
            model = self.model

            for attribute in name.split('.'):
                value = getattr(model, attribute)
                if (hasattr(value, 'property') and
                        hasattr(value.property, 'direction')):
                    model = value.property.mapper.class_
                    table = model.__table__

                    if self._need_join(table):
                        join_tables.append(table)

                attr = value
        else:
            attr = name

        if attr is None:
            raise Exception('Failed to find field for filter: %s' % name)

        # Figure out filters for related column
        if hasattr(attr, 'property') and hasattr(attr.property, 'direction'):
            filters = []

            for p in self._get_model_iterator(attr.property.mapper.class_):
                if hasattr(p, 'columns'):
                    # TODO: Check for multiple columns
                    column = p.columns[0]

                    if column.foreign_keys or column.primary_key:
                        continue

                    visible_name = '%s / %s' % (self.get_column_name(
                        attr.prop.table.name), self.get_column_name(p.key))

                    type_name = type(column.type).__name__
                    flt = self.filter_converter.convert(type_name,
                                                        column,
                                                        visible_name)

                    if flt:
                        table = column.table

                        if join_tables:
                            self._filter_joins[table.name] = join_tables
                        elif self._need_join(table.name):
                            self._filter_joins[table.name] = [table.name]
                        filters.extend(flt)

            return filters
        else:
            columns = self._get_columns_for_field(attr)

            if len(columns) > 1:
                raise Exception('Can not filter more than on one column for \
                                %s' % name)

            column = columns[0]

            if self._need_join(column.table) and name not in \
                    self.column_labels:
                visible_name = '%s / %s' % (
                    self.get_column_name(column.table.name),
                    self.get_column_name(column.name)
                )
            else:
                if not isinstance(name, string_types):
                    visible_name = self.get_column_name(name.property.key)
                else:
                    visible_name = self.get_column_name(name)

            type_name = type(column.type).__name__

            if join_tables:
                self._filter_joins[column.table.name] = join_tables
            if lable:
                visible_name = lable
            flt = self.filter_converter.convert(
                type_name,
                column,
                visible_name,
                options=self.column_choices.get(name),
            )

            if flt and not join_tables and self._need_join(column.table):
                self._filter_joins[column.table.name] = [column.table]
            return flt


class AuthMixin(object):
    extra_condition_field = ''

    @property
    def can_read(self):
        return self.is_accessible('can_read')

    @property
    def can_edit(self):
        return self.is_accessible('can_edit')

    @property
    def can_create(self):
        return self.is_accessible('can_create')

    @property
    def can_delete(self):
        return self.is_accessible('can_delete')

    def is_accessible(self, behavior=None):
        user = get_current_user()
        if user:
            if user.is_super:
                return True
            if self.extra_condition_field and not \
                    getattr(user, self.extra_condition_field, False):
                return False
            view_name = self.__class__.__name__.lower()
            if behavior:
                return user.has_permission('{}.{}'.format(view_name, behavior))
            return user.has_permission('{}'.format(view_name))
        return False

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('admin.index'))


class ExportXlsMixin(object):
    key_map = {
        'withdraw': {
            'realname': 'user',
        },
        'deposit': {
            'realname': 'user',
        },
        'plan': {
        }
    }

    def save_foreign_value(self, column_values):
        columns_keys = get_columns_by_model(self.model)
        foreign_keys = [key for key in self.column_list if key
                        not in columns_keys]
        breaks = []
        for key in foreign_keys:
            for item in column_values:
                foreign_key = self.key_map[
                    self.model.__name__.lower()].get(key, '')
                if foreign_key:
                    item_foreign = getattr(item, foreign_key)
                    setattr(item, key, getattr(item_foreign, key))
                else:
                    breaks.append(key)
                    break
        for key in breaks:
            self.column_list.remove(key)
        return column_values

    def generate_xls(self, query):
        column_values = self.save_foreign_value(query)
        col_values = sorted(column_values, key=lambda x: x.id)
        xls_file = export_xls(self.column_list, self.column_labels, col_values)

        res = make_response(xls_file)
        res.headers['Content-Type'] = 'application/download'

        content_dis = 'attachment; filename="导出.xls"'.encode()
        res.headers['Content-Disposition'] = content_dis
        res.headers['Content-Transfer-Encoding'] = 'utf-8'
        return res

    @action('export_xls', '导出excel')
    def export_xls(self, ids):
        column_values = self.get_query().filter(self.model.id.in_(ids)).all()
        return self.generate_xls(column_values)

    @admin.expose('/export_all_xls')
    def export_all_xls(self):
        # column_values = self.get_query().all()
        column_values = self.get_match_all_query.all()
        return self.generate_xls(column_values)


class GetQueryOrderByidDescMixin(object):
    def get_query(self):
        query = super(self.__class__, self).get_query()
        query = query.order_by(self.model.id.desc())
        return query
