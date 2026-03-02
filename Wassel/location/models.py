from django.db import models


class City(models.Model):
    # الاسم المعروض للمستخدم (بالعربي)
    name_ar = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="اسم المدينة بالعربي"
    )

    # الاسم الداخلي (إنجليزي) للاستخدام التقني
    name_en = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="اسم المدينة بالإنجليزي"
    )

    # slug للروابط مستقبلاً (اختياري لكن احترافي)
    slug = models.SlugField(
        unique=True,
        verbose_name="المعرف (slug)"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="مفعلة؟"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مدينة"
        verbose_name_plural = "المدن"
        ordering = ["name_ar"]

    def __str__(self):
        # هذا اللي يظهر في الـ dropdown
        return self.name_ar