"""Design patterns applied by AISCaMS: Strategy, Factory and Observer."""

from .factory import ServiceRequestFactory
from .observer import (AlertObserver, AuditTrailObserver, NotificationObserver,
                       Observer, Subject)
from .strategy import (Candidate, ProximityFirstStrategy, RecommendationCriteria,
                       RecommendationStrategy, ScoredRecommendation,
                       UtilisationBalancingStrategy, WeightedRankingStrategy,
                       available_strategies, get_strategy)

__all__ = [
    "ServiceRequestFactory", "Subject", "Observer", "NotificationObserver",
    "AlertObserver", "AuditTrailObserver", "RecommendationStrategy",
    "WeightedRankingStrategy", "ProximityFirstStrategy",
    "UtilisationBalancingStrategy", "RecommendationCriteria", "Candidate",
    "ScoredRecommendation", "get_strategy", "available_strategies",
]
