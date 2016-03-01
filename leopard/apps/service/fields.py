import datetime

from calendar import timegm
from email.utils import formatdate

from flask.ext.restful import fields
from flask.ext.restful.fields import Raw


def rfc822(dt):
    return formatdate(timegm(dt.timetuple()))


class LocalDateTime(Raw):

    def format(self, value):
        try:
            return value.isoformat()
        except Exception as e:
            raise e


class Timestamp(Raw):

    def format(self, value):
        return formatdate(timegm(datetime.datetime.fromtimestamp(value).
                                 timetuple()))


class UserNameMosaic(Raw):

    def format(self, value):
        return value.username[:2] + '**' + value.username[-1:]


class StringMosaic(Raw):

    def format(self, value):
        return value[:1] + '**' + value[-1:]


class PhoneMosaic(Raw):

    def format(self, value):
        return value[:3] + '****' + value[-4:]


class FloatQuantize(Raw):

    def format(self, value):
        from leopard.helpers import float_quantize_by_two
        return float_quantize_by_two(value)


repaymentmethod = {
    'id': fields.Integer,
    'logic': fields.String,
    'name': fields.String
}


application = {
    'id': fields.Integer,
    'name': fields.String,
    'status': fields.Integer,
    'amount': FloatQuantize,
    'rate': fields.Float,
    'nper_type': fields.Integer,
    'periods': fields.Integer,
    'guarantee': fields.String,
    'project': fields.Nested({'id': fields.Integer}),
    'added_at': LocalDateTime
}

finapplication = {
    'id': fields.Integer,
    'user': fields.String,
    'uid': fields.String,
    'status': fields.Integer,
    'amount': FloatQuantize,
    'rate': fields.Float,
    'periods': fields.Integer,
    'added_at': LocalDateTime,
    'loan_use_for': fields.String,
    'repay_method': fields.Nested(repaymentmethod)
}

finapplication_detail = {
    'id': fields.Integer,
    'user': fields.String,
    'status': fields.Integer,
    'amount': fields.String,
    'rate': fields.Float,
    'periods': fields.String,
    'loan_use_for': fields.String,
    'realname': fields.String,
    'idcard': fields.String,
    'school_name': fields.String,
    'school_address': fields.String,
    'address': fields.String,
    'edu_system': fields.String,
    # 'edu_passwd': fields.String,
    'student_code': fields.String,
    'qq': fields.String,
    'wechat': fields.String,
    'mobile': fields.String,
    'tel': fields.String,
    'composite_rank': fields.Integer,
    'class_size': fields.Integer,
    'pluses': fields.String,
    'dad': fields.String,
    'dad_phone': fields.String,
    'dad_unit': fields.String,
    'dad_unit_address': fields.String,
    'dad_unit_phone': fields.String,
    'mum': fields.String,
    'mum_phone': fields.String,
    'mum_unit': fields.String,
    'mum_unit_phone': fields.String,
    'mum_unit_address': fields.String,
    'coacher': fields.String,
    'coacher_phone': fields.String,
    'schoolmate': fields.String,
    'schoolmate_phone': fields.String,
    'roommate': fields.String,
    'roommate_phone': fields.String,
    'added_at': LocalDateTime,
    'repay_method': fields.Nested(repaymentmethod)
}


fin_mobile_application = {
    'id': fields.Integer,
    'name': fields.String,
    'idcard': fields.String,
    'phone': fields.String,
    'school': fields.String,
    'grade': fields.String,
    'amount': FloatQuantize,
    'term': fields.String,
    'added_at': LocalDateTime
}


fin_mobile_application_detail = fin_mobile_application


next_user = {
    'username': fields.String,
    'net_income': FloatQuantize,
    'added_at': LocalDateTime
}

