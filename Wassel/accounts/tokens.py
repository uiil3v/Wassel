from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(
    PasswordResetTokenGenerator
):

    def _make_hash_value(
        self,
        user,
        timestamp
    ):

        return (
            str(user.pk) +
            str(timestamp) +
            str(user.email_verified) +
            str(user.email) +
            str(user.pending_email)
        )


email_verification_token = (
    EmailVerificationTokenGenerator()
)