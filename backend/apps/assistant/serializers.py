from rest_framework import serializers


class HistoryItemSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    text = serializers.CharField(max_length=4000)


class AskSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500, trim_whitespace=True)
    page = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    history = HistoryItemSerializer(many=True, required=False, default=list)

    def validate_history(self, value):
        return value[-6:]
