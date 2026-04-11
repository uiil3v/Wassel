from django.shortcuts import redirect

def admin_required(levels=[1]):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):

            # لازم يكون admin
            if request.user.role != "admin":
                return redirect("main:index")

            # تحقق من المستوى
            if request.user.admin_level not in levels:
                return redirect("main:index")

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator