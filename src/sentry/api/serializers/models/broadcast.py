from django.db.models import Count

from sentry.api.serializers import Serializer, register
from sentry.models.broadcast import Broadcast, BroadcastSeen
from sentry.users.models.user import User


@register(Broadcast)
class BroadcastSerializer(Serializer):
    def get_attrs(self, item_list, user, **kwargs):
        if not user.is_authenticated:
            seen = set()
        else:
            seen = set(
                BroadcastSeen.objects.filter(broadcast__in=item_list, user_id=user.id).values_list(
                    "broadcast", flat=True
                )
            )

        return {item: {"seen": item.id in seen} for item in item_list}

    def serialize(self, obj, attrs, user, **kwargs):
        return {
            "id": str(obj.id),
            "message": obj.message,
            "title": obj.title,
            "link": obj.link,
            "cta": obj.cta,
            "mediaUrl": obj.media_url,
            "isActive": obj.is_active,
            "dateCreated": obj.date_added,
            "dateExpires": obj.date_expires,
            "hasSeen": attrs["seen"],
            "category": obj.category,
        }


class AdminBroadcastSerializer(BroadcastSerializer):
    def get_attrs(self, item_list, user, **kwargs):
        attrs = super().get_attrs(item_list, user)
        counts = dict(
            BroadcastSeen.objects.filter(broadcast__in=item_list)
            .values("broadcast")
            .distinct()
            .annotate(user_count=Count("broadcast"))
            .values_list("broadcast", "user_count")
        )
        created_by_ids = {item.created_by_id for item in item_list if item.created_by_id}
        users = {
            user.id: user.email
            for user in User.objects.filter(id__in=created_by_ids)
        }

        for item in item_list:
            attrs.setdefault(item, {})["user_count"] = counts.get(item.id, 0)
            if item.created_by_id:
                attrs[item]["created_by"] = users.get(item.created_by_id)

        return attrs

    def serialize(self, obj, attrs, user, **kwargs):
        context = super().serialize(obj, attrs, user)
        context["userCount"] = attrs["user_count"]
        context["createdBy"] = attrs.get("created_by")
        return context
