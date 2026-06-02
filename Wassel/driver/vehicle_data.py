from datetime import date


VEHICLE_CATALOG = {
    "toyota": {
        "name": "تويوتا",
        "models": [
            "كامري",
            "كورولا",
            "يارس",
            "راف فور",
            "هايلاندر",
            "فورتشنر",
            "لاندكروزر",
            "برادو",
            "هايس فان",
            "كوستر حافلة صغيرة",
        ],
    },
    "hyundai": {
        "name": "هيونداي",
        "models": [
            "إلنترا",
            "أكسنت",
            "سوناتا",
            "أزيرا",
            "توسان",
            "سانتافي",
            "ستاريا فان",
            "H1 فان",
            "H350 حافلة صغيرة",
        ],
    },
    "kia": {
        "name": "كيا",
        "models": [
            "سيراتو",
            "ريو",
            "K5",
            "K8",
            "سبورتاج",
            "سورينتو",
            "كارنفال فان",
            "بيغاس",
        ],
    },
    "nissan": {
        "name": "نيسان",
        "models": [
            "صني",
            "ألتيما",
            "ماكسيما",
            "إكس تريل",
            "باترول",
            "أورفان فان",
            "NV350 فان",
        ],
    },
    "ford": {
        "name": "فورد",
        "models": [
            "توروس",
            "فوكس",
            "فيوجن",
            "إكسبلورر",
            "إكسبديشن",
            "ترانزيت فان",
        ],
    },
    "chevrolet": {
        "name": "شيفروليه",
        "models": [
            "ماليبو",
            "إمبالا",
            "كابتيفا",
            "تاهو",
            "سوبربان",
            "إكسبريس فان",
        ],
    },
    "honda": {
        "name": "هوندا",
        "models": [
            "سيفيك",
            "أكورد",
            "سيتي",
            "CR-V",
            "بايلوت",
            "أوديسي فان",
        ],
    },
    "mazda": {
        "name": "مازدا",
        "models": [
            "مازدا 3",
            "مازدا 6",
            "CX-5",
            "CX-9",
            "CX-30",
        ],
    },
    "mitsubishi": {
        "name": "ميتسوبيشي",
        "models": [
            "أتراج",
            "لانسر",
            "أوتلاندر",
            "باجيرو",
            "إكسباندر",
            "L300 فان",
            "روزا حافلة صغيرة",
        ],
    },
    "gmc": {
        "name": "جي إم سي",
        "models": [
            "تيرين",
            "أكاديا",
            "يوكون",
            "سافانا فان",
        ],
    },
    "mercedes": {
        "name": "مرسيدس",
        "models": [
            "C-Class",
            "E-Class",
            "GLC",
            "GLE",
            "V-Class فان",
            "سبرنتر فان",
        ],
    },
    "changan": {
        "name": "شانجان",
        "models": [
            "السفن",
            "إيدو",
            "UNI-T",
            "UNI-K",
            "CS35",
            "CS75",
        ],
    },
    "geely": {
        "name": "جيلي",
        "models": [
            "إمجراند",
            "كولراي",
            "أزكارا",
            "مونجارو",
            "توجيلا",
        ],
    },
    "mg": {
        "name": "إم جي",
        "models": [
            "MG 5",
            "MG 6",
            "MG GT",
            "ZS",
            "HS",
            "RX8",
        ],
    },
    "other": {
        "name": "أخرى",
        "models": [
            "أخرى",
        ],
    },
}


VEHICLE_MAKE_CHOICES = tuple(
    (key, item["name"])
    for key, item in VEHICLE_CATALOG.items()
)


def vehicle_year_choices():
    current_year = date.today().year + 1
    return tuple((year, str(year)) for year in range(current_year, 1994, -1))


def vehicle_models_for_make(make):
    return VEHICLE_CATALOG.get(make, {}).get("models", [])


def vehicle_make_name(make):
    return VEHICLE_CATALOG.get(make, {}).get("name", make or "")
