PLAN_ORDER = ["tiny", "small", "medium", "large"]

# Models each plan can access (cumulative tiers)
PLAN_MODELS: dict[str, set[str]] = {
    "tiny":   {"tiny"},
    "small":  {"tiny", "small"},
    "medium": {"tiny", "small", "medium"},
    "large":  {"tiny", "small", "medium", "large"},
}

PLAN_PRICES: dict[str, int] = {
    "tiny":   0,
    "small":  5,
    "medium": 10,
    "large":  20,
}

VALID_PLANS = PLAN_ORDER  # ["tiny", "small", "medium", "large"]


def normalize_plan(plan: str) -> str:
    """Map legacy free/pro values to new plan names."""
    if plan == "free":
        return "tiny"
    if plan == "pro":
        return "large"
    if plan in PLAN_ORDER:
        return plan
    return "tiny"


def can_use_model(plan: str, model: str) -> bool:
    """Return True if the given plan allows access to the given model."""
    return model in PLAN_MODELS.get(normalize_plan(plan), {"tiny"})


def upgradeable_plans(current_plan: str) -> list[str]:
    """Return plans the user can upgrade to (higher than current)."""
    current = normalize_plan(current_plan)
    idx = PLAN_ORDER.index(current) if current in PLAN_ORDER else 0
    return PLAN_ORDER[idx + 1:]
