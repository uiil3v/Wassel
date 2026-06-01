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

from contracts.services import create_transport_contract

from django.contrib.auth import logout


from accounts.utils import send_email_change_confirmation

from Wassel.email_utils import (
    send_request_approved_email,
    send_request_rejected_email,
)


from notifications.utils import send_notification

from notifications.models import Notification


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

    active_subscriptions = sum(1 for sub in subscriptions if sub.current_status == "active")

    new_requests = SubscriptionRequest.objects.filter(
        subscription__driver=profile,
        status="pending"
    ).count()

    approved_requests = SubscriptionRequest.objects.filter(
        subscription__driver=profile,
        status="approved"
    )

    students_count = approved_requests.count()

    total_earnings = request.user.wallet.balance

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



        old_first_name = request.user.first_name
        old_last_name = request.user.last_name
        old_phone = request.user.phone
        old_city_id = str(request.user.city_id)

        old_vehicle_model = profile.vehicle_model
        old_gender = profile.gender
        
        # ===== بيانات الحساب =====
        request.user.first_name = request.POST.get("first_name")
        request.user.last_name = request.POST.get("last_name")

        new_email = request.POST.get("email")
        new_phone = request.POST.get("phone")
        new_city_id = request.POST.get("city")
        
        

        
        
        requires_reverification = False
        
        if (
            request.POST.get("first_name") != old_first_name
            or
            request.POST.get("last_name") != old_last_name
            or
            new_city_id != old_city_id
            or
            request.POST.get("vehicle_model") != (old_vehicle_model or "")
            or
            request.POST.get("gender") != (old_gender or "")
        ):
            requires_reverification = True
        

        # ===== تغيير البريد الإلكتروني =====

        email_changed = (
            new_email
            and
            new_email != request.user.email
        )

        if email_changed:

            if User.objects.filter(
                email=new_email
            ).exclude(
                pk=request.user.pk
            ).exists():

                messages.error(
                    request,
                    "البريد الإلكتروني مستخدم بالفعل."
                )

                return redirect("driver:profile")

            if User.objects.filter(
                pending_email=new_email
            ).exclude(
                pk=request.user.pk
            ).exists():

                messages.error(
                    request,
                    "هذا البريد الإلكتروني قيد التأكيد لحساب آخر."
                )

                return redirect("driver:profile")

            request.user.pending_email = new_email

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
        request.user.phone = new_phone
        request.user.city_id = new_city_id
        request.user.save()

        if email_changed:

            send_email_change_confirmation(
                request.user,
                request
            )

        # ===== بيانات السائق =====
        profile.vehicle_model = request.POST.get("vehicle_model")
        
        profile.gender = request.POST.get("gender")

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

        # # ===== إعادة مراجعة لو غير المدينة =====
        # if str(request.user.city_id) != new_city_id:
        #     profile.verification_status = "pending"
        #     messages.info(request, "تم تغيير المدينة وسيتم إعادة مراجعة حسابك.")

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

        if not (
            profile.vehicle_model
            and
            profile.gender
            and
            documents_complete
        ):

            profile.verification_status = "incomplete"

            messages.error(
                request,
                "يرجى إكمال جميع البيانات والمستندات."
            )

        elif requires_reverification:

            profile.verification_status = "pending"

            messages.success(
                request,
                "تم إرسال بياناتك للمراجعة."
            )

        profile.save()

        if email_changed:

            messages.success(
                request,
                "تم حفظ التعديلات وإرسال رابط تأكيد إلى البريد الإلكتروني الجديد."
            )

        return redirect("driver:profile")

    context = {
        "profile": profile,
        "cities": City.objects.filter(is_active=True)
    }

    return render(request, "driver/profile.html", context)




