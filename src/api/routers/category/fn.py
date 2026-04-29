from typing import Optional

from sqlmodel import delete, select

from src.api.core.response import api_response
from src.api.models.category_model import Category


def calculate_category_level(session, parent_id: Optional[int]) -> int:
    if not parent_id:
        return 1  # root level

    parent = session.get(Category, parent_id)
    if not parent:
        return api_response(400, "Parent category not found")

    if parent.level >= 3:
        return api_response(400, "Cannot create a category deeper than 3 levels")

    return parent.level + 1


def build_category_tree(categories):
    """
    Convert flat category list into nested tree:
    Level 1 -> Level 2 -> Level 3
    """

    category_map = {}
    tree = []

    # Step 1: Convert to dict + prepare children list
    for cat in categories:
        item = cat.model_dump() if hasattr(cat, "model_dump") else dict(cat)
        item["children"] = []
        category_map[item["id"]] = item

    # Step 2: Build hierarchy
    for cat_id, cat in category_map.items():
        parent_id = cat.get("parent_id")

        if parent_id and parent_id in category_map:
            category_map[parent_id]["children"].append(cat)
        else:
            # No parent → Level 1
            tree.append(cat)

    return tree


def collect_category_ids(session, category_id: int, ids: list):
    ids.append(category_id)

    children = session.exec(
        select(Category.id).where(Category.parent_id == category_id)
    ).all()

    for child_id in children:
        collect_category_ids(session, child_id, ids)


def delete_category_tree(session, category_id: int):
    """
    Recursively delete a category and all its children (safe from circular dependency).
    """

    # Get children IDs only (lightweight)
    children = session.exec(
        select(Category.id).where(Category.parent_id == category_id)
    ).all()

    # Delete children first
    for child_id in children:
        delete_category_tree(session, child_id)

    # Delete current node using SQL (NOT ORM)
    session.exec(delete(Category).where(Category.id == category_id))
