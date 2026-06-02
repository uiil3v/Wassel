from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone

from location.models import City
from subscriptions.models import Subscription, SubscriptionRequest
from driver.models import DriverProfile

def index(request):
    return render(request, "main/index.html")

def about(request):
    return render(request, "main/about.html")

def privacy_policy(request):
    return render(request, "main/privacy_policy.html")


def browse_drivers(request):
    search_query = request.GET.get("search", "").strip()
    city_id = request.GET.get("city", "").strip()
    gender = request.GET.get("gender", "").strip()
    has_subscriptions = request.GET.get("has_subscriptions", "").strip()
    sort = request.GET.get("sort", "").strip()

    cities = City.objects.filter(is_active=True)
    today = timezone.localdate()

    drivers = DriverProfile.objects.filter(
        user__status="active",
        verification_status="approved",
    ).select_related(
        "user",
        "user__city",
    ).annotate(
        active_subscriptions_count=Count(
            "subscriptions",
            filter=Q(
                subscriptions__status="active",
                subscriptions__available_seats__gt=0,
                subscriptions__end_date__gte=today,
            ),
            distinct=True,
        )
    )

    if request.user.is_authenticated and request.user.role == "student":
        drivers = drivers.filter(user__city=request.user.city)
        selected_city = str(request.user.city_id or "")
    else:
        selected_city = city_id
        if city_id:
            drivers = drivers.filter(user__city_id=city_id)

    if search_query:
        drivers = drivers.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__city__name_ar__icontains=search_query) |
            Q(vehicle_make__icontains=search_query) |
            Q(vehicle_model__icontains=search_query) |
            Q(vehicle_year__icontains=search_query)
        )

    if gender in ["male", "female"]:
        drivers = drivers.filter(gender=gender)

    if has_subscriptions == "yes":
        drivers = drivers.filter(active_subscriptions_count__gt=0)

    if sort == "rating":
        drivers = drivers.order_by("-average_rating", "-reviews_count", "user__first_name")
    elif sort == "subscriptions":
        drivers = drivers.order_by("-active_subscriptions_count", "user__first_name")
    elif sort == "newest":
        drivers = drivers.order_by("-submitted_at")
    else:
        drivers = drivers.order_by("user__first_name", "user__last_name")

    context = {
        "drivers": drivers,
        "cities": cities,
        "selected_city": selected_city,
        "search_query": search_query,
        "gender": gender,
        "has_subscriptions": has_subscriptions,
        "sort": sort,
        "results_count": drivers.count(),
    }

    return render(
        request,
        "main/drivers_browse.html",
        context
    )


def browse_subscriptions(request):
    search_query = request.GET.get("search", "").strip()
    city_id = request.GET.get("city", "").strip()
    duration = request.GET.get("duration", "")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    sort = request.GET.get("sort", "")

    cities = City.objects.filter(is_active=True)

    subscriptions = Subscription.objects.filter(
        status="active",
        driver__user__status="active",
        driver__verification_status="approved",
        available_seats__gt=0,
        end_date__gte=timezone.localdate(),
    ).select_related(
        "driver__user",
        "driver__user__city",
    )

    if request.user.is_authenticated and request.user.role == "student":
        subscriptions = subscriptions.filter(
            driver__user__city=request.user.city
        )
        selected_city = str(request.user.city_id or "")
    else:
        selected_city = city_id
        if city_id:
            subscriptions = subscriptions.filter(
                driver__user__city_id=city_id
            )

    if search_query:
        subscriptions = subscriptions.filter(
            Q(neighborhood__icontains=search_query) |
            Q(driver__user__first_name__icontains=search_query) |
            Q(driver__user__last_name__icontains=search_query)
        )

    if duration:
        subscriptions = subscriptions.filter(duration=duration)

    if min_price:
        try:
            subscriptions = subscriptions.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            subscriptions = subscriptions.filter(price__lte=float(max_price))
        except ValueError:
            pass

    if sort == "price_asc":
        subscriptions = subscriptions.order_by("price")
    elif sort == "price_desc":
        subscriptions = subscriptions.order_by("-price")
    elif sort == "seats":
        subscriptions = subscriptions.order_by("-available_seats")
    else:
        subscriptions = subscriptions.order_by("-created_at")

    has_active_request = False
    student_profile = getattr(request.user, "student_profile", None)
    if request.user.is_authenticated and request.user.role == "student" and student_profile:
        today = timezone.localdate()
        has_active_request = student_profile.subscription_requests.filter(
            Q(status="pending") |
            Q(status="approved", subscription__end_date__gte=today)
        ).exists()

    context = {
        "subscriptions": subscriptions,
        "cities": cities,
        "selected_city": selected_city,
        "search_query": search_query,
        "duration": duration,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort,
        "results_count": subscriptions.count(),
        "has_active_request": has_active_request,
        "is_public_browse": True,
    }

    return render(
        request,
        "main/subscriptions_browse.html",
        context
    )


def public_subscription_detail(request, sub_id):
    subscription = get_object_or_404(
        Subscription.objects.select_related(
            "driver__user",
            "driver__user__city",
        ),
        id=sub_id,
        status="active",
        driver__user__status="active",
        driver__verification_status="approved",
        end_date__gte=timezone.localdate(),
    )

    has_active_request = False
    student_profile = getattr(request.user, "student_profile", None)
    if request.user.is_authenticated and request.user.role == "student" and student_profile:
        today = timezone.localdate()
        has_active_request = student_profile.subscription_requests.filter(
            Q(status="pending") |
            Q(status="approved", subscription__end_date__gte=today)
        ).exists()

    context = {
        "subscription": subscription,
        "has_active_request": has_active_request,
        "can_accept_requests": subscription.can_accept_requests(),
    }

    return render(
        request,
        "main/subscription_public_detail.html",
        context
    )

