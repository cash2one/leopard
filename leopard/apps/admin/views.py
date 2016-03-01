import os
import os.path as op
import urllib
import logging
import datetime
from decimal import Decimal

from PIL import Image
from redis import Redis
from flask import Blueprint, flash, make_response, render_template, request
from flask.ext.admin.model import InlineFormAdmin
from flask.ext.admin import expose

from flask.ext.admin.actions import action
from flask.ext.admin.form import Select2Field
from wtforms import SelectField, TextAreaField, IntegerField
from wtforms.validators import required
from wtforms.widgets import TextArea


from leopard.conf import consts
from leopard.comps.redis import pool, redis_repeat_submit_by_admin_action
from leopard.comps.admin.fields import (AbstackImageUploadField,
                                        MultiCheckboxField)
from leopard.apps.service.tasks import (automatic_investments,
                                        batch_send_sms,
                                        activity_project_repay_all,
                                        max_lend_amount_limit)
from leopard.comps.admin import (BaseView, ModelView, ExportXlsMixin,
                                 GetQueryOrderByidDescMixin)
from leopard.core.orm import db_session
from leopard.core.business import common_full_tender, flow_borrow
from leopard.helpers import (get_config, generate_media_filename,
                             get_enum, get_current_user, generate_unique_code,
                             get_current_user_id, get_uwsgi)
from leopard.helpers.exceptions import FlowOperationException
from leopard.orm import (Application, User, Deposit, Withdraw, Project,
                         ProjectType, ProjectImages, Config, RepaymentMethod,
                         AuthenticationFieldType, AuthenticationField,
                         AuthenticationType, Authentication, Message,
                         RedPacketType, FinApplication, FinApplicationPlan,
                         CodeRedPacket, SourceWebsite, AutoInvestment,
                         Commodity, CommodityOrder, GiftPoint)

from . import AuthMixin

redis = Redis(connection_pool=pool)
uwsgi = get_uwsgi()

blueprint = Blueprint('views', __name__)
permissions = get_config('permissions')
project_config = get_config('project')

logger = logging.getLogger('admin')

file_path = op.abspath('')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in \
        get_enum('ALLOWED_EXTENSIONS')


@blueprint.route('/post_image_upload', methods=['POST'])
def post_image_upload():
    
    ck_num = request.values['CKEditorFuncNum']
    if not request.files:
        return make_response(render_template('admin/ck_callback.html',
                                             message="请选择上传图片",
                                             CKFuncNum=ck_num))
    f = request.files['upload']
    image_data = f.read()
    image_size = len(image_data)
    f.seek(0)
    if image_size > get_enum('MAX_IMAGE_SIZE'):
        return make_response(render_template('admin/ck_callback.html',
                                             message="图片太大了",
                                             CKFuncNum=ck_num))
    if not allowed_file(f.filename):
        return make_response(render_template('admin/ck_callback.html',
                                             message="图片格式错误",
                                             CKFuncNum=ck_num))
    name = f.filename
    image_name = '{}{}'.format(
        generate_media_filename(), os.path.splitext(name)[-1]).lower()
    save_path = os.path.join(get_enum('POSTS_IMAGE_FOLDER'), image_name)
    f.save(save_path)
    f.close()
    image = Image.open(save_path)
    try:
        exif = image._getexif()
        orientation_key = 274  # cf ExifTags
        if exif and orientation_key in exif:
            orientation = exif[orientation_key]
            rotate_values = {
                3: 180,
                6: 270,
                8: 90
            }
            if orientation in rotate_values:
                # Rotate and save the picture
                image = image.rotate(rotate_values[orientation])
                image.save(save_path, quality=100)
    except AttributeError:
        pass

    image_url = urllib.parse.urljoin(
        get_enum('POSTS_IMAGE_FOLDER'), image_name)
    image_path = urllib.parse.urljoin('/', image_url)
    return make_response(
        render_template(
            'admin/ck_callback.html', callback=True, image_path=image_path,
            CKFuncNum=ck_num))


class CKTextAreaWidget(TextArea):

    def __call__(self, field, **kwargs):
        kwargs.setdefault('class_', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)


class CKTextAreaField(TextAreaField):
    widget = CKTextAreaWidget()


class FriendInviteView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):

    column_filters = ('username', 'email', 'realname', 'phone')

    def get_query(self):
        query = super(FriendInviteView, self).get_query()
        query = query.filter(User.username != 'su')
        return query

    def get_count_query(self):
        query = super(FriendInviteView, self).get_count_query()
        query = query.filter(User.username != 'su')
        return query

    def update_model(self, form, model):
       
        if str(model.username) == str(form.invited.data):
            flash('推荐人不能为自己', 'error')
            return False
        else:
            return super(FriendInviteView, self).update_model(form, model)

class UserView(ExportXlsMixin, AuthMixin, ModelView,
               GetQueryOrderByidDescMixin):

    form_overrides = {
        'friend_invest_award_level': Select2Field
    }

    def get_query(self):
        query = super(UserView, self).get_query()
        query = query.filter(User.username != 'su')
        return query

    def get_count_query(self):
        query = super(UserView, self).get_count_query()
        query = query.filter(User.username != 'su')
        return query

    @action('sync_user', '同步用户')
    @redis_repeat_submit_by_admin_action()
    def sync_user(self, ids):
        queryset = User.query.filter(User.id.in_(ids))
        for user in queryset:
            user.is_sync = True
        db_session.commit()
        flash('操作成功', 'success')

    @action('ban_user', '冻结用户')
    @redis_repeat_submit_by_admin_action()
    def ban_user(self, ids):
        queryset = User.query.filter(User.id.in_(ids))
        for user in queryset:
            user.is_bane = True
        db_session.commit()
        flash('操作成功', 'success')

    @action('active_user', '启用')
    @redis_repeat_submit_by_admin_action()
    def active_user(self, ids):
        queryset = User.query.filter(User.id.in_(ids))
        for user in queryset:
            user.is_bane = False
        db_session.commit()
        flash('操作成功', 'success')

    # def after_model_change(self, form, model, is_created):
    def update_model(self, form, model):

        if str(model.invite_code) == str(form.invite_code.data):
            return super(UserView, self).update_model(form, model)

        if not form.is_staff.data:
            flash('该用户不是职员，不可修改邀请码！', 'error')
            return False

        exists = db_session.query(User.query.filter_by(
            invite_code=form.invite_code.data).exists()).scalar()
        if exists:
            flash('邀请码已经存在 !', 'error')
            return False

        return super(UserView, self).update_model(form, model)
        

class SpecialRemindView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    column_filters = ('birth_day', ('username', '用户名'),
                      ('realname', '真实姓名'),
                      'first_investment', 'first_top_up')
    extra_filters_type = {'birth_day': 'MonthDate'}

    def get_query(self):
        query = super(SpecialRemindView, self).get_query()
        query = query.filter(User.username != 'su')
        return query

    def get_count_query(self):
        query = super(SpecialRemindView, self).get_count_query()
        query = query.filter(User.username != 'su')
        return query


class PostView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    form_overrides = dict(content=CKTextAreaField, type=Select2Field)

    def on_model_change(self, form, model, is_created):
        model.user = get_current_user()

    def get_query(self):
        query = super(self.__class__, self).get_query()
        query = query.order_by(self.model.type.desc())
        return query


