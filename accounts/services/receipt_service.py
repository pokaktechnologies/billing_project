from .receipt_factory import ReceiptFactory
from ..models import ReceiptModel
from ..views.views import OrderNumberGeneratorView


class StudentReceiptService:

    @staticmethod
    def create_receipt(
        *,
        enrollment,
        payment,
        receipt_data,
        user,
    ):
        """
        Create an intern receipt from a student payment.
        """

        payload = {
            "receipt_type": "intern",

            "receipt_number": OrderNumberGeneratorView.generate_next_number(
                ReceiptModel,
                "receipt_number",
                "RP",
                6,
            ),

            "receipt_date": payment.payment_date,

            "intern": enrollment.student.profile.id,

            "course": enrollment.course.id,

            "cheque_amount": payment.amount_paid,

            "total_amount": payment.amount_paid,
        }

        # Merge frontend supplied receipt fields
        if receipt_data:
            payload.update(receipt_data)

        return ReceiptFactory.create(
            "intern",
            payload,
            user,
        )