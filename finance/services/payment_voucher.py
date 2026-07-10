from django.db import transaction

from ..models import PaymentVoucher

from finance.services.numbering import get_next_finance_number


def process_payment_voucher_creation(data, user):

    with transaction.atomic():

        data["user"] = user

        data["voucher_number"] = get_next_finance_number("PV")

        payment_voucher = PaymentVoucher.objects.create(
            **data
        )

        payment_voucher.create_or_update_journal_entry()

        return payment_voucher


def process_payment_voucher_update(instance, data):

    with transaction.atomic():

        for attr, value in data.items():
            setattr(instance, attr, value)

        instance.save()

        instance.create_or_update_journal_entry()

        return instance