class ProjectImageInlineModel(InlineFormAdmin):
    form_label = '补充材料'
    form_columns = ['id', 'name', 'image']
    column_labels = {'name': '名称', 'image': '图片'}

    form_overrides = dict(image=AbstackImageUploadField)
    form_args = {
        'image': {
            'base_path': file_path,
            'relative_path': 'media/project/avatar',
        }
    }

    def __init__(self):
        return super(ProjectImageInlineModel, self).__init__(ProjectImages)


class FinProjectPublishView(ExportXlsMixin, AuthMixin, ModelView,
                            GetQueryOrderByidDescMixin):

    """学仕贷 发布界面"""

    form_args = {
        'finapplication': {
            'query_factory': lambda: FinApplication.query.filter_by(
                project=None, status=get_enum('FINAPPLICATION_VERIFY_SUCCESS'))
        },
        'type': {
            'query_factory': lambda: ProjectType.query.filter_by(name='学仕贷')
        }
    }

    def get_query(self):
        query = super(FinProjectPublishView, self).get_query()
        query = query.filter_by(
            status=get_enum('PROJECT_READY'),
            category=get_enum('STUDENT_PROJECT')
        )
        return query

    def get_count_query(self):
        query = super(FinProjectPublishView, self).get_count_query()
        query = query.filter_by(status=get_enum('PROJECT_READY'),
                                category=get_enum('STUDENT_PROJECT'))
        return query

    @action('publish_project', '发布项目')
    @redis_repeat_submit_by_admin_action()
    def publish_project(self, ids):
        logger.info(('[后台发布项目] 操作人:{}, 操作对象({})').format(
            get_current_user_id(), ids))

        project_autoinvest = get_enum('PROJECT_AUTOINVEST')
        project_investing = get_enum('PROJECT_INVESTING')

        auto_enable = Config.get_bool('AUTO_INVESTMENT_ENABLE')
        projects = Project.query.filter(
            Project.id.in_(ids),
            Project.status == get_enum('PROJECT_READY')
        )
        targets = []
        try:
            for project in projects:
                project.status = project_investing
                # if auto_enable and not project.has_password:
                #     project.status = project_autoinvest  # 自动投标状态
                #     targets.append(project.id)
                # else:
                #     project.status = project_investing  # 正常投标状态
            db_session.commit()
            # if targets:
            #     [automatic_investments.delay(project_id) for project_id in targets]
        except Exception as e:
            logger.info('[后台发布项目] 操作失败 {}'.format(e))
            flash(e, 'failed')
        else:
            flash('操作完成', 'success')

    def create_model(self, form):
        if not form.finapplication.data:
            flash('请选择申请书', 'error')
            return False
        if form.max_lend_amount.data < Decimal('0.00') or \
           form.min_lend_amount.data < Decimal('0.00'):
            flash('请输入正确的投资金额限制', 'error')
            return False
        if form.max_lend_amount.data < form.min_lend_amount.data:
            flash('最大投资金额不能小于最小投资金额', 'error')
            return False
        return super(FinProjectPublishView, self).create_model(form)

    def on_model_change(self, form, model, is_created=None):
        if is_created:
            if redis.get('fin_project_view_create:'):
                raise Exception('请求太频繁，请稍后重试')
            else:
                redis.set('fin_project_view_create:', 0, 60)  # 60秒
                if is_created:
                    username = Config.get_config('FINPROJECT_USER')
                    user = User.query.filter_by(username=username).first()
                    if not user:
                        raise Exception('后台设置的学仕贷资金代管账户错误')
                    repay_method = Config.get_config(
                        'FINPROJECT_DEFAULT_REPAY_METHOD')
                    repay_method = RepaymentMethod.query.filter_by(
                        logic=repay_method).first()
                    if not repay_method:
                        raise Exception('后台设置的学仕贷还款方法错误')

                    model.amount = 0
                    for i in model.finapplication:
                        model.amount += i.amount
                    model.repaymentmethod = repay_method
                    model.user = user
                    model.status = get_enum('PROJECT_READY')
                    model.invest_award = 0              # 学仕贷没有投资奖励
                    model.category = get_enum('STUDENT_PROJECT')
                    model.rate = model.rate / 12
                    model.added_ip = request.remote_addr
                redis.delete('fin_project_view_create')


class FinProjectView(ExportXlsMixin, AuthMixin, ModelView,
                     GetQueryOrderByidDescMixin):
    """学仕贷"""

    form_args = {
        'finapplication': {
            'query_factory': lambda: FinApplication.query.filter_by(
                project=None, status=get_enum('FINAPPLICATION_VERIFY_SUCCESS'))
        },
        'type': {
            'query_factory': lambda: ProjectType.query.filter_by(name='学仕贷')
        }
    }

    @action('flow_borrow', '流标操作')
    @redis_repeat_submit_by_admin_action()
    def flow_borrow(self, ids):
        session = db_session()
        try:
            current_user = get_current_user()
            message = flow_borrow(ids, current_user, session)  # 流标操作
            session.commit()
            if message:
                raise Exception(message)
            logger.info('[项目流标] 项目ids: {} 操作人:{}'.format(
                        ids, current_user.username))
            flash('操作完成', 'success')
        except FlowOperationException as e:
            logger.info('[后台管理] 流标操作失败 {}'.format(e))
            session.rollback()
            flash(e.message, 'failed')
        except Exception as e:
            logger.info('[后台管理] 流标操作失败 {}'.format(e))
            session.rollback()
            flash('流标操作失败', 'failed')

    @action('audit_access', '审核通过')
    @redis_repeat_submit_by_admin_action()
    def audit_access(self, ids):
        message = None
        session = db_session()
        targets = []
        projects = Project.query.filter(
            Project.id.in_(ids),
            Project.status == get_enum('PROJECT_PENDING')
        )
        try:
            for project in projects:
                common_full_tender(project, session)      # 满标操作
                if project.repaymentmethod.logic == 'repayment_immediately':
                    targets.append(project.id)
            session.commit()
            if targets:
                activity_project_repay_all.delay(targets)
        except Exception as error:
            logger.info('[项目审核] 项目ids: {} ERROR:{}'.format(ids, error))
            session.rollback()
        finally:
            if message:
                flash(message, 'warning')
            else:
                session.commit()
                logger.info('[项目审核] 项目ids: {} 审核通过 操作人:{}'.format(
                    ids, get_current_user().username))

                flash('项目审核通过', 'success')

    def get_query(self):
        query = super(FinProjectView, self).get_query()
        query = query.filter_by(
            category=get_enum('STUDENT_PROJECT')
        ).filter(Project.status > get_enum('PROJECT_READY'))
        return query

    def get_count_query(self):
        query = super(FinProjectView, self).get_count_query()
        query = query.filter_by(category=get_enum('STUDENT_PROJECT'))
        return query


