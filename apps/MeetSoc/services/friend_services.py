"""
Friend suggestion algorithm — priority-based:
1. Friends of friends
2. Same city
3. Same country
4. Everyone else
"""
from django.db.models import Q

from apps.MeetSoc.models import BlockList, Friendship, GroupMembership
from apps.accounts.models import User, UserProfile


def _friend_ids(user):
    accepted = Friendship.objects.filter(
        Q(sender=user, status="accepted") | Q(receiver=user, status="accepted")
    )
    ids = set()
    for f in accepted:
        other = f.receiver_id if f.sender_id == user.id else f.sender_id
        ids.add(str(other))
    return ids


def _pending_request_ids(user):
    sent = Friendship.objects.filter(sender=user, status="pending").values_list("receiver_id", flat=True)
    received = Friendship.objects.filter(receiver=user, status="pending").values_list("sender_id", flat=True)
    return {str(x) for x in sent} | {str(x) for x in received}


def get_friend_suggestions(user: User, limit: int = 20):
    my_id = str(user.id)
    friends = _friend_ids(user)
    blocked_ids = set(
        BlockList.objects.filter(blocker=user).values_list("blocked_id", flat=True)
    ) | set(BlockList.objects.filter(blocked=user).values_list("blocker_id", flat=True))
    blocked_ids = {str(x) for x in blocked_ids}
    pending_ids = _pending_request_ids(user)

    exclude_ids = friends | blocked_ids | pending_ids | {my_id}

    try:
        my_profile = user.profile
        my_city = (my_profile.city or "").strip().lower()
        my_country = (my_profile.country or "").strip().lower()
    except UserProfile.DoesNotExist:
        my_city = ""
        my_country = ""

    result_ids = []
    seen = set()

    def add_users(queryset, label):
        for u in queryset:
            uid = str(u.id)
            if uid in exclude_ids or uid in seen:
                continue
            seen.add(uid)
            result_ids.append((label, u))

    # Priority 1: Friends of friends
    fof_ids = set()
    for fid in friends:
        fof = _friend_ids(User.objects.get(pk=fid))
        fof_ids.update(fof - exclude_ids)

    if fof_ids:
        fof_users = User.objects.filter(pk__in=fof_ids).select_related("profile")
        add_users(fof_users, "friends_of_friends")

    # Priority 2: Same city
    if my_city:
        city_users = User.objects.filter(
            profile__city__iexact=my_city
        ).exclude(pk__in=seen | {user.id}).select_related("profile")[:limit]
        add_users(city_users, "same_city")

    # Priority 3: Same country
    if my_country:
        country_users = User.objects.filter(
            profile__country__iexact=my_country
        ).exclude(pk__in=seen | {user.id}).select_related("profile")[:limit]
        add_users(country_users, "same_country")

    # Priority 4: Everyone else
    if len(result_ids) < limit:
        remaining = limit - len(result_ids)
        other_users = User.objects.exclude(
            pk__in=seen | {user.id}
        ).select_related("profile")[:remaining]
        add_users(other_users, "other")

    return [(label, u) for label, u in result_ids[:limit]]
