"""The admin overview figures."""

from rest_framework import serializers


class StatsResponseSerializer(serializers.Serializer):
    """Counts only, never a row: the overview answers how many, the list answers who."""

    total_users = serializers.IntegerField()
    signups_last_7_days = serializers.IntegerField()
