from django.db.models import Avg

from driver.models import DriverProfile
from student.models import StudentProfile


def update_user_rating(user):

    reviews = user.received_reviews.all()

    reviews_count = reviews.count()

    average_rating = reviews.aggregate(
        avg=Avg("rating")
    )["avg"] or 0

    # =========================
    # Driver
    # =========================

    if user.role == "driver":

        profile = DriverProfile.objects.get(user=user)

        profile.average_rating = round(average_rating, 2)
        profile.reviews_count = reviews_count

        profile.save()

    # =========================
    # Student
    # =========================

    elif user.role == "student":

        profile = StudentProfile.objects.get(user=user)

        profile.average_rating = round(average_rating, 2)
        profile.reviews_count = reviews_count

        profile.save()