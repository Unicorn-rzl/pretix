from urllib.parse import urlparse
from django.conf import settings
from django.core.urlresolvers import resolve, get_script_prefix
from django.utils.encoding import force_str
from django.shortcuts import resolve_url
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseNotFound
from django.utils.translation import ugettext as _

from pretix.base.models import Event, Organizer, EventPermission


class PermissionMiddleware:

    """
    This middleware enforces all requests to the control app to require login.
    Additionally, it enforces all requests to "control:event." URLs
    to be for an event the user has basic access to.
    """

    EXCEPTIONS = (
        "auth.login",
        "auth.register"
    )

    def process_request(self, request):
        url = resolve(request.path_info)
        url_name = url.url_name
        if not request.path.startswith(get_script_prefix() + 'control') or url_name in self.EXCEPTIONS:
            return
        if not request.user.is_authenticated():
            # Taken from django/contrib/auth/decorators.py
            path = request.build_absolute_uri()
            # urlparse chokes on lazy objects in Python 3, force to str
            resolved_login_url = force_str(
                resolve_url(settings.LOGIN_URL_CONTROL))
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if ((not login_scheme or login_scheme == current_scheme) and
                    (not login_netloc or login_netloc == current_netloc)):
                path = request.get_full_path()
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(
                path, resolved_login_url, REDIRECT_FIELD_NAME)

        request.user.events_cache = request.user.events.current.order_by(
            "organizer", "date_from").prefetch_related("organizer")
        if 'event' in url.kwargs and 'organizer' in url.kwargs:
            try:
                request.event = Event.objects.current.filter(
                    slug=url.kwargs['event'],
                    permitted__id__exact=request.user.id,
                    organizer__slug=url.kwargs['organizer'],
                ).select_related('organizer')[0]
                request.eventperm = EventPermission.objects.current.get(
                    event=request.event,
                    user=request.user
                )
                request.organizer = request.event.organizer
            except IndexError:
                return HttpResponseNotFound(_("The selected event was not found or you "
                                              "have no permission to administrate it."))
        elif 'organizer' in url.kwargs:
            try:
                request.organizer = Organizer.objects.current.filter(
                    slug=url.kwargs['organizer'],
                    permitted__id__exact=request.user.id,
                )[0]
            except IndexError:
                return HttpResponseNotFound(_("The selected organizer was not found or you "
                                              "have no permission to administrate it."))
