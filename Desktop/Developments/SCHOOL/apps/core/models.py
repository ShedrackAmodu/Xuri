# apps/core/models.py

import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings

# The Core app models

class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating created and modified fields.
    """
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True, db_index=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    Abstract base model that provides a UUID primary key instead of auto-increment.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class StatusModel(models.Model):
    """
    Abstract base model that provides status tracking with timestamps.
    """
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        PENDING = 'pending', _('Pending')
        SUSPENDED = 'suspended', _('Suspended')
        ARCHIVED = 'archived', _('Archived')

    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )
    status_changed_at = models.DateTimeField(_('status changed at'), auto_now_add=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Update status_changed_at when status changes.
        """
        if self.pk and not self._state.adding:  # Check if object exists and is not being added
            original = self.__class__.objects.get(pk=self.pk)
            if original.status != self.status:
                self.status_changed_at = timezone.now()
        super().save(*args, **kwargs)


class SoftDeleteModel(models.Model):
    """
    Abstract base model that provides soft delete functionality.
    """
    is_deleted = models.BooleanField(_('is deleted'), default=False, db_index=True)
    deleted_at = models.DateTimeField(_('deleted at'), null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """
        Soft delete by setting is_deleted flag and deleted_at timestamp.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        """
        Perform actual database deletion.
        """
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """
        Restore a soft-deleted instance.
        """
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class CoreBaseModel(TimeStampedModel, UUIDModel, StatusModel, SoftDeleteModel):
    """
    Comprehensive base model combining all core functionalities.
    All main models should inherit from this.
    """
    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__} {self.id}"


class AddressModel(models.Model):
    """
    Abstract model for storing address information.
    """
    address_line_1 = models.CharField(_('address line 1'), max_length=255, blank=True)
    address_line_2 = models.CharField(_('address line 2'), max_length=255, blank=True)
    city = models.CharField(_('city'), max_length=100, blank=True)
    state = models.CharField(_('state/province'), max_length=100, blank=True)
    postal_code = models.CharField(_('postal code'), max_length=20, blank=True)
    country = models.CharField(_('country'), max_length=100, blank=True)

    class Meta:
        abstract = True

    @property
    def full_address(self):
        """Return formatted full address."""
        parts = [
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ', '.join(filter(None, parts))


class ContactModel(models.Model):
    """
    Abstract model for storing contact information.
    """
    phone = models.CharField(_('phone number'), max_length=20, blank=True)
    mobile = models.CharField(_('mobile number'), max_length=20, blank=True)
    email = models.EmailField(_('email address'), blank=True)
    emergency_contact = models.CharField(_('emergency contact'), max_length=100, blank=True)
    emergency_phone = models.CharField(_('emergency phone'), max_length=20, blank=True)

    class Meta:
        abstract = True


class AuditLog(CoreBaseModel):
    """
    Model for tracking system-wide audit events.
    """
    class ActionType(models.TextChoices):
        CREATE = 'create', _('Create')
        UPDATE = 'update', _('Update')
        DELETE = 'delete', _('Delete')
        LOGIN = 'login', _('Login')
        LOGOUT = 'logout', _('Logout')
        VIEW = 'view', _('View')
        EXPORT = 'export', _('Export')
        IMPORT = 'import', _('Import')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_('user')
    )
    action = models.CharField(_('action'), max_length=20, choices=ActionType.choices)
    model_name = models.CharField(_('model name'), max_length=100)
    object_id = models.CharField(_('object id'), max_length=100)
    details = models.JSONField(_('details'), default=dict, blank=True)
    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)
    user_agent = models.TextField(_('user agent'), blank=True)
    timestamp = models.DateTimeField(_('timestamp'), auto_now_add=True)

    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name} - {self.timestamp}"


class SystemConfig(CoreBaseModel):
    """
    Model for storing system-wide configuration settings.
    """
    class ConfigType(models.TextChoices):
        GENERAL = 'general', _('General')
        ACADEMIC = 'academic', _('Academic')
        FINANCE = 'finance', _('Finance')
        COMMUNICATION = 'communication', _('Communication')
        SECURITY = 'security', _('Security')
        UI = 'ui', _('User Interface')

    key = models.CharField(_('config key'), max_length=100, unique=True, db_index=True)
    value = models.JSONField(_('config value'), default=dict)
    config_type = models.CharField(
        _('config type'),
        max_length=20,
        choices=ConfigType.choices,
        default=ConfigType.GENERAL
    )
    description = models.TextField(_('description'), blank=True)
    is_public = models.BooleanField(_('is public'), default=False)
    is_encrypted = models.BooleanField(_('is encrypted'), default=False)

    class Meta:
        verbose_name = _('System Configuration')
        verbose_name_plural = _('System Configurations')
        ordering = ['config_type', 'key']

    def __str__(self):
        return f"{self.key} ({self.config_type})"


class Notification(CoreBaseModel):
    """
    Model for system notifications to users.
    """
    class NotificationType(models.TextChoices):
        INFO = 'info', _('Information')
        SUCCESS = 'success', _('Success')
        WARNING = 'warning', _('Warning')
        ERROR = 'error', _('Error')
        ALERT = 'alert', _('Alert')

    class Priority(models.TextChoices):
        LOW = 'low', _('Low')
        MEDIUM = 'medium', _('Medium')
        HIGH = 'high', _('High')
        URGENT = 'urgent', _('Urgent')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('user')
    )
    title = models.CharField(_('title'), max_length=200)
    message = models.TextField(_('message'))
    notification_type = models.CharField(
        _('notification type'),
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    priority = models.CharField(
        _('priority'),
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    is_read = models.BooleanField(_('is read'), default=False)
    read_at = models.DateTimeField(_('read at'), null=True, blank=True)
    action_url = models.URLField(_('action URL'), blank=True)
    related_model = models.CharField(_('related model'), max_length=100, blank=True)
    related_object_id = models.CharField(_('related object ID'), max_length=100, blank=True)
    expires_at = models.DateTimeField(_('expires at'), null=True, blank=True)

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at', 'priority']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['expires_at', 'status']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user}"

    def mark_as_read(self):
        """Mark notification as read."""
        self.is_read = True
        self.read_at = timezone.now()
        self.save()


class FileAttachment(CoreBaseModel):
    """
    Model for storing file attachments with metadata.
    """
    class FileType(models.TextChoices):
        DOCUMENT = 'document', _('Document')
        IMAGE = 'image', _('Image')
        PDF = 'pdf', _('PDF')
        SPREADSHEET = 'spreadsheet', _('Spreadsheet')
        PRESENTATION = 'presentation', _('Presentation')
        ARCHIVE = 'archive', _('Archive')
        OTHER = 'other', _('Other')

    name = models.CharField(_('file name'), max_length=255)
    file = models.FileField(_('file'), upload_to='attachments/%Y/%m/%d/')
    file_type = models.CharField(
        _('file type'),
        max_length=20,
        choices=FileType.choices,
        default=FileType.DOCUMENT
    )
    mime_type = models.CharField(_('MIME type'), max_length=100)
    size = models.PositiveIntegerField(_('file size in bytes'))
    description = models.TextField(_('description'), blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_files',
        verbose_name=_('uploaded by')
    )
    related_model = models.CharField(_('related model'), max_length=100, blank=True)
    related_object_id = models.CharField(_('related object ID'), max_length=100, blank=True)

    class Meta:
        verbose_name = _('File Attachment')
        verbose_name_plural = _('File Attachments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['related_model', 'related_object_id']),
            models.Index(fields=['file_type', 'status']),
        ]

    def __str__(self):
        return self.name

    @property
    def file_size_human(self):
        """Return human-readable file size."""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024 * 1024 * 1024:
            return f"{self.size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size / (1024 * 1024 * 1024):.1f} GB"


class AcademicSession(CoreBaseModel):
    """
    Model for managing academic sessions/years.
    """
    
    name = models.CharField(_('session name'), max_length=100)
    number_of_semesters = models.PositiveSmallIntegerField(
        _('number of semesters'),
        choices=[(2, _('Two Semesters')), (3, _('Three Semesters'))],
        default=2,
        help_text=_('Specify if the school year has 2 or 3 semesters.'),
        db_index=True
    )
    term_number = models.PositiveSmallIntegerField(
        _('term/semester number'),
        choices=[
            (1, _('First Semester')),
            (2, _('Second Semester')),
            (3, _('Third Semester')),
        ],
        null=True,
        blank=True,
        help_text=_('Set to 1, 2 or 3 for term/semester-based schools; leave null for whole-session models.'),
        db_index=True
    )
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'))
    is_current = models.BooleanField(_('is current session'), default=False)

    class Meta:
        verbose_name = _('Academic Session')
        verbose_name_plural = _('Academic Sessions')
        ordering = ['-start_date']
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gt=models.F('start_date')),
                name='end_date_after_start_date'
            ),
            models.CheckConstraint(
                check=models.Q(term_number__isnull=True) | models.Q(term_number__lte=models.F('number_of_semesters')),
                name='term_number_within_semesters_range'
            )
        ]

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.end_date <= self.start_date:
            raise ValidationError(_('End date must be after start date.'))

        if self.term_number is not None and self.term_number > self.number_of_semesters:
            raise ValidationError(
                _('Term number cannot exceed the number of semesters configured for this session.')
            )

    def save(self, *args, **kwargs):
        """
        Ensure only one session can be marked as current.
        """
        if self.is_current:
            # Set all other sessions to not current
            AcademicSession.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)

    @property
    def semester_name(self):
        """Return the human-readable semester name."""
        if self.term_number == 1:
            return _('First Semester')
        elif self.term_number == 2:
            return _('Second Semester')
        elif self.term_number == 3:
            return _('Third Semester')
        return _('Full Session')


class Holiday(CoreBaseModel):
    """
    Model for managing holidays and special events.
    """
    name = models.CharField(_('holiday name'), max_length=200)
    date = models.DateField(_('date'))
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='holidays',
        verbose_name=_('academic session')
    )
    is_recurring = models.BooleanField(_('is recurring'), default=False)
    description = models.TextField(_('description'), blank=True)

    class Meta:
        verbose_name = _('Holiday')
        verbose_name_plural = _('Holidays')
        ordering = ['date']
        unique_together = ['date', 'academic_session']

    def __str__(self):
        return f"{self.name} - {self.date}"


class SequenceGenerator(CoreBaseModel):
    """
    Model for generating sequential numbers for various purposes.
    """
    class SequenceType(models.TextChoices):
        STUDENT_ID = 'student_id', _('Student ID')
        EMPLOYEE_ID = 'employee_id', _('Employee ID')
        INVOICE = 'invoice', _('Invoice Number')
        RECEIPT = 'receipt', _('Receipt Number')
        LIBRARY_BOOK = 'library_book', _('Library Book ID')
        TRANSPORT_BUS = 'transport_bus', _('Transport Bus ID')

    sequence_type = models.CharField(
        _('sequence type'),
        max_length=50,
        choices=SequenceType.choices,
        unique=True
    )
    prefix = models.CharField(_('prefix'), max_length=10, blank=True)
    suffix = models.CharField(_('suffix'), max_length=10, blank=True)
    last_number = models.PositiveIntegerField(_('last number'), default=0)
    padding = models.PositiveIntegerField(
        _('number padding'),
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    reset_frequency = models.CharField(
        _('reset frequency'),
        max_length=20,
        choices=[
            ('never', _('Never')),
            ('yearly', _('Yearly')),
            ('monthly', _('Monthly')),
            ('daily', _('Daily'))
        ],
        default='never'
    )

    class Meta:
        verbose_name = _('Sequence Generator')
        verbose_name_plural = _('Sequence Generators')

    def __str__(self):
        return f"{self.sequence_type} - Last: {self.last_number}"

    def get_next_number(self):
        """Generate and return the next sequential number."""
        self.last_number += 1
        self.save()
        
        number_str = str(self.last_number).zfill(self.padding)
        return f"{self.prefix}{number_str}{self.suffix}"
