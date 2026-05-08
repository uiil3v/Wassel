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

from notifications.utils import send_notification

from django.db.models import Q
from notifications.models import Notification




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
    if request.user.admin_level == 1:
        total_earnings = Transaction.objects.filter(
            type="commission",
            status="completed"
        ).aggregate(total=Sum("amount"))["total"] or 0
    else:
        total_earnings = None

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

    # 🔔 Notification
    send_notification(
        title="تم قبول طلبك",
        message="تم قبول طلب الاشتراك بنجاح ✅",
        target="user",
        user=obj.student.user,
        notification_type="system"
    )

    messages.success(request, "تم قبول الطلب ✅")
    return redirect("admin_panel:requests")


@admin_required(levels=[1, 2])
def reject_request(request, pk):
    obj = get_object_or_404(SubscriptionRequest, id=pk)
    obj.reject()

    # 🔔 Notification
    send_notification(
        title="تم رفض طلبك",
        message="تم رفض طلب الاشتراك ❌",
        target="user",
        user=obj.student.user,
        notification_type="system"
    )

    messages.error(request, "تم رفض الطلب ❌")
    return redirect("admin_panel:requests")

# =========================
# Actions - Drivers
# =========================


@admin_required(levels=[1, 2])
def approve_driver(request, pk):
    driver = get_object_or_404(DriverProfile, id=pk)
    driver.approve()

    # 🔔 Notification
    send_notification(
        title="تم اعتماد حسابك كسائق",
        message="تم توثيق حسابك بنجاح 🚗 يمكنك الآن استقبال الطلبات",
        target="user",
        user=driver.user,
        notification_type="system"
    )

    messages.success(request, "تم اعتماد السائق 🚗")
    return redirect("admin_panel:requests")



@admin_required(levels=[1, 2])
def reject_driver(request, pk):
    driver = get_object_or_404(DriverProfile, id=pk)

    if request.method == "POST":
        reason = request.POST.get("reason")

        driver.reject(reason)

        # 🔔 Notification
        send_notification(
            title="تم رفض طلب التوثيق",
            message=f"تم رفض طلبك ❌ السبب: {reason}",
            target="user",
            user=driver.user,
            notification_type="system"
        )

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

    # ===== Weekly Schedule =====

    ORDER = [
        "sunday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
    ]

    schedule_qs = req.schedule.all()

    schedule_dict = {
        s.day_of_week: s
        for s in schedule_qs
    }

    sorted_schedule = [
        schedule_dict[day]
        for day in ORDER
        if day in schedule_dict
    ]

    context = {
        "req": req,
        "driver": driver,
        "student": req.student,
        "schedule": sorted_schedule,
    }

    return render(
        request,
        "admin_panel/request_detail.html",
        context
    )
    
    
    
    
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

@admin_required(levels=[1, 2])
def ban_user(request, pk):
    user = get_object_or_404(User, id=pk)

    # ❌ منع حظر الأدمن
    if user.role == "admin":
        messages.error(request, "لا يمكنك حظر مشرف.")
        return redirect("admin_panel:user_detail", pk=pk)

    user.status = "banned"
    user.save()

    messages.success(request, "تم حظر المستخدم 🚫")
    return redirect("admin_panel:user_detail", pk=pk)

@admin_required(levels=[1, 2])
def activate_user(request, pk):
    user = get_object_or_404(User, id=pk)

    if user.role == "admin":
        messages.error(request, "لا يمكنك تعديل مشرف.")
        return redirect("admin_panel:user_detail", pk=pk)

    user.status = "active"
    user.save()

    messages.success(request, "تم تفعيل المستخدم ✅")
    return redirect("admin_panel:user_detail", pk=pk)



@admin_required(levels=[1])
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


@admin_required(levels=[1, 2])
def send_notification_view(request):

    users = User.objects.all()

    if request.method == "POST":
        title = request.POST.get("title")
        message = request.POST.get("message")
        target = request.POST.get("target")
        user_id = request.POST.get("user")

        selected_user = None

        # 🔥 إذا Manager → يجبر يكون User فقط
        if request.user.admin_level == 2:
            target = "user"

        # 🔥 تحقق اختيار المستخدم
        if target == "user":
            if not user_id:
                messages.error(request, "يجب اختيار مستخدم.")
                return redirect("admin_panel:send_notification")

            selected_user = User.objects.get(id=user_id)

        send_notification(
            title=title,
            message=message,
            target=target,
            user=selected_user,
            notification_type="admin"
        )

        messages.success(request, "تم إرسال الإشعار بنجاح 🔔")

    return render(request, "admin_panel/send_notification.html", {
        "users": users
    })

