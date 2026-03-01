from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from subscriptions.models import SubscriptionRequest
from subscriptions.models import (
    Subscription,
    SubscriptionRequest,
    SubscriptionRequestSchedule
)
from django.db import transaction
from django.utils import timezone


@login_required
def student_dashboard(request):

    if request.user.role != "student":
        return redirect("main:index")

    profile = getattr(request.user, "student_profile", None)

    if not profile:
        return redirect("students:profile")

    active_request = SubscriptionRequest.objects.filter(
        student=profile,
        status__in=["pending", "approved"]
    ).select_related("subscription__driver__user").first()

    available_subscriptions = None

    if not active_request:
        available_subscriptions = Subscription.objects.filter(
            status="active"
        ).select_related("driver__user")[:6]

    context = {
        "active_request": active_request,
        "available_subscriptions": available_subscriptions,
    }

    return render(request, "student/dashboard.html", context)



@login_required
def student_subscription_detail(request, req_id):

    if request.user.role != "student":
        return redirect("main:index")

    profile = request.user.student_profile

    req = get_object_or_404(
        SubscriptionRequest.objects.select_related(
            "subscription__driver__user"
        ).prefetch_related("schedule"),
        id=req_id,
        student=profile,
        status="approved"
    )

    context = {
        "req": req,
        "schedule": req.schedule.all()
    }

    return render(request, "student/subscription_detail.html", context)



@login_required
def available_subscriptions(request):

    if request.user.role != "student":
        return redirect("main:index")

    profile = request.user.student_profile

    # منع عرض الاشتراكات إذا عنده طلب نشط
    active_request_exists = profile.subscription_requests.filter(
        status__in=["pending", "approved"]
    ).exists()

    subscriptions = Subscription.objects.filter(
        status="active",
        available_seats__gt=0
    ).select_related("driver__user").order_by("-created_at")

    context = {
        "subscriptions": subscriptions,
        "has_active_request": active_request_exists,
    }

    return render(request, "student/subscriptions.html", context)



@login_required
def subscription_detail_view(request, sub_id):

    if request.user.role != "student":
        return redirect("main:index")

    profile = request.user.student_profile

    subscription = get_object_or_404(
        Subscription.objects.select_related("driver__user"),
        id=sub_id,
        status="active"
    )

    has_active_request = profile.subscription_requests.filter(
        status__in=["pending", "approved"]
    ).exists()

    context = {
        "subscription": subscription,
        "has_active_request": has_active_request,
    }

    return render(request, "student/subscription_detail_view.html", context)


@login_required
def create_request(request, sub_id):

    if request.user.role != "student":
        return redirect("main:index")

    profile = request.user.student_profile

    subscription = get_object_or_404(
        Subscription,
        id=sub_id,
        status="active"
    )

    if profile.subscription_requests.filter(
        status__in=["pending", "approved"]
    ).exists():
        return redirect("student:dashboard")

    days = [
        ("saturday", "السبت"),
        ("sunday", "الأحد"),
        ("monday", "الاثنين"),
        ("tuesday", "الثلاثاء"),
        ("wednesday", "الأربعاء"),
        ("thursday", "الخميس"),
        ("friday", "الجمعة"),
    ]

    if request.method == "POST":

        with transaction.atomic():

            req = SubscriptionRequest.objects.create(
                student=profile,
                subscription=subscription,
                status="pending",
                price_snapshot=subscription.price
            )

            for day_code, _ in days:

                is_off = request.POST.get(f"{day_code}_off") == "on"
                pickup = request.POST.get(f"{day_code}_pickup")
                ret = request.POST.get(f"{day_code}_return")

                schedule = SubscriptionRequestSchedule.objects.create(
                    request=req,
                    day_of_week=day_code,
                    is_off_day=is_off
                )

                if not is_off and pickup and ret:
                    schedule.pickup_time = pickup
                    schedule.return_time = ret
                    schedule.save()

        return redirect("student:dashboard")

    context = {
        "subscription": subscription,
        "days": days
    }

    return render(request, "student/create_request.html", context)




@login_required
def cancel_request(request, req_id):

    if request.user.role != "student":
        return redirect("main:index")

    profile = request.user.student_profile

    req = get_object_or_404(
        SubscriptionRequest,
        id=req_id,
        student=profile
    )

    if request.method == "POST":
        if req.status == "pending":
            req.status = "cancelled"
            req.save()
        elif req.status == "approved":
            req.cancel()

    return redirect("student:dashboard")