@login_required
def delete_driver_account(request):

    if request.user.role != "driver":
        return redirect("main:index")

    if request.method != "POST":
        return redirect("driver:profile")

    profile = request.user.driver_profile

    # يوجد اشتراكات مرتبطة بالسائق
    if Subscription.objects.filter(
        driver=profile
    ).exists():

        messages.error(
            request,
            "لا يمكنك حذف الحساب لوجود اشتراكات مرتبطة بحسابك."
        )

        return redirect("driver:profile")

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

            return redirect("driver:profile")

        if wallet.frozen_balance > 0:

            messages.error(
                request,
                "لا يمكنك حذف الحساب لوجود مبلغ مجمد في المحفظة."
            )

            return redirect("driver:profile")

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
@driver_verified_required
def create_subscription(request):

    if request.user.role != "driver":
        return redirect("main:index")

    profile = request.user.driver_profile
    
    blocked_subscription_exists = Subscription.objects.filter(
        driver=profile,
        status="inactive_by_admin"
    ).exists()

    if blocked_subscription_exists:

        messages.error(
            request,
            "لا يمكنك إنشاء اشتراك جديد لوجود اشتراك موقوف من إدارة المنصة. يرجى التواصل مع الدعم الفني."
        )

        return redirect("driver:subscriptions")

    if profile.verification_status != "approved":
        messages.error(request, "لا يمكنك إنشاء اشتراك قبل اعتماد حسابك.")
        return redirect("driver:dashboard")

    if request.method == "POST":

        neighborhood = request.POST.get("neighborhood")
        price = request.POST.get("price")
        seats = request.POST.get("seats")
        duration = request.POST.get("duration")  # monthly / semester
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        notes = request.POST.get("notes")

        # 🔥 تحقق من وجود start_date
        if not start_date:
            messages.error(request, "❌ يرجى اختيار تاريخ البداية")
            return redirect("driver:create_subscription")

        # 🔥 تحقق من النوع
        if duration not in ["monthly", "semester"]:
            messages.error(request, "❌ نوع الاشتراك غير صحيح")
            return redirect("driver:create_subscription")

        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            today = timezone.localdate()

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


            elif duration == "semester":

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
def edit_subscription(request, sub_id):

    if request.user.role != "driver":
        return redirect("main:index")

    profile = request.user.driver_profile

    subscription = get_object_or_404(
        Subscription,
        id=sub_id,
        driver=profile
    )

    # 🔒 منع التعديل
    if not subscription.can_edit:

        messages.error(
            request,
            "لا يمكنك تعديل الاشتراك بعد وجود طلبات أو طلاب."
        )

        return redirect(
            "driver:subscription_detail",
            sub_id=sub_id
        )

    if request.method == "POST":

        neighborhood = request.POST.get("neighborhood")
        price = request.POST.get("price")
        seats = request.POST.get("seats")
        duration = request.POST.get("duration")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        notes = request.POST.get("notes")

        try:

            start_date_obj = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()

            # =========================
            # شهري
            # =========================

            if duration == "monthly":

                end_date_obj = start_date_obj + timedelta(days=30)

            # =========================
            # فصلي
            # =========================

            else:

                if not end_date:

                    end_date_obj = (
                        start_date_obj +
                        timedelta(days=90)
                    )

                else:

                    end_date_obj = datetime.strptime(
                        end_date,
                        "%Y-%m-%d"
                    ).date()

            # =========================
            # تحديث البيانات
            # =========================

            subscription.neighborhood = neighborhood
            subscription.price = price
            subscription.seats = seats
            subscription.available_seats = seats
            subscription.duration = duration
            subscription.start_date = start_date_obj
            subscription.end_date = end_date_obj
            subscription.notes = notes

            subscription.save()

            messages.success(
                request,
                "تم تعديل الاشتراك بنجاح ✨"
            )

            return redirect(
                "driver:subscription_detail",
                sub_id=sub_id
            )

        except ValueError:

            messages.error(
                request,
                "صيغة التاريخ غير صحيحة."
            )

    context = {
        "subscription": subscription,
        "is_edit": True,
    }

    return render(
        request,
        "driver/create_subscription.html",
        context
    )


