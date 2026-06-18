from fastapi import APIRouter
from sqlmodel import select

from src.api.core.dependencies import GetSession, ListQueryParams, requireDefaultShop
from src.api.core.operation import listRecords
from src.api.core.response import api_response, raiseExceptions
from src.api.models.order_model.orderItemModel import (
    OrderItem,
    OrderItemsRead,
)

router = APIRouter(prefix="/order-item", tags=["Order Item"])


@router.get("/list", response_model=list[OrderItemsRead])
def list_order_items(query_params: ListQueryParams, user: requireDefaultShop):
    shop_id = user.get("default_shop_id")
    query_params = vars(query_params)
    return listRecords(
        query_params=query_params,
        searchFields=["product_name"],
        Model=OrderItem,
        Schema=OrderItemsRead,
        customFilters=[["shop_id", shop_id]],
    )


@router.get("/read/{id}", response_model=OrderItemsRead)
def read_order_item(id: int, session: GetSession, user: requireDefaultShop):
    shop_id = user.get("default_shop_id")
    item = session.exec(
        select(OrderItem).where(OrderItem.id == id, OrderItem.shop_id == shop_id)
    ).first()
    raiseExceptions((item, 404, "Order item not found"))
    return api_response(200, "Order item found", OrderItemsRead.model_validate(item))
