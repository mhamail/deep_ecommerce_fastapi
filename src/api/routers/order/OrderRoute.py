from typing import Optional

from fastapi import APIRouter
from sqlalchemy.orm import selectinload
from sqlmodel import delete, select

from src.api.models.order_model.orderItemModel import OrderItem
from src.api.models.shop_model.ShopChildModel import ShopUser
from src.api.core.utility import parse_list
from src.config import BCC_EMAILS
from src.api.core.smtp import send_email, send_email_options
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireDefaultShop,
    requireSignin,
    requireAdmin,
)
from src.api.core.operation import listRecords
from src.api.core.response import api_response, raiseExceptions
from src.api.models.addressModel import UserAddress
from src.api.models.cart_model.cartItemModel import CartItem
from src.api.models.cart_model.cartModel import Cart
from src.api.models.order_model.orderModel import Order, OrderCreate, OrderRead
from src.api.models.product_model.ProductVariantModel import ProductVariant
from src.api.models.product_model.productModel import Product
from src.api.models.userModel import User
from src.templates.order_template import order_template

router = APIRouter(prefix="/order", tags=["Order"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def get_product_variant(session: GetSession, variant_id: int):
    return session.exec(
        select(ProductVariant)
        .options(selectinload(ProductVariant.product))
        .where(ProductVariant.id == variant_id)
    ).first()


def get_cart_items_by_ids(session: GetSession, cart_item_ids: list[int], user_id: int):
    """Fetch cart items that belong to the user's active carts."""
    return session.exec(
        select(CartItem)
        .join(Cart, CartItem.cart_id == Cart.id)
        .options(
            selectinload(CartItem.variant).selectinload(ProductVariant.product),
            selectinload(CartItem.cart),
        )
        .where(
            CartItem.id.in_(cart_item_ids),
            Cart.user_id == user_id,
            Cart.status == "active",
        )
    ).all()


def remove_variant_stock(variant: ProductVariant, quantity: int):
    raiseExceptions((quantity > 0, 400, "Quantity must be greater than 0"))
    raiseExceptions(
        (
            variant.stock >= quantity,
            400,
            f"Only {variant.stock} items available for {variant.product.name}",
        )
    )
    variant.stock -= quantity
    variant.is_in_stock = variant.stock > 0


def get_default_shipping_address(session: GetSession, user_id: int) -> Optional[dict]:
    """Build a shipping_address dict from the user's profile + default address."""
    addr = session.exec(
        select(UserAddress).where(
            UserAddress.user_id == user_id,
            UserAddress.default == 1,
        )
    ).first()

    raiseExceptions(
        (
            addr.address.get("details") and addr.address.get("phone"),
            400,
            "Shipping details/phone are required",
        )
    )
    return addr.address


def require_manual_shipping_address(data: dict):
    shipping_address = data.get("shipping_address") or {}

    data["shipping_address"] = {
        **shipping_address,
    }

    raiseExceptions(
        (
            data["shipping_address"].get("details"),
            400,
            "Shipping details are required for manual orders",
        )
    )


def insertOrderItems(session, items_data, order):
    order_items = [
        OrderItem(
            order_id=order.id,
            shop_id=item["shop_id"],
            product_variant_id=item["product_variant_id"],
            product_id=item["product_id"],
            product_name=item["product_name"],
            quantity=item["quantity"],
            price=item["price"],
            actual_price=item["actual_price"],
            variant_attributes=item["variant_attributes"],
            image=item["image"],
        )
        for item in items_data
    ]

    session.add_all(order_items)


def destock_product_variants(session, items_data):
    for item in items_data:
        variant = item.pop("variant")  # remove before save

        qty = item["quantity"]

        if variant.stock < qty:
            api_response(
                400, f"Only {variant.stock} units available for {variant.product.name}"
            )

        variant.stock -= qty
        variant.is_in_stock = variant.stock > 0
        session.add(variant)


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/create", response_model=OrderRead)
async def create_order(session: GetSession, request: OrderCreate):
    data = request.model_dump()

    # Strip fields that are not Order table columns
    cart_item_ids = data.pop("cart_item_ids", None) or []
    user_id = request.user_id or None
    # manuals
    manual_items_data = data.pop("items", []) or []

    # ─────────────────────────────────────────────
    # MODE 1 — Cart-based order
    # Send: cart_item_ids + user_id
    # Address auto-fetched from user's default address
    # ─────────────────────────────────────────────
    items_data = []

    if cart_item_ids:
        raiseExceptions((user_id, 400, "user_id is required for cart order"))

        cart_items = get_cart_items_by_ids(session, cart_item_ids, user_id)
        raiseExceptions((cart_items, 404, "No valid cart items found for this user"))

        # Auto-populate shipping from user's default address (skip if already provided)

        data["shipping_address"] = get_default_shipping_address(session, user_id)

        items_data = [
            {
                "variant": item.variant,
                "id": item.id,
                "product_variant_id": item.product_variant_id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "variant_attributes": item.variant_attributes,
                "shop_id": item.cart.shop_id,
                "image": item.image,
                "quantity": item.quantity,
                "price": item.price,
                "actual_price": item.actual_price,
            }
            for item in cart_items
        ]

    # ─────────────────────────────────────────────
    # MODE 2 — Manual order
    # ─────────────────────────────────────────────
    else:
        raiseExceptions((manual_items_data, 400, "items are required for manual order"))
        require_manual_shipping_address(data)

        for item in manual_items_data:
            variant = None
            variant_id = item.get("product_variant_id")
            if variant_id:
                variant = get_product_variant(session, variant_id)
                raiseExceptions(
                    (variant, 404, f"Product variant {variant_id} not found")
                )
                items_data.append(
                    {
                        "variant": variant,
                        "product_variant_id": variant.id,
                        "product_id": variant.product_id,
                        "quantity": item.get("quantity", 1),
                        "product_name": variant.product.name,
                        "variant_attributes": variant.attributes,
                        "shop_id": variant.product.shop_id,
                        "image": variant.image,
                        "price": variant.discount_price or variant.price,
                        "actual_price": variant.price,
                    }
                )

    raiseExceptions((items_data, 400, "Order must have at least one item"))

    data["user_id"] = user_id
    # ─────────────────────────────────────────────
    # deduct stock
    # ─────────────────────────────────────────────
    destock_product_variants(session, items_data)
    # ─────────────────────────────────────────────
    # Calculate totals
    # ─────────────────────────────────────────────
    subtotal = 0
    subtotal = sum(item["price"] * item["quantity"] for item in items_data)

    data["subtotal"] = subtotal
    data["total"] = subtotal - (data.get("discount") or 0)

    order = Order(**data)
    session.add(order)
    session.flush()  # get order id

    insertOrderItems(session, items_data, order)

    # ─────────────────────────────────────────────
    # Cart cleanup — delete ordered items,
    # remove cart if it becomes empty
    # ─────────────────────────────────────────────
    if cart_item_ids and cart_items:
        cart_ids_affected = {item.cart_id for item in cart_items}

        for item in cart_items:
            session.delete(item)
        session.flush()

        for cid in cart_ids_affected:
            remaining = session.exec(
                select(CartItem).where(CartItem.cart_id == cid)
            ).first()
            if not remaining:
                cart = session.get(Cart, cid)
                if cart:
                    session.delete(cart)

    order_read = OrderRead.model_validate(order)
    items = [item.model_dump() for item in order_read.items]
    shop_ids = list({item["shop_id"] for item in items if item.get("shop_id")})

    admin_emails = session.exec(
        select(User.email)
        .join(ShopUser, ShopUser.user_id == User.id)
        .where(
            ShopUser.shop_id.in_(shop_ids),
            ShopUser.is_active == True,
        )
        .distinct()
    ).all()

    # Admin Email Notification
    send_email_options(
        to_emails=admin_emails,
        bcc_emails=parse_list(BCC_EMAILS),
        subject=f"New Order #{order.id}",
        body=order_template(order, items),
    )

    session.commit()
    session.refresh(order)

    return api_response(201, "Order Created Successfully", order_read)


@router.get("/read/{id}", response_model=OrderRead)
def read_order(id: int, session: GetSession, user: requireSignin):

    order = session.exec(
        select(Order).where(Order.id == id, Order.user_id == user.get("id"))
    ).first()
    raiseExceptions((order, 404, "Order not found"))
    return api_response(200, "Order Found", OrderRead.model_validate(order))


@router.get("/read/admin/{id}", response_model=OrderRead)
def read_order(id: int, session: GetSession, user: requireAdmin):

    order = session.get(Order, id).first()
    raiseExceptions((order, 404, "Order not found"))
    return api_response(200, "Order Found", OrderRead.model_validate(order))


@router.delete("/delete/{id}")
def delete_order(id: int, session: GetSession, user: requireDefaultShop):
    shop_id = user.get("default_shop_id")
    order = session.exec(
        select(Order).where(Order.id == id, Order.shop_id == shop_id)
    ).first()
    raiseExceptions((order, 404, "Order not found"))
    session.delete(order)
    session.commit()
    return api_response(200, f"Order {order.order_number} deleted")


@router.get("/list", response_model=list[OrderRead])
def list_orders(query_params: ListQueryParams, user: requireSignin):
    query_params = vars(query_params)
    searchFields = ["order_number", "status", "payment_status"]
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Order,
        Schema=OrderRead,
        customFilters=[["user_id", user.get("id")]],
    )
