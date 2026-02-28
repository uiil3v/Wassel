from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import DriverProfile
from accounts.models import User


@login_required
def driver_dashboard(request):

    if request.user.role != "driver":
        return redirect("main:index")

    profile = getattr(request.user, "driver_profile", None)

    if not profile:
        messages.warning(request, "يرجى إكمال بياناتك أولاً.")
        return redirect("driver:profile")

    if profile.verification_status == "incomplete":
        messages.warning(request, "يرجى إكمال بياناتك أولاً.")
        return redirect("driver:profile")

    if profile.verification_status == "pending":
        messages.warning(request, "طلبك قيد المراجعة حالياً.")
        return redirect("driver:profile")

    if profile.verification_status == "rejected":
        messages.error(request, "تم رفض طلبك، يرجى تعديل بياناتك.")
        return redirect("driver:profile")

    context = {
        "profile": profile,
        "active_subscriptions": 0,
        "new_requests": 0,
        "students_count": 0,
        "total_earnings": 0,
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

        # 🔒 منع التعديل أثناء المراجعة
        if profile.verification_status == "pending":
            messages.warning(request, "لا يمكنك التعديل أثناء المراجعة.")
            return redirect("driver:profile")

        # ================= تحديث بيانات الحساب =================

        request.user.first_name = request.POST.get("first_name")
        request.user.last_name = request.POST.get("last_name")

        new_email = request.POST.get("email")
        new_phone = request.POST.get("phone")

        # تحقق أن الإيميل غير مستخدم
        if User.objects.exclude(pk=request.user.pk).filter(email=new_email).exists():
            messages.error(request, "البريد الإلكتروني مستخدم بالفعل.")
            return redirect("driver:profile")

        request.user.email = new_email
        request.user.phone = new_phone
        request.user.save()

        # ================= تحديث بيانات السائق =================

        profile.vehicle_model = request.POST.get("vehicle_model")

        if request.FILES.get("id_document_image"):
            profile.id_document_image = request.FILES.get("id_document_image")

        if request.FILES.get("driving_license_image"):
            profile.driving_license_image = request.FILES.get("driving_license_image")

        if request.FILES.get("vehicle_registration_image"):
            profile.vehicle_registration_image = request.FILES.get("vehicle_registration_image")

        if request.FILES.get("vehicle_insurance_image"):
            profile.vehicle_insurance_image = request.FILES.get("vehicle_insurance_image")

        if request.FILES.get("vehicle_front_image"):
            profile.vehicle_front_image = request.FILES.get("vehicle_front_image")

        if request.FILES.get("vehicle_back_image"):
            profile.vehicle_back_image = request.FILES.get("vehicle_back_image")

        if request.FILES.get("vehicle_side_image"):
            profile.vehicle_side_image = request.FILES.get("vehicle_side_image")

        # ================= تحقق اكتمال البيانات =================

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
        "profile": profile
    }

    return render(request, "driver/profile.html", context)


@login_required
def driver_verification(request):

    if request.user.role != "driver":
        return redirect("main:index")

    return render(request, "driver/verification.html")