import os
import os.path as op

from PIL import Image
from wtforms import SelectMultipleField, ValidationError
from wtforms.widgets import ListWidget, CheckboxInput
from werkzeug.datastructures import FileStorage
from flask.ext.admin.babel import gettext
from flask.ext.admin._compat import urljoin
from flask.ext.admin.form.upload import ImageUploadField, ImageUploadInput

from leopard.helpers import generate_media_filename


class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


def prefix_name(obj, file_data):
    filename, suffix = op.splitext(file_data.filename)
    return '{}{}'.format(generate_media_filename(), suffix)


class AbstackImageUploadInput(ImageUploadInput):

    def get_url(self, field):
        if field.thumbnail_size:
            filename = field.thumbnail_fn(field.data)
        else:
            filename = field.data

        if field.url_relative_path:
            filename = urljoin(field.url_relative_path, filename)

        return filename


class AbstackImageUploadField(ImageUploadField):
    widget = AbstackImageUploadInput()

    def __init__(self, label=None, validators=None,
                 base_path=None, relative_path=None,
                 namegen=None, allowed_extensions=None,
                 max_size=None,
                 thumbgen=None, thumbnail_size=None,
                 permission=0o755,
                 url_relative_path=None, endpoint='static',
                 **kwargs):
        namegen = namegen or prefix_name
        super(AbstackImageUploadField,
              self).__init__(label=label, validators=validators,
                             base_path=base_path,
                             relative_path=relative_path, namegen=namegen,
                             allowed_extensions=allowed_extensions,
                             max_size=max_size, thumbgen=thumbgen,
                             thumbnail_size=thumbnail_size,
                             permission=permission,
                             url_relative_path=url_relative_path,
                             endpoint=endpoint, **kwargs)

    def pre_validate(self, form):
        if (self.data
                and self.data.filename
                and isinstance(self.data, FileStorage)):

            if not self.is_file_allowed(self.data.filename):
                raise ValidationError(gettext('Invalid file extension'))
            try:
                self.image = Image.open(self.data)
            except Exception as e:
                raise ValidationError('Invalid image: %s' % e)

    def _delete_file(self, filename):
        if filename.startswith('/'):
            filename = filename[1:]
        path = self._get_path(filename)

        if op.exists(path):
            os.remove(path)

    def populate_obj(self, obj, name):
        field = getattr(obj, name, None)

        if field:
            if self._should_delete:
                self._delete_file(field)
                setattr(obj, name, None)
                return

        if self.data and self.data.filename and isinstance(self.data,
                                                           FileStorage):
            if field:
                self._delete_file(field)

            filename = self.generate_name(obj, self.data)
            filename = self._save_file(self.data, filename)
            # update filename of FileStorage to our validated name
            self.data.filename = filename

            if filename and not filename.startswith('/'):
                filename = "/" + filename
            setattr(obj, name, filename)

    def _save_file(self, data, filename):
        path = self._get_path(filename)

        if not op.exists(op.dirname(path)):
            os.makedirs(os.path.dirname(path), self.permission)

        # Figure out format
        filename, format = self._get_save_format(filename, self.image)

        if self.image and (self.image.format != format or self.max_size):
            if self.max_size:
                image = self._resize(self.image, self.max_size)
            else:
                image = self.image

            self._save_image(image, self._get_path(filename), format)
        else:
            data.seek(0)
            data.save(self._get_path(filename))

        self._save_thumbnail(data, filename, format)
        return filename
