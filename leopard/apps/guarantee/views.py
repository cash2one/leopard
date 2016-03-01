import os
import urllib

from flask import (Blueprint, flash, make_response, redirect, render_template,
                   request, url_for)
from flask.ext.admin import BaseView, expose
from flask.ext.admin.actions import action
from PIL import Image
from wtforms import FileField

from leopard.comps.admin import ModelView
from leopard.core.orm import db_session
from leopard.helpers import generate_media_filename, get_enum, get_current_user
from leopard.orm import Application, Guarantee, Project

from . import AuthMixin

blueprint = Blueprint('views', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in get_enum('ALLOWED_EXTENSIONS')


def resize_logo(region_resize):
    region_x = region_resize[0]
    region_y = region_resize[1]
    if region_x/region_y >= 2:
        size = region_y / region_x * 400
        region_resize = (400, int(size))
    else:
        size = region_x / region_y * 200
        region_resize = (int(size), 200)
    return region_resize


def resize_thumb(thumbnail_resize):
    thumbnail_x = thumbnail_resize[0]
    thumbnail_y = thumbnail_resize[1]
    if thumbnail_x > 100:
        size = thumbnail_y / thumbnail_x * 100
        thumbnail_resize = (100, int(size))
    else:
        size = thumbnail_x / thumbnail_y * 100
        thumbnail_resize = (int(size), 100)
    return thumbnail_resize


@blueprint.route('/post_image_upload', methods=['POST'])
def post_image_upload():
    ck_num = request.values['CKEditorFuncNum']
    if not request.files:
        return make_response(render_template('admin/ck_callback.html', message="请选择上传图片", CKFuncNum=ck_num))
    f = request.files['upload']
    image_data = f.read()
    image_size = len(image_data)
    f.seek(0)
    if image_size > get_enum('MAX_IMAGE_SIZE'):
        return make_response(render_template('admin/ck_callback.html', message="图片太大了", CKFuncNum=ck_num))
    if not allowed_file(f.filename):
        return make_response(render_template('admin/ck_callback.html', message="图片格式错误", CKFuncNum=ck_num))
    name = f.filename
    image_name = '{}{}'.format(generate_media_filename(), os.path.splitext(name)[-1]).lower()
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

    image_url = urllib.parse.urljoin(get_enum('POSTS_IMAGE_FOLDER'), image_name)
    image_path = urllib.parse.urljoin('/', image_url)
    return make_response(render_template('admin/ck_callback.html', callback=True, image_path=image_path,
                                         CKFuncNum=ck_num))


class GuaranteeProfile(BaseView):

    def is_visible(self):
        return False

    @expose('/', methods=('GET', 'POST'))
    def index(self):
        if request.method == 'GET':
            user = get_current_user()
            if not user:
                return redirect(url_for('admin.login_view'))
            guarantee = Guarantee.query.get(user.guarantee.id)
            return self.render('edit_profile.html', guarantee=guarantee)
        else:
            user = get_current_user()
            if not user:
                return redirect(url_for('admin.login_view'))

            name = request.form['name']
            phone = request.form['phone']
            description = request.form['description']
            guarantee = Guarantee.query.get(user.guarantee.id)
            guarantee.name = name
            guarantee.phone = phone
            guarantee.description = description
            try:
                db_session.commit()
            except:
                flash('修改失败', 'danger')
            flash('修改成功', 'success')
            return self.render('edit_profile.html', guarantee=guarantee)


class UserView(AuthMixin, ModelView):
    pass


class ApplicationView(AuthMixin, ModelView):

    def get_query(self):
        user = get_current_user()
        query = super(ApplicationView, self).get_query()
        query = query.filter(Application.guarantee == user.guarantee,
                             Application.status == get_enum('APPLICATION_GUARANTEE_TRIALING'))
        return query

    def get_count_query(self):
        user = get_current_user()
        query = super(ApplicationView, self).get_count_query()
        query = query.filter(Application.guarantee == user.guarantee,
                             Application.status == get_enum('APPLICATION_GUARANTEE_TRIALING'))
        return query

    @action('auditing', '审核通过')
    def auditing(self, ids):
        for i in ids:
            application = Application.query.get(i)
            application.status = get_enum('APPLICATION_RISKCONTROL_TRIALING')

        db_session.commit()
        flash('操作成功!', 'success')

    @action('auditing_fail', '审核失败')
    def action_fail(self, ids):
        for i in ids:
            application = Application.query.get(i)
            application.status = get_enum('APPLICATION_GUARANTEE_TRIAL_FAILED')

        db_session.commit()
        flash('操作成功!', 'success')


class SuccessApplicationView(AuthMixin, ModelView):

    def get_query(self):
        user = get_current_user()
        query = super(SuccessApplicationView, self).get_query()
        query = query.filter(Application.guarantee == user.guarantee,
                             Application.status >= get_enum('APPLICATION_RISKCONTROL_TRIALING'))
        return query

    def get_count_query(self):
        user = get_current_user()
        query = super(SuccessApplicationView, self).get_count_query()
        query = query.filter(Application.guarantee == user.guarantee,
                             Application.status >= get_enum('APPLICATION_RISKCONTROL_TRIALING'))
        return query


class PublishedApplicationView(AuthMixin, ModelView):

    def get_query(self):
        user = get_current_user()
        query = super(PublishedApplicationView, self).get_query()
        query = query.filter(Application.auditor == user,
                             Application.status == get_enum('APPLICATION_PROJECT_PUBLISHED'))
        return query

    def get_count_query(self):
        user = get_current_user()
        query = super(PublishedApplicationView, self).get_count_query()
        query = query.filter(Application.auditor == user,
                             Application.status == get_enum('APPLICATION_PROJECT_PUBLISHED'))
        return query


class FailApplicationView(AuthMixin, ModelView):

    def get_query(self):
        user = get_current_user()
        query = super(FailApplicationView, self).get_query()
        query = query.filter(Application.auditor == user,
                             Application.status == get_enum('APPLICATION_GUARANTEE_TRIAL_FAILED'))
        return query

    def get_count_query(self):
        user = get_current_user()
        query = super(FailApplicationView, self).get_count_query()
        query = query.filter(Application.auditor == user,
                             Application.status == get_enum('APPLICATION_GUARANTEE_TRIAL_FAILED'))
        return query


class GuaranteeProfileView(AuthMixin, ModelView):
    pass


class GuaranteeLogoView(AuthMixin, ModelView):
    save_path = os.path.join(get_enum('GUARANTEE_FOLDER'))
    form_overrides = {'logo': FileField}
    column_descriptions = dict(
        logo='建议图片上传尺寸为(400*200)'
    )

    def update_model(self, form, model):
        if not form.data['logo'].filename:
            flash('请选择上传图片！', 'warning')
            return False
        if form.data['logo'].mimetype.split('/')[-1].lower() not in get_enum('ALLOWED_IMAGE_EXTENSIONS'):
            flash('图片格式错误！', 'warning')
            return False
        file_stream = form.data['logo'].stream
        file_size = len(file_stream.read())
        if file_size > get_enum('MAX_IMAGE_SIZE'):
            flash('图片太大了！', 'warning')
            return False
        file_stream.seek(0)
        return super(GuaranteeLogoView, self).update_model(form, model)

    def _on_model_change(self, form, model, is_created):
        file_data = request.files['logo']
        if file_data:
            region = Image.open(file_data.stream)
            thumbnail = region.copy()
            logo_name = '{}{}'.format(generate_media_filename(), os.path.splitext(file_data.filename)[-1]).lower()
            logo_path = os.path.join(get_enum('GUARANTEE_FOLDER'), logo_name)

            model.logo = logo_path
            region_resize = resize_logo(region.size)

            region = region.resize(region_resize, Image.ANTIALIAS)
            region.save(logo_path)

            thumbnail_resize = resize_thumb(region_resize)
            thumbnail_name = '{}@thumb{}'.format(generate_media_filename(), os.path.splitext(file_data.filename)[-1]).lower()
            thumbnail_path = os.path.join(get_enum('GUARANTEE_FOLDER'), thumbnail_name)
            thumbnail = thumbnail.resize(thumbnail_resize, Image.ANTIALIAS)
            thumbnail.save(thumbnail_path)


class ProjectView(AuthMixin, ModelView):

    def get_query(self):
        user = get_current_user()
        query = super(ProjectView, self).get_query()
        query = query.filter(Project.guarantee == user.guarantee)
        return query

    def get_count_query(self):
        user = get_current_user()
        query = super(ProjectView, self).get_count_query()
        query = query.filter(Project.guarantee == user.guarantee)
        return query


