from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from django.core.mail import send_mail
import time, logging

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=10)  # tune theo CPU/memory


def _send_with_retry(to, subject, body, html=None, retries=3, base_delay=2):
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            send_mail(subject, body, settings.EMAIL_HOST_USER, [to], html_message=html)
            return True
        except Exception as exc:
            last_exc = exc
            logger.exception("send_mail attempt %s failed for %s", attempt, to)
            time.sleep(base_delay * attempt)
    # Optional: persist failure for manual retry (create EmailDeliveryFailure model)
    logger.error("send_mail failed after %s attempts for %s: %s", retries, to, last_exc)
    return False


class send_email_task:
    @staticmethod
    def delay(to_address: str, subject: str, body: str, html: str | None = None):
        # Submit to bounded pool (non-blocking). Pool prevents unbounded thread spawn.
        _executor.submit(_send_with_retry, to_address, subject, body, html)