@login_required
@driver_verified_required
def driver_subscriptions(request):

    if request.user.role != "driver":
        return redirect("main:index")

    profile = request.user.driver_profile

    subscriptions = Subscription.objects.filter(
        driver=profile
    ).order_by("-created_at")


    blocked_by_admin = Subscription.objects.filter(
        driver=profile,
        status="inactive_by_admin"
    ).exists()

    context = {
        "subscriptions": subscriptions,
        "blocked_by_admin": blocked_by_admin,
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
    
    old_requests = subscription.requests.filter(
        status__in=["cancelled", "rejected"]
    ).select_related(
        "student__user"
    ).order_by("-request_date")

    context = {
        "subscription": subscription,
        "pending_requests": pending_requests,
        "approved_requests": approved_requests,
        "old_requests": old_requests,
    }

    return render(request, "driver/subscription_detail.html", context)



@login_required
@driver_verified_required
def delete_subscription(request, sub_id):

    if request.user.role != "driver":
        return redirect("main:index")

    if request.method != "POST":
        return redirect("driver:subscriptions")

    profile = request.user.driver_profile

    subscription = get_object_or_404(
        Subscription,
        id=sub_id,
        driver=profile
    )

    if subscription.requests.exists():

        messages.error(
            request,
            "لا يمكن حذف اشتراك سبق أن استقبل طلبات. يمكنك إيقافه فقط."
        )

        return redirect(
            "driver:subscription_detail",
            sub_id=sub_id
        )

    subscription.delete()

    messages.success(
        request,
        "تم حذف الاشتراك بنجاح."
    )

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
            if req.subscription.status == "inactive_by_admin":
                messages.error(
                    request,
                    "لا يمكنك قبول الطلبات لاشتراك موقوف من الإدارة."
                )

                return redirect(
                    "driver:subscription_detail",
                    sub_id=req.subscription.id
                )
            with transaction.atomic():
                req.approve()
                approve_subscription_payment(req)
                # 🔥 إنشاء العقد الإلكتروني
                create_transport_contract(req)
                
                send_request_approved_email(
                    req,
                    request
                )
                
                send_notification(
                    title="تم قبول طلب الاشتراك",
                    message="تمت الموافقة على طلبك وإنشاء العقد الإلكتروني بنجاح.",
                    target="user",
                    user=req.student.user,
                    notification_type="system"
                )

            messages.success(request, "تمت الموافقة وتحويل المبلغ بنجاح.")

        except ValidationError as e:
            messages.error(request, str(e))

    return redirect("driver:subscription_detail", sub_id=req.subscription.id)





@login_required
@driver_verified_required
def deactivate_subscription(request, sub_id):

    profile = request.user.driver_profile

    subscription = get_object_or_404(
        Subscription,
        id=sub_id,
        driver=profile
    )

    # إذا موقف إداريًا
    if subscription.status == "inactive_by_admin":

        messages.error(
            request,
            "لا يمكنك التحكم باشتراك موقوف من الإدارة."
        )

        return redirect(
            "driver:subscription_detail",
            sub_id=sub_id
        )

    # إذا موقف مسبقًا
    if subscription.status == "inactive_by_driver":

        messages.warning(
            request,
            "الاشتراك موقوف بالفعل."
        )

        return redirect(
            "driver:subscription_detail",
            sub_id=sub_id
        )

    subscription.deactivate_by_driver()

    messages.success(
        request,
        "تم إيقاف الاشتراك بنجاح 🚫"
    )

    return redirect(
        "driver:subscription_detail",
        sub_id=sub_id
    )
    

@login_required
@driver_verified_required
def activate_subscription(request, sub_id):

    profile = request.user.driver_profile

    subscription = get_object_or_404(
        Subscription,
        id=sub_id,
        driver=profile
    )

    # موقف إداريًا
    if subscription.status == "inactive_by_admin":

        messages.error(
            request,
            "لا يمكنك تفعيل اشتراك موقوف من الإدارة."
        )

        return redirect(
            "driver:subscription_detail",
            sub_id=sub_id
        )

    # مفعل أصلًا
    if subscription.current_status == "active":

        messages.warning(
            request,
            "الاشتراك مفعل بالفعل."
        )

        return redirect(
            "driver:subscription_detail",
            sub_id=sub_id
        )

    subscription.activate()

    messages.success(
        request,
        "تم تفعيل الاشتراك بنجاح ✅"
    )

    return redirect(
        "driver:subscription_detail",
        sub_id=sub_id
    )




@login_required
@driver_verified_required
def reject_request(request, req_id):

    req = get_object_or_404(SubscriptionRequest, id=req_id)

    if request.method == "POST":
        try:
            with transaction.atomic():
                req.reject()  # تغيير الحالة
                refund_frozen_amount(req)  # 🔥 إرجاع الفلوس
                send_request_rejected_email(req)
                
                send_notification(
                    title="تم رفض طلب الاشتراك",
                    message="تم رفض الطلب وإعادة المبلغ إلى محفظتك.",
                    target="user",
                    user=req.student.user,
                    notification_type="system"
                )

            messages.success(request, "تم رفض الطلب وإرجاع المبلغ للطالب.")

        except ValidationError as e:
            messages.error(request, str(e))

    return redirect("driver:subscription_detail", sub_id=req.subscription.id)





@login_required
def driver_notifications(request):
    if request.user.role != "driver":
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
        status="approved",
        subscription__end_date__gte=timezone.localdate()
    ).prefetch_related(
        "schedule",
        "student__user",
        "subscription"
    )

    weekly_schedule = defaultdict(list)

    for req in approved_requests:
        for s in req.schedule.all():

            # 🔥 تجاهل الإجازات
            if s.is_off_day:
                continue

            day_name = DAYS_MAP.get(s.day_of_week.lower(), s.day_of_week)

            weekly_schedule[day_name].append({
                "student": req.student.user.get_full_name(),
                "city": req.student.user.city.name_ar,
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

