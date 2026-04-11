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

from django.shortcuts import render
from accounts.models import User
from django.db.models import Q
from .decorators import admin_required

from django.shortcuts import render, get_object_or_404
from accounts.models import User
from .decorators import admin_required


from payment.models import Transaction
from django.db.models import Sum
from .decorators import admin_required

from payment.models import Transaction
from django.db.models import Sum, Q
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
    
    
@admin_required(levels=[1, 2])
def users_list(request):

    users = User.objects.all().order_by("-date_joined")

    # ======================
    # Search
    # ======================
    search = request.GET.get("search")

    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )

    # ======================
    # Filter by Role
    # ======================
    role = request.GET.get("role")

    if role and role != "all":
        users = users.filter(role=role)

    # ======================
    # Filter by Status
    # ======================
    status = request.GET.get("status")

    if status and status != "all":
        users = users.filter(status=status)

    context = {
        "users": users,
        "search": search,
        "role": role,
        "status": status,
    }

    return render(request, "admin_panel/users.html", context)


@admin_required(levels=[1, 2])
def user_detail(request, pk):

    user = get_object_or_404(User, id=pk)

    student = None
    driver = None

    # ======================
    # Detect Role
    # ======================
    if user.role == "student":
        student = getattr(user, "student_profile", None)

    elif user.role == "driver":
        driver = getattr(user, "driver_profile", None)

    context = {
        "user_obj": user,
        "student": student,
        "driver": driver,
    }

    return render(request, "admin_panel/user_detail.html", context)

@admin_required(levels=[1])
def ban_user(request, pk):
    user = get_object_or_404(User, id=pk)
    user.status = "banned"
    user.save()
    return redirect("admin_panel:user_detail", pk=pk)

@admin_required(levels=[1])
def activate_user(request, pk):
    user = get_object_or_404(User, id=pk)
    user.status = "active"
    user.save()
    return redirect("admin_panel:user_detail", pk=pk)



@admin_required(levels=[1, 2])
def payments_view(request):

    transactions = Transaction.objects.select_related("wallet__user").order_by("-created_at")

    # ======================
    # Filters
    # ======================

    search = request.GET.get("search")
    type_filter = request.GET.get("type")
    status_filter = request.GET.get("status")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    # 🔍 Search
    if search:
        transactions = transactions.filter(
            Q(wallet__user__first_name__icontains=search) |
            Q(wallet__user__last_name__icontains=search) |
            Q(wallet__user__email__icontains=search)
        )

    # 🎛️ Type
    if type_filter and type_filter != "all":
        transactions = transactions.filter(type=type_filter)

    # 🎛️ Status
    if status_filter and status_filter != "all":
        transactions = transactions.filter(status=status_filter)

    # 📅 Date From
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)

    # 📅 Date To
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)

    # ======================
    # Stats (نفسها)
    # ======================

    total_transactions = transactions.count()

    total_earnings = transactions.filter(
        type="commission",
        status="completed"
    ).aggregate(total=Sum("amount"))["total"] or 0

    total_withdrawals = transactions.filter(
        type="withdraw",
        status="completed"
    ).aggregate(total=Sum("amount"))["total"] or 0

    context = {
        "transactions": transactions,
        "total_transactions": total_transactions,
        "total_earnings": total_earnings,
        "total_withdrawals": total_withdrawals,

        # مهم عشان نحافظ على القيم في الفورم
        "search": search,
        "type": type_filter,
        "status": status_filter,
        "date_from": date_from,
        "date_to": date_to,
    }

    return render(request, "admin_panel/payments.html", context)
