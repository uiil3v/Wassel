from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from subscriptions.models import SubscriptionRequest
from .models import Review
from .forms import ReviewForm
from django.utils import timezone


@login_required
def create_review(request, request_id):

    subscription_request = get_object_or_404(
        SubscriptionRequest,
        id=request_id
    )

    # =========================
    # تحديد الطرفين
    # =========================

    student_user = subscription_request.student.user
    driver_user = subscription_request.subscription.driver.user

    # =========================
    # لازم يكون أحد الطرفين
    # =========================

    if request.user not in [student_user, driver_user]:

        messages.error(request, "ليس لديك صلاحية لإضافة تقييم.")
        return redirect("main:index")

    # =========================
    # تحديد الشخص المقيم
    # =========================

    if request.user == student_user:
        reviewed_user = driver_user

    else:
        reviewed_user = student_user

    # =========================
    # منع التقييم المكرر
    # =========================

    existing_review = Review.objects.filter(
        reviewer=request.user,
        subscription_request=subscription_request
    ).exists()

    if existing_review:

        messages.warning(request, "لقد قمت بإضافة تقييم مسبقًا.")
        return redirect("main:index")

    # =========================
    # إنشاء التقييم
    # =========================

    if request.method == "POST":

        form = ReviewForm(request.POST)

        if form.is_valid():

            review = form.save(commit=False)

            review.reviewer = request.user
            review.reviewed_user = reviewed_user
            review.subscription_request = subscription_request

            review.save()

            messages.success(request, "تم إضافة التقييم بنجاح ⭐")

            return redirect("main:index")

    else:
        form = ReviewForm()

    context = {
        "form": form,
        "subscription_request": subscription_request,
        "reviewed_user": reviewed_user,
    }

    return render(request, "reviews/create_review.html", context)



@login_required
def edit_review(request, review_id):

    review = get_object_or_404(
        Review,
        id=review_id,
        reviewer=request.user
    )

    # انتهت مدة التعديل
    if not review.can_edit:

        messages.error(
            request,
            "انتهت مدة تعديل التقييم."
        )

        return redirect(
            "accounts:public_profile",
            user_id=review.reviewed_user.id
        )

    if request.method == "POST":

        form = ReviewForm(
            request.POST,
            instance=review
        )

        if form.is_valid():

            updated_review = form.save(commit=False)

            # الطالب فقط يقدر يخفي اسمه
            if request.user.role != "student":
                updated_review.is_anonymous = False

            updated_review.updated_at = timezone.now()

            updated_review.save()

            messages.success(
                request,
                "تم تعديل التقييم بنجاح."
            )

            return redirect(
                "accounts:public_profile",
                user_id=review.reviewed_user.id
            )

    else:

        form = ReviewForm(instance=review)

    context = {
        "form": form,
        "review": review,
        "reviewed_user": review.reviewed_user,
        "subscription_request": review.subscription_request,
        "is_edit": True,
    }

    return render(
        request,
        "reviews/create_review.html",
        context
    )


@login_required
def delete_review(request, review_id):

    review = get_object_or_404(
        Review,
        id=review_id,
        reviewer=request.user
    )

    reviewed_user_id = review.reviewed_user.id

    if request.method == "POST":

        review.delete()

        messages.success(
            request,
            "تم حذف التقييم."
        )

    return redirect(
        "accounts:public_profile",
        user_id=reviewed_user_id
    )