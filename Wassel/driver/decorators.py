from django.shortcuts import redirect
from django.contrib import messages


def driver_verified_required(view_func):
    def wrapper(request, *args, **kwargs):

        if request.user.role != "driver":
            return redirect("main:index")

        profile = getattr(request.user, "driver_profile", None)

        if not profile:
            messages.warning(request, "يرجى إكمال بياناتك أولاً.")
            return redirect("driver:profile")

        if not profile.is_profile_complete:
            profile.enforce_incomplete_status()
            messages.warning(request, "يرجى إكمال بيانات الحساب والمركبة والمستندات أولاً.")
            return redirect("driver:profile")

        if profile.verification_status != "approved":
            messages.warning(request, "حسابك غير معتمد حالياً.")
            return redirect("driver:profile")

        return view_func(request, *args, **kwargs)

    return wrapper
