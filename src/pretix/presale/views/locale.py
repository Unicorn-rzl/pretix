from datetime import datetime, timedelta
from django.conf import settings
from django.shortcuts import redirect
from django.views.generic import View


class LocaleSet(View):

    def get(self, request, *args, **kwargs):
        locale = request.GET.get('locale')
        resp = redirect(request.GET.get('next', request.META.get('HTTP_REFERER', '/')))
        if locale in [lc for lc, ll in settings.LANGUAGES]:
            if request.user.is_authenticated():
                request.user.locale = locale
                request.user.save()

            max_age = 10 * 365 * 24 * 60 * 60
            resp.set_cookie(settings.LANGUAGE_COOKIE_NAME, locale, max_age=max_age,
                            expires=(datetime.utcnow() + timedelta(seconds=max_age)).strftime(
                                '%a, %d-%b-%Y %H:%M:%S GMT'),
                            domain=settings.SESSION_COOKIE_DOMAIN)
        return resp