class ProjectPublishView(ExportXlsMixin, AuthMixin, ModelView,
                         GetQueryOrderByidDescMixin):

    column_filters = ('name', ('user.username', '申请人'),
                      ('guarantee.name', '担保机构'))

    inline_models = (ProjectImageInlineModel(),)

    form_overrides = {
        'income': AbstackImageUploadField,
        'idcard': AbstackImageUploadField,
        'household': AbstackImageUploadField,
        'credit_reporting': AbstackImageUploadField,
        'house_property_card': AbstackImageUploadField,
        'vehicle_license': AbstackImageUploadField,
        'guarantee_contract': AbstackImageUploadField,
        'counter_guarantee_contract': AbstackImageUploadField,
        'business_license': AbstackImageUploadField,
        'tax_registration_certificate': AbstackImageUploadField,
        'bank_account_license': AbstackImageUploadField,
        'organization_code_certificate': AbstackImageUploadField,
        'mortgaged_property_certification': AbstackImageUploadField,
        'field_certification': AbstackImageUploadField,
        'grade': SelectField
    }

    form_args = {
        'income': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'idcard': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'household': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'credit_reporting': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'house_property_card': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'vehicle_license': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'guarantee_contract': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'counter_guarantee_contract': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'business_license': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'tax_registration_certificate': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'bank_account_license': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'organization_code_certificate': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'mortgaged_property_certification': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'field_certification': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'application': {
            'query_factory': lambda: Application.query.filter_by(
                project=None, status=get_enum('APPLICATION_PROJECT_PUBLISHED'))
        },
        'type': {
            # 默认只有流转标
            'query_factory': lambda: ProjectType.query.filter_by(logic='flow')
        }
    }

    def get_query(self):
        query = super(ProjectPublishView, self).get_query()
        query = query.filter_by(
            category=get_enum('COMMON_PROJECT'),
            status=get_enum('PROJECT_READY')
        )
        return query

    def get_count_query(self):
        query = super(ProjectPublishView, self).get_count_query()
        query = query.filter_by(
            status=get_enum('PROJECT_READY'),
            category=get_enum('COMMON_PROJECT'))
        return query

    def create_model(self, form):
        if not form.application.data:
            flash('请选择申请书', 'error')
            return False
        if form.max_lend_amount.data < Decimal('0.00') or \
           form.min_lend_amount.data < Decimal('0.00'):
            flash('请输入正确的投资金额限制', 'error')
            return False
        if form.max_lend_amount.data < form.min_lend_amount.data:
            flash('最大投资金额不能小于最小投资金额', 'error')
            return False
        if form.invest_award.data < Decimal('0.00'):
            flash('请输入正确的奖励利率', 'error')
            return False
        return super(ProjectPublishView, self).create_model(form)

    def on_model_change(self, form, model, is_created=None):
        if is_created:
            key = 'projectpublish_view_create:' + str(model.application.id)
            if redis.get(key):
                raise Exception('请求太频繁，请稍后重试')
            else:
                redis.set(key, 0, 60)  # 60秒
                if is_created:
                    application = model.application
                    db_session.refresh(application)

                    if application.project:
                        raise Exception('申请书已经使用过，请刷新！')

                    model.max_lend_amount = model.max_lend_amount
                    model.min_lend_amount = model.min_lend_amount
                    model.repaymentmethod = application.repay_method
                    model.guarantee = application.guarantee
                    model.user = application.user
                    model.nper_type = application.nper_type
                    model.amount = application.amount
                    model.rate = application.rate
                    model.periods = application.periods
                    model.added_ip = request.remote_addr
                    model.status = get_enum('PROJECT_READY')

    @action('hidden_project', '隐藏项目')
    @redis_repeat_submit_by_admin_action()
    def hidden_project(self, ids):
        logger.info(('[后台发布项目] 操作人:{}, 操作对象({})').format(
            get_current_user_id(), ids))
        projects = Project.query.filter(Project.id.in_(ids))

        projects.update({'status': get_enum('PROJECT_DELETE')},
                        synchronize_session='fetch')
        db_session.commit()
        flash('操作完成', 'success')

    @action('publish_project', '发布项目')
    @redis_repeat_submit_by_admin_action()
    def publish_project(self, ids):
        logger.info(('[后台发布项目] 操作人:{}, 操作对象({})').format(
            get_current_user_id(), ids))

        project_autoinvest = get_enum('PROJECT_AUTOINVEST')
        project_investing = get_enum('PROJECT_INVESTING')

        auto_enable = Config.get_bool('AUTO_INVESTMENT_ENABLE')
        projects = Project.query.filter(
            Project.id.in_(ids),
            Project.status == get_enum('PROJECT_READY')
        )
        targets = []
        try:
            for project in projects:
                if auto_enable and not project.has_password:
                    project.status = project_autoinvest  # 自动投标状态
                    targets.append(project.id)
                else:
                    project.status = project_investing  # 正常投标状态
            db_session.commit()
            if targets:
                [automatic_investments.delay(project_id) for project_id in targets]
        except Exception as e:
            logger.info('[后台发布项目] 操作失败 {}'.format(e))
            flash(e, 'failed')
        else:
            flash('操作完成', 'success')

    def after_model_change(self, form, model, is_created):
        logger.info('[项目发布] 申请书名称:{} 项目名称: {} 操作人:{}'.format(
            model.application.name, model.name, get_current_user().username))

        if is_created:
            redis.delete('project_view_create:' + str(model.application.id))
            project_id = model.id
            if model.status == get_enum('PROJECT_AUTOINVEST'):
                automatic_investments.delay(project_id)             # 自动投标

            if Config.get_bool('PROJECT_QUOTA_LIMIT_ENABLE'):
                countdown = Config.get_int('PROJECT_QUOTA_LIMIT_TIME')
                max_lend_amount_limit.apply_async(args=(project_id,),
                                                  countdown=countdown)

            project = Project.query.get(model.id)

            title = '系统信息 - 您所申请的项目（{}），已成功发布！'.format(
                project.application.name)
            content = '尊敬的用户 - 您于 {} 申请的项目（{}），已成功发布！'.format(
                project.application.added_at.strftime('%Y年%m月%d日 %H:%M:%S'),
                project.application.name)
            Message.system_inform(to_user=project.user, title=title,
                                  content=content)
            db_session.commit()


class RiskControlView(ExportXlsMixin, AuthMixin, ModelView,
                      GetQueryOrderByidDescMixin):
    form_overrides = dict(content=CKTextAreaField)


class ProjectSpecView(ExportXlsMixin, AuthMixin, ModelView,
                      GetQueryOrderByidDescMixin):
    pass


