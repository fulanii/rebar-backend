"""What an operator may change on someone else's account."""

from rest_framework import serializers

from authentication.models import CustomUser
from authentication.serializers.validators import validate_name, validate_us_phone_number

PRIVILEGE_FIELDS = {"is_staff", "is_superuser"}


class UserUpdateRequestSerializer(serializers.ModelSerializer):
    """
    Correcting an account on someone's behalf. Never a password, and never a code.

    A password is not editable here on purpose: an operator who can set one can sign in
    as the customer, and no audit trail can tell that apart from support work. The reset
    email is the route, because it makes the customer prove the address again.
    """

    class Meta:
        model = CustomUser
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "is_active",
            "is_verified",
            "is_staff",
            "is_superuser",
        ]
        extra_kwargs = {"email": {"validators": []}}

    def validate_email(self, value):
        email = value.strip().lower()

        if CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("An account with this email already exists.")

        return email

    def validate_first_name(self, value):
        return validate_name(value, "First name")

    def validate_last_name(self, value):
        return validate_name(value, "Last name")

    def validate_phone_number(self, value):
        return validate_us_phone_number(value) if value else value

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Send at least one field to change.")

        if PRIVILEGE_FIELDS & set(attrs):
            self.check_may_grant_privileges()

        return attrs

    def check_may_grant_privileges(self):
        """
        Nobody edits their own staff or superuser flag, superusers included.

        The route already refuses anyone who is not a superuser, so what is left to
        stop is the one thing that check cannot see: a superuser whose credentials have
        been taken editing the account they are signed in as, to lock the real owner out
        or to leave quietly with the flag switched back.
        """
        actor = self.context["request"].user

        if actor.pk == self.instance.pk:
            raise serializers.ValidationError("You cannot change your own staff or superuser access.")