auto_invest = {
    'is_open': fields.Boolean,
    'min_rate': FloatQuantize,
    'max_rate': FloatQuantize,
    'min_periods': fields.Integer,
    'max_periods': fields.Integer,
    'min_amount': FloatQuantize,
    'max_amount': FloatQuantize,
    'reserve_amount': FloatQuantize,
    'max_allow_amount': FloatQuantize
}

guarantee_list = {
    'id': fields.Integer,
    'name': fields.String,
    'full_name': fields.String,
    'contact': fields.String,
    'logo': fields.String
}

guarantee_detail = {
    'id': fields.Integer,
    'name': fields.String,
    'full_name': fields.String,
    'contact': fields.String,
    'logo': fields.String,
    'description': fields.String
}

vip_server = {
    'id': fields.Integer,
    'username': fields.String,
    'realname': fields.String,
    'avatar': fields.String,
    'icq': fields.String,
    'phone': fields.String
}

user_profile = {
    'address': fields.String,
    'age': fields.Integer,
    'sex': fields.String,
    'education': fields.String,
    'marital_status': fields.String
}

user_level = {
    'name': fields.String,
    'description': fields.String
}

user = {
    'id': fields.Integer,
    'username': fields.String,
    'email': fields.String,
    'card': fields.String,
    'realname': fields.String,
    'avatar': fields.String,
    'phone': PhoneMosaic,
    'icq': fields.String,
    'address': fields.String,
    'gift_points': FloatQuantize,
    'trade_password_enable': fields.Boolean,
    'investing_amount': FloatQuantize,
    'investing_interest': FloatQuantize,
    'invested_interest': FloatQuantize,
    'net_income': FloatQuantize,
    'invested_amount': FloatQuantize,
    'repaying_amount': FloatQuantize,
    'repaid_amount': FloatQuantize,
    'total_amount': FloatQuantize,
    'available_amount': FloatQuantize,
    'active_amount': FloatQuantize,
    'deposit_amount': FloatQuantize,
    'income_amount': FloatQuantize,
    'blocked_amount': FloatQuantize,
    'guarded_amount': FloatQuantize,
    'certify_level': fields.String,
    'available_credit_points': fields.Integer,
    'blocked_credit_points': fields.Integer,
    'is_active': fields.Boolean,
    'is_staff': fields.Boolean,
    'is_server': fields.Boolean,
    'is_vip': fields.Boolean,
    'is_bane': fields.Boolean,
    'vip_end_at': LocalDateTime,
    'is_league': fields.Boolean,
    'interest': FloatQuantize,
    'server': fields.Nested(vip_server),
    'invited': fields.String,
    'login_counter': fields.Integer,
    'last_login_ip': fields.String,
    'current_login_ip': fields.String,
    'friend_invitation': fields.String,
    'invite_code': fields.String,
    'last_login_at': LocalDateTime,
    'current_login_at': LocalDateTime,
    'added_at': LocalDateTime,
    'is_borrower': fields.Boolean,
    'next_users': fields.Nested(next_user),
    'bankcard_need_amount': FloatQuantize,
    'level': fields.Nested(user_level)
}

plan = {
    'amount': FloatQuantize,
    'executed_time': LocalDateTime,
    'interest': FloatQuantize,
    'period': fields.Integer,
    'status': fields.Integer,
    'is_advance': fields.Boolean,
    'plan_time': LocalDateTime
}

finapplication_plans = {
    'id': fields.Integer,
    'amount': FloatQuantize,
    'executed_time': LocalDateTime,
    'interest': FloatQuantize,
    'period': fields.Integer,
    'status': fields.Integer,
    'plan_time': LocalDateTime
}

collection_plan = {
    'project_id': fields.Integer,
    'project_name': fields.String,
    'amount': FloatQuantize,
    'executed_time': LocalDateTime,
    'interest': FloatQuantize,
    'period': fields.Integer,
    'nper_type': fields.Integer,
    'project_category': fields.Integer,
    'status': fields.Integer,
    'is_advance': fields.Boolean,
    'plan_time': LocalDateTime
}

