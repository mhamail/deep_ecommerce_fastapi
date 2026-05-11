from fastapi import APIRouter, Depends
from sqlalchemy.orm import selectinload
from sqlmodel import select

from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireDefaultShop,
)
from src.api.core.operation import listRecords, serialize_obj
from src.api.core.operation.media import uploadMediaFiles
from src.api.core.response import api_response, raiseExceptions
from src.api.models.order_model.orderItemModel import (
    OrderItem,
    OrderItemForm,
    OrderItemRead,
)
from src.api.models.order_model.orderModel import Order, OrderForm, OrderRead
from src.api.models.product_model.ProductVariantModel import ProductVariant
from src.api.models.product_model.productModel import Product

router = APIRouter(prefix="/order", tags=["Order"])


def get_shop_variant(session: GetSession, variant_id: int, shop_id: int):
    return session.exec(
        select(ProductVariant)
        .join(Product)
        .where(ProductVariant.id == variant_id, Product.shop_id == shop_id)
    ).first()


def build_order_item(
    data: dict,
    order_id: int,
    variant: ProductVariant | None = None,
    product: Product | None = None,
):
    item_data = {
        "order_id": order_id,
        "product_id": data.get("product_id"),
        "product_variant_id": data.get("product_variant_id"),
        "quantity": data.get("quantity") or 1,
    }

    if variant:
        item_data["product_id"] = variant.product_id
        item_data["product_name"] = variant.product.name
        item_data["variant_attributes"] = variant.attributes
        item_data["price"] = variant.discount_price or variant.price or 0
        item_data["image"] = variant.image
    elif product:
        item_data["product_id"] = product.id
        item_data["product_name"] = product.name
        item_data["variant_attributes"] = product.attributes
        item_data["price"] = product.discount_price or product.price or 0
        item_data["image"] = product.thumbnail
    else:
        item_data["product_name"] = data.get("product_name")
        item_data["variant_attributes"] = data.get("variant_attributes")
        item_data["price"] = data.get("price")
        item_data["image"] = data.get("image")

    raiseExceptions((item_data.get("product_name"), 400, "Product name is required"))
    raiseExceptions((item_data["price"] is not None, 400, "Price is required"))

    return OrderItem(**item_data)


@router.post("/create", response_model=OrderRead)
async def create_order(
    session: GetSession,
    request: OrderForm = Depends(),
):
    print(request.user_id)
    shop_id = request.shop_id
    raiseExceptions((shop_id, 400, "Shop ID is required"))
    user_id = request.user_id or None

    data = serialize_obj(request)
    items_data = data.pop("items", []) or []
    print("======<===============>======", items_data)

    data["user_id"] = user_id
    data["shop_id"] = shop_id
    order = Order(**data)
    session.add(order)
    session.flush()

    subtotal = 0
    for item_data in items_data:
        variant = None
        product = None
        variant_id = item_data.get("product_variant_id")
        if variant_id:
            variant = get_shop_variant(session, variant_id, shop_id)
            raiseExceptions((variant, 404, "Product Variant not found"))

        order_item = build_order_item(item_data, order.id, variant, product)
        subtotal += order_item.price * order_item.quantity
        session.add(order_item)

    if items_data:
        order.subtotal = subtotal
        order.total = subtotal - (order.discount or 0)
        session.add(order)

    session.commit()
    session.refresh(order)

    return api_response(
        201,
        "Order Created Successfully",
        OrderRead.model_validate(order),
    )


@router.post("/order-item/create/{order_id}", response_model=OrderItemRead)
async def create_order_item(
    order_id: int,
    session: GetSession,
    user: requireDefaultShop,
    request: OrderItemForm = Depends(),
):
    shop_id = user.get("default_shop_id")
    order = session.exec(
        select(Order).where(Order.id == order_id, Order.shop_id == shop_id)
    ).first()
    raiseExceptions((order, 404, "Order not found"))

    data = serialize_obj(request)
    await uploadMediaFiles(session, data, request)

    variant = None
    product = None
    if data.get("product_variant_id"):
        variant = get_shop_variant(session, data["product_variant_id"], shop_id)
        raiseExceptions((variant, 404, "Product Variant not found"))

    order_item = build_order_item(data, order_id, variant, product)
    session.add(order_item)

    order.subtotal = (order.subtotal or 0) + (order_item.price * order_item.quantity)
    order.total = order.subtotal - (order.discount or 0)
    session.add(order)

    session.commit()
    session.refresh(order_item)

    return api_response(
        201,
        "Order Item Created Successfully",
        OrderItemRead.model_validate(order_item),
    )


@router.get("/read/{id}", response_model=OrderRead)
def read_order(
    id: int,
    session: GetSession,
    user: requireDefaultShop,
):
    shop_id = user.get("default_shop_id")
    order = session.exec(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == id, Order.shop_id == shop_id)
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

    order_items = session.exec(select(OrderItem).where(OrderItem.order_id == id)).all()
    for item in order_items:
        session.delete(item)

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
        join_options=[selectinload(Order.items)],
        customFilters=[["shop_id", shop_id]],
    )