class ProjectView(ExportXlsMixin, AuthMixin, ModelView,
                  GetQueryOrderByidDescMixin):
    column_filters = ('name', ('user.username', '申请人'),
                      ('guarantee.name', '担保机构'))

    inline_models = (ProjectImageInlineModel(),)

    form_overrides = {
        'income': AbstackImageUploadField,
        'idcard': AbstackImageUploadField,
        'household': AbstackImageUploadField,
        'credit_reporting': AbstackImageUploadField,
        'house_property_card': AbstackImageUploadField,
        'vehicle_license': AbstackImageUploadField,
        'guarantee_contract': AbstackImageUploadField,
        'counter_guarantee_contract': AbstackImageUploadField,
        'business_license': AbstackImageUploadField,
        'tax_registration_certificate': AbstackImageUploadField,
        'bank_account_license': AbstackImageUploadField,
        'organization_code_certificate': AbstackImageUploadField,
        'mortgaged_property_certification': AbstackImageUploadField,
        'field_certification': AbstackImageUploadField,
    }

    form_args = {
        'income': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'idcard': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'household': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'credit_reporting': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'house_property_card': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'vehicle_license': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'guarantee_contract': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'counter_guarantee_contract': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'business_license': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'tax_registration_certificate': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'bank_account_license': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'organization_code_certificate': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'mortgaged_property_certification': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'field_certification': {
            'base_path': file_path,
            'relative_path': 'media/project/',
        },
        'application': {
            'query_factory': lambda: Application.query.filter_by(
                project=None, status=get_enum('APPLICATION_PROJECT_PUBLISHED'))
        },
        'type': {
            # 默认只有流转标
            'query_factory': lambda: ProjectType.query.filter_by(logic='flow')
        }
    }

    def get_query(self):
        query = super(ProjectView, self).get_query()
        query = query.filter_by(
            category=get_enum('COMMON_PROJECT')
        ).filter(Project.status.in_(get_enum('PROJECT_ADMIN_SHOW')))

        return query

    def get_count_query(self):
        query = super(ProjectView, self).get_count_query()
        query = query.filter_by(
            category=get_enum('COMMON_PROJECT')
        ).filter(Project.status.in_(get_enum('PROJECT_ADMIN_SHOW')))
        return query


class InvestmentView(ExportXlsMixin, AuthMixin, ModelView,
                     GetQueryOrderByidDescMixin):
    column_filters = (('user.username', '用户名'), 'status')

    form_args = {
        'user': {
            'query_factory': lambda: User.query.filter(User.username != 'su')
        }
    }


class ProjectTypeView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    form_extra_fields = {
        'logic': Select2Field('逻辑', choices=[('flow', '流转标'), ],
                              validators=[required()])
    }


class ProjectRepayView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    column_filters = ('period', ('user.username', '借款人'),
                      ('project.name', '项目'), 'plan_time',
                      'executed_time', 'status')

    list_template = 'admin/model/safe_project_plan_list.html'

    form_args = {
        'user': {
            'query_factory': lambda: User.query.filter(User.username != 'su')
        }
    }

    def get_query(self):
        query = super(self.__class__, self).get_query()
        query = query.order_by(self.model.status.asc(),
                               self.model.period.asc())
        return query


class RepaymentView(ExportXlsMixin, AuthMixin, ModelView,
                    GetQueryOrderByidDescMixin):
    pass


class WithdrawView(ExportXlsMixin, AuthMixin, ModelView,
                   GetQueryOrderByidDescMixin):
    column_filters = (('user.username', '用户名'),
                      ('user.realname', '真实姓名'),
                      'status', 'description')

    form_args = {
        'user': {
            'query_factory': lambda: User.query.filter(User.username != 'su')
        }
    }

    @action('deposit_failed', '提现失败')
    @redis_repeat_submit_by_admin_action()
    def withdraw_sort_c_failed(self, ids):
        format_str = '[后台提现记录] 提现失败操作(操作人:{}), 操作对象({})'
        logger.info(format_str.format(get_current_user_id(), ids))
        queryset = Withdraw.query.filter(Withdraw.id.in_(ids))

        for withdraw in queryset:
            withdraw.reject()
        db_session.commit()
        flash('操作成功, 注(已经成功或失败的提现记录将无法被再次操作)', 'success')

    @action('withdraw_success', '提现成功')
    @redis_repeat_submit_by_admin_action()
    def withdraw_sort_b_success(self, ids):
        format_str = '[后台提现记录] 提现成功操作(操作人:{}), 操作对象({})'
        logger.info(format_str.format(get_current_user_id(), ids))
        queryset = Withdraw.query.filter(Withdraw.id.in_(ids))

        for withdraw in queryset:
            withdraw.accept()
        db_session.commit()
        flash('操作成功, 注(已经成功或失败的提现记录将无法被再次操作)', 'success')

    @action('deposit_pending', '开始提现')
    @redis_repeat_submit_by_admin_action()
    def withdraw_sort_a_pending(self, ids):
        format_str = '[后台提现记录] 开始提现操作(操作人:{}), 操作对象({})'
        logger.info(format_str.format(get_current_user_id(), ids))
        queryset = Withdraw.query.filter(Withdraw.id.in_(ids))

        for withdraw in queryset:
            withdraw.start()
        db_session.commit()
        flash('操作成功, 注(已经成功或失败的提现记录将无法被再次操作)', 'success')


class DepositView(ExportXlsMixin, AuthMixin, ModelView,
                  GetQueryOrderByidDescMixin):
    column_filters = ('status', ('user.username', '用户名'),
                      ('platform.name', '平台'), 'added_at')
    form_args = {
        'user': {
            'query_factory': lambda: User.query.filter(User.username != 'su')
        }
    }

    @action('deposit_success', '充值成功')
    @redis_repeat_submit_by_admin_action()
    def deposit_success(self, ids):
        format_str = '[后台充值记录] 充值成功操作(操作人:{}), 操作对象({})'
        logger.info(format_str.format(get_current_user_id(), ids))
        queryset = Deposit.query.filter(Deposit.id.in_(ids))

        for deposit in queryset:
            deposit.accept()
        db_session.commit()
        flash('操作成功, 注(成功或失败的充值记录无法操作)', 'success')

    @action('deposit_failed', '充值失败')
    @redis_repeat_submit_by_admin_action()
    def deposit_failed(self, ids):
        format_str = '[后台充值记录] 充值失败操作(操作人:{}), 操作对象({})'
        logger.info(format_str.format(get_current_user_id(), ids))
        queryset = Deposit.query.filter(Deposit.id.in_(ids))

        for deposit in queryset:
            deposit.reject()
        db_session.commit()
        flash('操作成功, 注(成功或失败的充值记录无法操作)', 'success')


class LogView(ExportXlsMixin, AuthMixin, ModelView,
              GetQueryOrderByidDescMixin):
    column_filters = (('user.username', '用户名'), 'description', 'added_at')
    list_template = 'admin/model/safe_list.html'
    form_args = {
        'user': {
            'query_factory': lambda: User.query.filter(User.username != 'su')
        }
    }


