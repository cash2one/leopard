from flask import g, request, session
from flask.ext.seasurf import SeaSurf as official_SeaSurf, _same_origin
from flask.ext.restful import abort
from werkzeug.security import safe_str_cmp


REASON_NO_REFERER = 'Referer checking failed: no referer.'
REASON_BAD_REFERER = 'Referer checking failed: %s does not match %s.'
REASON_NO_CSRF_TOKEN = 'CSRF token not set.'
REASON_BAD_TOKEN = 'CSRF token missing or incorrect.'


class SeaSurf(official_SeaSurf):

    def _before_request(self):
        '''Determine if a view is exempt from CSRF validation and if not
        then ensure the validity of the CSRF token. This method is bound to
        the Flask `before_request` decorator.

        If a request is determined to be secure, i.e. using HTTPS, then we
        use strict referer checking to prevent a man-in-the-middle attack
        from being plausible.

        Validation is suspended if `TESTING` is True in your application's
        configuration.
        '''

        if self._csrf_disable:
            return  # don't validate for testing

        csrf_token = session.get(self._csrf_name, None)
        if not csrf_token:
            setattr(g, self._csrf_name, self._generate_token())
        else:
            setattr(g, self._csrf_name, csrf_token)

        # Always set this to let the response know whether or not to set the
        # CSRF token
        g._view_func = self.app.view_functions.get(request.endpoint)

        if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            # Retrieve the view function based on the request endpoint and
            # then compare it to the set of exempted views
            if not self._should_use_token(g._view_func):
                return

            if request.is_secure:
                referer = request.headers.get('Referer')
                if referer is None:
                    error = (REASON_NO_REFERER, request.path)
                    self.app.logger.warning('Forbidden (%s): %s' % error)
                    return abort(403, message='请重试', status=403)

                # by setting the Access-Control-Allow-Origin header, browsers
                # will let you send cross-domain ajax requests so if there is
                # an Origin header, the browser has already decided that it
                # trusts this domain otherwise it would have blocked the
                # request before it got here.
                allowed_referer = (request.headers.get('Origin') or
                                   request.url_root)
                if not _same_origin(referer, allowed_referer):
                    error = REASON_BAD_REFERER % (referer, allowed_referer)
                    error = (error, request.path)
                    self.app.logger.warning('Forbidden (%s): %s' % error)
                    return abort(403, message='请重试', status=403)

            request_csrf_token = request.form.get(self._csrf_name, '')
            if request_csrf_token == '':
                # As per the Django middleware, this makes AJAX easier and
                # PUT and DELETE possible
                request_csrf_token = request.headers.get(
                    self._csrf_header_name, '')

            some_none = None in (request_csrf_token, csrf_token)
            if some_none or not safe_str_cmp(request_csrf_token, csrf_token):
                error = (REASON_BAD_TOKEN, request.path)
                self.app.logger.warning('Forbidden (%s): %s' % error)
                return abort(403, message='请重试', status=403)
