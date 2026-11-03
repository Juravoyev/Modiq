class HideCostFieldsMixin:
    """Tannarx maydonlarini faqat egasi va menejerga ko'rsatadi, kassirdan yashiradi."""

    cost_fields = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        membership = getattr(request, "membership", None)
        if not (membership and membership.is_manager):
            for name in self.cost_fields:
                data.pop(name, None)
        return data