class ApplicationView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    column_filters = ('name', ('user.username', '申请人'),
                      ('guarantee.name', '担保机构'))

    form_args = {
        'user': {
            'query_factory': lambda: User.query.filter(User.username != 'su')
        }
    }

    def get_query(self):
        query = super(ApplicationView, self).get_query()
        query = query.filter(
            Application.status == get_enum('APPLICATION_RISKCONTROL_TRIALING'))
        return query

    def get_count_query(self):
        query = super(ApplicationView, self).get_count_query()
        query = query.filter(
            Application.status == get_enum('APPLICATION_RISKCONTROL_TRIALING'))
        return query

    @action('audit_success', '审核通过')
    @redis_repeat_submit_by_admin_action()
    def audit_success(self, ids):
        applications = Application.query.filter(
            Application.id.in_(ids)
        )
        for application in applications:
            application.status = get_enum('APPLICATION_PROJECT_PUBLISHED')
            # 申请书审核站内信
            title = '系统信息 - 您所申请的项目（{}），已通过审核！'.format(application.name)
            content = '尊敬的用户 - 您于 {} 申请的项目（{}），已通过审核！'.format(
                application.added_at.strftime('%Y年%m月%d日 %H:%M:%S'),
                application.name)
            Message.system_inform(
                to_user=application.user, title=title, content=content)
        db_session.commit()

        logger.info('[申请书审核] 项目ids: {} 审核通过 操作人:{}'.format(
            ids, get_current_user().username))
        flash('操作成功', 'success')

    @action('audit_fail', '审核失败')
    @redis_repeat_submit_by_admin_action()
    def audit_fail(self, ids):
        applications = Application.query.filter(
            Application.id.in_(ids)
        )
        for application in applications:
            application.status = get_enum(
                'APPLICATION_RISKCONTROL_TRIAL_FAILED')
            # 申请书审核站内信
            title = '系统信息 - 您所申请的项目（{}），已通过审核！'.format(application.name)
            content = '尊敬的用户 - 您于 {} 申请的项目（{}），已通过审核！'.format(
                application.added_at.strftime('%Y年%m月%d日 %H:%M:%S'),
                application.name)
            Message.system_inform(
                to_user=application.user, title=title, content=content)
        db_session.commit()

        logger.info('[申请书审核] 项目ids: {} 审核失败 操作人:{}'.format(
            ids, get_current_user().username))
        flash('操作成功!', 'success')


class HistoryFailApplicationView(AuthMixin, ModelView,
                                 GetQueryOrderByidDescMixin):
    column_filters = ('name', ('user.username', '申请人'),
                      ('guarantee.name', '担保机构'))

    form_args = {
        'user': {
            'query_factory': lambda: User.query.filter(User.username != 'su')
        }
    }

    def get_query(self):
        query = super(HistoryFailApplicationView, self).get_query()
        query = query.filter_by(
            status=get_enum('APPLICATION_RISKCONTROL_TRIAL_FAILED'))
        return query

    def get_count_query(self):
        query = super(HistoryFailApplicationView, self).get_count_query()
        query = query.filter_by(
            status=get_enum('APPLICATION_RISKCONTROL_TRIAL_FAILED'))
        return query


class HistorySuccessApplicationView(AuthMixin, ModelView,
                                    GetQueryOrderByidDescMixin):
    column_filters = ('name', ('user.username', '申请人'),
                      ('guarantee.name', '担保机构'))

    form_args = {
        'user': {
            'query_factory': lambda: User.query.filter(User.username != 'su')
        }
    }

    def get_query(self):
        query = super(HistorySuccessApplicationView, self).get_query()
        query = query.filter(
            Application.status == get_enum('APPLICATION_PROJECT_PUBLISHED'))
        return query

    def get_count_query(self):
        query = super(HistorySuccessApplicationView, self).get_count_query()
        query = query.filter(
            Application.status == get_enum('APPLICATION_PROJECT_PUBLISHED'))
        return query


class ConfigView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    pass


class DepositPlatformView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.logic = 'Offline'


class PlansView(ExportXlsMixin, AuthMixin, ModelView):
    column_filters = ('status',
                      ('investment.repayment.user.username', '借款人'),
                      ('investment.user.username', '投资人'))

    def get_query(self):
        query = super(self.__class__, self).get_query()
        query = query.order_by(self.model.status.asc(),
                               self.model.plan_time.asc(),
                               self.model.id.desc())
        return query


class BankcardView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    column_filters = (('user.username', '用户名'), 'card', 'bank')

    form_args = {
        'user': {
            'query_factory': lambda: User.query.filter(User.username != 'su')
        }
    }


class RedPacketTypeView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    def delete_model(self, model):
        if len(model.redpackets) != 0:
            flash('该红包类型，已在使用不能删除！', 'warning')
            return False
        else:
            return super(RedPacketTypeView, self).delete_model(model=model)

    @action('delete', '删除')
    @redis_repeat_submit_by_admin_action()
    def action_delete(self, ids):
        message = None
        session = db_session()
        packets = RedPacketType.query.filter(
            RedPacketType.id.in_(ids)
        )
        try:
            for item in packets:
                if len(item.redpackets) != 0:
                    message = '该红包类型，已在使用不能删除！'
                    break
                session.delete(item)
            session.commit()
        except Exception as ex:
            session.rollback()
            logger.error('[红包类型管理] {}'.format(ex))
            flash('出现未知错误，请联系管理员！', 'error')
        else:
            if message:
                flash(message, 'warning')
            else:
                flash('删除成功', 'success')


class CodeRedPacketLogView(ExportXlsMixin, AuthMixin, ModelView,
                           GetQueryOrderByidDescMixin):
    """ 代码红包兑换记录 """
    pass


class CodeRedPacketView(ExportXlsMixin, AuthMixin, ModelView,
                        GetQueryOrderByidDescMixin):
    """ 代码红包 """

    form_extra_fields = {
        'quantity': IntegerField('数量', validators=[required()]),
        'logic_code': SelectField('类型', validators=[required()],
                                  choices=[('single', '单次使用'),
                                           ('reuse', '重复使用')],)
    }

    def create_model(self, form):
        if form.quantity.data < 1:
            flash('错误的数量!', 'error')
            return False

        if form.invest_amount.data is None or form.invest_amount.data < 0:
            flash('投资要求金额不合理!', 'error')
            return False

        if form.logic_code.data not in consts.REDPACKET_LOGIC_CHOICES:
            flash('类型错误!', 'error')
            return False

        quantity = form.quantity.data
        logic = form.logic_code.data

        while(1):
            if quantity <= 0:
                break
            model = self.model()
            form.populate_obj(model)
            model.calc_expires_at(model.valid)
            model.code = generate_unique_code(CodeRedPacket)
            model.logic = logic
            self.session.add(model)
            self._on_model_change(form, model, True)
            self.session.commit()
            quantity -= 1
        return True


class RedPacketView(ExportXlsMixin, AuthMixin, ModelView,
                    GetQueryOrderByidDescMixin):
    column_filters = (('user.username', '用户名'), ('type.name', '类型'),
                      'is_use', 'is_available', 'added_at')

    form_args = {
        'user': {
            'query_factory': lambda: User.query.filter(User.username != 'su')
        },
        'type': {
            'query_factory': lambda: RedPacketType.query.filter_by(
                is_show=True,
            ).filter(
                RedPacketType.logic != consts.CODE_REDPACKET_TYPE_LOGIC
            )
        },
    }

    def create_form(self, obj=None):
        form = super(RedPacketView, self).create_form(obj)
        form.is_available.data = True
        return form

    def on_model_change(self, form, model, is_created=None):
        if redis.get('redpacket_view_create:{}'.format(model.user.id)):
            raise Exception('请求太频繁，请稍后重试')
        redis.set('redpacket_view_create:{}'.format(model.user.id), 0, 3)

        if is_created:
            model.added_at = datetime.datetime.now()


class AuthenticationFieldTypeInlineModelForm(InlineFormAdmin):
    form_columns = ['id', 'name', 'order', 'is_content', 'required', 'score']
    column_labels = {'name': '名称', 'order': '排序',
                     'is_content': '是否是文本', 'required': '是否必须', 'score': '宝币'}


class AuthenticationTypeView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    inline_models = (
        AuthenticationFieldTypeInlineModelForm(AuthenticationFieldType),)


