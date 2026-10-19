from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notification
from Wassel.http_utils import safe_return_url

@login_required
def mark_notification_read(request, notification_id):

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )

    notification.is_read = True
    notification.save()

    return redirect(safe_return_url(request))


@login_required
def mark_all_notifications_read(request):

    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    return redirect(safe_return_url(request))

@login_required
def delete_notification(request, notification_id):

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )

    notification.delete()

    return redirect(safe_return_url(request))

@login_required
def delete_all_notifications(request):

    Notification.objects.filter(
        user=request.user
    ).delete()

    return redirect(safe_return_url(request))
