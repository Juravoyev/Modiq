from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BusinessOwnedModel(TimeStampedModel):
    """Har bir tenant (biznes) ma'lumoti shu modeldan meros oladi."""

    business = models.ForeignKey("accounts.Business", on_delete=models.CASCADE, related_name="+")

    class Meta:
        abstract = True
