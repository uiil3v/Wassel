import secrets
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from Wassel.email_utils import send_support_ticket_verification_email



from .models import (
    SupportTicket,
    SupportMessage,
)


from .forms import (
    SupportTicketForm,
    TicketTrackingForm,
    SupportTicketCodeForm,
    SupportMessageForm,
)


SUPPORT_TICKET_VERIFY_SESSION_KEY = "support_ticket_verify"
SUPPORT_TICKET_ACCESS_SESSION_KEY = "support_ticket_access"
SUPPORT_TICKET_CODE_MINUTES = 10
SUPPORT_TICKET_ACCESS_MINUTES = 30
SUPPORT_TICKET_MAX_ATTEMPTS = 5


def _build_support_code():

    return str(
        secrets.randbelow(900000) + 100000
    )


def _ticket_access_expires_at(minutes):

    return (
        timezone.now() + timedelta(minutes=minutes)
    ).isoformat()


def _session_datetime(value):

    if not value:

        return None

    parsed = parse_datetime(value)

    if parsed and timezone.is_naive(parsed):

        parsed = timezone.make_aware(parsed)

    return parsed


def _grant_ticket_access(request, ticket):

    access_map = request.session.get(
        SUPPORT_TICKET_ACCESS_SESSION_KEY,
        {}
    )

    access_map[str(ticket.id)] = _ticket_access_expires_at(
        SUPPORT_TICKET_ACCESS_MINUTES
    )

    request.session[
        SUPPORT_TICKET_ACCESS_SESSION_KEY
    ] = access_map

    request.session.modified = True


def _has_ticket_access(request, ticket):

    if (
        request.user.is_authenticated
        and ticket.user_id == request.user.id
    ):

        return True

    access_map = request.session.get(
        SUPPORT_TICKET_ACCESS_SESSION_KEY,
        {}
    )

    expires_at = _session_datetime(
        access_map.get(str(ticket.id))
    )

    if expires_at and expires_at > timezone.now():

        return True

    if str(ticket.id) in access_map:

        access_map.pop(str(ticket.id), None)

        request.session[
            SUPPORT_TICKET_ACCESS_SESSION_KEY
        ] = access_map

        request.session.modified = True

    return False


def contact_view(request):

    if request.method == "POST":

        form = SupportTicketForm(
            request.POST,
            request.FILES,
            user=request.user
        )

        if form.is_valid():

            # =========================
            # منع التذاكر المفتوحة المتعددة
            # =========================

            if request.user.is_authenticated:

                existing_ticket = (
                    request.user.support_tickets.filter(
                        status__in=[
                            "new",
                            "in_progress",
                            "waiting_user",
                        ]
                    ).first()
                )

            else:

                existing_ticket = (
                    SupportTicket.objects.filter(
                        email=form.cleaned_data["email"],
                        phone=form.cleaned_data["phone"],
                        status__in=[
                            "new",
                            "in_progress",
                            "waiting_user",
                        ]
                    ).first()
                )

            if existing_ticket:

                messages.error(
                    request,
                    (
                        f"لديك تذكرة مفتوحة بالفعل "
                        f"برقم {existing_ticket.ticket_number}. "
                        f"يرجى انتظار معالجة الطلب الحالي قبل إنشاء تذكرة جديدة."
                    )
                )

                return redirect(
                    "support:contact"
                )

            # =========================
            # إنشاء التذكرة
            # =========================

            ticket = form.save(commit=False)

            if request.user.is_authenticated:

                ticket.user = request.user

                # إجبار استخدام بيانات الحساب الفعلية
                ticket.name = request.user.full_name
                ticket.email = request.user.email
                ticket.phone = request.user.phone

            ticket.save()
            
            # =========================
            # أول رسالة بالمحادثة
            # =========================

            SupportMessage.objects.create(

                ticket=ticket,

                sender=request.user
                if request.user.is_authenticated
                else None,

                sender_type=(
                    "user"
                    if request.user.is_authenticated
                    else "guest"
                ),

                message=ticket.message,
            )

            messages.success(
                request,
                (
                    f"تم إرسال طلبك بنجاح. "
                    f"رقم التذكرة: {ticket.ticket_number}"
                )
            )

            return redirect(
                "support:contact"
            )

    else:

        initial = {}

        # =========================
        # تعبئة تلقائية للمستخدم المسجل
        # =========================

        if request.user.is_authenticated:

            initial = {
                "name": request.user.full_name,
                "email": request.user.email,
                "phone": request.user.phone,
            }

        form = SupportTicketForm(
            initial=initial,
            user=request.user
        )

    context = {
        "form": form
    }

    return render(
        request,
        "support/contact.html",
        context
    )
    
    
