from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.chats.models import AIChatMessage


class Command(BaseCommand):
    help = "Hard-delete chat messages whose purge_after timestamp has passed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only count records that would be deleted.",
        )

    def handle(self, *args, **options):
        queryset = AIChatMessage.objects.filter(
            purge_after__isnull=False,
            purge_after__lte=timezone.now(),
        )
        count = queryset.count()

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(f"{count} chat message(s) would be deleted.")
            )
            return

        deleted_count, _ = queryset.delete()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted_count} chat message(s).")
        )
