def validate_default_shop(user_dict):
    default_shop = user_dict.default_shop

    if not default_shop:
        return None

    shop = user_dict.shop
    shops_member = user_dict.shop_memberships

    if shop and shop.id == default_shop.id:
        return default_shop.id

    if shops_member and any(s.shop_id == default_shop.id for s in shops_member):
        return default_shop.id

    return None
