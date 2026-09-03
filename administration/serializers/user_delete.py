"""What is left behind when an account is deleted."""

from rest_framework import serializers


class UserDeleteResponseSerializer(serializers.Serializer):
    """
    A receipt for a row that no longer exists.

    Worth returning because the account cannot be looked up afterwards to confirm what
    went, and because nothing in this app writes an audit trail yet.
    """

    id = serializers.IntegerField()
    email = serializers.EmailField()
    suspensions_deleted = serializers.IntegerField()
