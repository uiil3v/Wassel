from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from accounts.models import User
from driver.models import DriverProfile
from student.models import StudentProfile
from subscriptions.models import Subscription, SubscriptionRequest
from payment.models import Transaction
from .decorators import admin_required
from django.contrib import messages
from django.db.models import Q
from notifications.utils import send_notification
from notifications.models import Notification

import csv
from django.http import HttpResponse


from Wassel.email_utils import (
    send_driver_approved_email,
    send_driver_rejected_email,
    send_user_banned_email,
    send_user_activated_email,
    send_subscription_deactivated_email,
    send_subscription_activated_email,
    send_admin_notification_email,
)






from support.forms import SupportMessageForm

from support.models import (
    SupportTicket,
    SupportMessage,
)


@admin_required(levels=[1, 2])
def dashboard(request):
    today = timezone.now().date()

    users_count = User.objects.count()
    drivers_count = DriverProfile.objects.count()
    students_count = StudentProfile.objects.count()

    pending_requests_qs = SubscriptionRequest.objects.select_related(
        "student__user",
        "subscription__driver__user",
        "subscription__driver__user__city",
    ).filter(status="pending")

    pending_requests = pending_requests_qs.count()
    completed_requests = SubscriptionRequest.objects.filter(
        status="approved"
    ).count()

    pending_drivers_qs = DriverProfile.objects.select_related(
        "user",
        "user__city",
    ).filter(verification_status="pending")

    open_tickets_qs = SupportTicket.objects.select_related(
        "user",
        "handled_by",
    ).filter(status__in=["in_progress", "waiting_user"])

    active_subscriptions = Subscription.objects.filter(
        status="active",
        end_date__gte=today,
    ).count()

    full_subscriptions = Subscription.objects.filter(
        status="full",
        end_date__gte=today,
    ).count()

    inactive_subscriptions = Subscription.objects.filter(
        status__in=["inactive_by_admin", "inactive_by_driver"]
    ).count()

    expired_subscriptions = Subscription.objects.filter(
        end_date__lt=today
    ).count()

    if request.user.admin_level == 1:
        total_earnings = Transaction.objects.filter(
            type="commission",
            status="completed"
        ).aggregate(total=Sum("amount"))["total"] or 0
    else:
        total_earnings = None

    latest_requests = SubscriptionRequest.objects.select_related(
        "student__user",
        "subscription__driver__user",
        "subscription__driver__user__city",
    ).order_by("-request_date")[:6]

    context = {
        "users_count": users_count,
        "drivers_count": drivers_count,
        "students_count": students_count,
        "pending_requests": pending_requests,
        "completed_requests": completed_requests,
        "pending_drivers_count": pending_drivers_qs.count(),
        "pending_drivers": pending_drivers_qs.order_by("-submitted_at")[:4],
        "open_tickets_count": open_tickets_qs.count(),
        "waiting_user_tickets_count": SupportTicket.objects.filter(status="waiting_user").count(),
        "unassigned_tickets_count": open_tickets_qs.filter(handled_by__isnull=True).count(),
        "open_tickets": open_tickets_qs.order_by("-updated_at")[:4],
        "active_subscriptions": active_subscriptions,
        "full_subscriptions": full_subscriptions,
        "inactive_subscriptions": inactive_subscriptions,
        "expired_subscriptions": expired_subscriptions,
        "total_earnings": total_earnings,
        "latest_requests": latest_requests,
        "pending_request_items": pending_requests_qs.order_by("-request_date")[:4],
    }

    return render(request, "admin_panel/dashboard.html", context)





