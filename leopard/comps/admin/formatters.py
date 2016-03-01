from flask import url_for
from jinja2 import escape, Markup

from leopard.core.config import get_config
from leopard.helpers.utils import float_quantize_by_two, get_enum

# FIXME Use 'leopard.comps.admin.formatters.yaml' instead.
config = get_config("leopard.services.auth")


def phone(view, context, model, name):
    property = getattr(model, name)
    if property:
        return Markup('<span style="cursor:pointer" class="needShowFullInfo" '
                      'data-full="{}">{}****{}</span>'.format(property,
                                                              property[:3],
                                                              property[-4:]))
    return ''


def amount(view, context, model, name):
    property = getattr(model, name)
    if property:
        if property >= 10000:
            return '{:.1f}万'.format(property / 10000)
        return '{:.1f}'.format(property)
    return 0


def user(view, context, model, name):
    property = getattr(model, name)
    if property:
        return Markup('<a href="{}" target="_blank">{}</a>'.format(
            url_for('user.read_view', id=property.id), escape(property)))
    return ''


def repayment(view, context, model, name):
    property = getattr(model, name)
    # property = property[0]
    if property:
        return Markup('<a href="{}" target="_blank">{}</a>'.format(
            url_for('repayment.read_view', id=property.id), escape(property)))
    return ''


def plans(view, context, model, name):
    property = getattr(model, name)
    data = ''
    for item in property:
        str = '<a href="{}" target="_blank">{}</a>'.format(
            url_for('plan.read_view', id=item.id), escape(item))
        data = data + str + ','
    return Markup(data)


def config_value(view, context, model, name):
    property = getattr(model, name)
    if len(property) > 80:
        fmt = ('<span style="cursor:pointer" class="needShowFullInfo" '
               'data-full="{}">{}...</span>')
        property = Markup(fmt).format(escape(property), escape(property[:80]))
    return property


def rate(view, context, model, name):
    attr = getattr(model, name)
    if model.nper_type == 100:
        attr *= 12
    else:
        attr *= 365
    return "{:.1f}%".format(float_quantize_by_two(attr))


def date(view, context, model, name):
    property = getattr(model, name)
    if property:
        msgfmt = ('<span style="cursor:pointer" class="needShowFullInfo" '
                  'data-full="{}">{}</span>')
        fmt = property.strftime('%Y年%m月%d日 %H:%M:%S')
        fmt2 = property.strftime('%Y年%m月%d日')
        return Markup(msgfmt.format(fmt, fmt2))
    return ''


def project(view, context, model, name):
    property = getattr(model, name)
    if property:
        return Markup('<a href="{}" target="_blank">{}</a>'.format(
            url_for('project.read_view', id=property.id), escape(property)))
    return ''


def application(view, context, model, name):
    property = getattr(model, name)
    if property:
        return Markup('<a href="{}" target="_blank">{}</a>'.format(
            url_for('success_application.read_view', id=property.id),
            escape(property)))
    return ''


def money(view, context, model, name):
    property = getattr(model, name)
    if property is None:
        return "-"
    if property:
        property = float_quantize_by_two(property)
        return "{:,.2f}".format(property)
    return "0.00"


def commission(view, context, model, name):
    property = getattr(model, name)
    if property:
        return "{}".format(float_quantize_by_two(float(property)))
    return ''


def card(view, context, model, name):
    property = getattr(model, name)
    if property:
        return Markup('<span style="cursor:pointer" class="needShowFullInfo" '
                      'data-full="{}">{}****{}</span>'.format(property,
                                                              property[:4],
                                                              property[-4:]))
    return ''


# FIXME Is model.logo safe?
def _list_thumbnail(view, context, model, name):
    if not model.logo:
        return ''
    return Markup('<img src="/{}" style="width:100px;height:100px;">'.format(
                  model.logo))


def bit_status(view, context, model, name):
    property = getattr(model, name)
    if property:
        return '通过'
    else:
        return '未通过'


def auth_fieldtype(view, context, model, name):
    property = getattr(model, name)
    if property:
        result = ''
        for item in property:
            result = result + item.name + ' '
        return result
    return '-'


def auth_field(view, context, model, name):
    property = getattr(model, name)
    if property:
        result = ''
        for item in property:
            result = result + item.type.name + ': ' + item.value + '<br>'
        return Markup(result)
    return '-'


def group_users(view, context, model, name):
    property = getattr(model, name)
    if property:
        result = ''
        for item in property[:-1]:
            result = result + item.username + ", "
        result += property[-1].username
        return Markup(result)
    return '-'


def groups(view, context, model, name):
    property = getattr(model, name)
    if property:
        result = ''
        for item in property[:-1]:
            result = result + item.name + ", "
        result += property[-1].name
        return Markup(result)
    return '-'


def birth_day(view, context, model, name):
    property = getattr(model, name)
    if property:
        fmt = ('<span style="cursor:pointer" class="needShowFullInfo" '
               'data-full="{}">{}</span>')
        return Markup(fmt.format(
            property.strftime('%Y-%m-%d'),
            property.strftime('%m-%d'))
        )
    return '-'


def banner(view, context, model, name):
    property = getattr(model, name)
    if property:
        return Markup('<img src="{}" style="width:300px;">'.format(property))
    else:
        return '无图片'


def banner_location(view, context, model, name):
    return get_enum('BANNER_LOCATION').get(model.location, '无效位置')


def firend_link_logic(view, context, model, name):
    switch = {
        'firendlink': '合作伙伴',
        'guarantee': '合作担保机构',
        'links': '友情链接',
    }
    return switch.get(model.logic, '无效位置')


def title(view, congtext, model, name):
    property = getattr(model, name)
    if len(property) > 30:
        property = property[:30] + '...'
    return property


def realname(view, context, model, name):
    return model.user.realname


def plan_borrowed(view, context, model, name):
    return model.investment.repayment.user


def finapplication_plan_borrowed(view, context, model, name):
    return model.application.user


def finapplication_plan_uid(view, context, model, name):
    return model.application.uid


def plan_tender(view, context, model, name):
    return model.investment.user


def invest_award(view, context, model, name):
    """投标奖励"""
    property = getattr(model, name)
    if property:
        return '{:.2f}%'.format(property * 100)
    return '-'
