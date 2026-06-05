from fastapi import APIRouter, Depends
from sqlalchemy.orm import selectinload
from sqlmodel import select

from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireDefaultShop,
)
from src.api.core.operation import listRecords, serialize_obj
from src.api.core.response import api_response, raiseExceptions
from src.api.models.cart_model.cartItemModel import CartItem
from src.api.models.cart_model.cartModel import Cart
from src.api.models.order_model.orderModel import Order, OrderForm, OrderRead
from src.api.models.product_model.ProductVariantModel import ProductVariant
from src.api.models.product_model.productModel import Product

router = APIRouter(prefix="/order", tags=["Order"])


def get_shop_variant(session: GetSession, variant_id: int, shop_id: int):
    return session.exec(
        select(ProductVariant)
        .options(selectinload(ProductVariant.product))
        .join(Product)
        .where(ProductVariant.id == variant_id, Product.shop_id == shop_id)
    ).first()


def get_user_cart(session: GetSession, cart_id: int, user_id: int):
    return session.exec(
        select(Cart)
        .options(
            selectinload(Cart.items)
            .selectinload(CartItem.variant)
            .selectinload(ProductVariant.product)
        )
        .where(Cart.id == cart_id, Cart.user_id == user_id, Cart.status == "active")
    ).first()


def build_order_item_snapshot(
    data: dict,
    variant: ProductVariant | None = None,
):
    item_data = {
        "product_variant_id": data.get("product_variant_id"),
        "quantity": data.get("quantity") or 1,
    }

    if variant:
        item_data["product_id"] = variant.product_id
        item_data["product_name"] = variant.product.name
        item_data["variant_attributes"] = variant.attributes
        item_data["price"] = variant.discount_price or variant.price or 0
        item_data["image"] = variant.image
    else:
        item_data["product_name"] = data.get("product_name")
        item_data["variant_attributes"] = data.get("variant_attributes")
        item_data["price"] = data.get("price")
        item_data["image"] = data.get("image")

    raiseExceptions((item_data.get("product_name"), 400, "Product name is required"))
    raiseExceptions((item_data["price"] is not None, 400, "Price is required"))
    raiseExceptions((item_data["quantity"] > 0, 400, "Quantity must be greater than 0"))

    item_data["line_total"] = item_data["price"] * item_data["quantity"]
    return item_data


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


@router.post("/create", response_model=OrderRead)
async def create_order(
    session: GetSession,
    request: OrderForm = Depends(),
):
    data = serialize_obj(request)
    cart_id = data.pop("cart_id", None)
    items_data = data.pop("items", []) or []
    user_id = request.user_id or None
    cart = None

    if cart_id:
        raiseExceptions((user_id, 400, "User ID is required for cart order"))
        cart = get_user_cart(session, cart_id, user_id)
        raiseExceptions((cart, 404, "Cart not found"))
        raiseExceptions((cart.items, 400, "Cart is empty"))

        shop_id = cart.shop_id
        items_data = [
            {
                "product_variant_id": item.product_variant_id,
                "quantity": item.quantity,
                "variant_attributes": item.variant_attributes,
                "image": item.image,
            }
            for item in cart.items
        ]
    else:
        shop_id = request.shop_id

    raiseExceptions((shop_id, 400, "Shop ID is required"))
    raiseExceptions((items_data, 400, "Order items are required"))

    data["user_id"] = user_id
    data["shop_id"] = shop_id

    subtotal = 0
    order_items = []
    for item_data in items_data:
        variant = None
        variant_id = item_data.get("product_variant_id")
        if variant_id:
            variant = get_shop_variant(session, variant_id, shop_id)
            raiseExceptions((variant, 404, "Product Variant not found"))
            remove_variant_stock(variant, item_data.get("quantity") or 1)
            session.add(variant)

        order_item = build_order_item_snapshot(item_data, variant)
        subtotal += order_item["line_total"]
        order_items.append(order_item)

    data["items"] = order_items
    data["subtotal"] = subtotal
    data["total"] = subtotal - (data.get("discount") or 0)

    order = Order(**data)
    session.add(order)

    if cart:
        session.delete(cart)

    session.commit()
    session.refresh(order)

    return api_response(
        201,
        "Order Created Successfully",
        OrderRead.model_validate(order),
    )


@router.get("/read/{id}", response_model=OrderRead)
def read_order(
    id: int,
    session: GetSession,
    user: requireDefaultShop,
):
    shop_id = user.get("default_shop_id")
    order = session.exec(
        select(Order).where(Order.id == id, Order.shop_id == shop_id)
    ).first()
    raiseExceptions((order, 404, "Order not found"))

    return api_response(200, "Order Found", OrderRead.model_validate(order))


@router.delete("/delete/{id}")
def delete_order(
    id: int,
    session: GetSession,
    user: requireDefaultShop,
):
    shop_id = user.get("default_shop_id")
    order = session.exec(
        select(Order).where(Order.id == id, Order.shop_id == shop_id)
    ).first()
    raiseExceptions((order, 404, "Order not found"))

    session.delete(order)
    session.commit()

    return api_response(200, f"The Order {order.order_number} deleted")


@router.get("/list", response_model=list[OrderRead])
def list_orders(
    query_params: ListQueryParams,
    user: requireDefaultShop,
):
    shop_id = user.get("default_shop_id")
    query_params = vars(query_params)
    searchFields = ["order_number", "status", "payment_status"]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Order,
        Schema=OrderRead,
        customFilters=[["shop_id", shop_id]],
    )
