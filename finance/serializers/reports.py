# This file is intended for report-specific serializers if any (e.g. for custom JSON output structures)
# For now, it might be empty or used for Cashflow if preferred.
# Keeping it for consistency with the plan.
from rest_framework import serializers

class GenericReportSerializer(serializers.Serializer):
    # Placeholders for future report-specific serializers
    pass