class AuthenticationFieldInlineModelForm(InlineFormAdmin):
    form_columns = ['id', 'type', 'value']
    column_labels = {'type': '认证类型', 'value': '内容'}


class AuthenticationView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    inline_models = (AuthenticationFieldInlineModelForm(AuthenticationField),)
    form_readonly_columns = ['user', 'type']
    column_filters = (('user.username', '用户名'), ('type.name', '类型'))
    form_extra_fields = {
        'is_pass': SelectField('审核', choices=[
            ('pending', '待审核'), ('access', '通过'), ('failed', '失败')])
    }

    form_args = {
        'user': {
            'query_factory': lambda: User.query.filter(User.username != 'su')
        }
    }

    def get_query(self):
        query = super(AuthenticationView, self).get_query()
        query = query.filter(Authentication.type_id == AuthenticationType.id,
                             AuthenticationType.logic == 'idcard')
        return query

    def get_count_query(self):
        query = super(AuthenticationView, self).get_count_query()
        query = query.filter(Authentication.type_id == AuthenticationType.id,
                             AuthenticationType.logic == 'idcard')
        return query

    def edit_form(self, obj=None):
        form = super(AuthenticationView, self).edit_form(obj=obj)
        if request.method == 'GET':
            if obj.status:
                form.is_pass.data = 'access'
            else:
                form.is_pass.data = 'pending'
        return form

    def on_model_change(self, form, model, is_created):
        user_id = get_current_user_id()
        if not is_created:
            is_pass = request.form.get('is_pass')
            if is_pass == 'access':
                model.accept()
                logger.info('[{}] (审核通过) 审核人:{}, 用户:{}'.format(
                    model.type, user_id, model.user.id))
            elif is_pass == 'failed':
                model.reject()
                model.is_edit = True
                logger.info('[{}] (审核失败) 审核人:{}, 用户:{}'.format(
                    model.type, user_id, model.user.id))


class IdCardLogView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    pass


class AuthView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    column_filters = ('username',)

    form_extra_fields = {
        'auths': MultiCheckboxField('认证类型', choices=[], coerce=int)
    }

    def get_query(self):
        query = super(AuthView, self).get_query()
        query = query.filter(User.username != 'su').order_by('id')
        return query

    def get_count_query(self):
        query = super(AuthView, self).get_count_query()
        query = query.filter(User.username != 'su')
        return query

    def edit_form(self, obj=None):
        form = super(AuthView, self).edit_form(obj=obj)
        form.auths.choices = db_session.\
            query(AuthenticationType.id, AuthenticationType.name).filter(
                AuthenticationType.logic.notin_(('idcard', 'email'))).all()
        if request.method == 'GET':
            authentications = Authentication.query.filter_by(
                user_id=obj.id).all()
            form.auths.data = [i.type.id for i in authentications if i.status]
        return form

    def on_model_change(self, form, model, is_created):
        if not is_created:
            choices = list(c[0] for c in form.auths.choices)
            for i in choices:
                if i in form.auths.data:
                    Authentication.get_or_create_object_with_accept(model, i)
                else:
                    Authentication.get_or_create_object_with_reject(model, i)

    def after_model_change(self, form, model, is_created):
        if not is_created:
            model.calculate_cert_level()
            db_session.commit()


def get_permission_choices(permission_dict):
    return [(key, permission_dict[key]) for key in
            sorted(permission_dict.keys())]


class GroupView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    permission_unit = get_permission_choices(
        permissions.get('staff_permissions_key'))

    form_extra_fields = {
        'permission_unit': MultiCheckboxField('权限类型',
                                              choices=permission_unit,
                                              coerce=str)
    }

    def edit_form(self, obj=None):
        form = super(GroupView, self).edit_form(obj=obj)
        if request.method == 'GET':
            form.permission_unit.data = obj._permissions
        return form

    def on_model_change(self, form, model, is_created):
        model._permissions = model.permission_unit


class UserPermissionView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    def get_query(self):
        query = super(UserPermissionView, self).get_query()
        query = query.filter(User.username != 'su',
            User.is_staff == True).order_by('id')
        return query

    def get_count_query(self):
        query = super(UserPermissionView, self).get_count_query()
        query = query.filter(User.username != 'su',
            User.is_staff == True)
        return query


class BannerView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    form_overrides = {
        'src': AbstackImageUploadField,
        'location': SelectField
    }
    form_args = {
        'src': {
            'base_path': file_path,
            'relative_path': 'media/banner/',
        },
        'location': {
            'label': '显示位置',
            'choices': [(str(get_enum('BANNER_WEB')), 'PC端'),
                        (str(get_enum('BANNER_WECHAT')), '微信')]
        }
    }

    def on_model_change(self, form, model, is_created=None):
        if model and not model.src.startswith('/'):
            model.src = "/" + model.src

    def edit_form(self, obj=None):
        form = super(BannerView, self).edit_form(obj=obj)

        if request.method == 'POST' and obj.src and not form.src.data.filename:
            form._fields.pop('src')
        return form


class WechatBannerView(BannerView):

    form_args = {
        'src': {
            'base_path': file_path,
            'relative_path': 'media/banner/',
        },
        'location': {
            'label': '显示位置',
            'choices': [(str(get_enum('BANNER_WECHAT')), '微信')]
        }
    }

    def get_query(self):
        query = super(WechatBannerView, self).get_query()
        query = query.filter_by(location=get_enum('BANNER_WECHAT'))
        return query

    def get_count_query(self):
        query = super(WechatBannerView, self).get_count_query()
        query = query.filter_by(location=get_enum('BANNER_WECHAT'))
        return query


class PCBannerView(BannerView):

    form_args = {
        'src': {
            'base_path': file_path,
            'relative_path': 'media/banner/',
        },
        'location': {
            'label': '显示位置',
            'choices': [(str(get_enum('BANNER_WEB')), 'PC端')]
        }
    }

    def get_query(self):
        query = super(PCBannerView, self).get_query()
        query = query.filter_by(location=get_enum('BANNER_WEB'))
        return query

    def get_count_query(self):
        query = super(PCBannerView, self).get_count_query()
        query = query.filter_by(location=get_enum('BANNER_WEB'))
        return query


class StudentApplyBannerView(BannerView):

    form_args = {
        'src': {
            'base_path': file_path,
            'relative_path': 'media/banner/',
        },
        'location': {
            'label': '显示位置',
            'choices': [(str(get_enum('BANNER_STUDENT_APPLY')), '学仕贷')]
        }
    }

    def get_query(self):
        query = super(StudentApplyBannerView, self).get_query()
        query = query.filter_by(location=get_enum('BANNER_STUDENT_APPLY'))
        return query

    def get_count_query(self):
        query = super(StudentApplyBannerView, self).get_count_query()
        query = query.filter_by(location=get_enum('BANNER_STUDENT_APPLY'))
        return query