project_min_detail = {
    'id': fields.Integer,
    'amount': FloatQuantize,
    'borrowed_amount': FloatQuantize,
    'progress': FloatQuantize,
    'status': fields.Integer,
    'controls': fields.String,
    'guarantee': fields.String,
    'guarantee_id': fields.Integer,
    'rate': fields.Float,
    'category': fields.Integer,
    'nper_type': fields.Integer,
    'periods': fields.Integer,
    'name': fields.String,
    'has_password': fields.Boolean,
    'type': fields.String,
    'description': fields.String,
    'min_lend_amount': fields.Integer,
    'max_lend_amount': fields.Integer,
    'added_at': LocalDateTime,
    'user': UserNameMosaic,
    'invest_award': fields.Float,
    'repaymentmethod': fields.Nested(repaymentmethod)
}

investment_list = {
    'id': fields.Integer,
    'status': fields.Integer,
    'periods': fields.Integer,
    'nper_type': fields.Integer,
    'amount': FloatQuantize,
    'interest': FloatQuantize,
    'category': fields.Integer,
    'received_interest': FloatQuantize,
    'plans': fields.Nested(plan),
    'project': fields.Nested(project_min_detail),
    'transfering_start_time': LocalDateTime,
    'transfering_end_time': LocalDateTime,
    'executing_plans': fields.Nested(plan),
    'executed_plans': fields.Nested(plan),
    'added_at': LocalDateTime,
    'remain_periods_capital': FloatQuantize,
    'transfer_interest': FloatQuantize,
    'transfer_invest_award': FloatQuantize,
    'transfer_service_fee': fields.String,
    'is_transfer': fields.Boolean,
    'can_apply_transfer': fields.Boolean
}

account_investment_list = {
    'id': fields.Integer,
    'status': fields.Integer,
    'periods': fields.Integer,
    'nper_type': fields.Integer,
    'amount': FloatQuantize,
    'interest': FloatQuantize,
    'category': fields.Integer,
    'received_interest': FloatQuantize,
    'plans': fields.Nested(plan),
    'project': fields.Nested(project_min_detail),
    'executing_plans': fields.Nested(plan),
    'executed_plans': fields.Nested(plan),
    'added_at': LocalDateTime,
    'is_transfer': fields.Boolean,
    'has_previous': fields.Boolean,
    'can_apply_transfer': fields.Boolean
}
# 账户中心投资记录 详情
account_investment_detail = {
    'id': fields.Integer,
    'status': fields.Integer,
    'periods': fields.Integer,
    'nper_type': fields.Integer,
    'amount': FloatQuantize,
    'interest': FloatQuantize,
    'category': fields.Integer,
    'received_interest': FloatQuantize,
    'plans': fields.Nested(plan),
    'project': fields.Nested(project_min_detail),
    'transfering_start_time': LocalDateTime,
    'transfering_end_time': LocalDateTime,
    'executing_plans': fields.Nested(plan),
    'executed_plans': fields.Nested(plan),
    'added_at': LocalDateTime,
    'remain_periods_capital': FloatQuantize,
    'transfer_interest': FloatQuantize,
    'transfer_invest_award': FloatQuantize,
    'transfer_service_fee': fields.String,
    'is_transfer': fields.Boolean,
    'can_apply_transfer': fields.Boolean
}

investment_transfer_list = {
    'id': fields.Integer,
    'status': fields.Integer,
    'periods': fields.Integer,
    'amount': FloatQuantize,
    'interest': FloatQuantize,
    'discount': FloatQuantize,
    'project': fields.Nested(project_min_detail),
    'transfering_remain_periods': fields.Integer,
    'added_at': LocalDateTime,
    'remain_periods_capital': FloatQuantize,
    'transfer_interest': FloatQuantize,
    'expiration_time': LocalDateTime,
    'transfering_start_time': LocalDateTime,
    'transfer_invest_award': FloatQuantize,
}

