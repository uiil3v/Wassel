from django.shortcuts import render
from django.db.models import Sum

from accounts.models import User
from driver.models import DriverProfile
from student.models import StudentProfile
from subscriptions.models import SubscriptionRequest
from payment.models import Transaction

from .decorators import admin_required

from subscriptions.models import SubscriptionRequest

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from subscriptions.models import SubscriptionRequest
from driver.models import DriverProfile

from .decorators import admin_required

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from subscriptions.models import SubscriptionRequest
from driver.models import DriverProfile

from .decorators import admin_required


@admin_required(levels=[1, 2])
def dashboard(request):

    # ===============================
    # Stats
    # ===============================
    users_count = User.objects.count()
    drivers_count = DriverProfile.objects.count()
    students_count = StudentProfile.objects.count()

    pending_requests = SubscriptionRequest.objects.filter(
        status="pending"
    ).count()

    # 💰 مجموع الأرباح (مو count!)
    total_earnings = Transaction.objects.filter(
        type="commission",
        status="completed"
    ).aggregate(total=Sum("amount"))["total"] or 0

    # ===============================
    # Latest Requests
    # ===============================
    latest_requests = SubscriptionRequest.objects.select_related(
        "student__user",
        "subscription__driver__user"
    ).order_by("-request_date")[:5]
    
    completed_requests = SubscriptionRequest.objects.filter(
        status="approved"
    ).count()

    # ===============================
    # Context
    # ===============================
    context = {
        "users_count": users_count,
        "drivers_count": drivers_count,
        "students_count": students_count,
        "pending_requests": pending_requests,
        "total_earnings": total_earnings,
        "latest_requests": latest_requests,
        "completed_requests": completed_requests,
    }

    return render(request, "admin_panel/dashboard.html", context)


@admin_required(levels=[1, 2])
def requests_list(request):

    requests = SubscriptionRequest.objects.select_related(
        "student__user",
        "subscription__driver__user"
    ).order_by("-request_date")

    return render(request, "admin_panel/requests.html", {
        "requests": requests
    })
    
    

@admin_required(levels=[1, 2])
def requests_list(request):

    # =========================
    # Filters
    # =========================
    request_status = request.GET.get("status")
    driver_status = request.GET.get("driver_status")

    requests = SubscriptionRequest.objects.select_related(
        "student__user",
        "subscription__driver__user"
    ).order_by("-request_date")

    drivers = DriverProfile.objects.select_related(
        "user"
    ).order_by("-submitted_at")

    if request_status:
        requests = requests.filter(status=request_status)

    if driver_status:
        drivers = drivers.filter(verification_status=driver_status)

    context = {
        "requests": requests,
        "drivers": drivers,
    }

    return render(request, "admin_panel/requests.html", context)


# =========================
# Actions - Requests
# =========================

@admin_required(levels=[1, 2])
def approve_request(request, pk):
    obj = get_object_or_404(SubscriptionRequest, id=pk)
    obj.approve()
    messages.success(request, "تم قبول الطلب ✅")
    return redirect("admin_panel:requests")


@admin_required(levels=[1, 2])
def reject_request(request, pk):
    obj = get_object_or_404(SubscriptionRequest, id=pk)
    obj.reject()
    messages.error(request, "تم رفض الطلب ❌")
    return redirect("admin_panel:requests")


# =========================
# Actions - Drivers
# =========================

@admin_required(levels=[1, 2])
def approve_driver(request, pk):
    driver = get_object_or_404(DriverProfile, id=pk)
    driver.approve()
    messages.success(request, "تم اعتماد السائق 🚗")
    return redirect("admin_panel:requests")


@admin_required(levels=[1, 2])
def reject_driver(request, pk):
    driver = get_object_or_404(DriverProfile, id=pk)

    if request.method == "POST":
        reason = request.POST.get("reason")
        driver.reject(reason)
        messages.error(request, "تم رفض السائق ❌")

    return redirect("admin_panel:driver_detail", pk=pk)




@admin_required(levels=[1, 2])
def request_detail(request, pk):

    req = get_object_or_404(
        SubscriptionRequest.objects.select_related(
            "student__user",
            "subscription__driver__user"
        ),
        id=pk
    )

    driver = req.subscription.driver

    context = {
        "req": req,
        "driver": driver,
        "student": req.student,
    }

    return render(request, "admin_panel/request_detail.html", context)


@admin_required(levels=[1, 2])
def driver_detail(request, pk):

    driver = get_object_or_404(DriverProfile, id=pk)

    return render(request, "admin_panel/driver_detail.html", {
        "driver": driver
    })
    
    
    