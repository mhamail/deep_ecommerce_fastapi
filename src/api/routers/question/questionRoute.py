from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Query
from sqlalchemy.orm import selectinload
from sqlmodel import func, select

from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireShopPermission,
    requireSignin,
)
from src.api.core.operation import listRecords
from src.api.core.response import api_response, raiseExceptions
from src.api.core.security import get_user_permissions
from src.api.core.smtp import send_email_options
from src.api.core.utility import parse_list
from src.api.models.product_model.productModel import Product
from src.api.models.question_model.questionModel import (
    PendingQuestions,
    ProductQuestion,
    QuestionAnswer,
    QuestionCreate,
    QuestionRead,
    ShopQuestionRead,
)
from src.api.routers.question.fn import (
    count_unanswered_questions,
    shop_staff_emails,
    unanswered_questions_stmt,
)
from src.config import BCC_EMAILS
from src.templates.question_template import question_template

router = APIRouter(prefix="/question", tags=["Question"])

PUBLIC_PAGE_LIMIT = 50
ADMIN_PERMISSIONS = {"system:*"}


# ==========================================================================
# helpers
# ==========================================================================
def _active_product(session, product_id: int) -> Product:
    product = session.get(Product, product_id)
    raiseExceptions((product and product.is_active, 404, "Product not found"))
    return product


def _is_site_admin(user: dict) -> bool:
    return bool(user.get("is_root") or get_user_permissions(user) & ADMIN_PERMISSIONS)


def _owns_product(user: dict, product: Product) -> bool:
    return user.get("default_shop_id") == product.shop_id


def _page(stmt, page: int, limit: int):
    return stmt.offset((page - 1) * limit).limit(limit)


# ==========================================================================
# public / signed-in customer
# ==========================================================================
@router.get("/public/{product_id}")
def public_questions(
    product_id: int,
    session: GetSession,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=PUBLIC_PAGE_LIMIT),
):
    stmt = select(ProductQuestion).where(ProductQuestion.product_id == product_id)
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    rows = session.exec(
        _page(
            stmt.options(selectinload(ProductQuestion.user)).order_by(
                ProductQuestion.created_at.desc(), ProductQuestion.id.desc()
            ),
            page,
            limit,
        )
    ).all()

    return api_response(
        200, "Questions found", [QuestionRead.model_validate(q) for q in rows], total
    )


@router.post("/create/{product_id}")
def create_question(
    product_id: int,
    request: QuestionCreate,
    session: GetSession,
    user: requireSignin,
    background_tasks: BackgroundTasks,
):
    product = _active_product(session, product_id)
    question = ProductQuestion(
        product_id=product_id,
        user_id=user["id"],
        question=request.question.strip(),
    )
    session.add(question)
    session.commit()
    session.refresh(question)

    # Tell the shop. Recipients and body are resolved here (the session is
    # closed by the time a background task runs); the SMTP round trip itself
    # runs after the response so a slow/failed mail server never blocks or
    # fails the customer's post.
    recipients = shop_staff_emails(session, product.shop_id)
    if recipients:
        background_tasks.add_task(
            send_email_options,
            to_emails=recipients,
            bcc_emails=parse_list(BCC_EMAILS),
            subject=f"New question on {' '.join(product.name.split())}"[:150],
            body=question_template(
                product.name, question.question, question.author_name
            ),
        )

    return api_response(200, "Question posted", QuestionRead.model_validate(question))


@router.delete("/delete/{id}")
def delete_question(id: int, session: GetSession, user: requireSignin):
    """The asker, the product's shop, or a site admin."""
    question = session.get(ProductQuestion, id)
    raiseExceptions((question, 404, "Question not found"))
    product = session.get(Product, question.product_id)
    if not (
        question.user_id == user["id"]
        or _is_site_admin(user)
        or (product and _owns_product(user, product))
    ):
        api_response(403, "You can only delete your own question")

    session.delete(question)
    session.commit()

    return api_response(200, "Question deleted")


# ==========================================================================
# questions — shop side
# ==========================================================================
@router.get("/list")
def shop_questions(
    query_params: ListQueryParams,
    status: Literal["unanswered", "answered"] | None = Query(None),
    user=requireShopPermission(["product:read", "product:update"]),
):
    """Questions on the caller's own shop's products (newest first),
    optionally only the unanswered / answered ones."""
    shop_id = user.get("default_shop_id")

    def scope(stmt, _Model):
        stmt = stmt.join(Product, Product.id == ProductQuestion.product_id).where(
            Product.shop_id == shop_id
        )
        if status == "unanswered":
            stmt = stmt.where(ProductQuestion.answer.is_(None))
        elif status == "answered":
            stmt = stmt.where(ProductQuestion.answer.is_not(None))
        return stmt

    return listRecords(
        query_params=vars(query_params),
        searchFields=["question", "answer"],
        Model=ProductQuestion,
        Schema=ShopQuestionRead,
        join_options=[
            selectinload(ProductQuestion.user),
            selectinload(ProductQuestion.product),
        ],
        otherFilters=scope,
    )


@router.get("/pending")
def pending_questions(
    session: GetSession,
    user=requireShopPermission(["product:read", "product:update"]),
):
    """Header bell: unanswered count + the newest few."""
    shop_id = user.get("default_shop_id")
    latest = session.exec(
        unanswered_questions_stmt(shop_id)
        .options(
            selectinload(ProductQuestion.user), selectinload(ProductQuestion.product)
        )
        .order_by(ProductQuestion.created_at.desc(), ProductQuestion.id.desc())
        .limit(5)
    ).all()
    return api_response(
        200,
        "Pending questions",
        PendingQuestions(
            count=count_unanswered_questions(session, shop_id),
            latest=[ShopQuestionRead.model_validate(q) for q in latest],
        ),
    )


@router.put("/answer/{id}")
def answer_question(
    id: int,
    request: QuestionAnswer,
    session: GetSession,
    user=requireShopPermission(["product:update"]),
):
    question = session.get(ProductQuestion, id)
    raiseExceptions((question, 404, "Question not found"))
    product = session.get(Product, question.product_id)
    if not product or not _owns_product(user, product):
        api_response(403, "You can only answer questions on your own products")

    question.answer = request.answer.strip()
    question.answered_by = user["id"]
    question.answered_at = datetime.now(timezone.utc)
    question.updated_at = question.answered_at
    session.add(question)
    session.commit()
    session.refresh(question)

    return api_response(200, "Answer saved", QuestionRead.model_validate(question))
