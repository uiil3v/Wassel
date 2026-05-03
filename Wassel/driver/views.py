from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import DriverProfile
from accounts.models import User
from subscriptions.models import Subscription
from django.utils.translation import gettext_lazy as _
from subscriptions.models import Subscription, SubscriptionRequest
from django.db.models import Sum
from accounts.models import City
from payment.services import approve_subscription_payment, refund_frozen_amount
from django.core.exceptions import ValidationError
from django.db import transaction

from notifications.models import Notification
from collections import defaultdict

from .decorators import driver_verified_required

from datetime import datetime, timedelta
from django.utils import timezone




@login_required
def driver_dashboard(request):

    if request.user.role != "driver":
        return redirect("main:index")

    profile = getattr(request.user, "driver_profile", None)

    if not profile:
        messages.warning(request, "يرجى إكمال بياناتك أولاً.")
        return redirect("driver:profile")

    if profile.verification_status != "approved":
        messages.warning(request, "حسابك غير معتمد حالياً.")
        return redirect("driver:profile")

    # ===============================
    # الحسابات الحقيقية
    # ===============================

    subscriptions = Subscription.objects.filter(driver=profile)

    active_subscriptions = subscriptions.filter(status="active").count()

    new_requests = SubscriptionRequest.objects.filter(
        subscription__driver=profile,
        status="pending"
    ).count()

    approved_requests = SubscriptionRequest.objects.filter(
        subscription__driver=profile,
        status="approved"
    )

    students_count = approved_requests.count()

    total_earnings = approved_requests.aggregate(
        total=Sum("price_snapshot")
    )["total"] or 0

    # ===============================
    # آخر الطلبات 🔥
    # ===============================
    last_requests = SubscriptionRequest.objects.filter(
        subscription__driver=profile
    ).select_related(
        "student__user",
        "subscription"
    ).order_by("-request_date")[:5]

    # ===============================
    # Context
    # ===============================
    context = {
        "profile": profile,
        "active_subscriptions": active_subscriptions,
        "new_requests": new_requests,
        "students_count": students_count,
        "total_earnings": total_earnings,
        "last_requests": last_requests,  # 🔥 المهم
    }

    return render(request, "driver/dashboard.html", context)



@login_required
def driver_profile(request):

    if request.user.role != "driver":
        return redirect("main:index")

    profile, created = DriverProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":

        if profile.verification_status == "pending":
            messages.warning(request, "لا يمكنك التعديل أثناء المراجعة.")
            return redirect("driver:profile")

        # ===== بيانات الحساب =====
        request.user.first_name = request.POST.get("first_name")
        request.user.last_name = request.POST.get("last_name")

        new_email = request.POST.get("email")
        new_phone = request.POST.get("phone")
        new_city_id = request.POST.get("city")

        # تحقق من تكرار الإيميل
        if User.objects.exclude(pk=request.user.pk).filter(email=new_email).exists():
            messages.error(request, "البريد الإلكتروني مستخدم بالفعل.")
            return redirect("driver:profile")

        # ===== منع تغيير المدينة لو عنده اشتراكات أو طلاب =====
        has_active_subscriptions = Subscription.objects.filter(
            driver=profile,
            status="active"
        ).exists()

        has_approved_students = SubscriptionRequest.objects.filter(
            subscription__driver=profile,
            status="approved"
        ).exists()

        if (has_active_subscriptions or has_approved_students) and str(request.user.city_id) != new_city_id:
            messages.error(request, "لا يمكنك تغيير المدينة أثناء وجود اشتراكات أو طلاب نشطين.")
            return redirect("driver:profile")

        # ===== حفظ بيانات المستخدم =====
        request.user.email = new_email
        request.user.phone = new_phone
        request.user.city_id = new_city_id
        request.user.save()

        # ===== بيانات السائق =====
        profile.vehicle_model = request.POST.get("vehicle_model")

        # ملفات
        for field in [
            "id_document_image",
            "driving_license_image",
            "vehicle_registration_image",
            "vehicle_insurance_image",
            "vehicle_front_image",
            "vehicle_back_image",
            "vehicle_side_image",
        ]:
            if request.FILES.get(field):
                setattr(profile, field, request.FILES.get(field))

        # ===== إعادة مراجعة لو غير المدينة =====
        if str(request.user.city_id) != new_city_id:
            profile.verification_status = "pending"
            messages.info(request, "تم تغيير المدينة وسيتم إعادة مراجعة حسابك.")

        # ===== تحقق اكتمال البيانات =====
        documents_complete = all([
            profile.id_document_image,
            profile.driving_license_image,
            profile.vehicle_registration_image,
            profile.vehicle_insurance_image,
            profile.vehicle_front_image,
            profile.vehicle_back_image,
            profile.vehicle_side_image,
        ])

        if profile.vehicle_model and documents_complete:
            profile.verification_status = "pending"
            messages.success(request, "تم إرسال بياناتك للمراجعة.")
        else:
            profile.verification_status = "incomplete"
            messages.error(request, "يرجى إكمال جميع البيانات والمستندات.")

        profile.save()
        return redirect("driver:profile")

    context = {
        "profile": profile,
        "cities": City.objects.filter(is_active=True)
    }

    return render(request, "driver/profile.html", context)






