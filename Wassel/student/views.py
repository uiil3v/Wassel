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
from django.db.models import Q
from student.models import StudentProfile
from accounts.models import User
from django.contrib import messages
from accounts.models import City
from payment.services import freeze_student_amount
from django.core.exceptions import ValidationError
from payment.services import refund_frozen_amount, refund_after_approval

from notifications.models import Notification
from payment.models import Transaction


from datetime import datetime

from reviews.models import Review

from .decorators import student_profile_completed_required


from django.contrib.auth import logout

@login_required
@student_profile_completed_required
def student_dashboard(request):

    if request.user.role != "student":
        return redirect("main:index")

    profile = getattr(request.user, "student_profile", None)

    if not profile:
        return redirect("student:profile")

    today = timezone.now().date()

    active_request = SubscriptionRequest.objects.filter(
        student=profile,
        status="approved",
        subscription__end_date__gte=today
    ).select_related("subscription__driver__user").first()
    
    pending_request = SubscriptionRequest.objects.filter(
        student=profile,
        status="pending"
    ).first()

    available_subscriptions = None

    if not active_request:
        available_subscriptions = Subscription.objects.filter(
            status="active",
            driver__user__status="active",
            driver__user__city=request.user.city
        ).select_related("driver__user")[:6]

    context = {
        "active_request": active_request,
        "pending_request": pending_request,
        "available_subscriptions": available_subscriptions,
    }

    return render(request, "student/dashboard.html", context)




@login_required
@student_profile_completed_required
def my_subscriptions(request):

    if request.user.role != "student":
        return redirect("main:index")

    profile = request.user.student_profile
    today = timezone.now().date()

    subscriptions = SubscriptionRequest.objects.filter(
        student=profile
    ).select_related("subscription__driver__user").order_by("-request_date")

    active = []
    expired = []
    cancelled = []
    pending = []

    for sub in subscriptions:

        if sub.status == "pending":
            pending.append(sub)

        elif sub.status == "cancelled":
            cancelled.append(sub)

        elif sub.status == "approved":
            if sub.subscription.end_date >= today:
                active.append(sub)
            else:
                already_reviewed = Review.objects.filter(
                    reviewer=request.user,
                    subscription_request=sub
                ).exists()

                sub.already_reviewed = already_reviewed

                expired.append(sub)

    context = {
        "active": active,
        "expired": expired,
        "cancelled": cancelled,
        "pending": pending,
    }

    return render(request, "student/my_subscriptions.html", context)



@login_required
@student_profile_completed_required
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
    )

    context = {
        "req": req,
        "schedule": req.schedule.all()
    }

    return render(request, "student/subscription_detail.html", context)



@login_required
@student_profile_completed_required
def available_subscriptions(request):

    if request.user.role != "student":
        return redirect("main:index")

    # ================= GET PARAMETERS =================
    search_query = request.GET.get("search", "").strip()
    duration = request.GET.get("duration", "")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    sort = request.GET.get("sort", "")

    # ================= BASE QUERY =================
    
    subscriptions = Subscription.objects.filter(
        status="active",
        driver__user__status="active",
        available_seats__gt=0,
        end_date__gte=timezone.now().date(),
        driver__user__city=request.user.city
    )
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

    return render(request, "student/subscriptions.html", context)



@login_required
@student_profile_completed_required
def subscription_detail_view(request, sub_id):

    if request.user.role != "student":
        return redirect("main:index")

    profile = request.user.student_profile

    subscription = get_object_or_404(
        Subscription.objects.select_related("driver__user"),
        id=sub_id,
        status="active",
        driver__user__status="active",
        driver__user__city=request.user.city
    )

    today = timezone.now().date()

    has_active_request = profile.subscription_requests.filter(
        Q(status="pending") |
        Q(status="approved", subscription__end_date__gte=today)
    ).exists()

    context = {
        "subscription": subscription,
        "has_active_request": has_active_request,
    }

    return render(request, "student/subscription_detail_view.html", context)



