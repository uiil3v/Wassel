from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from .services import deposit_wallet, withdraw_wallet



@login_required
def wallet_view(request):

    wallet = request.user.wallet

    is_driver_blocked = False

    # 🔥 تحقق إذا السائق غير معتمد
    if request.user.role == "driver":
        profile = getattr(request.user, "driver_profile", None)

        if profile and profile.verification_status != "approved":
            is_driver_blocked = True

    # ===============================
    # Handle Deposit / Withdraw
    # ===============================
    if request.method == "POST":

        if is_driver_blocked:
            messages.error(request, "لا يمكنك إجراء عمليات مالية قبل توثيق حسابك.")
            return redirect("payment:wallet")

        action = request.POST.get("action")
        amount = request.POST.get("amount")

        try:
            if action == "deposit":
                deposit_wallet(request.user, amount)
                messages.success(request, "تم شحن الرصيد بنجاح.")

            elif action == "withdraw":
                withdraw_wallet(request.user, amount)
                messages.success(request, "تم سحب المبلغ بنجاح.")

        except ValidationError as e:
            messages.error(request, str(e))

        return redirect("payment:wallet")

    transactions = wallet.transactions.order_by("-created_at")

    if request.user.role == "driver":
        template = "payment/wallet_driver.html"
    else:
        template = "payment/wallet_student.html"

    context = {
        "wallet": wallet,
        "transactions": transactions,
        "is_driver_blocked": is_driver_blocked,  # 🔥 مهم
    }

    return render(request, template, context)