@login_required
@driver_verified_required
def create_subscription(request):

    if request.user.role != "driver":
        return redirect("main:index")

    profile = request.user.driver_profile

    if profile.verification_status != "approved":
        messages.error(request, "لا يمكنك إنشاء اشتراك قبل اعتماد حسابك.")
        return redirect("driver:dashboard")

    if request.method == "POST":

        neighborhood = request.POST.get("neighborhood")
        price = request.POST.get("price")
        seats = request.POST.get("seats")
        duration = request.POST.get("duration")  # monthly / quarterly
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        notes = request.POST.get("notes")

        # 🔥 تحقق من وجود start_date
        if not start_date:
            messages.error(request, "❌ يرجى اختيار تاريخ البداية")
            return redirect("driver:create_subscription")

        # 🔥 تحقق من النوع
        if duration not in ["monthly", "quarterly"]:
            messages.error(request, "❌ نوع الاشتراك غير صحيح")
            return redirect("driver:create_subscription")

        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            today = timezone.now().date()

            # 🔥 منع الماضي
            if start_date_obj < today:
                messages.error(request, "❌ لا يمكنك اختيار تاريخ في الماضي")
                return redirect("driver:create_subscription")

            # =========================
            # 🔥 منطق الاشتراك
            # =========================

            if duration == "monthly":

                # 🔒 لو المستخدم حاول يغير end_date
                if end_date:
                    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
                    days_diff = (end_date_obj - start_date_obj).days

                    if days_diff != 30:
                        messages.error(request, "❌ الاشتراك الشهري يجب أن يكون 30 يوم بالضبط")
                        return redirect("driver:create_subscription")

                # 🔥 النظام يحسبه دائمًا
                end_date_obj = start_date_obj + timedelta(days=30)


            elif duration == "quarterly":

                # 🟡 لو ما حدد → 90 يوم
                if not end_date:
                    end_date_obj = start_date_obj + timedelta(days=90)

                else:
                    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

                    if end_date_obj < start_date_obj:
                        messages.error(request, "❌ تاريخ النهاية يجب أن يكون بعد البداية")
                        return redirect("driver:create_subscription")

                    days_diff = (end_date_obj - start_date_obj).days

                    # 🔥 هنا أهم شرطك
                    if days_diff < 90:
                        messages.error(request, "❌ الاشتراك الفصلي يجب أن يكون 90 يوم على الأقل")
                        return redirect("driver:create_subscription")

            # 🔥 إنشاء الاشتراك
            Subscription.objects.create(
                driver=profile,
                neighborhood=neighborhood,
                price=price,
                seats=seats,
                duration=duration,
                start_date=start_date_obj,
                end_date=end_date_obj,
                notes=notes
            )

            messages.success(request, "تم إنشاء الاشتراك بنجاح 🎉")
            return redirect("driver:subscriptions")

        except ValueError:
            messages.error(request, "❌ صيغة التاريخ غير صحيحة")
        except Exception as e:
            messages.error(request, f"حدث خطأ: {e}")

    return render(request, "driver/create_subscription.html")





@login_required
@driver_verified_required
def driver_subscriptions(request):

    if request.user.role != "driver":
        return redirect("main:index")

    profile = request.user.driver_profile

    subscriptions = Subscription.objects.filter(
        driver=profile
    ).order_by("-created_at")

    context = {
        "subscriptions": subscriptions
    }

    return render(request, "driver/subscriptions.html", context)



@login_required
@driver_verified_required
def driver_requests(request):

    if request.user.role != "driver":
        return redirect("main:index")

    profile = request.user.driver_profile

    # 🔥 الطلبات الجديدة
    pending_requests = SubscriptionRequest.objects.filter(
        subscription__driver=profile,
        status="pending"
    ).select_related(
        "student__user",
        "subscription"
    ).order_by("-request_date")

    # 🔥 الطلبات السابقة
    old_requests = SubscriptionRequest.objects.filter(
        subscription__driver=profile
    ).exclude(
        status="pending"
    ).select_related(
        "student__user",
        "subscription"
    ).order_by("-request_date")

    context = {
        "pending_requests": pending_requests,
        "old_requests": old_requests,
    }

    return render(request, "driver/requests.html", context)



