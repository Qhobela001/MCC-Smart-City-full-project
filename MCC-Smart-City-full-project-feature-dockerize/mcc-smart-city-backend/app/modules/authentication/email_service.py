import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


logger = logging.getLogger(__name__)


def _message(
    recipient: str,
    recipient_name: str,
    reset_url: str,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "MCC Command Center password reset"
    message["From"] = (
        f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    )
    message["To"] = recipient

    display_name = recipient_name.strip() or "MCC user"

    message.set_content(
        "\n".join(
            [
                f"Hello {display_name},",
                "",
                "A password reset was requested for your MCC Command Center account.",
                "",
                f"Reset your password using this link:\n{reset_url}",
                "",
                (
                    "This link expires in "
                    f"{settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes "
                    "and can only be used while your current password remains unchanged."
                ),
                "",
                "If you did not request this reset, you can ignore this message.",
                "",
                "Maseru City Council",
                "MCC Command Center",
            ]
        )
    )

    return message


def send_password_reset_email(
    recipient: str,
    recipient_name: str,
    reset_url: str,
) -> bool:
    if not settings.SMTP_HOST:
        if settings.APP_ENV.lower() != "production":
            logger.warning(
                "PASSWORD RESET DEV LINK for %s: %s",
                recipient,
                reset_url,
            )
        else:
            logger.error(
                "Password reset email could not be sent because SMTP_HOST is not configured"
            )

        return False

    message = _message(
        recipient,
        recipient_name,
        reset_url,
    )

    context = ssl.create_default_context()

    try:
        if settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
                context=context,
            ) as smtp:
                if settings.SMTP_USERNAME:
                    smtp.login(
                        settings.SMTP_USERNAME,
                        settings.SMTP_PASSWORD,
                    )

                smtp.send_message(message)
        else:
            with smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            ) as smtp:
                smtp.ehlo()

                if settings.SMTP_USE_TLS:
                    smtp.starttls(context=context)
                    smtp.ehlo()

                if settings.SMTP_USERNAME:
                    smtp.login(
                        settings.SMTP_USERNAME,
                        settings.SMTP_PASSWORD,
                    )

                smtp.send_message(message)

        return True

    except Exception:
        logger.exception(
            "Failed to send password reset email to %s",
            recipient,
        )
        return False
