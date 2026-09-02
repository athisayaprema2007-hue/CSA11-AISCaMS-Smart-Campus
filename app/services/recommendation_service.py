"""Intelligent, explainable resource recommendation.

Hard constraints (availability, capacity, equipment, booking conflicts) are
applied first and every rejected resource keeps the reason it was rejected.
The surviving candidates are then ranked by the selected
`RecommendationStrategy`, so the ranking policy can change without touching
this service.
"""

from ..domain.users import Permission
from ..exceptions import PermissionDeniedError, ValidationError
from ..patterns.strategy import (Candidate, RecommendationCriteria,
                                 available_strategies, get_strategy)
from ..utils import human_clock, parse_datetime


class RecommendationService:
    """Filters, scores and explains campus resource suggestions."""

    def __init__(self, resource_repository, booking_repository, iot_repository):
        self._resources = resource_repository
        self._bookings = booking_repository
        self._iot = iot_repository

    # ------------------------------------------------------------- helpers
    @staticmethod
    def strategies():
        return available_strategies()

    def _rejection(self, resource, reason):
        data = resource.to_dict()
        data["rejection_reason"] = reason
        return data

    # -------------------------------------------------------------- filter
    def filter_candidates(self, criteria):
        """Return (candidates, rejected) after applying every hard constraint."""
        pool = self._resources.list_resources(
            resource_type=None if criteria.resource_type in (None, "ANY")
            else criteria.resource_type,
            bookable_only=criteria.resource_type in (None, "ANY"))
        pool = [resource for resource in pool if resource.is_bookable()]

        busy_ids = set()
        if criteria.start_time and criteria.end_time:
            busy_ids = self._bookings.busy_resource_ids(criteria.start_time,
                                                        criteria.end_time)
        occupancy = self._iot.latest_occupancy_map()

        candidates = []
        rejected = []
        for resource in pool:
            if not resource.is_available():
                rejected.append(self._rejection(
                    resource, "Not available - current status is %s"
                    % resource.status.replace("_", " ").lower()))
                continue
            if not resource.matches_capacity(criteria.attendees):
                rejected.append(self._rejection(
                    resource, "Insufficient capacity - seats %d, %d attendees requested"
                    % (resource.capacity, criteria.attendees)))
                continue
            missing = resource.missing_equipment(criteria.required_equipment)
            if missing:
                rejected.append(self._rejection(
                    resource, "Missing required equipment: %s" % ", ".join(missing)))
                continue
            if resource.id in busy_ids:
                conflicts = self._bookings.conflicts(resource.id, criteria.start_time,
                                                     criteria.end_time)
                detail = ", ".join("%s-%s" % (human_clock(booking.start_time),
                                              human_clock(booking.end_time))
                                   for booking in conflicts) or "another booking"
                rejected.append(self._rejection(
                    resource, "Already booked during the requested slot (%s)" % detail))
                continue
            candidates.append(Candidate(resource, occupancy.get(resource.id)))
        return candidates, rejected

    # --------------------------------------------------------------- ranks
    def recommend(self, user, attendees=1, required_equipment=None,
                  preferred_building=None, start_time=None, end_time=None,
                  resource_type="CLASSROOM", strategy_key=None, limit=5):
        """Rank the resources that satisfy every hard constraint."""
        if user is not None and not user.has_permission(Permission.VIEW_RECOMMENDATIONS):
            raise PermissionDeniedError(
                "%s users cannot request resource recommendations." % user.role)
        if start_time and end_time:
            start_time = parse_datetime(start_time, "start time")
            end_time = parse_datetime(end_time, "end time")
            if end_time <= start_time:
                raise ValidationError("End time must be after the start time.",
                                      {"field": "end_time"})
        criteria = RecommendationCriteria(
            attendees=attendees, required_equipment=required_equipment,
            preferred_building=preferred_building, start_time=start_time,
            end_time=end_time, resource_type=resource_type)
        strategy = get_strategy(strategy_key)
        candidates, rejected = self.filter_candidates(criteria)
        ranked = strategy.rank(candidates, criteria)
        return {
            "criteria": criteria.to_dict(),
            "strategy": strategy.to_dict(),
            "considered": len(candidates) + len(rejected),
            "eligible": len(candidates),
            "recommendations": [item.to_dict() for item in ranked[:limit]],
            "rejected": rejected,
        }
