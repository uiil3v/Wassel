from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import TransportContract


from django.http import HttpResponse
from django.template.loader import render_to_string

from weasyprint import HTML

from .models import TransportContract


@login_required
def my_contracts(request):

    # =========================
    # الطالب
    # =========================

    if request.user.role == "student":

        contracts = TransportContract.objects.filter(
            subscription_request__student__user=request.user
        ).select_related(
            "subscription_request__subscription",
            "subscription_request__subscription__driver__user"
        ).order_by("-created_at")

    # =========================
    # السائق
    # =========================

    elif request.user.role == "driver":

        contracts = TransportContract.objects.filter(
            subscription_request__subscription__driver__user=request.user
        ).select_related(
            "subscription_request__student__user",
            "subscription_request__subscription"
        ).order_by("-created_at")

    # =========================
    # الأدمن
    # =========================

    elif request.user.role == "admin":

        contracts = TransportContract.objects.select_related(
            "subscription_request__student__user",
            "subscription_request__subscription__driver__user"
        ).order_by("-created_at")

    else:
        return redirect("main:index")

    context = {
        "contracts": contracts
    }

    return render(
        request,
        "contracts/my_contracts.html",
        context
    )
    
    
@login_required
def download_contract_pdf(request, contract_id):

    contract = get_object_or_404(
        TransportContract.objects.select_related(
            "subscription_request__student__user",
            "subscription_request__subscription__driver__user",
            "subscription_request__subscription"
        ).prefetch_related(
            "subscription_request__schedule"
        ),
        id=contract_id
    )
    
    contract.refresh_status()

    # =========================
    # الصلاحيات
    # =========================

    is_student_owner = (
        request.user == contract.subscription_request.student.user
    )

    is_driver_owner = (
        request.user ==
        contract.subscription_request.subscription.driver.user
    )

    is_admin = (
        request.user.role == "admin"
    )

    if not any([
        is_student_owner,
        is_driver_owner,
        is_admin
    ]):
        return redirect("main:index")

    # =========================
    # HTML Template
    # =========================

    html_string = render_to_string(
        "contracts/contract_pdf.html",
        {
            "contract": contract
        }
    )

    # =========================
    # Generate PDF
    # =========================

    html = HTML(
        string=html_string,
        base_url=request.build_absolute_uri("/")
    )

    pdf_file = html.write_pdf()

    # =========================
    # Response
    # =========================

    response = HttpResponse(
        pdf_file,
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = (
        f'filename="{contract.contract_number}.pdf"'
    )

    return response