@admin_required(levels=[1, 2])
def notifications_list(request):

    notifications = Notification.objects.select_related("user").order_by("-created_at")

    # ======================
    # Search
    # ======================
    search = request.GET.get("search", "")
    if search:
        notifications = notifications.filter(
            Q(title__icontains=search) |
            Q(message__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )

    # ======================
    # Filter: Target (Role-based)
    # ======================
    target = request.GET.get("target", "all")

    if target == "student":
        notifications = notifications.filter(user__role="student")

    elif target == "driver":
        notifications = notifications.filter(user__role="driver")

    elif target == "admin":
        notifications = notifications.filter(user__role="admin")

    elif target == "user":
        notifications = notifications.filter(target="user")

    # ======================
    # Filter: Type
    # ======================
    n_type = request.GET.get("type", "all")
    if n_type != "all":
        notifications = notifications.filter(notification_type=n_type)

    # ======================
    # Context
    # ======================
    context = {
        "notifications": notifications,
        "search": search,
        "target": target,
        "type": n_type,
    }

    return render(request, "admin_panel/notifications.html", context)


from django.db.models import Q
from subscriptions.models import Subscription

@admin_required(levels=[1, 2])
def subscriptions_list(request):

    # ================= GET PARAMETERS =================
    search_query = request.GET.get("search", "").strip()
    duration = request.GET.get("duration", "")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    sort = request.GET.get("sort", "")

    # ================= BASE QUERY =================
    subscriptions = Subscription.objects.select_related(
        "driver__user"
    )

    # 🔥 هنا الفرق عن الطالب:
    # ❌ ما نحط:
    # status="active"
    # available_seats__gt=0
    # driver__user__city=request.user.city

    # ================= SEARCH =================
    if search_query:
        subscriptions = subscriptions.filter(
            Q(neighborhood__icontains=search_query) |
            Q(driver__user__first_name__icontains=search_query) |
            Q(driver__user__last_name__icontains=search_query)
        )

    # ================= DURATION FILTER =================
    if duration:
        subscriptions = subscriptions.filter(duration=duration)

    # ================= PRICE FILTER =================
    if min_price:
        try:
            subscriptions = subscriptions.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            subscriptions = subscriptions.filter(price__lte=float(max_price))
        except ValueError:
            pass

    # ================= SORTING =================
    if sort == "price_asc":
        subscriptions = subscriptions.order_by("price")
    elif sort == "price_desc":
        subscriptions = subscriptions.order_by("-price")
    elif sort == "seats":
        subscriptions = subscriptions.order_by("-available_seats")
    else:
        subscriptions = subscriptions.order_by("-created_at")

    # ================= RESULTS COUNT =================
    results_count = subscriptions.count()

    # ================= CONTEXT =================
    context = {
        "subscriptions": subscriptions,
        "search_query": search_query,
        "duration": duration,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort,
        "results_count": results_count,
    }

    return render(request, "admin_panel/subscriptions.html", context)



from subscriptions.models import Subscription

@admin_required(levels=[1, 2])
def subscription_detail(request, pk):

    subscription = get_object_or_404(Subscription, id=pk)

    pending_requests = subscription.requests.filter(
        status="pending"
    ).select_related("student__user")

    approved_requests = subscription.requests.filter(
        status="approved"
    ).select_related("student__user")

    context = {
        "subscription": subscription,
        "pending_requests": pending_requests,
        "approved_requests": approved_requests,
    }

    return render(request, "admin_panel/subscription_detail.html", context)
    
    
@admin_required(levels=[1, 2])
def deactivate_subscription(request, pk):

    subscription = get_object_or_404(Subscription, id=pk)

    # 🔥 تأكد إنه active
    if subscription.status != "active":
        messages.warning(request, "الاشتراك موقوف بالفعل.")
        return redirect("admin_panel:subscription_detail", pk=pk)

    subscription.deactivate()

    messages.success(request, "تم إيقاف الاشتراك بنجاح 🚫")

    return redirect("admin_panel:subscription_detail", pk=pk)


@admin_required(levels=[1, 2])
def activate_subscription(request, pk):

    subscription = get_object_or_404(Subscription, id=pk)

    if subscription.status == "active":
        messages.warning(request, "الاشتراك مفعل بالفعل.")
        return redirect("admin_panel:subscription_detail", pk=pk)

    # 🔥 نرجعه active
    subscription.status = "active"
    subscription.save()

    messages.success(request, "تم إعادة تفعيل الاشتراك ✅")

    return redirect("admin_panel:subscription_detail", pk=pk)

@admin_required(levels=[1, 2])
def subscription_request_detail(request, pk):

    req = get_object_or_404(
        SubscriptionRequest.objects.select_related(
            "student__user",
            "subscription__driver__user"
        ),
        id=pk
    )

    # ===== ترتيب الأيام =====

    ORDER = [
        "sunday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
    ]

    schedule_qs = req.schedule.all()

    schedule_dict = {
        s.day_of_week: s
        for s in schedule_qs
    }

    sorted_schedule = [
        schedule_dict[day]
        for day in ORDER
        if day in schedule_dict
    ]

    return render(
        request,
        "admin_panel/subscription_request_detail.html",
        {
            "req": req,
            "schedule": sorted_schedule
        }
    )
    
    
    