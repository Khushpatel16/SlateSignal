from datetime import date

from slatesignal.domain.schemas import Genre, OptimizeRequest
from slatesignal.services.optimizer import GreenlightOptimizer


def test_optimizer_returns_three_editable_plans() -> None:
    request = OptimizeRequest(
        title="The Last Archive",
        synopsis=(
            "When every public record begins disappearing, a junior archivist discovers that her "
            "missing mother built a hidden library beneath the city. She must protect the final "
            "copies of human history before a private intelligence network rewrites the past."
        ),
        genres=[Genre.THRILLER, Genre.MYSTERY, Genre.DRAMA],
        target_budget=45_000_000,
        earliest_release=date(2027, 1, 1),
        latest_release=date(2028, 12, 31),
        risk_tolerance="balanced",
    )

    result = GreenlightOptimizer().optimize(request)

    assert [plan.id for plan in result.plans] == ["precision", "balanced", "event"]
    assert result.plans[0].request.budget < result.plans[1].request.budget
    assert result.plans[1].request.budget < result.plans[2].request.budget
    assert all(
        request.earliest_release <= plan.request.release_date <= request.latest_release
        for plan in result.plans
    )
    assert "Commercial balance" in result.recommendation
