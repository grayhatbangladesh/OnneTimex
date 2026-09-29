from datetime import timedelta

from django.db import connection
from django.db.models import Q
from django.utils import timezone

from apps.MeetSoc.models import Group, Page, Post, RecentSearch
from apps.accounts.models import User


def _people_rows(qs):
    """Serialize user rows.

    `full_name` is a Python @property on the User model, NOT a DB column, so it
    can never be used in filter()/values()/SearchVector — build it in Python.
    """
    rows = []
    for r in qs.values("id", "username", "first_name", "last_name"):
        rows.append(
            {
                "id": str(r.get("id")),
                "username": r.get("username") or "",
                "full_name": " ".join(
                    x for x in [r.get("first_name"), r.get("last_name")] if x
                ).strip(),
            }
        )
    return rows


def _personalize_post_search_results(user, rows, query: str):
    """Boost rows using last-3-day search history + top category interests."""
    if not rows:
        return rows
    try:
        from apps.MeetSoc.services.interest_services import InterestService

        preferred = set(InterestService.get_top_category_ids(user, 12))
    except Exception:
        preferred = set()
    since = timezone.now() - timedelta(days=3)
    recent_qs = RecentSearch.objects.filter(user=user, created_at__gte=since).values_list(
        "query", flat=True
    )[:40]
    recent_terms = set()
    for q in recent_qs:
        for w in (q or "").lower().split():
            if len(w) > 2:
                recent_terms.add(w)
    qwords = {w for w in query.lower().split() if len(w) > 1}

    def score_row(r):
        s = 0.0
        cid = r.get("category_id")
        if cid and str(cid) in preferred:
            s += 4.0
        content = (r.get("content") or "").lower()
        blob = recent_terms | qwords
        for t in blob:
            if t and t in content:
                s += 0.8
        return s

    ranked = sorted(rows, key=lambda r: (-score_row(r), str(r.get("id"))))
    return ranked


class SearchService:
    def search(self, query, user, search_type="all", page=1):
        results = {"people": [], "posts": [], "groups": [], "pages": []}
        if not query or len(query.strip()) < 2:
            return results
        qstr = query.strip()
        use_fts = connection.vendor == "postgresql"

        if use_fts:
            from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

            q = SearchQuery(query)

        if search_type in ("all", "people"):
            if use_fts:
                vector = (
                    SearchVector("first_name", weight="A")
                    + SearchVector("last_name", weight="A")
                    + SearchVector("username", weight="B")
                )
                qs = (
                    User.objects.annotate(rank=SearchRank(vector, q))
                    .filter(rank__gt=0.05)
                    .order_by("-rank")[:10]
                )
                people = _people_rows(qs)
                if not people:
                    people = _people_rows(
                        User.objects.filter(
                            Q(username__icontains=qstr)
                            | Q(first_name__icontains=qstr)
                            | Q(last_name__icontains=qstr)
                        )[:10]
                    )
            else:
                people = _people_rows(
                    User.objects.filter(
                        Q(username__icontains=qstr)
                        | Q(first_name__icontains=qstr)
                        | Q(last_name__icontains=qstr)
                    )[:10]
                )
            results["people"] = people

        if search_type in ("all", "posts"):
            if use_fts:
                from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

                q = SearchQuery(query)
                vector = SearchVector("content")
                qs = (
                    Post.objects.annotate(rank=SearchRank(vector, q))
                    .filter(rank__gt=0.05, privacy="public")
                    .order_by("-rank")[:20]
                )
                raw = list(qs.values("id", "content", "author_id", "category_id"))
                results["posts"] = _personalize_post_search_results(user, raw, qstr)[:10]
            else:
                raw = list(
                    Post.objects.filter(privacy="public", content__icontains=qstr).values(
                        "id", "content", "author_id", "category_id"
                    )[:20]
                )
                results["posts"] = _personalize_post_search_results(user, raw, qstr)[:10]

        if search_type in ("all", "groups"):
            if use_fts:
                from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

                q = SearchQuery(query)
                vector = SearchVector("name", weight="A") + SearchVector("description", weight="B")
                qs = (
                    Group.objects.annotate(rank=SearchRank(vector, q))
                    .filter(rank__gt=0.05)
                    .order_by("-rank")[:10]
                )
                results["groups"] = list(qs.values("id", "name", "slug"))
            else:
                results["groups"] = list(
                    Group.objects.filter(Q(name__icontains=qstr) | Q(description__icontains=qstr)).values(
                        "id", "name", "slug"
                    )[:10]
                )

        if search_type in ("all", "pages"):
            if use_fts:
                from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

                q = SearchQuery(query)
                vector = SearchVector("name", weight="A") + SearchVector("description", weight="B")
                qs = (
                    Page.objects.annotate(rank=SearchRank(vector, q))
                    .filter(rank__gt=0.05)
                    .order_by("-rank")[:10]
                )
                results["pages"] = list(qs.values("id", "name", "slug"))
            else:
                results["pages"] = list(
                    Page.objects.filter(Q(name__icontains=qstr) | Q(description__icontains=qstr)).values(
                        "id", "name", "slug"
                    )[:10]
                )

        return results
