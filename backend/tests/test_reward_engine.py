from services.reward_engine import calculate_reward


def test_recyclable_metal_earns_double_base_points():
    assert calculate_reward("METAL", 250, 0.95) == 50


def test_low_confidence_halves_reward_after_category_factor():
    # 200g => 20 base; PLASTIC factor 1.5 => 30; confidence penalty => 15.
    assert calculate_reward("PLASTIC", 200, 0.59) == 15


def test_other_uses_half_factor_and_truncates_to_integer_points():
    assert calculate_reward("OTHER", 190, 0.90) == 9


def test_missing_weight_or_confidence_is_safe():
    assert calculate_reward("ORGANIC", None, None) == 0