@login_required
@student_profile_completed_required
def create_request(request, sub_id):

    if request.user.role != "student":
        return redirect("main:index")

    profile = request.user.student_profile

    subscription = get_object_or_404(
        Subscription,
        id=sub_id,
        status="active",
        driver__user__city=request.user.city
    )
    
    # 🔥 منع الاشتراك إذا قرب ينتهي
    if not subscription.can_accept_requests():
        
        messages.error(
            request,
            "هذا الاشتراك على وشك الانتهاء او منتهي بالفعل."
        )

        return redirect(
            "student:subscription_detail_view",
            sub_id=sub_id
        )

    today = timezone.now().date()
    if profile.subscription_requests.filter(
        Q(status="pending") |
        Q(status="approved", subscription__end_date__gte=today)
    ).exists():
        messages.warning(request, "لديك طلب اشتراك نشط بالفعل.")
        return redirect("student:dashboard")

    days = SubscriptionRequestSchedule.DAYS_OF_WEEK

    if request.method == "POST":

        try:
            with transaction.atomic():

                # إنشاء الطلب
                req = SubscriptionRequest.objects.create(
                    student=profile,
                    subscription=subscription,
                    status="pending",
                    price_snapshot=subscription.price
                )

                # 🔥 تجميد المبلغ
                freeze_student_amount(request.user, req)

                # إنشاء الجدول
                for day_code, _ in days:

                    is_off = request.POST.get(f"{day_code}_off") == "on"
                    pickup = request.POST.get(f"{day_code}_pickup")
                    ret = request.POST.get(f"{day_code}_return")

                    if not is_off and pickup and ret:
                        try:
                            pickup_time = datetime.strptime(pickup, "%H:%M").time()
                            return_time = datetime.strptime(ret, "%H:%M").time()

                            if return_time <= pickup_time:
                                raise ValidationError("وقت العودة يجب أن يكون بعد وقت الذهاب.")

                        except ValueError:
                            raise ValidationError("صيغة الوقت غير صحيحة.")

                        schedule = SubscriptionRequestSchedule.objects.create(
                            request=req,
                            day_of_week=day_code,
                            is_off_day=False,
                            pickup_time=pickup_time,
                            return_time=return_time
                        )

                    else:
                        # يوم إجازة
                        schedule = SubscriptionRequestSchedule.objects.create(
                            request=req,
                            day_of_week=day_code,
                            is_off_day=True
                        )

            messages.success(request, "تم إرسال الطلب وتجميد المبلغ بنجاح.")
            return redirect("student:dashboard")

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect("student:subscription_detail_view", sub_id=sub_id)

    context = {
        "subscription": subscription,
        "days": days
    }

    return render(request, "student/create_request.html", context)



@login_required
@student_profile_completed_required
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
            refund_frozen_amount(req)
            req.status = "cancelled"
            req.save()

        elif req.status == "approved":
            refund_after_approval(req)

        return redirect("student:dashboard")
    
    
    

@login_required
def student_profile(request):

    if request.user.role != "student":
        return redirect("main:index")

    profile, created = StudentProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":

        # ===== تحديث بيانات الحساب =====
        request.user.first_name = request.POST.get("first_name")
        request.user.last_name = request.POST.get("last_name")

        new_email = request.POST.get("email")
        new_phone = request.POST.get("phone")
        new_city_id = request.POST.get("city")

        # تحقق أن الإيميل غير مستخدم
        if User.objects.exclude(pk=request.user.pk).filter(email=new_email).exists():
            messages.error(request, "البريد الإلكتروني مستخدم بالفعل.")
            return redirect("student:profile")

        # ===== منع تغيير المدينة لو عنده اشتراك نشط =====
        has_active_request = profile.subscription_requests.filter(
            status__in=["pending", "approved"]
        ).exists()

        if has_active_request and str(request.user.city_id) != new_city_id:
            messages.error(request, "لا يمكنك تغيير المدينة أثناء وجود اشتراك نشط.")
            return redirect("student:profile")

        # حفظ بيانات الحساب
        request.user.email = new_email
        request.user.phone = new_phone
        request.user.city_id = new_city_id
        request.user.save()

        # ===== تحديث بيانات الطالب =====
        profile.university_name = request.POST.get("university_name")
        gender = request.POST.get("gender")
        if not gender:
            messages.error(request, "يرجى اختيار الجنس.")
            return redirect("student:profile")

        profile.gender = gender
        profile.neighborhood = request.POST.get("neighborhood")
        profile.location_url = request.POST.get("location_url")

        profile.save()

        messages.success(request, "تم حفظ التعديلات بنجاح 🎉")
        return redirect("student:profile")

    context = {
        "profile": profile,
        "cities": City.objects.all()
    }

    return render(request, "student/profile.html", context)


@login_required
def delete_student_account(request):

    if request.user.role != "student":
        return redirect("main:index")

    if request.method != "POST":
        return redirect("student:profile")

    profile = request.user.student_profile

    # يوجد طلب قيد الانتظار
    if profile.subscription_requests.filter(
        status="pending"
    ).exists():

        messages.error(
            request,
            "لا يمكنك حذف الحساب لوجود طلب اشتراك قيد الانتظار."
        )

        return redirect("student:profile")

    # يوجد اشتراك قائم
    if profile.subscription_requests.filter(
        status="approved",
        subscription__end_date__gte=timezone.now().date()
    ).exists():

        messages.error(
            request,
            "لا يمكنك حذف الحساب لوجود اشتراك قائم."
        )

        return redirect("student:profile")

    wallet = getattr(
        request.user,
        "wallet",
        None
    )
    
    if wallet:

        if wallet.balance > 0:

            messages.error(
                request,
                "يرجى سحب الرصيد الموجود في المحفظة قبل حذف الحساب."
            )

            return redirect("student:profile")

        if wallet.frozen_balance > 0:

            messages.error(
                request,
                "لا يمكنك حذف الحساب لوجود مبلغ مجمد في المحفظة."
            )

            return redirect("student:profile")

    request.user.status = "deleted"
    request.user.deleted_at = timezone.now()
    request.user.save()

    logout(request)

    messages.success(
        request,
        "تم حذف حسابك بنجاح."
    )

    return redirect("main:index")



@login_required
def student_notifications(request):
    if request.user.role != "student":
        return redirect("main:index")

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    unread_count = notifications.filter(
        is_read=False
    ).count()

    context = {
        "notifications": notifications,
        "unread_count": unread_count,
    }

    return render(request, "student/notifications.html", context)


