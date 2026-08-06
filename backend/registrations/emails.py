import io
import qrcode
import base64
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string


def _render_txt(template_name, context):
    return render_to_string(template_name, context)
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def _generate_qr_png(token: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=8, border=3)
    qr.add_data(str(token))
    qr.make(fit=True)
    img = qr.make_image(fill_color='#000000', back_color='#ffffff')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def send_confirmation_email(registration):
    qr_png = _generate_qr_png(registration.qr_token)
    qr_b64 = base64.b64encode(qr_png).decode()
    checkin_url = f'{settings.SITE_BASE_URL}/checkin.html?token={registration.qr_token}'

    context = {
        'name': registration.full_name,
        'email': registration.email,
        'university': registration.get_university_display(),
        'team_preference': registration.get_team_preference_display(),
        'checkin_url': checkin_url,
        'qr_b64': qr_b64,
    }

    subject = '🎉 Registration Confirmed — Legal Hackathon @ UNISG'
    text_body = _render_txt('emails/confirmation.txt', context)
    html_body = render_to_string('emails/confirmation.html', context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[registration.email],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=False)


def send_received_email(registration):
    context = {'name': registration.full_name}
    subject = 'Application Received — Legal Hackathon @ UNISG'
    text_body = _render_txt('emails/received.txt', context)
    html_body = render_to_string('emails/received.html', context)
    msg = EmailMultiAlternatives(subject=subject, body=text_body, from_email=settings.DEFAULT_FROM_EMAIL, to=[registration.email])
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=False)


def send_set_password_email(registration, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    portal_url = f'{settings.SITE_BASE_URL}/portal.html?uid={uid}&token={token}'
    context = {'name': registration.full_name, 'portal_url': portal_url}
    subject = 'Set Your Password — Legal Hackathon Portal'
    text_body = _render_txt('emails/set_password.txt', context)
    html_body = render_to_string('emails/set_password.html', context)
    msg = EmailMultiAlternatives(subject=subject, body=text_body, from_email=settings.DEFAULT_FROM_EMAIL, to=[registration.email])
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=False)


def send_waitlist_email(registration):
    context = {
        'name': registration.full_name,
        'email': registration.email,
        'university': registration.get_university_display(),
    }

    subject = 'You\'re on the Waitlist — Legal Hackathon @ UNISG'
    text_body = _render_txt('emails/waitlist.txt', context)
    html_body = render_to_string('emails/waitlist.html', context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[registration.email],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=False)