@login_required
@driver_verified_required
def subscription_detail(request, sub_id):

    if request.user.role != "driver":
        return redirect("main:index")

    profile = request.user.driver_profile

    subscription = get_object_or_404(
        Subscription,
        id=sub_id,
        driver=profile
    )

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

    return render(request, "driver/subscription_detail.html", context)



@login_required
@driver_verified_required
def delete_subscription(request, sub_id):

    if request.user.role != "driver":
        return redirect("main:index")

    profile = request.user.driver_profile

    subscription = get_object_or_404(
        Subscription,
        id=sub_id,
        driver=profile
    )

    # تحقق
    has_students = subscription.requests.filter(status="approved").exists()
    has_pending = subscription.requests.filter(status="pending").exists()

    if has_students:
        messages.error(request, "لا يمكن حذف الاشتراك لوجود طلاب مشتركين.")
        return redirect("driver:subscription_detail", sub_id=sub_id)

    if has_pending:
        messages.error(request, "لا يمكن حذف الاشتراك لوجود طلبات قيد الانتظار.")
        return redirect("driver:subscription_detail", sub_id=sub_id)

    subscription.delete()
    messages.success(request, "تم حذف الاشتراك بنجاح.")

    return redirect("driver:subscriptions")





@login_required
@driver_verified_required
def subscription_request_detail(request, req_id):

    if request.user.role != "driver":
        return redirect("main:index")

    profile = request.user.driver_profile

    request_obj = get_object_or_404(
        SubscriptionRequest.objects.select_related(
            "student__user",
            "subscription"
        ).prefetch_related("schedule"),
        id=req_id,
        subscription__driver=profile
    )

    # ✅ ترتيب الأيام (الأحد → السبت)
    ORDER = [
        "sunday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
    ]

    schedule_qs = request_obj.schedule.all()

    # نحولها لدكشنري
    schedule_dict = {s.day_of_week: s for s in schedule_qs}

    # نرتبها
    sorted_schedule = [
        schedule_dict[day]
        for day in ORDER
        if day in schedule_dict
    ]

    context = {
        "req": request_obj,
        "schedule": sorted_schedule
    }

    return render(
        request,
        "driver/subscription_request_detail.html",
        context
    )
    
    
    
@login_required
@driver_verified_required
def approve_request(request, req_id):

    req = get_object_or_404(SubscriptionRequest, id=req_id)

    if request.method == "POST":

        try:
            with transaction.atomic():
                req.approve()  # الموافقة الأصلية
                approve_subscription_payment(req)  # 🔥 تحويل الأموال

            messages.success(request, "تمت الموافقة وتحويل المبلغ بنجاح.")

        except ValidationError as e:
            messages.error(request, str(e))

    return redirect("driver:subscription_detail", sub_id=req.subscription.id)


@login_required
@driver_verified_required
def reject_request(request, req_id):

    req = get_object_or_404(SubscriptionRequest, id=req_id)

    if request.method == "POST":
        try:
            with transaction.atomic():
                req.reject()  # تغيير الحالة
                refund_frozen_amount(req)  # 🔥 إرجاع الفلوس

            messages.success(request, "تم رفض الطلب وإرجاع المبلغ للطالب.")

        except ValidationError as e:
            messages.error(request, str(e))

    return redirect("driver:subscription_detail", sub_id=req.subscription.id)


@login_required
def driver_notifications(request):
    if request.user.role != "driver":
        return redirect("main")

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    context = {
        "notifications": notifications
    }

    return render(request, "driver/notifications.html", context)



DAYS_MAP = {
    "saturday": "السبت",
    "sunday": "الأحد",
    "monday": "الإثنين",
    "tuesday": "الثلاثاء",
    "wednesday": "الأربعاء",
    "thursday": "الخميس",
    "friday": "الجمعة",
}

ORDER = ["الأحد","الإثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت"]




@login_required
@driver_verified_required
def driver_schedule(request):

    if request.user.role != "driver":
        return redirect("main:index")

    profile = request.user.driver_profile

    approved_requests = SubscriptionRequest.objects.filter(
        subscription__driver=profile,
        status="approved"
    ).prefetch_related("schedule", "student__user", "subscription")

    weekly_schedule = defaultdict(list)

    for req in approved_requests:
        for s in req.schedule.all():

            # 🔥 تجاهل الإجازات
            if s.is_off_day:
                continue

            day_name = DAYS_MAP.get(s.day_of_week.lower(), s.day_of_week)

            weekly_schedule[day_name].append({
                "student": req.student.user.get_full_name(),
                "neighborhood": req.subscription.neighborhood,
                "pickup": s.pickup_time,
                "return": s.return_time,
            })

    # 🔥 ترتيب الأيام
    sorted_schedule = {day: weekly_schedule.get(day, []) for day in ORDER}

    context = {
        "schedule": sorted_schedule
    }

    return render(request, "driver/schedule.html", context)

