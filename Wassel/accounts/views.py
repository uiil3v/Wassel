from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from .forms import RegisterForm


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

            # 🚍 إذا سائق → يكون معلق
            if user.role == "driver":
                user.status = "suspended"
            else:
                user.status = "active"

            user.save()

            # نسجل دخوله عادي
            login(request, user)

            if user.role == "driver":
                messages.warning(request, "يرجى تسجيل الدخول  وإكمال بياناتك، سيكون حسابك قيد المراجعة.")
            else:
                messages.success(request, "تم إنشاء الحساب بنجاح 🎉")

            return redirect("main:index")

        else:
            messages.error(request, "حدث خطأ أثناء التسجيل، يرجى مراجعة البيانات.")

    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.status == "suspended":
                messages.warning(request, "حسابك قيد المراجعة، يرجى إكمال بياناتك.")

            else:
                messages.success(request, "تم تسجيل الدخول بنجاح 👋")

            return redirect("main:index")

        else:
            messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")

    return render(request, "accounts/login.html")



def logout_view(request):
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح 👋")
    return redirect("main:index")