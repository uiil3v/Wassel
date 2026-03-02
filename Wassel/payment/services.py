from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Transaction, PlatformEarning, Wallet
from django.utils import timezone


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

    start_date = subscription.start_date
    end_date = subscription.end_date

    # -------------------------
    # الحالة 1: قبل البداية
    # -------------------------
    if today < start_date:

        refund_amount = driver_received  # يرجع 95%

    else:
        # -------------------------
        # الحالة 2: بعد البداية (نسبي)
        # -------------------------

        total_days = (end_date - start_date).days

        # حماية من القسمة على صفر
        if total_days <= 0:
            refund_amount = Decimal("0.00")
        else:
            used_days = (today - start_date).days

            if used_days < 0:
                used_days = 0

            if used_days >= total_days:
                refund_amount = Decimal("0.00")
            else:
                remaining_days = total_days - used_days
                ratio = Decimal(remaining_days) / Decimal(total_days)
                refund_amount = driver_received * ratio

    # 🔹 تأكد أن السائق يملك الرصيد الكافي
    if driver_wallet.balance < refund_amount:
        raise ValidationError("رصيد السائق غير كافي لإتمام الاسترجاع.")

    # 🔹 خصم من السائق
    driver_wallet.balance -= refund_amount
    driver_wallet.save()

    Transaction.objects.create(
        wallet=driver_wallet,
        subscription_request=subscription_request,
        type="withdraw",
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
    
    
    
    
@transaction.atomic
def withdraw_wallet(user, amount):

    amount = Decimal(amount)

    if amount <= 0:
        raise ValidationError("المبلغ غير صالح.")

    wallet = user.wallet

    if wallet.balance < amount:
        raise ValidationError("رصيدك غير كافي.")

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
    
