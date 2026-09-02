"""Strategy pattern - explainable resource recommendation.

The engine is deliberately *not* a trained machine-learning model.  It is an
explainable weighted-ranking strategy: every candidate resource is scored on a
fixed set of normalised factors, each factor contributes `weight x value`
points, and the reasons shown in the interface are generated from exactly the
same numbers that produced the score.

Swapping `RecommendationStrategy` implementations changes the ranking policy
without touching the service, the repositories or the user interface.
"""

from abc import ABC, abstractmethod

MAX_WALKING_DISTANCE_M = 500.0
#: Occupancy assumed when a room has no recent IoT occupancy reading.
UNKNOWN_OCCUPANCY_VALUE = 0.5


class RecommendationCriteria:
    """Immutable description of what the user is looking for."""

    def __init__(self, attendees=1, required_equipment=None, preferred_building=None,
                 start_time=None, end_time=None, resource_type="CLASSROOM"):
        self.attendees = int(attendees or 1)
        self.required_equipment = tuple(sorted(set(required_equipment or ())))
        self.preferred_building = preferred_building or None
        self.start_time = start_time
        self.end_time = end_time
        self.resource_type = resource_type

    def to_dict(self):
        return {
            "attendees": self.attendees,
            "required_equipment": list(self.required_equipment),
            "preferred_building": self.preferred_building,
            "resource_type": self.resource_type,
        }

    def __repr__(self):  # pragma: no cover - debugging helper
        return "<RecommendationCriteria attendees=%s equipment=%s>" % (
            self.attendees, ",".join(self.required_equipment) or "-")


class Candidate:
    """A resource that already passed every hard filter, plus live context."""

    def __init__(self, resource, occupancy_ratio=None, free_now=True):
        self.resource = resource
        #: Latest measured occupancy as a ratio of capacity (None when unknown).
        self.occupancy_ratio = occupancy_ratio
        self.free_now = free_now


class ScoredRecommendation:
    """Result object carrying the score and the reasons behind it."""

    def __init__(self, resource, score, factors, reasons, strategy_name):
        self.resource = resource
        self.score = score
        self.factors = factors
        self.reasons = reasons
        self.strategy_name = strategy_name

    @property
    def rank_key(self):
        return (-self.score, -self.resource.capacity, self.resource.code)

    def to_dict(self):
        data = self.resource.to_dict()
        data.update({
            "score": self.score,
            "reasons": list(self.reasons),
            "factors": list(self.factors),
            "strategy": self.strategy_name,
        })
        return data

    def __repr__(self):  # pragma: no cover - debugging helper
        return "<ScoredRecommendation %s %.1f>" % (self.resource.code, self.score)


class RecommendationStrategy(ABC):
    """Abstract ranking policy."""

    key = "abstract"
    label = "Abstract strategy"
    description = ""

    @abstractmethod
    def score(self, candidate, criteria):
        """Return (score_0_to_100, factor_breakdown, reasons)."""

    def rank(self, candidates, criteria):
        """Score every candidate and return them ordered best first."""
        results = []
        for candidate in candidates:
            score, factors, reasons = self.score(candidate, criteria)
            results.append(ScoredRecommendation(candidate.resource, score, factors,
                                                reasons, self.label))
        results.sort(key=lambda item: item.rank_key)
        return results

    def to_dict(self):
        return {"key": self.key, "label": self.label, "description": self.description,
                "weights": dict(getattr(self, "weights", {}))}


