from .receipt import InternReceiptService, ClientReceiptService, ClientReceiptUpdater, InternReceiptUpdater

class ReceiptFactory:

    @staticmethod
    def create(receipt_type, data, user):
        receipt_type = receipt_type.lower().strip()

        if receipt_type == "intern":
            return InternReceiptService.create(data, user)

        if receipt_type == "client":
            return ClientReceiptService.create(data, user)

        raise ValueError("Invalid receipt type")


    @staticmethod
    def get_updater(receipt):
        if receipt.receipt_type == "client":
            return ClientReceiptUpdater()

        if receipt.receipt_type == "intern":
            return InternReceiptUpdater()

        raise ValueError("Unsupported receipt type")
