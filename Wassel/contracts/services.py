from .models import TransportContract


def create_transport_contract(subscription_request):

    # إذا فيه عقد مسبق لا تنشئ واحد جديد
    existing_contract = getattr(
        subscription_request,
        "contract",
        None
    )

    if existing_contract:
        return existing_contract

    contract = TransportContract.objects.create(
        subscription_request=subscription_request
    )

    return contract