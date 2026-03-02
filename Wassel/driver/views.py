from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import DriverProfile
from accounts.models import User
from subscriptions.models import Subscription
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from subscriptions.models import Subscription, SubscriptionRequest
from django.db.models import Sum
from accounts.models import City
from payment.services import approve_subscription_payment
from django.core.exceptions import ValidationError
from django.db import transaction




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

    context = {
        "profile": profile,
        "active_subscriptions": active_subscriptions,
        "new_requests": new_requests,
        "students_count": students_count,
        "total_earnings": total_earnings,
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
        duration = request.POST.get("duration")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        notes = request.POST.get("notes")

        try:
            Subscription.objects.create(
                driver=profile,
                neighborhood=neighborhood,
                price=price,
                seats=seats,
                duration=duration,
                start_date=start_date,
                end_date=end_date,
                notes=notes
            )

            messages.success(request, "تم إنشاء الاشتراك بنجاح 🎉")
            return redirect("driver:subscriptions")

        except Exception as e:
            messages.error(request, f"حدث خطأ: {e}")

    return render(request, "driver/create_subscription.html")


@login_required
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
def driver_requests(request):
    if request.user.role != "driver":
        return redirect("main:index")

    return render(request, "driver/requests.html")

@login_required
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

    context = {
        "req": request_obj,
        "schedule": request_obj.schedule.all()
    }

    return render(
        request,
        "driver/subscription_request_detail.html",
        context
    )
    
    
@login_required
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
def reject_request(request, req_id):

    req = get_object_or_404(SubscriptionRequest, id=req_id)

    if request.method == "POST":
        req.reject()

    return redirect("driver:subscription_detail", sub_id=req.subscription.id)


@login_required
def driver_notifications(request):
    if request.user.role != "driver":
        return redirect("main:index")

    return render(request, "driver/notifications.html")