class WeightedRankingStrategy(RecommendationStrategy):
    """Weighted sum of normalised factors; every subclass tunes the weights."""

    key = "balanced"
    label = "Balanced smart match"
    description = ("Weighs capacity fit, equipment, live occupancy, historical "
                   "utilisation, preferred building and walking distance.")
    weights = {
        "capacity_fit": 0.25,
        "equipment_match": 0.20,
        "live_occupancy": 0.15,
        "past_utilisation": 0.15,
        "walking_distance": 0.15,
        "building_preference": 0.10,
    }

    FACTOR_LABELS = {
        "capacity_fit": "Capacity fit",
        "equipment_match": "Equipment match",
        "live_occupancy": "Current occupancy",
        "past_utilisation": "Previous utilisation",
        "walking_distance": "Walking distance",
        "building_preference": "Preferred building",
    }

    # ------------------------------------------------------------- factors
    @staticmethod
    def _capacity_fit(resource, criteria):
        capacity = max(resource.capacity, 1)
        ratio = min(criteria.attendees / float(capacity), 1.0)
        text = "Seats %d, needed %d (%.0f%% of the room is used)" % (
            resource.capacity, criteria.attendees, ratio * 100)
        return ratio, text

    @staticmethod
    def _equipment_match(resource, criteria):
        if criteria.required_equipment:
            matched = [code for code in criteria.required_equipment
                       if resource.has_equipment(code)]
            value = len(matched) / float(len(criteria.required_equipment))
            text = "Provides all requested equipment: %s" % ", ".join(matched) \
                if value >= 1 else "Provides %d of %d requested items" % (
                    len(matched), len(criteria.required_equipment))
        else:
            installed = len(resource.equipment_codes)
            value = min(installed / 4.0, 1.0)
            text = "Equipped with %d item(s): %s" % (
                installed, ", ".join(resource.equipment_codes) or "none")
        return value, text

    @staticmethod
    def _live_occupancy(candidate):
        ratio = candidate.occupancy_ratio
        if ratio is None:
            return UNKNOWN_OCCUPANCY_VALUE, "No live occupancy reading available"
        value = max(0.0, 1.0 - min(float(ratio), 1.0))
        return value, "Currently %.0f%% occupied according to IoT sensors" % (float(ratio) * 100)

    @staticmethod
    def _past_utilisation(resource):
        value = max(0.0, 1.0 - min(resource.utilisation, 1.0))
        return value, "Historical utilisation %.0f%% - %s" % (
            resource.utilisation * 100,
            "under-used, good for load balancing" if resource.utilisation < 0.6
            else "already heavily booked")

    @staticmethod
    def _walking_distance(resource):
        distance = float(resource.walking_distance_m)
        value = max(0.0, 1.0 - min(distance / MAX_WALKING_DISTANCE_M, 1.0))
        return value, "%d m walk from the main gate (%s)" % (
            int(distance), resource.building_name)

    @staticmethod
    def _building_preference(resource, criteria):
        if not criteria.preferred_building:
            return 1.0, "No building preference was specified"
        preferred = str(criteria.preferred_building).strip().upper()
        actual_code = (resource.building.code if resource.building else "") or ""
        actual_name = (resource.building_name or "").upper()
        if preferred in (actual_code.upper(), actual_name):
            return 1.0, "Located in the preferred building (%s)" % resource.building_name
        return 0.0, "Not in the preferred building (%s)" % resource.building_name

    # --------------------------------------------------------------- score
    def score(self, candidate, criteria):
        resource = candidate.resource
        values = {}
        texts = {}
        values["capacity_fit"], texts["capacity_fit"] = self._capacity_fit(resource, criteria)
        values["equipment_match"], texts["equipment_match"] = self._equipment_match(resource, criteria)
        values["live_occupancy"], texts["live_occupancy"] = self._live_occupancy(candidate)
        values["past_utilisation"], texts["past_utilisation"] = self._past_utilisation(resource)
        values["walking_distance"], texts["walking_distance"] = self._walking_distance(resource)
        values["building_preference"], texts["building_preference"] = self._building_preference(
            resource, criteria)

        factors = []
        total = 0.0
        for name, weight in self.weights.items():
            value = values[name]
            points = weight * value * 100.0
            total += points
            factors.append({
                "key": name,
                "label": self.FACTOR_LABELS[name],
                "weight": round(weight, 3),
                "value": round(value, 3),
                "points": round(points, 1),
                "explanation": texts[name],
            })
        factors.sort(key=lambda item: -item["points"])
        reasons = ["%s (+%.1f): %s" % (item["label"], item["points"], item["explanation"])
                   for item in factors]
        return round(total, 1), factors, reasons


class ProximityFirstStrategy(WeightedRankingStrategy):
    """Ranks nearby rooms first - useful between back-to-back classes."""

    key = "proximity"
    label = "Nearest available first"
    description = "Prioritises walking distance and the preferred building."
    weights = {
        "walking_distance": 0.40,
        "building_preference": 0.20,
        "capacity_fit": 0.15,
        "equipment_match": 0.15,
        "live_occupancy": 0.05,
        "past_utilisation": 0.05,
    }


class UtilisationBalancingStrategy(WeightedRankingStrategy):
    """Spreads demand across the campus by favouring under-used rooms."""

    key = "utilisation"
    label = "Least used first"
    description = "Prioritises low historical utilisation and low live occupancy."
    weights = {
        "past_utilisation": 0.35,
        "live_occupancy": 0.25,
        "capacity_fit": 0.20,
        "equipment_match": 0.10,
        "walking_distance": 0.05,
        "building_preference": 0.05,
    }


STRATEGIES = {
    WeightedRankingStrategy.key: WeightedRankingStrategy,
    ProximityFirstStrategy.key: ProximityFirstStrategy,
    UtilisationBalancingStrategy.key: UtilisationBalancingStrategy,
}

DEFAULT_STRATEGY = WeightedRankingStrategy.key


def get_strategy(key=None):
    """Factory helper returning a strategy instance for a key."""
    cls = STRATEGIES.get((key or DEFAULT_STRATEGY).lower(), WeightedRankingStrategy)
    return cls()


def available_strategies():
    return [cls().to_dict() for cls in
            (WeightedRankingStrategy, ProximityFirstStrategy, UtilisationBalancingStrategy)]
