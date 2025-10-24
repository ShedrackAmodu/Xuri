from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import AuditLog, Notification, FileAttachment


class CoreModelSmokeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        # Create a simple user record; using create() avoids custom manager hooks
        self.user = User.objects.create(email="core_test@example.com", password="testpass")

    def test_create_auditlog_notification_fileattachment(self):
        # Create AuditLog
        audit = AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ActionType.CREATE,
            model_name="CoreModel",
            object_id="1",
            details={"note": "created by test"}
        )
        self.assertIsNotNone(audit.pk)

        # Create Notification
        note = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            message="This is a test",
        )
        self.assertFalse(note.is_read)
        note.mark_as_read()
        note.refresh_from_db()
        self.assertTrue(note.is_read)

        # Create FileAttachment
        file_content = b"hello world"
        uploaded = SimpleUploadedFile("hello.txt", file_content, content_type="text/plain")
        fa = FileAttachment.objects.create(
            name="hello.txt",
            file=uploaded,
            file_type=FileAttachment.FileType.DOCUMENT,
            mime_type="text/plain",
            size=len(file_content),
            uploaded_by=self.user
        )
        self.assertTrue(fa.pk)
        self.assertEqual(fa.file_size_human.split()[1], "B")