@admin_required(levels=[1, 2])
def requests_list(request):


    # Filters
    active_tab = request.GET.get("tab", "subscriptions")
    if active_tab not in ["subscriptions", "drivers"]:
        active_tab = "subscriptions"

    request_search = request.GET.get("request_search", "").strip()
    driver_search = request.GET.get("driver_search", "").strip()
    request_status = request.GET.get("request_status", request.GET.get("status", ""))
    driver_status = request.GET.get("driver_status", "")
    request_date_from = request.GET.get("request_date_from", "")
    request_date_to = request.GET.get("request_date_to", "")
    driver_date_from = request.GET.get("driver_date_from", "")
    driver_date_to = request.GET.get("driver_date_to", "")

    base_requests = SubscriptionRequest.objects.select_related(
        "student__user",
        "subscription__driver__user",
        "subscription__driver__user__city",
    ).order_by("-request_date")

    base_drivers = DriverProfile.objects.select_related(
        "user",
        "user__city",
    ).order_by("-submitted_at")

    requests = base_requests
    drivers = base_drivers

    if request_search:
        requests = requests.filter(
            Q(request_code__icontains=request_search) |
            Q(student__user__first_name__icontains=request_search) |
            Q(student__user__last_name__icontains=request_search) |
            Q(student__user__email__icontains=request_search) |
            Q(subscription__driver__user__first_name__icontains=request_search) |
            Q(subscription__driver__user__last_name__icontains=request_search) |
            Q(subscription__neighborhood__icontains=request_search)
        )

    if request_status:
        requests = requests.filter(status=request_status)

    if request_date_from:
        requests = requests.filter(request_date__date__gte=request_date_from)

    if request_date_to:
        requests = requests.filter(request_date__date__lte=request_date_to)

    if driver_search:
        drivers = drivers.filter(
            Q(user__first_name__icontains=driver_search) |
            Q(user__last_name__icontains=driver_search) |
            Q(user__email__icontains=driver_search) |
            Q(user__phone__icontains=driver_search) |
            Q(vehicle_model__icontains=driver_search)
        )

    if driver_status:
        drivers = drivers.filter(verification_status=driver_status)

    if driver_date_from:
        drivers = drivers.filter(submitted_at__date__gte=driver_date_from)

    if driver_date_to:
        drivers = drivers.filter(submitted_at__date__lte=driver_date_to)

    context = {
        "requests": requests,
        "drivers": drivers,
        "active_tab": active_tab,
        "request_search": request_search,
        "driver_search": driver_search,
        "request_status": request_status,
        "driver_status": driver_status,
        "request_date_from": request_date_from,
        "request_date_to": request_date_to,
        "driver_date_from": driver_date_from,
        "driver_date_to": driver_date_to,
        "requests_count": requests.count(),
        "drivers_count": drivers.count(),
        "pending_requests_count": base_requests.filter(status="pending").count(),
        "approved_requests_count": base_requests.filter(status="approved").count(),
        "rejected_requests_count": base_requests.filter(status="rejected").count(),
        "cancelled_requests_count": base_requests.filter(status="cancelled").count(),
        "pending_drivers_count": base_drivers.filter(verification_status="pending").count(),
        "approved_drivers_count": base_drivers.filter(verification_status="approved").count(),
        "rejected_drivers_count": base_drivers.filter(verification_status="rejected").count(),
        "incomplete_drivers_count": base_drivers.filter(verification_status="incomplete").count(),
    }

    return render(request, "admin_panel/requests.html", context)






@admin_required(levels=[1, 2])
def approve_driver(request, pk):
    driver = get_object_or_404(DriverProfile, id=pk)
    driver.approve()

    # Notification
    send_notification(
        title="تم اعتماد حسابك كسائق",
        message="تم توثيق حسابك بنجاح 🚗 يمكنك الآن استقبال الطلبات",
        target="user",
        user=driver.user,
        notification_type="system"
    )
    
    send_driver_approved_email(
        driver.user,
        request
    )

    messages.success(request, "تم اعتماد السائق 🚗")
    return redirect("admin_panel:requests")



@admin_required(levels=[1, 2])
def reject_driver(request, pk):
    driver = get_object_or_404(DriverProfile, id=pk)

    if request.method == "POST":
        reason = request.POST.get("reason")

        driver.reject(reason)

        # Notification
        send_notification(
            title="تم رفض طلب التوثيق",
            message=f"تم رفض طلبك ❌ السبب: {reason}",
            target="user",
            user=driver.user,
            notification_type="system"
        )
        
        send_driver_rejected_email(
            driver.user,
            reason
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

    base_users = User.objects.all()
    users = base_users.order_by("-date_joined")

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
        "results_count": users.count(),
        "total_users": base_users.count(),
        "students_count": base_users.filter(role="student").count(),
        "drivers_count": base_users.filter(role="driver").count(),
        "admins_count": base_users.filter(role="admin").count(),
        "banned_users_count": base_users.filter(status="banned").count(),
    }

    return render(request, "admin_panel/users.html", context)


