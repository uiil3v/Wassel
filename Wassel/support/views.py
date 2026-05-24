from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages



from .models import (
    SupportTicket,
    SupportMessage,
)


from .forms import (
    SupportTicketForm,
    TicketTrackingForm,
    SupportMessageForm,
)


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
                email=email
            ).first()

            if ticket:

                return redirect(
                    "support:ticket_detail",
                    ticket_number=ticket.ticket_number
                )

            messages.error(
                request,
                "لم يتم العثور على تذكرة بهذه البيانات."
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