class ManuallySMSView(AuthMixin, BaseView):

    @expose('/', methods=['GET', 'POST'])
    def index(self):
        users = db_session.query(
            User.id, User.username
        ).filter_by(is_staff=False, is_super=False, is_active=True).all()

        ids = [i[0] for i in users]
        data = {'users': users, 'can_send': False}

        if request.method == 'POST':
            data['init'] = False
            data['can_send'] = False
            content = request.form.get('content')
            data['content'] = content
            recvs = request.form.getlist('users')

            if redis.exists('manuallysmsview'):
                data['message'] = '请求太频繁，请稍后重试!'
                return self.render('admin/manually_send_sms.html', data=data)

            if not content or content.strip() == '':
                data['message'] = '请输入短信内容!'
            elif len(content) > 280:
                data['message'] = '短信内容不能多于280个字!'
            else:
                if not recvs:
                    data['can_send'] = True
                    data['recv'] = '所有用户'
                    data['message'] = '成功'
                    batch_send_sms.delay(content, ids)
                else:
                    recv_ids = self.get_recv_ids(recvs)
                    if not recv_ids or set(recv_ids) > set(ids):
                        data['message'] = '不存在的用户'
                        data['check_users'] = recv_ids
                    else:
                        data['can_send'] = True
                        data['recv'] = '指定用户'
                        data['message'] = '成功'
                        batch_send_sms.delay(content, recv_ids)

            if data['can_send']:
                redis.set('manuallysmsview', 0, 30)
            return self.render('admin/manually_send_sms.html', data=data)
        else:
            return self.redirect_get(data)

    def get_recv_ids(self, data):
        try:
            recv_ids = [int(i) for i in data]
        except ValueError:
            return None
        else:
            return recv_ids

    def redirect_get(self, data):
        data = {'users': data['users'], 'can_send': False, 'init': True}
        return self.render('admin/manually_send_sms.html', data=data)


class FirendLinkView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    form_overrides = {
        'img': AbstackImageUploadField,
        'logic': SelectField
    }
    form_args = {
        'img': {
            'base_path': file_path,
            'relative_path': 'media/firend/',
        },
        'logic': {
            'label': '存放位置',
            'choices': [('firendlink', '合作伙伴'), ('links', '友情链接')]
        }
    }

    def create_form(self, obj=None):
        form = super(FirendLinkView, self).create_form(obj=obj)
        if request.method == 'POST' and not form.img.data.filename and \
                form.data['logic'] == 'links':
            form._fields.pop('img')
        return form

    def edit_form(self, obj=None):
        form = super(FirendLinkView, self).edit_form(obj=obj)

        if request.method == 'POST' and obj.img and not form.img.data.filename:
            form._fields.pop('img')
        if request.method == 'POST' and obj.logic == 'links':
            form._fields.pop('img')
        return form

    def on_model_change(self, form, model, is_created=None):
        if model and model.img and not model.img.startswith('/'):
            model.img = "/" + model.img


class MessageView(ExportXlsMixin, AuthMixin, ModelView,
                  GetQueryOrderByidDescMixin):
    column_filters = ('title', ('to_user.username', '收件人'), 'content',
                      'added_at')
    form_overrides = dict(select_user=Select2Field)
    form_columns = ('select_user', 'title', 'content')
    user_list = [
        [0, '所有用户']
    ]

    form_extra_fields = {
        'select_user': Select2Field('收件人', choices=user_list, coerce=int)
    }
    action_disallowed_list = ['delete']

    def on_model_change(self, form, model, is_created):
        admin_user = User.query.get(2)  # 发件人
        model.to_user = admin_user

        select_user = model.select_user   # 收件人
        if select_user == 0:
            user_list = User.query.filter(User.username != 'su').all()
            for item in user_list:
                Message.system_inform(to_user=item, title=model.title,
                                      content=model.content)

    su = User.query.filter(User.username == 'su').first()

    def get_query(self):
        query = super(MessageView, self).get_query()
        query = query.filter(Message.to_user != self.su)
        return query

    def get_count_query(self):
        query = super(MessageView, self).get_count_query()
        query = query.filter(Message.to_user != self.su)
        return query


class CheckSMSCodeView(AuthMixin, BaseView):
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        if request.method == 'POST':
            phone = request.form.get('phone')
            if not phone.isdigit() or len(phone) != 11:
                flash('手机号码错误', 'error')
                return self.redirect_get()
            keys = redis.keys("*{}*".format(phone))
            data = []
            for key in keys:
                value = redis.get(key).decode()
                key = key.decode().split(':')[0]
                key = project_config['SMS_CODE_ALLOWED_KEYWORD_STR'].get(
                    key[:-11], '未知操作')
                data.append((key, value))
            return self.render('admin/check_sms_code.html', search=True,
                               data=data, phone=phone)
        else:
            return self.redirect_get()

    def redirect_get(self):
        return self.render('admin/check_sms_code.html', search=False)


class FinApplicationPlanInlineModel(InlineFormAdmin):
    form_label = '还款计划'
    form_columns = ['id', 'period', 'amount', 'interest', 'status',
                    'plan_time', 'executed_time']
    column_labels = {
        'id': '编号',
        'period': '期数',
        'amount': '金额',
        'interest': '利息',
        'status': '状态',
        'is_advance': '是否垫付',
        'plan_time': '计划时间',
        'executed_time': '还款时间'
    }

    def __init__(self):
        return super(FinApplicationPlanInlineModel, self).__init__(
            FinApplicationPlan)


class FinApplicationView(ExportXlsMixin, AuthMixin, ModelView,
                         GetQueryOrderByidDescMixin):
    """理财申请书"""

    column_filters = ('uid', ('user.username', '申请人'))
    inline_models = (FinApplicationPlanInlineModel(),)

    def get_query(self):
        query = super(FinApplicationView, self).get_query()
        query = query.filter_by(
            status=get_enum('FINAPPLICATION_PENDING')
        )
        return query

    def get_count_query(self):
        query = super(FinApplicationView, self).get_count_query()
        query = query.filter_by(
            status=get_enum('FINAPPLICATION_PENDING')
        )
        return query

    @action('review_pass', '审核通过')
    @redis_repeat_submit_by_admin_action()
    def review_pass(self, ids):
        items = FinApplication.query.filter(FinApplication.id.in_(ids))
        user = get_current_user()
        username = Config.get_config('FINPROJECT_USER')
        claim = User.query.filter_by(username=username).first()
        if not claim:
            raise Exception('后台设置的学仕贷资金代管账户错误')
        for item in items:
            if item.status == get_enum('FINAPPLICATION_PENDING'):
                item.status = get_enum('FINAPPLICATION_VERIFY_SUCCESS')
                item.auditor = user
                item.claim = claim
                item.success()
                item.generate_plan()
                item.end_at = datetime.datetime.now()
        db_session.commit()
        flash('操作成功', 'success')

    @action('review_fail', '审核失败')
    @redis_repeat_submit_by_admin_action()
    def review_fail(self, ids):
        items = FinApplication.query.filter(FinApplication.id.in_(ids))
        user = get_current_user()
        for item in items:
            if item.status == get_enum('FINAPPLICATION_PENDING'):
                item.status = get_enum('FINAPPLICATION_VERIFY_FAILED')
                item.auditor = user
                item.end_at = datetime.datetime.now()
        db_session.commit()
        flash('操作成功', 'success')


class FinMobileApplicationView(ExportXlsMixin, AuthMixin, ModelView,
                               GetQueryOrderByidDescMixin):
    """手机端理财申请书"""
    column_filters = (('user.username', '申请人'),)


