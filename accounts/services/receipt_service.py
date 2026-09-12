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

from decimal import Decimal

from django.db import transaction

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
    @transaction.atomic
    def create_admission_receipts(
        *,
        enrollment,
        receipt_data,
        user,
    ):
        """
        Create slot and/or advance receipt using one receipt payload.

        If slot amount exists -> create slot receipt.
        If advance amount exists -> create advance receipt.

        If a receipt already exists, it is skipped.
        """

        student = enrollment.student

        created_receipts = []
        skipped_receipts = []

        # =====================================================
        # 1. SLOT RECEIPT
        # =====================================================

        slot_amount = Decimal(
            str(student.slot_amount or 0)
        )

        if slot_amount > 0:

            slot_exists = ReceiptModel.objects.filter(
                receipt_type="intern",
                receipt_for="slot",
                intern=student.profile,
                course=enrollment.course,
            ).exists()

            if slot_exists:

                skipped_receipts.append("slot")

            else:

                slot_data = receipt_data.copy()

                slot_data["receipt_for"] = "slot"

                slot_data.setdefault(
                    "remark",
                    "Slot Booking Payment",
                )

                slot_data.setdefault(
                    "description",
                    "Slot Booking",
                )

                receipt = StudentReceiptService.create_receipt(
                    enrollment=enrollment,
                    receipt_data=slot_data,
                    user=user,
                    amount=slot_amount,
                    payment_date=enrollment.payment_date,
                )

                created_receipts.append({
                    "type": "slot",
                    "receipt_id": receipt.id,
                    "receipt_number": receipt.receipt_number,
                    "amount": str(slot_amount),
                })

        # =====================================================
        # 2. ADVANCE RECEIPT
        # =====================================================

        advance_amount = Decimal(
            str(enrollment.advance_amount or 0)
        )

        if advance_amount > 0:

            advance_exists = ReceiptModel.objects.filter(
                receipt_type="intern",
                receipt_for="advance",
                intern=student.profile,
                course=enrollment.course,
            ).exists()

            if advance_exists:

                skipped_receipts.append("advance")

            else:

                payment = CoursePayment.objects.filter(
                    enrollment=enrollment,
                    payment_type="advance",
                ).first()

                if not payment:
                    raise ValueError(
                        "Advance payment record does not exist."
                    )

                advance_data = receipt_data.copy()

                advance_data["receipt_for"] = "advance"

                advance_data.setdefault(
                    "remark",
                    "Advance Payment",
                )

                advance_data.setdefault(
                    "description",
                    "Student Advance Payment",
                )

                receipt = StudentReceiptService.create_receipt(
                    enrollment=enrollment,
                    payment=payment,
                    receipt_data=advance_data,
                    user=user,
                )

                created_receipts.append({
                    "type": "advance",
                    "receipt_id": receipt.id,
                    "receipt_number": receipt.receipt_number,
                    "amount": str(advance_amount),
                })

        # =====================================================
        # 3. NOTHING AVAILABLE
        # =====================================================

        if not created_receipts and not skipped_receipts:

            raise ValueError(
                "No slot or advance amount available for receipt creation."
            )

        return {
            "created": created_receipts,
            "skipped": skipped_receipts,
        }

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