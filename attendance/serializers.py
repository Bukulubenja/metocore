from rest_framework import serializers

from attendance.models import CheckIn


class CheckInRequestSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    gps_accuracy_m = serializers.IntegerField(min_value=0)


class CheckInResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckIn
        fields = [
            "id",
            "status",
            "reason",
            "distance_m",
            "gps_accuracy_m",
            "latitude",
            "longitude",
            "checked_in_at",
        ]
        read_only_fields = fields