tender_investment = {
    'id': fields.Integer,
    'status': fields.Integer,
    'rate': fields.Float,
    'nper_type': fields.Integer,
    'periods': fields.Integer,
    'amount': FloatQuantize,
    'return_amount': FloatQuantize,
    'interest': FloatQuantize,
    'description': fields.String,
    'previous': fields.String,
    'previous_id': fields.Integer,
    'transfering_start_time': LocalDateTime,
    'transfering_end_time': LocalDateTime,
    'next': fields.String,
    'next_id': fields.Integer,
    'added_at': LocalDateTime
}

investment_detail = {
    'id': fields.Integer,
    'status': fields.Integer,
    'rate': fields.Float,
    'nper_type': fields.Integer,
    'periods': fields.Integer,
    'amount': FloatQuantize,
    'return_amount': FloatQuantize,
    'interest': FloatQuantize,
    'received_interest': FloatQuantize,
    'description': fields.String,
    'user': UserNameMosaic,
    'plans': fields.Nested(plan),
    'project': fields.Nested(project_min_detail),
    'previous': fields.String,
    'previous_id': fields.Integer,
    'transfering_start_time': LocalDateTime,
    'transfering_end_time': LocalDateTime,
    'executing_plans': fields.Nested(plan),
    'executed_plans': fields.Nested(plan),
    'next': fields.String,
    'next_id': fields.Integer,
    'added_at': LocalDateTime
}

repayment_list = {
    'id': fields.Integer,
    'status': fields.Integer,
    'periods': fields.Integer,
    'nper_type': fields.Integer,
    'amount': FloatQuantize,
    'interest': FloatQuantize,
    'project_category': fields.Integer,
    'added_at': LocalDateTime,
    'plans': fields.Nested(plan),
    'executing_plans': fields.Nested(plan),
    'executed_plans': fields.Nested(plan),
    'processed_at': LocalDateTime,
    'project': fields.String,
    'project_id': fields.Integer
}

repayment_detail = {
    'id': fields.Integer,
    'status': fields.Integer,
    'periods': fields.Integer,
    'nper_type': fields.Integer,
    'amount': FloatQuantize,
    'interest': FloatQuantize,
    'added_at': LocalDateTime,
    'plans': fields.Nested(plan),
    'description': fields.String,
    'executing_plans': fields.Nested(plan),
    'executed_plans': fields.Nested(plan),
    'processed_at': LocalDateTime,
    'project': fields.String,
    'project_id': fields.Integer
}


finproject_list = {
    'id': fields.Integer,
    'name': fields.String,
    'has_password': fields.Boolean,
    'amount': FloatQuantize,
    'controls': fields.String,
    'category': fields.Integer,
    'rate': fields.Float,
    'nper_type': fields.Integer,
    'guarantee': fields.Nested(guarantee_detail),
    'guarantee_id': fields.Integer,
    'status': fields.Integer,
    'progress': FloatQuantize,
    'periods': fields.Integer,
    'added_at': LocalDateTime,
    'borrowed_amount': FloatQuantize,
    'type': fields.String,
    'invest_award': fields.Float,
    'repaymentmethod': fields.Nested(repaymentmethod)
}

project_detail_user = {
    'username': fields.String,
    'address': fields.String,
    'age': fields.Integer,
    'sex': fields.String,
    'education': fields.String,
    'marital_status': fields.String
}

investment_min_detail = {
    'id': fields.Integer,
    'status': fields.Integer,
    'rate': fields.Float,
    'nper_type': fields.Integer,
    'periods': fields.Integer,
    'amount': FloatQuantize,
    'return_amount': FloatQuantize,
    'interest': FloatQuantize,
    'description': fields.String,
    'user': UserNameMosaic,
    'user_id': fields.Integer,
    'invest_from': fields.Integer,
    'added_at': LocalDateTime
}


