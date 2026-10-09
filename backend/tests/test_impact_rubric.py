from app.impact import rubric


def test_no_evidence_abstains():
    factors = rubric.extract_factors("The weather is nice today.")
    assert rubric.score(factors) is None


def test_quantified_loss_bands():
    small = rubric.score(rubric.extract_factors("Revenue fell 3 percent."))
    medium = rubric.score(rubric.extract_factors("Revenue fell 25 percent."))
    large = rubric.score(rubric.extract_factors("Revenue fell 60 percent."))
    assert small == 1
    assert medium == 5
    assert large == 7


def test_site_scope_without_quantification_scores_low():
    factors = rubric.extract_factors("A plant in Ohio halted operations briefly.")
    assert rubric.score(factors) == 3


def test_company_wide_broadens_band():
    site = rubric.score(rubric.extract_factors("Revenue fell 25 percent at one site."))
    broad = rubric.score(
        rubric.extract_factors("Revenue fell 25 percent across the company.")
    )
    assert broad > site


def test_continuity_threat_is_transformative():
    factors = rubric.extract_factors(
        "The company faces bankruptcy after defaulting on debt."
    )
    assert rubric.score(factors) == 9


def test_default_is_lower_score_in_band():
    # 25% loss -> band 5-6; must return the lower edge.
    assert rubric.score(rubric.extract_factors("Revenue fell 25 percent.")) == 5


def test_never_assigns_score_from_category_alone():
    factors = rubric.extract_factors("The company reported earnings today.")
    assert rubric.score(factors) is None


def test_explanation_names_factors():
    factors = rubric.extract_factors("Revenue fell 25 percent across the company.")
    impact = rubric.score(factors)
    explanation = rubric.explain(factors, impact)
    assert "25%" in explanation
    assert "company-wide" in explanation
    assert "not a prediction" in explanation
