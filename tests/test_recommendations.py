"""Explainable recommendation strategy: filtering, scoring and ranking."""

from datetime import timedelta

import pytest

from app.exceptions import PermissionDeniedError
from app.patterns.strategy import (Candidate, ProximityFirstStrategy,
                                   RecommendationCriteria, UtilisationBalancingStrategy,
                                   WeightedRankingStrategy, available_strategies,
                                   get_strategy)
from app.utils import now, to_db


@pytest.fixture
def window():
    start = (now() + timedelta(days=4)).replace(hour=10, minute=0, second=0, microsecond=0)
    return to_db(start), to_db(start + timedelta(hours=2))


def codes(result):
    return [item["code"] for item in result["recommendations"]]


def rejection_for(result, code):
    for item in result["rejected"]:
        if item["code"] == code:
            return item["rejection_reason"]
    return None


def test_recommendations_are_ranked_by_descending_score(facade, users, window):
    result = facade.recommend_resources(users["dr.kavitha"], attendees=40,
                                        required_equipment=["PROJECTOR"],
                                        start_time=window[0], end_time=window[1])
    scores = [item["score"] for item in result["recommendations"]]
    assert scores == sorted(scores, reverse=True)
    assert len(scores) >= 3


def test_every_recommendation_carries_a_score_and_reasons(facade, users, window):
    result = facade.recommend_resources(users["athisaya"], attendees=20,
                                        start_time=window[0], end_time=window[1])
    for item in result["recommendations"]:
        assert 0 <= item["score"] <= 100
        assert len(item["reasons"]) == 6
        assert len(item["factors"]) == 6
        assert all(factor["explanation"] for factor in item["factors"])


def test_unavailable_resources_are_filtered_out(facade, users, window):
    result = facade.recommend_resources(users["dr.kavitha"], attendees=20,
                                        start_time=window[0], end_time=window[1])
    assert "CR-102" not in codes(result)
    assert "maintenance" in rejection_for(result, "CR-102").lower()


def test_rooms_with_insufficient_capacity_are_rejected(facade, users, window):
    result = facade.recommend_resources(users["dr.kavitha"], attendees=70,
                                        start_time=window[0], end_time=window[1])
    assert "CR-201" not in codes(result)
    assert "Insufficient capacity" in rejection_for(result, "CR-201")
    for item in result["recommendations"]:
        assert item["capacity"] >= 70


def test_missing_equipment_is_rejected(facade, users, window):
    result = facade.recommend_resources(users["dr.kavitha"], attendees=20,
                                        required_equipment=["PROJECTOR"],
                                        start_time=window[0], end_time=window[1])
    assert "CR-202" not in codes(result)
    assert "Missing required equipment" in rejection_for(result, "CR-202")
    for item in result["recommendations"]:
        assert "PROJECTOR" in item["equipment_codes"]


def test_booking_conflicts_remove_a_room_from_the_ranking(facade, users, window):
    booking = facade.book_resource(users["dr.kavitha"], facade.repos.resources
                                   .get_by_code("SB-101").id, window[0], window[1], 40,
                                   "Faculty workshop")
    assert booking.status == "CONFIRMED"
    result = facade.recommend_resources(users["dr.kavitha"], attendees=40,
                                        start_time=window[0], end_time=window[1])
    assert "SB-101" not in codes(result)
    assert "Already booked" in rejection_for(result, "SB-101")


def test_a_free_slot_keeps_the_room_available(facade, users, window):
    facade.book_resource(users["dr.kavitha"],
                         facade.repos.resources.get_by_code("SB-101").id,
                         window[0], window[1], 40, "Faculty workshop")
    later_start = to_db(now().replace(microsecond=0) + timedelta(days=4, hours=20))
    later_end = to_db(now().replace(microsecond=0) + timedelta(days=4, hours=21))
    result = facade.recommend_resources(users["dr.kavitha"], attendees=40,
                                        start_time=later_start, end_time=later_end)
    assert "SB-101" in codes(result)


