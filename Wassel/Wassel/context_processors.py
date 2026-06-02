def student_addressing(request):
    user = getattr(request, "user", None)
    gender = None

    if user and user.is_authenticated and getattr(user, "role", None) == "student":
        profile = getattr(user, "student_profile", None)
        gender = getattr(profile, "gender", None)

    is_female = gender == "female"

    return {
        "student_address": {
            "is_female": is_female,
            "role": "طالبة" if is_female else "طالب",
            "role_with_article": "الطالبة" if is_female else "الطالب",
            "university_role": "طالبة جامعية" if is_female else "طالب جامعي",
            "dashboard_title": "لوحة الطالبة" if is_female else "لوحة الطالب",
            "welcome": "مرحباً بكِ" if is_female else "مرحباً بك",
            "follow": "تابعي" if is_female else "تابع",
            "review": "راجعي" if is_female else "راجع",
            "enter": "ادخلي" if is_female else "ادخل",
            "start": "ابدئي" if is_female else "ابدأ",
            "browse": "استعرضي" if is_female else "استعرض",
            "choose": "اختاري" if is_female else "اختر",
            "send": "أرسلي" if is_female else "أرسل",
            "select": "حددي" if is_female else "حدد",
            "make": "اجعلي" if is_female else "اجعل",
            "look": "اطلعي" if is_female else "اطلع",
            "update": "حدّثي" if is_female else "حدّث",
            "rate": "قيّمي" if is_female else "قيّم",
            "cancel": "ألغِي" if is_female else "ألغِ",
            "charge": "اشحني" if is_female else "اشحن",
            "withdraw": "اسحبي" if is_female else "اسحب",
            "active_request_notice": (
                "لديكِ طلب أو اشتراك قائم بالفعل، لذلك لن تتمكني من التقديم على اشتراك جديد حالياً."
                if is_female
                else "لديك طلب أو اشتراك قائم بالفعل، لذلك لن تتمكن من التقديم على اشتراك جديد حالياً."
            ),
        }
    }
