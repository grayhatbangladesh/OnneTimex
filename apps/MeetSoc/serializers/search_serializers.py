from rest_framework import serializers


class SearchResultSerializer(serializers.Serializer):
    """Generic serializer for universal search results."""
    id = serializers.CharField()
    type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(required=False)
    image = serializers.URLField(required=False)


class RecentSearchSerializer(serializers.Serializer):
    """Serializer for recent searches."""
    query = serializers.CharField()
    timestamp = serializers.DateTimeField()


class TrendingSerializer(serializers.Serializer):
    """Serializer for trending content."""
    title = serializers.CharField()
    count = serializers.IntegerField()
    category = serializers.CharField()