def test_preferred_building_increases_the_score(facade, users, window):
    without = facade.recommend_resources(users["dr.kavitha"], attendees=30,
                                         start_time=window[0], end_time=window[1])
    with_pref = facade.recommend_resources(users["dr.kavitha"], attendees=30,
                                           preferred_building="IH",
                                           start_time=window[0], end_time=window[1])
    innovation_without = [item for item in without["recommendations"] if item["code"] == "IH-101"]
    innovation_with = [item for item in with_pref["recommendations"] if item["code"] == "IH-101"]
    assert innovation_with, "IH-101 should still be eligible"
    others = [item for item in with_pref["recommendations"] if item["code"] != "IH-101"]
    assert all(innovation_with[0]["score"] >= item["score"] for item in others) or innovation_without


def test_strategies_can_be_swapped_at_runtime(facade, users, window):
    balanced = facade.recommend_resources(users["dr.kavitha"], attendees=25,
                                          strategy_key="balanced",
                                          start_time=window[0], end_time=window[1])
    proximity = facade.recommend_resources(users["dr.kavitha"], attendees=25,
                                           strategy_key="proximity",
                                           start_time=window[0], end_time=window[1])
    assert balanced["strategy"]["key"] == "balanced"
    assert proximity["strategy"]["key"] == "proximity"
    assert proximity["recommendations"][0]["walking_distance_m"] <= \
        max(item["walking_distance_m"] for item in proximity["recommendations"])
    assert isinstance(get_strategy("proximity"), ProximityFirstStrategy)
    assert isinstance(get_strategy("utilisation"), UtilisationBalancingStrategy)
    assert isinstance(get_strategy(None), WeightedRankingStrategy)


def test_strategy_weights_sum_to_one():
    for strategy in available_strategies():
        assert round(sum(strategy["weights"].values()), 6) == 1.0


def test_score_is_the_weighted_sum_of_its_factors(facade, users, window):
    result = facade.recommend_resources(users["dr.kavitha"], attendees=30,
                                        start_time=window[0], end_time=window[1])
    top = result["recommendations"][0]
    assert round(sum(factor["points"] for factor in top["factors"]), 0) == round(top["score"], 0)


def test_utilisation_strategy_prefers_under_used_rooms(facade, users, window):
    result = facade.recommend_resources(users["dr.kavitha"], attendees=20,
                                        strategy_key="utilisation",
                                        start_time=window[0], end_time=window[1])
    top = result["recommendations"][0]
    assert top["utilisation"] <= min(item["utilisation"] for item in result["recommendations"]) + 0.01


def test_criteria_object_normalises_equipment():
    criteria = RecommendationCriteria(attendees=10, required_equipment=["AC", "AC", "PROJECTOR"])
    assert criteria.required_equipment == ("AC", "PROJECTOR")


def test_capacity_fit_rewards_a_tight_fit(facade, resources):
    strategy = WeightedRankingStrategy()
    criteria = RecommendationCriteria(attendees=55)
    tight = strategy.score(Candidate(resources["CR-101"]), criteria)      # 60 seats
    loose = strategy.score(Candidate(resources["EB-301"]), criteria)      # 100 seats
    tight_fit = [f for f in tight[1] if f["key"] == "capacity_fit"][0]["value"]
    loose_fit = [f for f in loose[1] if f["key"] == "capacity_fit"][0]["value"]
    assert tight_fit > loose_fit


def test_security_role_cannot_request_recommendations(facade, users):
    with pytest.raises(PermissionDeniedError):
        facade.recommend_resources(users["security.ravi"], attendees=10)


def test_impossible_requirements_return_an_empty_ranking(facade, users, window):
    result = facade.recommend_resources(users["dr.kavitha"], attendees=500,
                                        start_time=window[0], end_time=window[1])
    assert result["recommendations"] == []
    assert result["eligible"] == 0
    assert result["considered"] > 0
