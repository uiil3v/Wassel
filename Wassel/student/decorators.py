from django.shortcuts import redirect
from django.contrib import messages


def student_profile_completed_required(view_func):

    def wrapper(request, *args, **kwargs):

        if request.user.role != "student":
            return redirect("main:index")

        profile = getattr(
            request.user,
            "student_profile",
            None
        )

        # إذا ما عنده بروفايل
        if not profile:

            messages.warning(
                request,
                "يرجى إكمال ملفك الشخصي أولاً."
            )

            return redirect("student:profile")

        required_fields = [
            profile.university_name,
            profile.gender,
            profile.neighborhood,
        ]

        # تحقق من البيانات المطلوبة
        if any(not field for field in required_fields):

            messages.warning(
                request,
                "يرجى إكمال بياناتك الشخصية أولاً."
            )

            return redirect("student:profile")

        return view_func(request, *args, **kwargs)

    return wrapper