finproject_detail = {
    'id': fields.Integer,
    'amount': FloatQuantize,
    'borrowed_amount': FloatQuantize,
    'progress': FloatQuantize,
    'status': fields.Integer,
    'nper_type': fields.Integer,
    'rate': fields.Float,
    'periods': fields.Integer,
    'name': fields.String,
    'description': fields.String,
    'min_lend_amount': fields.Integer,
    'max_lend_amount': fields.Integer,
    'added_at': LocalDateTime,
    'user': fields.Nested(project_detail_user),
    'investments': fields.Nested(investment_min_detail),
    'repayments': fields.Nested(repayment_list),
    'repaymentmethod': fields.Nested(repaymentmethod),
    'finapplication': fields.Nested(finapplication)
}

project_list = {
    'id': fields.Integer,
    'uid': fields.String,
    'name': fields.String,
    'has_password': fields.Boolean,
    'amount': FloatQuantize,
    'controls': fields.String,
    'category': fields.Integer,
    'rate': fields.Float,
    'nper_type': fields.Integer,
    'status': fields.Integer,
    'progress': FloatQuantize,
    'guarantee': fields.Nested(guarantee_detail),
    'guarantee_id': fields.Integer,
    'periods': fields.Integer,
    'paid_periods': fields.Integer,
    'added_at': LocalDateTime,
    'borrowed_amount': FloatQuantize,
    'type': fields.String,
    'invest_award': fields.Float,
    'repaymentmethod': fields.Nested(repaymentmethod),
    'remain_bid_time': fields.Integer,
    'grade': fields.Integer
}

project_detail_authentication = {
    'idcard': fields.Boolean,
    'household': fields.Boolean,
    'income': fields.Boolean,
    'credit_reporting': fields.Boolean,
    'house_property_card': fields.Boolean,
    'vehicle_license': fields.Boolean,
    'guarantee_contract': fields.Boolean,
    'counter_guarantee_contract': fields.Boolean,
    'business_license': fields.Boolean,
    'tax_registration_certificate': fields.Boolean,
    'bank_account_license': fields.Boolean,
    'organization_code_certificate': fields.Boolean,
    'mortgaged_property_certification': fields.Boolean,
    'field_certification': fields.Boolean
}

project_images = {
    'name': fields.String,
    'image': fields.String
}

risk_controls = {
    'title': fields.String,
    'content': fields.String,
}

project_specs = {
    'title': fields.String,
    'desc': fields.String,
}

project_detail = {
    'id': fields.Integer,
    'uid': fields.String,
    'amount': FloatQuantize,
    'borrowed_amount': FloatQuantize,
    'progress': FloatQuantize,
    'status': fields.Integer,
    'controls': fields.String,
    'guarantee': fields.Nested(guarantee_detail),
    'guarantee_id': fields.Integer,
    'relation_images': fields.Nested(project_images),
    'filter_risk_controls': fields.Nested(risk_controls),
    'filter_specs': fields.Nested(project_specs),
    'rate': fields.Float,
    'nper_type': fields.Integer,
    'periods': fields.Integer,
    'paid_periods': fields.Integer,
    'name': fields.String,
    'has_password': fields.Boolean,
    'description': fields.String,
    'min_lend_amount': fields.Integer,
    'max_lend_amount': fields.Integer,
    'added_at': LocalDateTime,
    'bid_at': LocalDateTime,
    'user': fields.Nested(project_detail_user),
    'certify': fields.Nested(project_detail_authentication),
    'investments': fields.Nested(investment_min_detail),
    'repaymentmethod': fields.Nested(repaymentmethod),
    'remain_day': fields.Integer,
    'use_of_funds': fields.String,
    'payment_from': fields.String,
    'type': fields.String,
    'guaranty': fields.String,
    'guarantee_info': fields.String,
    'asset_description': fields.String,
    'invest_award': fields.Float,
    'use_project_attestation': fields.Boolean,
    'income': fields.String,
    'idcard': fields.String,
    'household': fields.String,
    'credit_reporting': fields.String,
    'house_property_card': fields.String,
    'vehicle_license': fields.String,
    'guarantee_contract': fields.String,
    'counter_guarantee_contract': fields.String,
    'business_license': fields.String,
    'tax_registration_certificate': fields.String,
    'bank_account_license': fields.String,
    'organization_code_certificate': fields.String,
    'mortgaged_property_certification': fields.String,
    'field_certification': fields.String,
    'remain_bid_time': fields.Integer,
}

