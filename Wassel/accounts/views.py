from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from .forms import RegisterForm


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

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