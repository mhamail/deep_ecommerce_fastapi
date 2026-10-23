from sqlmodel import func, select

from src.api.models.order_model.orderItemModel import OrderItem
from src.api.models.order_model.orderModel import Order
from src.api.models.product_model.productModel import Product
from src.api.models.review_model.reviewModel import ProductReview


def recompute_rating(session, product_id: int) -> None:
    """Refresh the product's stored rating aggregate from its reviews.

    Staged only (no commit) so it lands in the same transaction as the
    review write that triggered it."""
    rows = session.exec(
        select(ProductReview.rating, func.count())
        .where(ProductReview.product_id == product_id)
        .group_by(ProductReview.rating)
    ).all()

    breakdown = {str(star): 0 for star in range(1, 6)}
    for star, n in rows:
        breakdown[str(star)] = n

    count = sum(breakdown.values())
    total = sum(int(star) * n for star, n in breakdown.items())

    product = session.get(Product, product_id)
    if not product:
        return
    product.rating_count = count
    product.rating_average = round(total / count, 2) if count else 0
    product.rating_breakdown = breakdown
    session.add(product)


def has_delivered_purchase(session, user_id: int, product_id: int) -> bool:
    return (
        session.exec(
            select(OrderItem.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.user_id == user_id,
                OrderItem.product_id == product_id,
                OrderItem.status == "delivered",
            )
            .limit(1)
        ).first()
        is not None
    )