investment_transfer_detail = {
    'id': fields.Integer,
    'status': fields.Integer,
    'rate': fields.Float,
    'nper_type': fields.Integer,
    'periods': fields.Integer,
    'amount': FloatQuantize,
    'return_amount': FloatQuantize,
    'interest': FloatQuantize,
    'discount': FloatQuantize,
    'description': fields.String,
    'user': UserNameMosaic,
    'plans': fields.Nested(plan),
    'project': fields.Nested(project_detail),
    'previous': fields.String,
    'previous_id': fields.Integer,
    'executing_plans': fields.Nested(plan),
    'executed_plans': fields.Nested(plan),
    'next': fields.String,
    'next_id': fields.Integer,
    'added_at': LocalDateTime,
    'transfering_start_time': LocalDateTime,
    'transfer_invest_award': FloatQuantize,
    'remain_periods_capital': FloatQuantize,
    'transfer_expected_return': FloatQuantize,
    'transfer_interest': FloatQuantize,
    'transfer_service_fee': fields.String,
    'expiration_time': LocalDateTime,
}

message = {
    'id': fields.Integer,
    'title': fields.String,
    'content': fields.String,
    'is_read': fields.Boolean,
    'added_at': LocalDateTime,
    'from_user': fields.String,
    'to_user': fields.String
}

banner_list = {
    'id': fields.Integer,
    'src': fields.String,
    'link': fields.String
}

banner_detail = {
    'id': fields.Integer,
    'src': fields.String,
    'link': fields.String
}

post_list = {
    'id': fields.Integer,
    'title': fields.String,
    'added_at': LocalDateTime,
    'type': fields.Integer,
    'content': fields.String
}

post_detail = {
    'id': fields.Integer,
    'title': fields.String,
    'added_at': LocalDateTime,
    'type': fields.Integer,
    'content': fields.String
}

deposit = {
    'id': fields.Integer,
    'platform_order': fields.String,
    'amount': FloatQuantize,
    'commission': FloatQuantize,
    'status': fields.Integer,
    'added_at': LocalDateTime,
    'processed_at': LocalDateTime
}

deposit_planform = {
    'id': fields.Integer,
    'name': fields.String,
    'description': fields.String,
    'innerHTML': fields.String,
    'logic': fields.String,
    'priority': fields.Integer
}

bankcard = {
    'id': fields.Integer,
    'bank': fields.String,
    'card': fields.String,
    'need_amount': FloatQuantize
}

withdraw = {
    'id': fields.Integer,
    'amount': FloatQuantize,
    'commission': FloatQuantize,
    'status': fields.Integer,
    'added_at': LocalDateTime,
    'processed_at': LocalDateTime
}

wd = {
    'id': fields.Integer,
    'platform_order': fields.String,
    'order_number': fields.String,
    'amount': FloatQuantize,
    'commission': FloatQuantize,
    'status': fields.Integer,
    'added_at': LocalDateTime,
    'processed_at': LocalDateTime
}

log = {
    'id': fields.Integer,
    'amount': FloatQuantize,
    'active_amount': FloatQuantize,
    'deposit_amount': FloatQuantize,
    'income_amount': FloatQuantize,
    'blocked_amount': FloatQuantize,
    'guarded_amount': FloatQuantize,
    'added_at': LocalDateTime,
    'description': fields.String
}

red_packet_type = {
    'name': fields.String,
    'valid': fields.Integer,
    'description': fields.String
}

