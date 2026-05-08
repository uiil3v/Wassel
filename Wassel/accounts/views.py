from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from .forms import RegisterForm

from django.shortcuts import get_object_or_404
from .models import User

from driver.models import DriverProfile
from student.models import StudentProfile

from reviews.models import Review




def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            
            if user.role not in ["student", "driver"]:
                user.role = "student"

            # الحالة الافتراضية للحساب
            user.status = "active"
            user.save()

            # تسجيل الدخول مباشرة بعد التسجيل
            login(request, user)

            # إذا كان سائق → يروح يكمل بياناته
            if user.role == "driver":
                messages.warning(request, "يرجى إكمال بياناتك أولاً.")
                return redirect("driver:profile")

            # إذا طالب
            messages.success(request, "تم إنشاء الحساب بنجاح 🎉")
            return redirect("main:index")

        else:
            messages.error(request, "حدث خطأ أثناء التسجيل، يرجى مراجعة البيانات.")

    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})




def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")   # 🔥 بدل username
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:

            # 🔒 منع المحظورين
            if user.status == "banned":
                messages.error(request, "حسابك محظور.")
                return redirect("accounts:login")

            login(request, user)
            messages.success(request, "تم تسجيل الدخول بنجاح 👋")
            return redirect("main:index")

        else:
            messages.error(request, "البريد الإلكتروني أو كلمة المرور غير صحيحة.")

    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح 👋")
    return redirect("main:index")



def public_profile_view(request, user_id):

    user_obj = get_object_or_404(
        User,
        id=user_id
    )

    reviews = Review.objects.filter(
        reviewed_user=user_obj
    ).select_related(
        "reviewer"
    )[:10]

    driver_profile = None
    student_profile = None

    # ===== Driver =====
    if user_obj.role == "driver":

        driver_profile = getattr(
            user_obj,
            "driver_profile",
            None
        )

    # ===== Student =====
    elif user_obj.role == "student":

        student_profile = getattr(
            user_obj,
            "student_profile",
            None
        )

    context = {
        "profile_user": user_obj,
        "driver_profile": driver_profile,
        "student_profile": student_profile,
        "reviews": reviews,
    }

        # =========================
    # اختيار الـ template حسب المستخدم الحالي
    # =========================

    if request.user.is_authenticated:

        if request.user.role == "student":
            template_name = "student/public_profile.html"

        elif request.user.role == "driver":
            template_name = "driver/public_profile.html"

        elif request.user.role == "admin":
            template_name = "admin_panel/public_profile.html"

        else:
            template_name = "accounts/public_profile_content.html"

    else:
        template_name = "accounts/public_profile_content.html"

    return render(
        request,
        template_name,
        context
    )