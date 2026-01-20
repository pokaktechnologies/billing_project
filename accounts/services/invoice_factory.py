from .invoice import InternInvoiceService, ClientInvoiceService, ClientInvoiceUpdater, InternInvoiceUpdater
class InvoiceFactory:

    @staticmethod
    def create(invoice_type, data, user):
        invoice_type = invoice_type.lower().strip()

        if invoice_type == "intern":
            return InternInvoiceService.create(data, user)

        if invoice_type == "client":
            return ClientInvoiceService.create(data, user)

        raise ValueError("Invalid invoice type")


    @staticmethod
    def get_updater(invoice):
        if invoice.invoice_type == "client":
            return ClientInvoiceUpdater()

        if invoice.invoice_type == "intern":
            return InternInvoiceUpdater()

        raise ValueError("Unsupported invoice type")
