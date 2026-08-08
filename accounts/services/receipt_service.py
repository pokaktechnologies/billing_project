# from .receipt_factory import ReceiptFactory
# from ..models import ReceiptModel
# from ..views.views import OrderNumberGeneratorView


# class StudentReceiptService:

#     @staticmethod
#     def create_receipt(
#         *,
#         enrollment,
#         payment,
#         receipt_data,
#         user,
#     ):
#         """
#         Create an intern receipt from a student payment.
#         """

#         payload = {
#             "receipt_type": "intern",

#             "receipt_number": OrderNumberGeneratorView.generate_next_number(
#                 ReceiptModel,
#                 "receipt_number",
#                 "RP",
#                 6,
#             ),

#             "receipt_date": payment.payment_date,

#             "intern": enrollment.student.profile.id,

#             "course": enrollment.course.id,

#             "cheque_amount": payment.amount_paid,

#             "total_amount": payment.amount_paid,
#         }

#         # Merge frontend supplied receipt fields
#         if receipt_data:
#             payload.update(receipt_data)

#         return ReceiptFactory.create(
#             "intern",
#             payload,
#             user,
#         )

from .receipt_factory import ReceiptFactory
from ..models import ReceiptModel
from internship.models import CoursePayment
from ..views.views import OrderNumberGeneratorView


class StudentReceiptService:

    @staticmethod
    def create_advance_receipt(
        *,
        enrollment,
        receipt_data,
        user,
    ):
        """
        Create receipt for advance payment if receipt data is provided.
        """

        if not receipt_data:
            return None

        payment = CoursePayment.objects.filter(
            enrollment=enrollment,
            payment_type="advance",
        ).first()

        if not payment:
            return None

        return StudentReceiptService.create_receipt(
            enrollment=enrollment,
            payment=payment,
            receipt_data=receipt_data,
            user=user,
        )

    @staticmethod
    def create_slot_receipt(
        *,
        enrollment,
        application,
        receipt_data,
        user,
    ):
        """
        Create receipt for slot booking payment.
        """

        if (
            not receipt_data
            or not application
            or not application.slot_amount
            or not application.slot_payment_date
            or not application.slot_payment_method
        ):
            return None

        slot_receipt_data = receipt_data.copy()

        slot_receipt_data.setdefault(
            "remark",
            "Slot Booking Payment",
        )

        slot_receipt_data.setdefault(
            "description",
            "Slot Booking",
        )

        return StudentReceiptService.create_receipt(
            enrollment=enrollment,
            receipt_data=slot_receipt_data,
            user=user,
            amount=application.slot_amount,
            payment_date=application.slot_payment_date,
        )
    @staticmethod
    def create_installment_receipt(
        *,
        payment,
        receipt_data,
        user,
    ):
        if not receipt_data:
            return None

        return StudentReceiptService.create_receipt(
            enrollment=payment.enrollment,
            payment=payment,
            receipt_data=receipt_data,
            user=user,
        )

    @staticmethod
    def create_receipt(
        *,
        enrollment,
        receipt_data,
        user,
        payment=None,
        amount=None,
        payment_date=None,
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

            "receipt_date": payment.payment_date if payment else payment_date,

            "intern": enrollment.student.profile.id,

            "course": enrollment.course.id,

            "cheque_amount": payment.amount_paid if payment else amount,

            "total_amount": payment.amount_paid if payment else amount,
        }

        if receipt_data:
            payload.update(receipt_data)

        return ReceiptFactory.create(
            "intern",
            payload,
            user,
        )