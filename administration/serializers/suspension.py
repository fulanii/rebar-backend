"""Suspending an account, and the record that is left behind."""

from rest_framework import serializers

from administration.models import Suspension


class SuspensionRequestSerializer(serializers.ModelSerializer):
    """
    Why an account is being suspended. The reason is the whole point of the record.

    `notes` is where the ticket number goes. Six months later "why is this person
    locked out" is answered by this row or by nobody.
    """

    class Meta:
        model = Suspension
        fields = ["reason", "notes"]

    def validate(self, attrs):
        target = self.context["target"]

        if target.pk == self.context["request"].user.pk:
            raise serializers.ValidationError("You cannot suspend your own account.")

        if target.is_suspended:
            raise serializers.ValidationError("This account is already suspended.")

        return attrs


class SuspensionResponseSerializer(serializers.ModelSerializer):
    """The record itself, both sides of it once the suspension has been lifted."""

    suspended_by = serializers.EmailField(source="suspended_by.email", read_only=True, allow_null=True)
    lifted_by = serializers.EmailField(source="lifted_by.email", read_only=True, allow_null=True)

    class Meta:
        model = Suspension
        fields = [
            "id",
            "user",
            "reason",
            "notes",
            "suspended_at",
            "suspended_by",
            "lifted_at",
            "lifted_by",
        ]
        read_only_fields = fields
