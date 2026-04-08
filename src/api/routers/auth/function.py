def validate_default_shop(user_dict):
    default_shop = user_dict.get("default_shop")

    if not default_shop:
        return None

    shop = user_dict.get("shop")
    shops_member = user_dict.get("shops_member")

    if shop and shop.get("id") == default_shop.get("id"):
        return default_shop.get("id")

    if shops_member and any(
        s.get("shop_id") == default_shop.get("id") for s in shops_member
    ):
        return default_shop.get("id")

    return None
