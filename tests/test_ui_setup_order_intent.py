def test_setup_order_should_prioritize_task_roles_before_profile_and_overrides():
    order = [
        "task_roles",
        "profile",
        "theory",
        "override",
    ]

    assert order.index("task_roles") < order.index("profile")
    assert order.index("task_roles") < order.index("override")
    assert order.index("profile") < order.index("override")