from sqlmodel import func, or_, select

from src.api.models.product_model.productModel import Product
from src.api.models.question_model.questionModel import ProductQuestion
from src.api.models.shop_model.ShopChildModel import ShopUser
from src.api.models.shop_model.shopModel import Shop
from src.api.models.userModel import User


def unanswered_questions_stmt(shop_id: int):
    """Questions on this shop's products that nobody has answered yet."""
    return (
        select(ProductQuestion)
        .join(Product, Product.id == ProductQuestion.product_id)
        .where(Product.shop_id == shop_id, ProductQuestion.answer.is_(None))
    )


def count_unanswered_questions(session, shop_id: int) -> int:
    return session.exec(
        select(func.count()).select_from(unanswered_questions_stmt(shop_id).subquery())
    ).one()


def shop_staff_emails(session, shop_id: int) -> list[str]:
    """The shop's owner plus its active members — who should hear about
    new questions."""
    return list(
        session.exec(
            select(User.email)
            .where(
                User.is_active == True,
                or_(
                    User.id.in_(select(Shop.owner_id).where(Shop.id == shop_id)),
                    User.id.in_(
                        select(ShopUser.user_id).where(
                            ShopUser.shop_id == shop_id, ShopUser.is_active == True
                        )
                    ),
                ),
            )
            .distinct()
        ).all()
    )
