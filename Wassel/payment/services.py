from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Transaction, PlatformEarning, Wallet
from django.utils import timezone
from subscriptions.models import SubscriptionRequest

# ==========================================
# Freeze Amount عند إنشاء الطلب
# ==========================================

@transaction.atomic
def freeze_student_amount(student_user, subscription_request):

    # 🔥 تأكد أن عنده Wallet (لو ما عنده ننشئ له)
    wallet, created = Wallet.objects.get_or_create(user=student_user)

    amount = subscription_request.subscription.price

    # تحقق من الرصيد
    if wallet.balance < amount:
        raise ValidationError("رصيدك غير كافي لإتمام الطلب.")

    # خصم من الرصيد
    wallet.balance -= amount
    wallet.frozen_balance += amount
    wallet.save()

    # تسجيل العملية
    Transaction.objects.create(
        wallet=wallet,
        subscription_request=subscription_request,
        type="freeze",
        amount=amount,
        status="completed"
    )


# ==========================================
# تحويل المبلغ عند الموافقة + العمولة
# ==========================================

@transaction.atomic
def approve_subscription_payment(subscription_request):

    # 🔥 تأكد أن المحافظ موجودة
    student_wallet, _ = Wallet.objects.get_or_create(
        user=subscription_request.student.user
    )

    driver_wallet, _ = Wallet.objects.get_or_create(
        user=subscription_request.subscription.driver.user
    )

    amount = subscription_request.subscription.price
    commission_rate = Decimal("0.05")

    commission = amount * commission_rate
    driver_amount = amount - commission

    # تحقق أن المبلغ مجمد فعلاً
    if student_wallet.frozen_balance < amount:
        raise ValidationError("لا يوجد مبلغ مجمد كافي.")

    # فك التجميد
    student_wallet.frozen_balance -= amount
    student_wallet.save()

    Transaction.objects.create(
        wallet=student_wallet,
        subscription_request=subscription_request,
        type="release",
        amount=amount,
        status="completed"
    )

    # تحويل 95% للسائق
    driver_wallet.balance += driver_amount
    driver_wallet.save()

    Transaction.objects.create(
        wallet=driver_wallet,
        subscription_request=subscription_request,
        type="deposit",
        amount=driver_amount,
        commission_amount=commission,
        status="completed"
    )

    # تسجيل عمولة النظام
    commission_tx = Transaction.objects.create(
        wallet=student_wallet,  # للتوثيق فقط
        subscription_request=subscription_request,
        type="commission",
        amount=commission,
        status="completed"
    )

    PlatformEarning.objects.create(
        transaction=commission_tx,
        amount=commission
    )
    
    
@transaction.atomic
def refund_frozen_amount(subscription_request):

    student_wallet = subscription_request.student.user.wallet
    amount = subscription_request.subscription.price

    # تحقق أن فيه مبلغ مجمد
    if student_wallet.frozen_balance < amount:
        raise ValidationError("لا يوجد مبلغ مجمد كافي للاسترجاع.")

    # فك التجميد
    student_wallet.frozen_balance -= amount
    student_wallet.balance += amount
    student_wallet.save()

    # تسجيل العملية
    Transaction.objects.create(
        wallet=student_wallet,
        subscription_request=subscription_request,
        type="refund",
        amount=amount,
        status="completed"
    )
    
    
    
    
@transaction.atomic
def refund_after_approval(subscription_request):

    # 🔴 حماية ضد التكرار أو الطلبات غير المعتمدة
    if subscription_request.status != "approved":
        raise ValidationError("لا يمكن استرجاع طلب غير معتمد.")

    student_wallet, _ = Wallet.objects.get_or_create(
        user=subscription_request.student.user
    )

    driver_wallet, _ = Wallet.objects.get_or_create(
        user=subscription_request.subscription.driver.user
    )

    subscription = subscription_request.subscription

    total_amount = subscription.price
    commission_rate = Decimal("0.05")

    commission = total_amount * commission_rate
    driver_received = total_amount - commission  # 95%

    today = timezone.now().date()
    
    if not subscription_request.joined_at:
        raise ValidationError("لا يوجد تاريخ بداية للطالب.")

    start_date = subscription_request.joined_at.date()
    end_date = subscription.end_date
    
    remaining_days = (end_date - today).days

    # ❌ منع بعد النهاية
    if remaining_days <= 0:
        raise ValidationError("لا يمكن إلغاء الاشتراك بعد انتهائه.")



    # -------------------------
    # الحالة 1: قبل البداية
    # -------------------------
    if today < start_date:

        refund_amount = driver_received  # يرجع 95%

    else:
        # -------------------------
        # الحالة 2: بعد البداية (نسبي)
        # -------------------------

        total_days = (end_date - start_date).days + 1

        # حماية من القسمة على صفر
        if total_days <= 0:
            refund_amount = Decimal("0.00")
        else:
            used_days = (today - start_date).days + 1

            if used_days < 0:
                used_days = 0

            if used_days >= total_days:
                refund_amount = Decimal("0.00")
            else:
                remaining_days_after_use = total_days - used_days
                ratio = Decimal(remaining_days_after_use) / Decimal(total_days)
                remaining_ratio = Decimal(remaining_days_after_use) / Decimal(total_days)
                
                if remaining_ratio < Decimal("0.1"):
                    refund_amount = Decimal("0.00")
                else:
                    refund_amount = (driver_received * ratio).quantize(Decimal("0.01"))



    # 🔹 تأكد أن السائق يملك الرصيد الكافي
    if driver_wallet.balance < refund_amount:
        raise ValidationError("رصيد السائق غير كافي لإتمام الاسترجاع.")

    # 🔹 خصم من السائق
    driver_wallet.balance -= refund_amount
    driver_wallet.save()

    Transaction.objects.create(
        wallet=driver_wallet,
        subscription_request=subscription_request,
        type="refund",
        amount=refund_amount,
        status="completed"
    )

    # 🔹 إضافة للطالب
    student_wallet.balance += refund_amount
    student_wallet.save()

    Transaction.objects.create(
        wallet=student_wallet,
        subscription_request=subscription_request,
        type="refund",
        amount=refund_amount,
        status="completed"
    )

    # 🔹 تحديث حالة الطلب
    subscription_request.status = "cancelled"
    subscription_request.save()

    # 🔹 إعادة المقعد
    subscription.increase_seat()



    
    