def track_ticket(request):

    if request.method == "POST":

        form = TicketTrackingForm(
            request.POST
        )

        if form.is_valid():

            ticket_number = form.cleaned_data[
                "ticket_number"
            ]

            email = form.cleaned_data[
                "email"
            ]

            ticket = SupportTicket.objects.filter(
                ticket_number=ticket_number,
                email__iexact=email
            ).first()

            if ticket:

                code = _build_support_code()

                request.session[
                    SUPPORT_TICKET_VERIFY_SESSION_KEY
                ] = {
                    "ticket_id": ticket.id,
                    "code_hash": make_password(code),
                    "expires_at": _ticket_access_expires_at(
                        SUPPORT_TICKET_CODE_MINUTES
                    ),
                    "attempts": 0,
                }

                send_support_ticket_verification_email(
                    ticket,
                    code
                )

                messages.success(
                    request,
                    "تم إرسال رمز التحقق إلى بريدك الإلكتروني."
                )

                return redirect(
                    "support:verify_ticket_code"
                )

            messages.warning(
                request,
                "إذا كانت البيانات صحيحة فسيتم إرسال رمز تحقق إلى البريد المرتبط بالتذكرة."
            )

    else:

        form = TicketTrackingForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "support/track_ticket.html",
        context
    )


def verify_ticket_code(request):

    pending = request.session.get(
        SUPPORT_TICKET_VERIFY_SESSION_KEY
    )

    if not pending:

        messages.warning(
            request,
            "ابدأ بإدخال بيانات التذكرة لإرسال رمز التحقق."
        )

        return redirect(
            "support:track_ticket"
        )

    expires_at = _session_datetime(
        pending.get("expires_at")
    )

    if not expires_at or expires_at <= timezone.now():

        request.session.pop(
            SUPPORT_TICKET_VERIFY_SESSION_KEY,
            None
        )

        messages.warning(
            request,
            "انتهت صلاحية رمز التحقق. يرجى طلب رمز جديد."
        )

        return redirect(
            "support:track_ticket"
        )

    if pending.get("attempts", 0) >= SUPPORT_TICKET_MAX_ATTEMPTS:

        request.session.pop(
            SUPPORT_TICKET_VERIFY_SESSION_KEY,
            None
        )

        messages.error(
            request,
            "تم تجاوز عدد المحاولات المسموح. يرجى طلب رمز جديد."
        )

        return redirect(
            "support:track_ticket"
        )

    ticket = get_object_or_404(
        SupportTicket,
        id=pending.get("ticket_id")
    )

    if request.method == "POST":

        form = SupportTicketCodeForm(
            request.POST
        )

        if form.is_valid():

            code = form.cleaned_data["code"]

            if check_password(
                code,
                pending.get("code_hash", "")
            ):

                _grant_ticket_access(
                    request,
                    ticket
                )

                request.session.pop(
                    SUPPORT_TICKET_VERIFY_SESSION_KEY,
                    None
                )

                messages.success(
                    request,
                    "تم التحقق بنجاح."
                )

                return redirect(
                    "support:ticket_detail",
                    ticket_number=ticket.ticket_number
                )

            pending["attempts"] = pending.get(
                "attempts",
                0
            ) + 1

            request.session[
                SUPPORT_TICKET_VERIFY_SESSION_KEY
            ] = pending

            messages.error(
                request,
                "رمز التحقق غير صحيح."
            )

    else:

        form = SupportTicketCodeForm()

    context = {
        "form": form,
        "ticket_email": ticket.email,
        "expires_at": expires_at,
    }

    return render(
        request,
        "support/verify_ticket_code.html",
        context
    )

def ticket_detail_view(
    request,
    ticket_number
):

    ticket = get_object_or_404(
        SupportTicket.objects.prefetch_related(
            "messages"
        ),
        ticket_number=ticket_number
    )

    if not _has_ticket_access(
        request,
        ticket
    ):

        messages.warning(
            request,
            "يرجى التحقق من البريد الإلكتروني قبل عرض التذكرة."
        )

        return redirect(
            "support:track_ticket"
        )

    # =========================
    # إرسال رد جديد
    # =========================

    if request.method == "POST":

        action = request.POST.get("action")

        # رد العميل
        if action == "reply":

            if ticket.status in [
                "closed",
                "resolved"
            ]:

                messages.warning(
                    request,
                    "لا يمكن الرد على تذكرة مغلقة."
                )

                return redirect(
                    "support:ticket_detail",
                    ticket_number=ticket.ticket_number
                )

            form = SupportMessageForm(
                request.POST
            )

            if form.is_valid():

                SupportMessage.objects.create(

                    ticket=ticket,

                    sender=(
                        request.user
                        if request.user.is_authenticated
                        else None
                    ),

                    sender_type=(
                        "user"
                        if request.user.is_authenticated
                        else "guest"
                    ),

                    message=form.cleaned_data[
                        "message"
                    ]
                )

                ticket.mark_in_progress()

                messages.success(
                    request,
                    "تم إرسال ردك بنجاح."
                )

                return redirect(
                    "support:ticket_detail",
                    ticket_number=ticket.ticket_number
                )

        # اعتماد الحل
        elif action == "resolve":

            ticket.mark_resolved()

            messages.success(
                request,
                "تم اعتماد الحل وإغلاق التذكرة."
            )

            return redirect(
                "support:ticket_detail",
                ticket_number=ticket.ticket_number
            )

    message_form = SupportMessageForm()

    context = {

        "ticket": ticket,

        "messages_list": ticket.messages.all(),

        "message_form": message_form,
    }

    return render(
        request,
        "support/ticket_detail.html",
        context
    )

