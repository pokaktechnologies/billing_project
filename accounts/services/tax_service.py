from decimal import Decimal

class TaxService:
    @staticmethod
    def calculate(amount, sgst_pct, cgst_pct):
        sgst = (amount * sgst_pct) / Decimal("100")
        cgst = (amount * cgst_pct) / Decimal("100")
        return sgst, cgst, amount + sgst + cgst


class InvoiceItemCalculator:
    """
    Single source of truth for invoice item calculations.
    """

    @staticmethod
    def calculate(quantity, unit_price, sgst_pct=0, cgst_pct=0):
        quantity = Decimal(quantity)
        unit_price = Decimal(unit_price)
        sgst_pct = Decimal(sgst_pct)
        cgst_pct = Decimal(cgst_pct)

        total = quantity * unit_price
        sgst = (total * sgst_pct) / Decimal("100")
        cgst = (total * cgst_pct) / Decimal("100")
        sub_total = total + sgst + cgst

        return {
            "total": total,
            "sgst": sgst,
            "cgst": cgst,
            "sub_total": sub_total,
        }