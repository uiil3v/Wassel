from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from .services import deposit_wallet, withdraw_wallet

from payment.services import calculate_driver_withdrawable
from django.db.models import Sum
from decimal import Decimal

import csv
from django.http import HttpResponse

from notifications.utils import send_notification

from Wassel.email_utils import (
    send_wallet_deposit_email,
    send_wallet_withdraw_email,
)





@login_required
def wallet_view(request):

    wallet = request.user.wallet
    
    # 🔥 منع الطالب إذا ماكمل بياناته
    if request.user.role == "student":

        profile = getattr(
            request.user,
            "student_profile",
            None
        )

        required_fields = [
            profile.university_name,
            profile.gender,
            profile.neighborhood,
        ]

        if not profile or any(not field for field in required_fields):

            messages.warning(
                request,
                "يرجى إكمال ملفك الشخصي أولاً."
            )

            return redirect("student:profile")

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
                deposit_wallet(
                    request.user,
                    amount
                )

                send_notification(
                    title="تم شحن المحفظة",
                    message=f"تم إضافة {amount} ريال إلى محفظتك بنجاح.",
                    target="user",
                    user=request.user,
                    notification_type="system"
                )

                send_wallet_deposit_email(
                    request.user,
                    amount
                )

                messages.success(
                    request,
                    "تم شحن الرصيد بنجاح."
                )

            elif action == "withdraw":

                withdraw_wallet(
                    request.user,
                    amount
                )

                send_notification(
                    title="تم سحب مبلغ من المحفظة",
                    message=f"تم سحب {amount} ريال من محفظتك بنجاح.",
                    target="user",
                    user=request.user,
                    notification_type="system"
                )

                send_wallet_withdraw_email(
                    request.user,
                    amount
                )

                messages.success(
                    request,
                    "تم سحب المبلغ بنجاح."
                )

        except ValidationError as e:
            messages.error(request, str(e))

        return redirect("payment:wallet")

    transactions = wallet.transactions.order_by("-created_at")

    if request.user.role == "driver":
        template = "payment/wallet_driver.html"
    else:
        template = "payment/wallet_student.html"
    
    available_to_withdraw = Decimal("0.00")
    

    # 🔥 نحسب فقط للسائق
    if request.user.role == "driver" and not is_driver_blocked:
        
        

        withdrawable = calculate_driver_withdrawable(request.user)

        already_withdrawn = wallet.transactions.filter(
            type="withdraw"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        available_to_withdraw = max(
            withdrawable - already_withdrawn,
            Decimal("0.00")
        )
    
    frozen_amount = max(wallet.balance - available_to_withdraw, Decimal("0.00"))
    wallet_total = wallet.balance + wallet.frozen_balance

    context = {
        "wallet": wallet,
        "transactions": transactions,
        "is_driver_blocked": is_driver_blocked,  # 🔥 مهم
        "available_to_withdraw": available_to_withdraw,  # 🔥 الجديد
        "frozen_amount": frozen_amount,  # 🔥 الجديد
        "wallet_total": wallet_total,
    }

    return render(request, template, context)



@login_required
def export_wallet_csv(request):

    wallet = request.user.wallet

    transactions = wallet.transactions.order_by(
        "-created_at"
    )

    response = HttpResponse(
        content_type="text/csv; charset=utf-8"
    )

    response.write('\ufeff')

    response[
        "Content-Disposition"
    ] = 'attachment; filename="wallet_transactions.csv"'

    writer = csv.writer(response)

    # Header
    writer.writerow([
        "Type",
        "Amount",
        "Status",
        "Date",
    ])

    # Rows
    for tx in transactions:

        writer.writerow([
            tx.get_type_display(),
            f"{tx.amount:.2f}",
            tx.get_status_display(),
            tx.created_at.strftime("%d/%m/%Y %H:%M"),
        ])

    return response