class HistoryFailFinApplicationView(ExportXlsMixin, AuthMixin, ModelView,
                                    GetQueryOrderByidDescMixin):
    """理财申请书审核失败"""
    column_filters = ('uid', ('user.username', '申请人'))

    def get_query(self):
        query = super(HistoryFailFinApplicationView, self).get_query()
        query = query.filter_by(
            status=get_enum('FINAPPLICATION_VERIFY_FAILED')
        )
        return query

    def get_count_query(self):
        query = super(HistoryFailFinApplicationView, self).get_count_query()
        query = query.filter_by(
            status=get_enum('FINAPPLICATION_VERIFY_FAILED')
        )
        return query


class HistorySuccessFinApplicationView(ExportXlsMixin, AuthMixin, ModelView,
                                       GetQueryOrderByidDescMixin):
    """理财申请书审核成功"""
    column_filters = ('uid', ('user.username', '申请人'))

    def get_query(self):
        query = super(HistorySuccessFinApplicationView, self).get_query()
        query = query.filter_by(
            status=get_enum('FINAPPLICATION_VERIFY_SUCCESS')
        )
        return query

    def get_count_query(self):
        query = super(HistorySuccessFinApplicationView, self).get_count_query()
        query = query.filter_by(
            status=get_enum('FINAPPLICATION_VERIFY_SUCCESS')
        )
        return query


class FinApplicationPlansView(ExportXlsMixin, AuthMixin, ModelView):
    column_filters = ('status', ('application.uid', '申请书编号'))

    def get_query(self):
        query = super(self.__class__, self).get_query()
        query = query.order_by(self.model.status.asc(),
                               self.model.plan_time.asc(),
                               self.model.id.desc())
        return query


class BorrowerView(ExportXlsMixin, AuthMixin, ModelView,
                   GetQueryOrderByidDescMixin):

    def get_query(self):
        query = super(BorrowerView, self).get_query()
        query = query.filter(
            User.username != 'su',
            User.is_borrower == True)

        return query

    def get_count_query(self):
        query = super(BorrowerView, self).get_count_query()
        query = query.filter(
            User.username != 'su',
            User.is_borrower == True)
        return query


class RealNameAuthView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    """ 第三方实名认证 """
    column_filters = (('user.username', '用户名'),)


class SourceWebsiteView(ExportXlsMixin, AuthMixin, ModelView,
                   GetQueryOrderByidDescMixin):

    def get_query(self):
        query = super(SourceWebsiteView, self).get_query()
        return query

    def get_count_query(self):
        query = super(SourceWebsiteView, self).get_count_query()
        return query


class SourceUserView(ExportXlsMixin, AuthMixin, ModelView,
                   GetQueryOrderByidDescMixin):
 
    column_filters = (('source_website.name', '推广来源'), 'source_code', 'added_at')
    def get_query(self):
        query = super(SourceUserView, self).get_query()
        query = query.filter(
            User.username != 'su',
            User.source_website_id !=None)

        return query

    def get_count_query(self):
        query = super(SourceUserView, self).get_count_query()
        query = query.filter(
            User.username != 'su',
            User.source_website_id !=None)
        return query

class AutomaticView(ExportXlsMixin, AuthMixin, ModelView,
                   GetQueryOrderByidDescMixin):

    column_filters = (('user.username', '用户名'), 'is_open')

    def get_query(self):
        query = super(AutomaticView, self).get_query()
        query = query.filter()
        return query

    def get_count_query(self):
        query = super(AutomaticView, self).get_count_query()
        query = query.filter()
        return query

    @action('auto_switch', '开启/关闭')
    @redis_repeat_submit_by_admin_action()
    def auto_switch(self, ids):
        queryset = AutoInvestment.query.filter(AutoInvestment.id.in_(ids))
        for user in queryset:
            user.is_open = not user.is_open
        db_session.commit()
        flash('操作成功', 'success')

class CommoditysView(ExportXlsMixin, AuthMixin, ModelView,
                   GetQueryOrderByidDescMixin):
    column_filters = ('is_show', 'type')
    
    form_overrides = {
        'src': AbstackImageUploadField,
        'type': Select2Field,
        'category': Select2Field,
        'details': CKTextAreaField
    }
    form_args = {
        'src': {
            'base_path': file_path,
            'relative_path': 'media/mall/',
        },
    }

    def on_model_change(self, form, model, is_created=None):
        if model and not model.src.startswith('/'):
            model.src = "/" + model.src

    def edit_form(self, obj=None):
        form = super(CommoditysView, self).edit_form(obj=obj)

        if request.method == 'POST' and obj.src and not form.src.data.filename:
            form._fields.pop('src')
        return form

    @action('show_switch', '显示/关闭')
    @redis_repeat_submit_by_admin_action()
    def show_switch(self, ids):
        queryset = Commodity.query.filter(Commodity.id.in_(ids))
        for commod in queryset:
            commod.is_show = not commod.is_show
        db_session.commit()
        flash('操作成功', 'success')


class CommodityOrderView(ExportXlsMixin, AuthMixin, ModelView,
                   GetQueryOrderByidDescMixin):
    column_filters = (('user.username', '订单人'), 
        ('commodity.name', '订单名称'), 'status')
    form_overrides = {
        'status': Select2Field
    }

    def action(name, text, confirmation=None):
        def wrap(f):
            f._action = (name, text, confirmation)
            return f
        return wrap

    @action('cancel_order', '取消订单', '本次操作将会退回宝币(交易完成和取消订单将会跳过)，确定操作吗？')
    @redis_repeat_submit_by_admin_action()
    def cancel_order(self, ids):
        queryset = CommodityOrder.query.filter(CommodityOrder.id.in_(ids))
        for order in queryset:
            if order.status in  (get_enum('ORDER_STATUS_CANCEL'), 
                get_enum('ORDER_STATUS_SUCCESS')):
                continue
            order.user.gift_points += order.amount

            msgstr = '您在 {}兑换的 - {} 订单被撤销，合计退回 {} 点宝币'
            desc = msgstr.format(
                order.added_at.strftime('%Y年%m月%d日 %H:%M:%S'),
                order.commodity.name,
                '{:,.2f}'.format(order.amount)
            )
            order.status = get_enum('ORDER_STATUS_CANCEL')
            order.process_at.data = datetime.datetime.now()
            GiftPoint.add(user=order.user, points=order.amount, description=desc)

            logger.info(('[后台商城订单撤销] 操作人:{}, 操作对象({})').format(
            get_current_user_id(), ids))

        db_session.commit()
        flash('操作成功', 'success')

    def update_model(self, form, model):
        if model.status != get_enum('ORDER_STATUS_CANCEL') and \
            form.status.data == get_enum('ORDER_STATUS_CANCEL'):
            flash('无权限取消订单', 'error')
            return False
        elif model.commodity.type != get_enum('MALL_COMMODITY_VIRTAUL'):
            form.process_at.data = datetime.datetime.now()

        return super(CommodityOrderView, self).update_model(form, model)


class GiftPointView(ExportXlsMixin, AuthMixin, ModelView,
                   GetQueryOrderByidDescMixin):
    column_filters = (('user.username', '用户'), 'added_at')

class UserLevelView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    pass

class UserLevelLogView(AuthMixin, ModelView, GetQueryOrderByidDescMixin):
    column_filters = (('user.username', '用户'), 'added_at')