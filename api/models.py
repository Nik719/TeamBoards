# Models: Company (with role + api_key), KBEntry, and QueryLog
from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
    class Role(models.TextChoices):
        ADMIN  = 'admin',  'Admin'
        CLIENT = 'client', 'Client'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='company',
    )
    company_name = models.CharField(max_length=255)
    api_key      = models.CharField(max_length=64, unique=True, blank=True)
    role         = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CLIENT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['company_name']
        verbose_name        = 'Company'
        verbose_name_plural = 'Companies'

    def __str__(self):
        return f"{self.company_name} ({self.role})"


class KBEntry(models.Model):
    class Category(models.TextChoices):
        API       = 'api',       'API'
        DATABASE  = 'database',  'Database'
        CLOUD     = 'cloud',     'Cloud'
        FRAMEWORK = 'framework', 'Framework'
        GENERAL   = 'general',   'General'

    question   = models.TextField()
    answer     = models.TextField()
    category   = models.CharField(max_length=20, choices=Category.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['category', 'id']
        verbose_name        = 'Knowledge Base Entry'
        verbose_name_plural = 'Knowledge Base Entries'

    def __str__(self):
        return self.question[:80]


class QueryLog(models.Model):
    company       = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='query_logs',
    )
    search_term   = models.CharField(max_length=255)
    results_count = models.PositiveIntegerField()
    queried_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-queried_at']
        verbose_name        = 'Query Log'
        verbose_name_plural = 'Query Logs'
        indexes             = [
            models.Index(fields=['company', 'queried_at']),
            models.Index(fields=['search_term']),
        ]

    def __str__(self):
        return f"{self.company.company_name} → '{self.search_term}' ({self.results_count} results)"
