from django.db import transaction

from ..models import (
    Account,
    FinancialYear,
    AccountOpeningBalance,
)

def update_opening_balances(financial_year_id, balances):
    """
    Create or update opening balances for a financial year.
    """

    financial_year = FinancialYear.objects.get(
        id=financial_year_id
    )

    with transaction.atomic():

        for row in balances:

            account = Account.objects.get(
                id=row["account"]
            )

            AccountOpeningBalance.objects.update_or_create(
                account=account,
                financial_year=financial_year,
                defaults={
                    "opening_balance": row["opening_balance"]
                }
            )

    return True