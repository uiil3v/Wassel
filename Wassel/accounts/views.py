from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from .forms import RegisterForm

from django.shortcuts import get_object_or_404
from .models import User

from driver.models import DriverProfile
from student.models import StudentProfile

from reviews.models import Review
from subscriptions.models import Subscription

from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

from .tokens import email_verification_token


from django.core.mail import send_mail

from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from django.urls import reverse

from django.conf import settings

from django.contrib.auth.decorators import login_required

from django.utils import timezone
from datetime import timedelta

from django.contrib.auth.views import PasswordResetView

from .utils import send_email_change_confirmation

from Wassel.email_utils import send_platform_email


def redirect_authenticated_user(user):
    if user.role == "student":
        return redirect("student:dashboard")

    if user.role == "driver":
        return redirect("driver:dashboard")

    if user.role == "admin":
        return redirect("admin_panel:dashboard")

    return redirect("main:index")




def register_view(request):
    if request.user.is_authenticated:
        return redirect_authenticated_user(request.user)

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            
            if user.role not in ["student", "driver"]:
                user.role = "student"

            # الحالة الافتراضية للحساب
            user.status = "active"

            user.save()

            # =========================
            # إنشاء رابط التفعيل
            # =========================

            uid = urlsafe_base64_encode(
                force_bytes(user.pk)
            )

            token = email_verification_token.make_token(
                user
            )

            verification_url = request.build_absolute_uri(
                reverse(
                    "accounts:verify_email",
                    kwargs={
                        "uidb64": uid,
                        "token": token
                    }
                )
            )

            # =========================
            # إرسال الإيميل
            # =========================
            
            send_platform_email(
                subject="أهلاً بك في وصل",
                recipient=user.email,
                template_name="emails/welcome_email.html",
                context={
                    "user": user,
                    "verification_url": verification_url,
                }
            )


            messages.success(
                request,
                "تم إنشاء الحساب. تحقق من بريدك الإلكتروني لتفعيل الحساب 📩"
            )

            return redirect("accounts:login")

        else:
            messages.error(request, "حدث خطأ أثناء التسجيل، يرجى مراجعة البيانات.")

    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})




def verify_email_view(request, uidb64, token):

    try:

        uid = force_str(
            urlsafe_base64_decode(uidb64)
        )

        user = User.objects.get(pk=uid)

    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist
    ):

        user = None

    # =========================
    # تحقق من التوكن
    # =========================

    if (
        user is not None
        and
        email_verification_token.check_token(
            user,
            token
        )
    ):

        user.email_verified = True
        user.save()
        
        login(request, user)

        messages.success(
            request,
            "تم تفعيل بريدك الإلكتروني بنجاح ✅"
        )

        return redirect("main:index")

    # =========================
    # رابط غير صالح
    # =========================

    messages.error(
        request,
        "رابط التفعيل غير صالح أو منتهي."
    )

    return redirect("accounts:login")



def confirm_email_change_view(request, uidb64, token):

    try:

        uid = force_str(
            urlsafe_base64_decode(uidb64)
        )

        user = User.objects.get(pk=uid)

    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist
    ):

        user = None

    if (
        user is not None
        and
        user.pending_email
        and
        email_verification_token.check_token(
            user,
            token
        )
    ):

        user.email = user.pending_email
        user.pending_email = None
        user.email_verified = True

        user.save()

        messages.success(
            request,
            "تم تغيير البريد الإلكتروني بنجاح ✅"
        )

        return redirect("main:index")

    messages.error(
        request,
        "رابط تأكيد البريد الإلكتروني غير صالح أو منتهي."
    )

    return redirect("main:index")




@login_required
def resend_email_change_confirmation_view(request):

    if not request.user.pending_email:

        messages.error(
            request,
            "لا يوجد بريد إلكتروني بانتظار التأكيد."
        )

        return redirect("main:index")
    
    
    # =========================
    # منع إعادة الإرسال قبل 10 دقائق
    # =========================

    if request.user.last_email_change_confirmation_sent:

        time_passed = (
            timezone.now()
            -
            request.user.last_email_change_confirmation_sent
        )

        if time_passed < timedelta(minutes=10):

            remaining = (
                10
                -
                int(
                    time_passed.total_seconds()
                    // 60
                )
            )

            messages.warning(
                request,
                f"يمكنك إعادة إرسال رابط التأكيد بعد {remaining} دقيقة."
            )

            return redirect(
                request.META.get(
                    "HTTP_REFERER",
                    "main:index"
                )
            )

    send_email_change_confirmation(
        request.user,
        request
    )

    messages.success(
        request,
        "تم إعادة إرسال رابط التأكيد إلى البريد الإلكتروني الجديد 📩"
    )
    
    request.user.last_email_change_confirmation_sent = (
        timezone.now()
    )

    request.user.save(
        update_fields=[
            "last_email_change_confirmation_sent"
        ]
    )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "main:index"
        )
    )


@login_required
def cancel_email_change_view(request):

    request.user.pending_email = None

    request.user.save(
        update_fields=["pending_email"]
    )

    messages.success(
        request,
        "تم إلغاء طلب تغيير البريد الإلكتروني."
    )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "main:index"
        )
    )



@login_required
def verify_email_notice_view(request):

    # إذا فعل مسبقًا
    if request.user.email_verified:
        return redirect("main:index")

    return render(
        request,
        "accounts/verify_email_notice.html"
    )