@admin_required(levels=[1, 2])
def user_detail(request, pk):

    user = get_object_or_404(User, id=pk)

    student = None
    driver = None
    profile_stats = {}

    # ======================
    # Detect Role
    # ======================
    if user.role == "student":
        student = getattr(user, "student_profile", None)
        if student:
            profile_stats = {
                "total_requests": student.subscription_requests.count(),
                "pending_requests": student.subscription_requests.filter(status="pending").count(),
                "approved_requests": student.subscription_requests.filter(status="approved").count(),
                "rejected_requests": student.subscription_requests.filter(status="rejected").count(),
                "cancelled_requests": student.subscription_requests.filter(status="cancelled").count(),
            }

    elif user.role == "driver":
        driver = getattr(user, "driver_profile", None)
        if driver:
            driver_subscriptions = list(driver.subscriptions.all())
            profile_stats = {
                "total_subscriptions": len(driver_subscriptions),
                "active_subscriptions": sum(
                    1 for sub in driver_subscriptions
                    if sub.current_status == "active"
                ),
                "admin_stopped_subscriptions": driver.subscriptions.filter(status="inactive_by_admin").count(),
                "received_requests": SubscriptionRequest.objects.filter(subscription__driver=driver).count(),
                "pending_requests": SubscriptionRequest.objects.filter(
                    subscription__driver=driver,
                    status="pending"
                ).count(),
            }

    context = {
        "user_obj": user,
        "student": student,
        "driver": driver,
        "profile_stats": profile_stats,
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
    
    send_notification(
        title="تم تقييد حسابك",
        message="تم إيقاف حسابك مؤقتاً من قبل إدارة المنصة. يرجى التواصل مع الدعم الفني للمزيد من المعلومات.",
        target="user",
        user=user,
        notification_type="system"
    )

    send_user_banned_email(user)

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
    
    send_notification(
        title="تم إعادة تفعيل حسابك",
        message="تمت إعادة تفعيل حسابك ويمكنك الآن استخدام المنصة بشكل طبيعي.",
        target="user",
        user=user,
        notification_type="system"
    )

    send_user_activated_email(user)

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

    paid_subscriptions_count = Transaction.objects.filter(
        type="commission",
        status="completed"
    ).count()

    context = {
        "transactions": transactions,
        "total_transactions": total_transactions,
        "total_earnings": total_earnings,
        "paid_subscriptions_count": paid_subscriptions_count,

        # مهم عشان نحافظ على القيم في الفورم
        "search": search,
        "type": type_filter,
        "status": status_filter,
        "date_from": date_from,
        "date_to": date_to,
    }

    return render(request, "admin_panel/payments.html", context)



@admin_required(levels=[1])
def export_payments_csv(request):

    transactions = Transaction.objects.select_related(
        "wallet__user"
    ).order_by("-created_at")

    # ======================
    # نفس الفلاتر الحالية
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
        transactions = transactions.filter(
            created_at__date__gte=date_from
        )

    # 📅 Date To
    if date_to:
        transactions = transactions.filter(
            created_at__date__lte=date_to
        )

    # ======================
    # CSV Response
    # ======================

    response = HttpResponse(
    content_type="text/csv; charset=utf-8"
    )

    response.write('\ufeff')

    response[
        "Content-Disposition"
    ] = 'attachment; filename="payments.csv"'

    writer = csv.writer(response)

    # Header
    writer.writerow([
        "User",
        "Email",
        "Type",
        "Amount",
        "Status",
        "Date",
    ])

    # Rows
    for tx in transactions:

        writer.writerow([
            tx.wallet.user.full_name,
            tx.wallet.user.email,
            tx.get_type_display(),
            f"{tx.amount:.2f}",
            tx.get_status_display(),
            tx.created_at.strftime("%d/%m/%Y %H:%M"),
        ])

    return response




@admin_required(levels=[1, 2])
def send_notification_view(request):

    users = User.objects.all()

    if request.method == "POST":
        title = request.POST.get("title")
        message = request.POST.get("message")
        target = request.POST.get("target")
        user_id = request.POST.get("user")

        selected_user = None
        
        send_email = request.POST.get(
            "send_email"
        )

        # 🔥 إذا Manager → يجبر يكون User فقط
        if request.user.admin_level == 2:
            target = "user"

        # 🔥 تحقق اختيار المستخدم
        if target == "user":
            if not user_id:
                messages.error(request, "يجب اختيار مستخدم.")
                return redirect("admin_panel:send_notification")

            selected_user = get_object_or_404(
                User,
                id=user_id
            )

        send_notification(
            title=title,
            message=message,
            target=target,
            user=selected_user,
            notification_type="admin",
            sent_by=request.user
        )
        
        if send_email:
            

            if target == "user":

                send_admin_notification_email(
                    selected_user,
                    title,
                    message
                )

            elif target == "student":

                for user in User.objects.filter(
                    role="student"
                ):

                    send_admin_notification_email(
                        user,
                        title,
                        message
                    )

            elif target == "driver":

                for user in User.objects.filter(
                    role="driver"
                ):

                    send_admin_notification_email(
                        user,
                        title,
                        message
                    )

            elif target == "admin":

                for user in User.objects.filter(
                    role="admin"
                ):

                    send_admin_notification_email(
                        user,
                        title,
                        message
                    )

            elif target == "all":

                for user in User.objects.all():

                    send_admin_notification_email(
                        user,
                        title,
                        message
                    )

        messages.success(request, "تم إرسال الإشعار بنجاح 🔔")
        
        return redirect(
            "admin_panel:send_notification"
        )

    return render(request, "admin_panel/send_notification.html", {
        "users": users
    })





@admin_required(levels=[1, 2])
def notifications_list(request):

    notifications = Notification.objects.select_related("user", "sent_by").order_by("-created_at")

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

@admin_required(levels=[1, 2])
def subscriptions_list(request):

    # ================= GET PARAMETERS =================
    search_query = request.GET.get("search", "").strip()
    duration = request.GET.get("duration", "")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    sort = request.GET.get("sort", "")
    status_filter = request.GET.get("status", "")

    # ================= BASE QUERY =================
    base_subscriptions = Subscription.objects.select_related(
        "driver__user",
        "driver__user__city",
    )
    subscriptions = base_subscriptions

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
        
    # ================= STATUS FILTER =================
    if status_filter:

        filtered_subscription_ids = []

        for sub in subscriptions:

            if status_filter == "inactive":
                if sub.current_status in ["inactive_by_admin", "inactive_by_driver"]:
                    filtered_subscription_ids.append(sub.id)
            elif sub.current_status == status_filter:
                filtered_subscription_ids.append(sub.id)

        subscriptions = Subscription.objects.filter(
            id__in=filtered_subscription_ids
        ).select_related(
            "driver__user",
            "driver__user__city",
        )

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
    base_subscriptions_list = list(base_subscriptions)
    active_count = sum(1 for sub in base_subscriptions_list if sub.current_status == "active")
    expired_count = sum(1 for sub in base_subscriptions_list if sub.current_status == "expired")
    full_count = sum(1 for sub in base_subscriptions_list if sub.current_status == "full")
    inactive_count = sum(
        1 for sub in base_subscriptions_list
        if sub.current_status in ["inactive_by_admin", "inactive_by_driver"]
    )

    # ================= CONTEXT =================
    context = {
        "subscriptions": subscriptions,
        "search_query": search_query,
        "duration": duration,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort,
        "results_count": results_count,
        "status_filter": status_filter,
        "total_subscriptions": len(base_subscriptions_list),
        "active_count": active_count,
        "expired_count": expired_count,
        "full_count": full_count,
        "inactive_count": inactive_count,
    }

    return render(request, "admin_panel/subscriptions.html", context)
@admin_required(levels=[1, 2])
def subscription_detail(request, pk):

    subscription = get_object_or_404(Subscription, id=pk)

    pending_requests = subscription.requests.filter(
        status="pending"
    ).select_related("student__user")

    approved_requests = subscription.requests.filter(
        status="approved"
    ).select_related("student__user")

    rejected_requests_count = subscription.requests.filter(
        status="rejected"
    ).count()

    cancelled_requests_count = subscription.requests.filter(
        status="cancelled"
    ).count()

    context = {
        "subscription": subscription,
        "pending_requests": pending_requests,
        "approved_requests": approved_requests,
        "rejected_requests_count": rejected_requests_count,
        "cancelled_requests_count": cancelled_requests_count,
    }

    return render(request, "admin_panel/subscription_detail.html", context)
    
    
@admin_required(levels=[1, 2])
def deactivate_subscription(request, pk):

    subscription = get_object_or_404(Subscription, id=pk)

    # إذا موقوف إداريًا بالفعل
    if subscription.status == "inactive_by_admin":

        messages.warning(
            request,
            "الاشتراك موقوف بالفعل من الإدارة."
        )

        return redirect(
            "admin_panel:subscription_detail",
            pk=pk
        )

    subscription.deactivate_by_admin()
    
    send_notification(
        title="تم إيقاف أحد اشتراكاتك",
        message="تم إيقاف الاشتراك من قبل إدارة المنصة. يرجى التواصل مع الدعم الفني للمزيد من المعلومات.",
        target="user",
        user=subscription.driver.user,
        notification_type="system"
    )

    send_subscription_deactivated_email(
        subscription
    )

    messages.success(
        request,
        "تم إيقاف الاشتراك من قبل الإدارة 🚫"
    )

    return redirect("admin_panel:subscription_detail", pk=pk)


@admin_required(levels=[1, 2])
def activate_subscription(request, pk):

    subscription = get_object_or_404(Subscription, id=pk)

    if subscription.current_status == "active":
        messages.warning(request, "الاشتراك مفعل بالفعل.")
        return redirect("admin_panel:subscription_detail", pk=pk)
    
    if subscription.status == "inactive_by_driver":

        messages.error(
            request,
            "هذا الاشتراك موقوف بواسطة السائق."
        )

        return redirect(
            "admin_panel:subscription_detail",
            pk=pk
        )

    subscription.activate()
    
    send_notification(
        title="تمت إعادة تفعيل الاشتراك",
        message="تمت إعادة تفعيل الاشتراك ويمكنك الآن استقبال الطلبات بشكل طبيعي.",
        target="user",
        user=subscription.driver.user,
        notification_type="system"
    )

    send_subscription_activated_email(
        subscription
    )

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
    
    
    
    
@admin_required(levels=[1, 2])
def support_tickets(request):

    tickets = SupportTicket.objects.select_related(
        "user",
        "handled_by"
    ).order_by("-created_at")

    # ======================
    # Search
    # ======================

    search = request.GET.get("search", "").strip()

    if search:

        tickets = tickets.filter(

            Q(ticket_number__icontains=search) |
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(subject__icontains=search) |
            Q(message__icontains=search)

        )

    # ======================
    # Category Filter
    # ======================

    category = request.GET.get("category", "")

    if category:

        tickets = tickets.filter(
            category=category
        )

    # ======================
    # Status Filter
    # ======================

    status = request.GET.get("status", "")

    if status:

        tickets = tickets.filter(
            status=status
        )

    # ======================
    # Admin Filter
    # ======================

    handled_by = request.GET.get(
        "handled_by",
        ""
    )

    if handled_by == "unassigned":

        tickets = tickets.filter(
            handled_by__isnull=True
        )

    elif handled_by:

        tickets = tickets.filter(
            handled_by_id=handled_by
        )

    # ======================
    # Attachment Filter
    # ======================

    attachment = request.GET.get(
        "attachment",
        ""
    )

    if attachment == "yes":

        tickets = tickets.exclude(
            attachment=""
        ).exclude(
            attachment__isnull=True
        )

    elif attachment == "no":

        tickets = tickets.filter(
            attachment__isnull=True
        )

    # ======================
    # Date Filters
    # ======================

    date_from = request.GET.get(
        "date_from"
    )

    date_to = request.GET.get(
        "date_to"
    )

    if date_from:

        tickets = tickets.filter(
            created_at__date__gte=date_from
        )

    if date_to:

        tickets = tickets.filter(
            created_at__date__lte=date_to
        )

    # ======================
    # Sorting
    # ======================

    sort = request.GET.get(
        "sort",
        "-created_at"
    )

    allowed_sorts = [
        "-created_at",
        "created_at",
        "-updated_at",
        "updated_at",
    ]

    if sort in allowed_sorts:

        tickets = tickets.order_by(sort)

    # ======================
    # Statistics
    # ======================

    total_tickets = SupportTicket.objects.count()

    in_progress_count = SupportTicket.objects.filter(
        status="in_progress"
    ).count()

    waiting_user_count = SupportTicket.objects.filter(
        status="waiting_user"
    ).count()

    resolved_count = SupportTicket.objects.filter(
        status="resolved"
    ).count()

    closed_count = SupportTicket.objects.filter(
        status="closed"
    ).count()

    unassigned_count = SupportTicket.objects.filter(
        handled_by__isnull=True
    ).count()

    attachment_count = SupportTicket.objects.exclude(
        attachment=""
    ).exclude(
        attachment__isnull=True
    ).count()

    admins = User.objects.filter(
        role="admin"
    )

    context = {

        "tickets": tickets,
        "admins": admins,

        "search": search,
        "category": category,
        "status": status,
        "handled_by": handled_by,
        "attachment": attachment,
        "date_from": date_from,
        "date_to": date_to,
        "sort": sort,

        "total_tickets": total_tickets,
        "in_progress_count": in_progress_count,
        "waiting_user_count": waiting_user_count,
        "resolved_count": resolved_count,
        "closed_count": closed_count,
        "unassigned_count": unassigned_count,
        "attachment_count": attachment_count,
    }

    return render(
        request,
        "admin_panel/support_tickets.html",
        context
    )
  
  
  
@admin_required(levels=[1, 2])
def support_ticket_detail(request, pk):

    ticket = get_object_or_404(
        SupportTicket.objects.select_related(
            "user",
            "handled_by"
        ).prefetch_related(
            "messages"
        ),
        id=pk
    )

    # =========================
    # هل يملك صلاحية التعديل؟
    # =========================

    can_manage = (

        request.user.admin_level == 1

        or

        ticket.handled_by == request.user

        or

        ticket.handled_by is None

    )

    # =========================
    # POST
    # =========================

    if request.method == "POST":

        action = request.POST.get("action")

        # =====================
        # استلام التذكرة
        # =====================

        if action == "claim":

            if ticket.handled_by is None:

                ticket.handled_by = request.user
                ticket.save()

                messages.success(
                    request,
                    "تم استلام التذكرة بنجاح."
                )

            else:

                messages.warning(
                    request,
                    "التذكرة مستلمة بالفعل."
                )

            return redirect(
                "admin_panel:support_ticket_detail",
                pk=ticket.id
            )

        # =====================
        # الرد على التذكرة
        # =====================

        elif action == "reply":

            if not can_manage:

                messages.error(
                    request,
                    "لا تملك صلاحية الرد على هذه التذكرة."
                )

                return redirect(
                    "admin_panel:support_ticket_detail",
                    pk=ticket.id
                )

            if ticket.handled_by != request.user:

                messages.error(
                    request,
                    "يجب استلام التذكرة أولاً قبل الرد عليها."
                )

                return redirect(
                    "admin_panel:support_ticket_detail",
                    pk=ticket.id
                )

            if ticket.status in [
                "closed",
                "resolved"
            ]:

                messages.warning(
                    request,
                    "لا يمكن الرد على تذكرة مغلقة أو محلولة."
                )

                return redirect(
                    "admin_panel:support_ticket_detail",
                    pk=ticket.id
                )

            form = SupportMessageForm(
                request.POST
            )

            if form.is_valid():

                SupportMessage.objects.create(

                    ticket=ticket,

                    sender=request.user,

                    sender_type="admin",

                    message=form.cleaned_data[
                        "message"
                    ]
                )

                ticket.mark_waiting_user()

                if ticket.user:

                    send_notification(

                        title="تم الرد على تذكرتك",

                        message=(
                            f"تم الرد على تذكرتك "
                            f"({ticket.ticket_number})"
                        ),

                        target="user",

                        user=ticket.user,

                        notification_type="admin",

                        sent_by=request.user
                    )

                messages.success(
                    request,
                    "تم إرسال الرد بنجاح."
                )

            return redirect(
                "admin_panel:support_ticket_detail",
                pk=ticket.id
            )

        # =====================
        # إغلاق التذكرة
        # =====================

        elif action == "close":

            if ticket.handled_by != request.user:

                messages.error(
                    request,
                    "يجب استلام التذكرة أولاً."
                )

                return redirect(
                    "admin_panel:support_ticket_detail",
                    pk=ticket.id
                )

            ticket.mark_closed()

            messages.success(
                request,
                "تم إغلاق التذكرة بنجاح."
            )

            return redirect(
                "admin_panel:support_ticket_detail",
                pk=ticket.id
            )

    admins = User.objects.filter(
        role="admin"
    ).order_by(
        "first_name",
        "last_name"
    )

    message_form = SupportMessageForm()

    context = {

        "ticket": ticket,
        "admins": admins,
        "can_manage": can_manage,
        "messages_list": ticket.messages.all(),
        "message_form": message_form,

    }

    return render(
        request,
        "admin_panel/support_ticket_detail.html",
        context
    )
