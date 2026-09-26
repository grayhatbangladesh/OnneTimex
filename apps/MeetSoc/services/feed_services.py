import random

from django.db.models import Q
from django.utils import timezone

from apps.MeetSoc.models import BlockList, Friendship, FeedHide, FeedSnooze, Post


class FeedService:
    """
    Simple, reliable tiered feed:
      1. Liked-category posts (latest first)
      2. Friends' posts (latest first)
      3. Group posts — every 3-4 posts
      4. Same-country posts (latest first)
      5. All other public posts (latest first)
    Ads every 15 posts. Seen posts excluded. Recycled when exhausted.
    """

    def __init__(self, user):
        self.user = user
        self._now = timezone.now()

    # ------------------------------------------------------------------
    # Exclusions
    # ------------------------------------------------------------------

    def _blocked_author_ids(self):
        blocked = set(
            BlockList.objects.filter(blocker=self.user).values_list("blocked_id", flat=True)
        ) | set(BlockList.objects.filter(blocked=self.user).values_list("blocker_id", flat=True))
        snoozed = set(
            FeedSnooze.objects.filter(user=self.user, until__gt=self._now).values_list(
                "snoozed_user_id", flat=True
            )
        )
        return blocked | snoozed

    def _hidden_post_ids(self):
        return set(FeedHide.objects.filter(user=self.user).values_list("post_id", flat=True))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_friend_ids(self):
        return set(
            Friendship.objects.filter(
                Q(sender=self.user, status="accepted") | Q(receiver=self.user, status="accepted")
            ).values_list("sender_id", flat=True)
        ) | set(
            Friendship.objects.filter(
                Q(sender=self.user, status="accepted") | Q(receiver=self.user, status="accepted")
            ).values_list("receiver_id", flat=True)
        )

    def _get_group_ids(self):
        from apps.MeetSoc.models import GroupMembership
        return set(
            GroupMembership.objects.filter(user=self.user, status="active").values_list("group_id", flat=True)
        )

    def _get_followed_page_ids(self):
        from apps.MeetSoc.models import PageFollower
        return set(
            PageFollower.objects.filter(user=self.user, is_liked=True).values_list("page_id", flat=True)
        )

    def _get_user_country(self):
        if hasattr(self.user, "profile") and getattr(self.user.profile, "country", ""):
            return self.user.profile.country
        return ""

    # ------------------------------------------------------------------
    # Tier builders — each returns list of Post objects, -created_at
    # ------------------------------------------------------------------

    def _tier1(self, exclude, limit=200):
        from apps.recommendations.models import UserCategoryScore
        cats = list(
            UserCategoryScore.objects.filter(user=self.user)
            .order_by("-score").values_list("category_id", flat=True)[:5]
        )
        if not cats:
            return []
        return list(
            Post.objects.filter(category_id__in=cats, privacy="public")
            .exclude(id__in=exclude).exclude(is_on_hold=True).select_related("category", "author")
            .order_by("-created_at")[:limit]
        )

    def _tier2(self, friend_ids, exclude, limit=200):
        if not friend_ids:
            return []
        return list(
            Post.objects.filter(author_id__in=friend_ids)
            .exclude(id__in=exclude).exclude(is_on_hold=True).select_related("category", "author")
            .order_by("-created_at")[:limit]
        )

    def _tier3(self, group_ids, exclude, limit=200):
        if not group_ids:
            return []
        return list(
            Post.objects.filter(group_id__in=group_ids)
            .exclude(author=self.user).exclude(id__in=exclude).exclude(is_on_hold=True)
            .select_related("category", "author")
            .order_by("-created_at")[:limit]
        )

    def _tier4(self, country, exclude, limit=200):
        if not country:
            return []
        return list(
            Post.objects.filter(author__profile__country=country, privacy="public")
            .exclude(author=self.user).exclude(id__in=exclude).exclude(is_on_hold=True)
            .select_related("category", "author")
            .order_by("-created_at")[:limit]
        )

    def _all_posts(self, exclude, limit=1000):
        return list(
            Post.objects.filter(privacy="public")
            .exclude(id__in=exclude).exclude(is_on_hold=True)
            .select_related("category", "author")
            .order_by("-created_at")[:limit]
        )

    def _tier_page_posts(self, page_ids, exclude, limit=200):
        if not page_ids:
            return []
        return list(
            Post.objects.filter(page_id__in=page_ids)
            .exclude(id__in=exclude).exclude(is_on_hold=True)
            .select_related("category", "author", "page")
            .order_by("-created_at")[:limit]
        )

    # ------------------------------------------------------------------
    # Ads
    # ------------------------------------------------------------------

    def _targeted_ads(self, limit=20):
        from apps.ads.models import Ad
        ads = list(
            Ad.objects.filter(status="active", started_at__lte=self._now, ends_at__gte=self._now)
            .select_related("advertiser")[:50]
        )
        if not ads:
            return []
        profile = getattr(self.user, "activity_profile", None)
        country = getattr(profile, "country", "") if profile else ""
        interests = set(profile.interests.keys()) if profile else set()
        matched = []
        for ad in ads:
            if ad.target_gender != "all":
                g = getattr(profile, "inferred_gender", "") if profile else ""
                if g and ad.target_gender != g:
                    continue
            if ad.target_countries and country and country not in ad.target_countries:
                continue
            if ad.target_interests and interests and not interests.intersection(set(ad.target_interests)):
                continue
            matched.append(ad)
        random.shuffle(matched)
        return matched[:limit]

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------

    def get_feed(self, page=1, page_size=20, seen_ids=None):
        hidden = self._hidden_post_ids()
        blocked = self._blocked_author_ids()
        exclude_all = hidden | (set(seen_ids) if seen_ids else set())

        friend_ids = self._get_friend_ids()
        group_ids = self._get_group_ids()
        page_ids = self._get_followed_page_ids()
        country = self._get_user_country()

        # Build each tier (excluding blocked authors + already-seen posts)
        t1 = self._tier1(exclude_all)
        t2 = self._tier2(friend_ids, exclude_all)
        t3 = self._tier3(group_ids, exclude_all)
        t4 = self._tier4(country, exclude_all)
        t_page = self._tier_page_posts(page_ids, exclude_all)

        # ALL public posts (this catches everything — no author filter here)
        all_posts = self._all_posts(exclude_all)

        # Interleave: tier1, tier2, group-every-3-4, page posts, tier4, then remaining
        feed = self._merge(t1, t2, t3, t4, all_posts, t_page)

        # Recycled: if too few, show seen posts again
        if len(feed) < page_size and seen_ids:
            recycled = self._all_posts(hidden, limit=500)
            existing = {p.id for p in feed}
            for p in recycled:
                if p.id not in existing:
                    feed.append(p)
                    existing.add(p.id)

        # Inject ads
        ads = self._targeted_ads()
        feed = self._inject_ads(feed, ads)

        total = len(feed)
        start = (page - 1) * page_size
        end = start + page_size
        return feed[start:end], total

    # ------------------------------------------------------------------
    # Merge tiers → flat list
    # ------------------------------------------------------------------

    def _merge(self, t1, t2, t3, t4, all_posts, t_page=None):
        if t_page is None:
            t_page = []
        seen_ids = set()
        result = []

        # Collect ALL post IDs from tiers 1-4 + page so all_posts can exclude them
        tier14_ids = set()
        for lst in [t1, t2, t4, t_page]:
            for p in lst:
                tier14_ids.add(p.id)
        for p in t3:
            tier14_ids.add(p.id)

        # Remaining posts (not in any tier)
        remaining = [p for p in all_posts if p.id not in tier14_ids]

        # Priority order: t1, t2, remaining, page_posts, t4
        pools = [p for p in [t1, t2, remaining, t_page, t4] if p]
        group_pool = t3
        group_idx = 0
        since_group = 0
        pool_idx = 0

        if not pools and not group_pool:
            return result

        total = sum(len(p) for p in pools) + len(group_pool)
        max_iter = total + len(group_pool) + 10

        for _ in range(max_iter):
            # Pick from regular pools
            post = None
            if pools:
                attempts = 0
                while attempts < len(pools):
                    pool = pools[pool_idx % len(pools)]
                    if pool:
                        candidate = pool.pop(0)
                        if candidate.id not in seen_ids:
                            post = candidate
                            seen_ids.add(post.id)
                            break
                    pool_idx += 1
                    attempts += 1

            if post is None:
                break

            result.append(post)
            since_group += 1

            # Group post every 3 regular posts
            if since_group >= 3 and group_idx < len(group_pool):
                gpost = group_pool[group_idx]
                if gpost.id not in seen_ids:
                    result.append(gpost)
                    seen_ids.add(gpost.id)
                group_idx += 1
                since_group = 0

            pool_idx += 1

        # Drain remaining groups
        while group_idx < len(group_pool):
            gpost = group_pool[group_idx]
            if gpost.id not in seen_ids:
                result.append(gpost)
                seen_ids.add(gpost.id)
            group_idx += 1

        return result

    # ------------------------------------------------------------------
    # Ad injection
    # ------------------------------------------------------------------

    def _inject_ads(self, feed, ads, every_n=15):
        result = []
        ad_idx = 0
        post_count = 0
        for item in feed:
            result.append({"type": "post", "id": str(item.id)})
            post_count += 1
            if ads and post_count % every_n == 0 and ad_idx < len(ads):
                ad = ads[ad_idx]
                result.append({
                    "type": "ad", "id": str(ad.id),
                    "title": ad.title, "message": ad.message,
                    "image": ad.image.url if ad.image else None,
                    "cta_button": ad.cta_button,
                    "content_type": ad.content_type,
                    "content_id": str(ad.content_id),
                    "advertiser_id": str(ad.advertiser_id),
                })
                ad_idx += 1
        return result