def calculate_driver_withdrawable(driver_user):

    today = timezone.now().date()

    requests = SubscriptionRequest.objects.filter(
        subscription__driver__user=driver_user,
        status__in=["approved", "cancelled"]
    )

    total_withdrawable = Decimal("0.00")

    for req in requests:

        if not req.joined_at:
            continue

        start_date = req.joined_at.date()
        end_date = req.subscription.end_date

        total_amount = req.price_snapshot
        commission = total_amount * Decimal("0.05")
        driver_amount = total_amount - commission

        # 🔥 إذا ملغي نحسب فقط الجزء المستخدم
        if req.status == "cancelled":

            cancel_date = req.decision_date.date() if req.decision_date else today

            total_days = (end_date - start_date).days + 1
            used_days = (cancel_date - start_date).days + 1

            if total_days <= 0:
                continue

            if used_days < 0:
                used_days = 0

            if used_days > total_days:
                used_days = total_days

            ratio_used = Decimal(used_days) / Decimal(total_days)

        else:
            # approved (نفس القديم)
            if today >= end_date:
                ratio_used = Decimal("1.0")
            else:
                total_days = (end_date - start_date).days + 1
                used_days = (today - start_date).days + 1

                if total_days <= 0:
                    continue

                if used_days < 0:
                    used_days = 0

                if used_days > total_days:
                    used_days = total_days

                ratio_used = Decimal(used_days) / Decimal(total_days)

        withdrawable = (driver_amount * ratio_used).quantize(Decimal("0.01"))

        total_withdrawable += withdrawable

    return total_withdrawable


from django.db.models import Sum
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction

@transaction.atomic
def withdraw_wallet(user, amount):

    amount = Decimal(amount)

    # 🔴 تحقق من صحة المبلغ
    if amount <= 0:
        raise ValidationError("المبلغ غير صالح.")

    # 🔴 تأكد من وجود المحفظة
    wallet = user.wallet

    # 🔥 احسب المبلغ المسموح سحبه (حسب التقدم)
    withdrawable = calculate_driver_withdrawable(user)

    # 🔥 احسب كم سحب سابقًا
    already_withdrawn = wallet.transactions.filter(
        type="withdraw"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # 🔥 المبلغ المتبقي للسحب
    available_to_withdraw = max(
        withdrawable - already_withdrawn,
        Decimal("0.00")
    )

    # ❌ منع سحب أكثر من المسموح
    if amount > available_to_withdraw:
        raise ValidationError("لا يمكنك سحب هذا المبلغ حالياً.")

    # ❌ منع سحب أكثر من الرصيد الفعلي
    if wallet.balance < amount:
        raise ValidationError("رصيدك غير كافي.")

    # ✅ تنفيذ السحب
    wallet.balance -= amount
    wallet.save()

    Transaction.objects.create(
        wallet=wallet,
        type="withdraw",
        amount=amount,
        status="completed"
    )
  
  
  
   
    
@transaction.atomic
def deposit_wallet(user, amount):

    amount = Decimal(amount)

    if amount <= 0:
        raise ValidationError("المبلغ غير صالح.")

    wallet, _ = Wallet.objects.get_or_create(user=user)

    wallet.balance += amount
    wallet.save()

    Transaction.objects.create(
        wallet=wallet,
        type="deposit",
        amount=amount,
        status="completed"
    )
    
