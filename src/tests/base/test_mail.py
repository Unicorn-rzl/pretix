from django.conf import settings
from django.utils.timezone import now
from django.core import mail as djmail
from django.utils.translation import ugettext_lazy as _
import pytest

from pretix.base.models import Event, Organizer, User
from pretix.base.services.mail import mail


@pytest.fixture
def env():
    o = Organizer.objects.create(name='Dummy', slug='dummy')
    event = Event.objects.create(
        organizer=o, name='Dummy', slug='dummy',
        date_from=now(), plugins='pretix.plugins.banktransfer'
    )
    user = User.objects.create_user('dummy@dummy.dummy', 'dummy@dummy.dummy', 'dummy')
    user.email = 'dummy@dummy.dummy'
    user.save()
    return event, user, o


@pytest.mark.django_db
def test_send_mail_with_prefix(client, env):
    djmail.outbox = []
    event, user, organizer = env
    event.settings.set('mail_prefix', 'test')
    mail(user, 'Test subject',
         'mailtest.txt', {}, event)

    assert len(djmail.outbox) == 1
    assert djmail.outbox[0].to == [user.email]
    assert djmail.outbox[0].subject == '[test] Test subject'


@pytest.mark.django_db
def test_send_mail_with_event_sender(client, env):
    djmail.outbox = []
    event, user, organizer = env
    event.settings.set('mail_from', 'foo@bar')
    mail(user, 'Test subject',
         'mailtest.txt', {}, event)

    assert len(djmail.outbox) == 1
    assert djmail.outbox[0].to == [user.email]
    assert djmail.outbox[0].subject == 'Test subject'
    assert djmail.outbox[0].from_email == 'foo@bar'


@pytest.mark.django_db
def test_send_mail_with_default_sender(client, env):
    djmail.outbox = []
    event, user, organizer = env
    mail(user, 'Test subject',
         'mailtest.txt', {}, event)
    del event.settings['mail_from']

    assert len(djmail.outbox) == 1
    assert djmail.outbox[0].to == [user.email]
    assert djmail.outbox[0].subject == 'Test subject'
    assert djmail.outbox[0].from_email == settings.MAIL_FROM


@pytest.mark.django_db
def test_send_mail_with_user_locale(client, env):
    djmail.outbox = []
    event, user, organizer = env
    user.locale = 'de'
    user.save()
    mail(user, _('User'),
         'mailtest.txt', {}, event)
    del event.settings['mail_from']

    assert len(djmail.outbox) == 1
    assert djmail.outbox[0].subject == 'Benutzer'
    assert 'The language code used for rendering this e-mail is de.' in djmail.outbox[0].body