@login_required
def resend_verification_email_view(request):

    # إذا فعل مسبقًا
    if request.user.email_verified:

        messages.success(
            request,
            "بريدك الإلكتروني مفعل بالفعل."
        )

        return redirect("main:index")
    
    # =========================
    # منع إعادة الإرسال قبل 10 دقائق
    # =========================

    if request.user.last_verification_email_sent:

        time_passed = (
            timezone.now()
            -
            request.user.last_verification_email_sent
        )

        if time_passed < timedelta(minutes=10):

            remaining = 10 - int(
                time_passed.total_seconds() // 60
            )

            messages.warning(
                request,
                f"يمكنك إعادة إرسال رابط التفعيل بعد {remaining} دقيقة."
            )

            return redirect(
                "accounts:verify_email_notice"
            )

    # =========================
    # إنشاء رابط جديد
    # =========================

    uid = urlsafe_base64_encode(
        force_bytes(request.user.pk)
    )

    token = email_verification_token.make_token(
        request.user
    )

    verification_url = request.build_absolute_uri(
        reverse(
            "accounts:verify_email",
            kwargs={
                "uidb64": uid,
                "token": token
            }
        )
    )

    # =========================
    # إرسال الإيميل
    # =========================

    send_platform_email(
        subject="إعادة إرسال رابط التفعيل",
        recipient=request.user.email,
        template_name="emails/welcome_email.html",
        context={
            "user": request.user,
            "verification_url": verification_url,
        }
    )
    
    request.user.last_verification_email_sent = timezone.now()

    request.user.save()

    messages.success(
        request,
        "تم إرسال رابط تفعيل جديد إلى بريدك الإلكتروني 📩"
    )

    return redirect(
        "accounts:verify_email_notice"
    )



class CustomPasswordResetView(PasswordResetView):

    template_name = "accounts/forgot_password.html"
    
    subject_template_name = (
        "emails/password_reset_subject.txt"
    )
    
    email_template_name = (
        "accounts/password_reset_email.html"
    )

    html_email_template_name = (
        "emails/password_reset_email.html"
    )

    success_url = (
        "/accounts/forgot-password/done/"
    )

    def form_valid(self, form):

        email = form.cleaned_data["email"]

        user = User.objects.filter(
            email=email
        ).first()

        if user:

            if user.last_password_reset_email_sent:

                time_passed = (
                    timezone.now()
                    -
                    user.last_password_reset_email_sent
                )

                if time_passed < timedelta(
                    minutes=10
                ):

                    remaining = (
                        10
                        -
                        int(
                            time_passed.total_seconds()
                            // 60
                        )
                    )

                    messages.warning(
                        self.request,
                        f"يمكنك طلب إعادة تعيين كلمة المرور بعد {remaining} دقيقة."
                    )

                    return redirect(
                        "accounts:forgot_password"
                    )

        response = super().form_valid(form)

        if user:

            user.last_password_reset_email_sent = (
                timezone.now()
            )

            user.save(
                update_fields=[
                    "last_password_reset_email_sent"
                ]
            )

        return response




def login_view(request):
    if request.user.is_authenticated:
        return redirect_authenticated_user(request.user)

    if request.method == "POST":
        email = request.POST.get("email")   
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:

            # المحظور ممنوع من استخدام المنصه 
            if user.status == "banned":
                messages.error(request, "حسابك محظور.")
                return redirect("accounts:login")
            
            # الحساب محذوف
            if user.status == "deleted":

                request.session["restore_user_id"] = user.id

                return redirect(
                    "accounts:restore_account"
                )
            
            # الحساب غير مفعل
            if not user.email_verified:

                login(request, user)

                messages.warning(
                    request,
                    "يرجى تفعيل بريدك الإلكتروني أولاً."
                )

                return redirect(
                    "accounts:verify_email_notice"
                )

            login(request, user)
            messages.success(request, "تم تسجيل الدخول بنجاح 👋")
            return redirect("main:index")

        else:
            messages.error(request, "البريد الإلكتروني أو كلمة المرور غير صحيحة.")

    return render(request, "accounts/login.html")


def restore_account_view(request):

    user_id = request.session.get(
        "restore_user_id"
    )

    if not user_id:

        return redirect(
            "accounts:login"
        )

    user = get_object_or_404(
        User,
        id=user_id,
        status="deleted"
    )

    if request.method == "POST":

        user.status = "active"
        user.deleted_at = None
        user.save()

        login(
            request,
            user
        )

        request.session.pop(
            "restore_user_id",
            None
        )

        messages.success(
            request,
            "تمت إعادة تنشيط حسابك بنجاح 🎉"
        )

        return redirect(
            "main:index"
        )

    return render(
        request,
        "accounts/restore_account.html"
    )




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
    driver_available_subscriptions = None

    # ===== Driver =====
    if user_obj.role == "driver":
        driver_profile = getattr(
            user_obj,
            "driver_profile",
            None
        )

        if driver_profile:
            driver_available_subscriptions = Subscription.objects.filter(
                driver=driver_profile,
                status="active",
                driver__user__status="active",
                driver__verification_status="approved",
                available_seats__gt=0,
                end_date__gte=timezone.localdate(),
            ).select_related(
                "driver__user",
                "driver__user__city",
            ).order_by("-created_at")

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
        "driver_available_subscriptions": driver_available_subscriptions,
        "reviews": reviews,
    }

    if request.user.is_authenticated:

        if request.user.role == "student":
            template_name = "student/public_profile.html"

        elif request.user.role == "driver":
            template_name = "driver/public_profile.html"

        elif request.user.role == "admin":
            template_name = "admin_panel/public_profile.html"

        else:
            template_name = "accounts/public_profile.html"

    else:
        template_name = "accounts/public_profile.html"

    return render(
        request,
        template_name,
        context
    )