red_packet = {
    'id': fields.Integer,
    'name': fields.String,
    'amount': FloatQuantize,
    'invest_amount': FloatQuantize,
    'added_at': LocalDateTime,
    'expires_at': LocalDateTime,
    'description': fields.String,
    'is_use': fields.Boolean,
    'is_available': fields.Boolean,
    'is_expiry': fields.Boolean,
    'type': fields.Nested(red_packet_type)
}

authentication_field_type = {
    'id': fields.Integer,
    'name': fields.String,
    'order': fields.Integer,
    'is_content': fields.Boolean,
    'required': fields.Boolean,
    'pattern': fields.String,
    'score': fields.Integer
}

authentication_field = {
    'value': fields.String,
    'type': fields.String,
    'is_content': fields.Boolean
}

authentication = {
    'id': fields.Integer,
    'status': fields.Boolean,
    'is_edit': fields.Boolean,
    'message': fields.String,
    'fields': fields.List(fields.Nested(authentication_field))
}

authentication_type = {
    'id': fields.Integer,
    'name': fields.String,
    'logic': fields.String,
    'description': fields.String,
    'fields': fields.List(fields.Nested(authentication_field_type)),
    'authentication': fields.Nested(authentication)
}

gift_points = {
    'id': fields.Integer,
    'points': FloatQuantize,
    'description': fields.String,
    'added_at': LocalDateTime
}

rank_field = {
    'username': StringMosaic,
    # 'number': fields.Integer,
    # 'total_amount': FloatQuantize
    'number': fields.Integer,
    'total_amount': fields.String
}

rank_list = {
    'daylist': fields.List(fields.Nested(rank_field)),
    'weeklist': fields.List(fields.Nested(rank_field)),
    'monthlist': fields.List(fields.Nested(rank_field)),
    'totallist': fields.List(fields.Nested(rank_field))
}

# 交易量统计
trade_stat = {
    'turnover': FloatQuantize,
    'users_income': FloatQuantize,
    'gross_income': FloatQuantize
}

project_plan_detail = {
    'id': fields.Integer,
    'period': fields.Integer,
    'status': fields.Integer,
    'amount': FloatQuantize,
    'interest': FloatQuantize,
    'amount_interest': FloatQuantize,
    'remain_amount': FloatQuantize,
    'plan_time': LocalDateTime,
    'executed_time': LocalDateTime
}

project_plan_list = {
    'id': fields.Integer,
    'period': fields.Integer,
    'status': fields.Integer,
    'amount': FloatQuantize,
    'interest': FloatQuantize,
    'amount_interest': FloatQuantize,
    'remain_amount': FloatQuantize,
    'plan_time': LocalDateTime,
    'executed_time': LocalDateTime
}

sourcewebsite_field = {
    'username': StringMosaic,
    'added_at': LocalDateTime,
    'phone': fields.String,
    'source_code': fields.String,
    'source_website': fields.Nested({
        'name': fields.String,
        'puthin': fields.String
        })
}

commodity_detail = {
    'name': fields.String,
    'slogan': fields.String,
    'promotion': fields.String,
    'price': FloatQuantize,
    'number': fields.Integer,
    'src': fields.String,
    'details': fields.String,
    'type': fields.Integer,
}

commodity_field = {
    'id': fields.Integer,
    'name': fields.String,
    'slogan': fields.String,
    'promotion': fields.String,
    'price': FloatQuantize,
    'number': fields.Integer,
    'src': fields.String,
    'type': fields.Integer,
}

commodity_order_list = {
    'commodity': fields.Nested(commodity_field),
    'addressee': fields.String,
    'amount': FloatQuantize,
    'phone': fields.String,
    'number': fields.Integer,
    'addressee': fields.String,
    'status': fields.String,
    'added_at': LocalDateTime,
    'process_at': LocalDateTime
}

desposit_bankcard = {
    'bank_name': fields.String,
    'card_no': fields.String,
    'card_type': fields.String,
    'no_agree': fields.String
}
