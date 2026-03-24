<!-- Filter Methods -->

# My Filter List Code

## Route

```py
@router.get("/list", response_model=list[ProductRead])
def list(query_params: ListQueryParams):
    query_params = vars(query_params)
    searchFields = ["name", "description", "category.name"]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Product,
        Schema=ProductRead,
    )

```

## query param

```py
ListQueryParams = Annotated[dict, Depends(list_query_params)]
class list_query_params:
    def __init__(
        self,
        dateRange: Optional[str] = Query(
            None, description="Example : ['created_at', '01-01-2025', '01-12-2025']"
        ),
        numberRange: Optional[str] = Query(
            None, description="Example : ['amount', 0, 100000]"
        ),
        searchTerm: str | None = Query(None, description="Search term"),
        columnFilters: Optional[str] = Query(
            None, description="Example : '[['name','car'],['description','product']]"
        ),
        page: int = Query(1, description="Page number"),
        skip: int = Query(0, description="Number of items to skip"),
        limit: int = Query(10, description="Number of items to return"),
    ):
        self.dateRange = dateRange
        self.skip = skip
        self.limit = limit
        self.searchTerm = searchTerm
        self.columnFilters = columnFilters
        self.page = page
        self.numberRange = numberRange
```

## list function

```py
def listop(
    session: Session,
    Model: type[SQLModel],
    filters: dict[str, any],
    searchFields: List[str],
    join_options: list = [],
    page: int = None,
    skip: int = 0,
    limit: int = Query(10, ge=1, le=200),
    Statement=None,
    otherFilters=None,
):

    # Compute skip based on page
    if page is not None and page > 0:
        skip = (page - 1) * limit

    # ✅ Fix: avoid boolean check on SQLAlchemy statements
    statement = Statement if Statement is not None else select(Model)

    # Apply JOINs (like selectinload)
    if join_options:
        for option in join_options:
            statement = statement.options(option)

    searchTerm = filters.get("searchTerm")
    columnFilters = filters.get("columnFilters")
    dateRange = filters.get("dateRange")
    numberRange = filters.get("numberRange")
    customFilters = filters.get("customFilters")
    # Apply Filters
    statement = applyFilters(
        statement,
        Model=Model,
        searchTerm=searchTerm,
        searchFields=searchFields,
        columnFilters=columnFilters,
        dateRange=dateRange,
        numberRange=numberRange,
        customFilters=customFilters,
        otherFilters=otherFilters,
    )

    # Total count (before pagination)
    total = _exec(session, statement, Model)
    total_count = len(total)

    # Now apply pagination (skip/limit)
    paginated_stmt = statement.offset(skip).limit(limit)
    results = _exec(session, paginated_stmt, Model)

    return {"data": results, "total": total_count}


def listRecords(
    query_params: dict,
    searchFields: list[str],
    Model,
    customFilters: Optional[List[List[str]]] = None,
    join_options: list = [],
    Schema: type[SQLModel] = None,
    otherFilters=None,
    Statement=None,
):
    session = next(get_session())  # get actual Session object
    try:
        # Extract params from query dict
        dateRange = query_params.get("dateRange")
        numberRange = query_params.get("numberRange")
        searchTerm = query_params.get("searchTerm")
        columnFilters = query_params.get("columnFilters")
        page = int(query_params.get("page", 1))
        skip = int(query_params.get("skip", 0))
        limit = int(query_params.get("limit", 10))

        filters = {
            "searchTerm": searchTerm,
            "columnFilters": columnFilters,
            "dateRange": dateRange,
            "numberRange": numberRange,
            "customFilters": customFilters,
        }

        result = listop(
            session=session,
            Model=Model,
            searchFields=searchFields,
            filters=filters,
            skip=skip,
            page=page,
            limit=limit,
            join_options=join_options,
            otherFilters=otherFilters,
            Statement=Statement,
        )

        if not result["data"]:
            return api_response(404, "No Result found")
        # Convert each SQLModel Model instance into a ModelRead Pydantic model
        if not Schema:
            return result
        list_data = [Schema.model_validate(prod) for prod in result["data"]]
        return api_response(
            200,
            f"data found",
            list_data,
            result["total"],
        )
    except DataError as e:
        # This will catch OFFSET/limit errors and send proper API response
        return api_response(
            400,
            f"Invalid pagination values: {str(e).splitlines()[0]}",
        )
    finally:
        session.close()

```

## filter handles

```py
def _get_column_type(attr):
    # attr is InstrumentedAttribute of a column
    try:
        return attr.property.columns[0].type
    except Exception:
        return None  # relationship or something unexpected


def _is_string_type(t):
    return isinstance(t, (SATypes.String, SATypes.Text))


def _is_integer_type(t):
    return isinstance(t, (SATypes.Integer, SATypes.BigInteger, SATypes.SmallInteger))


def _is_numeric_type(t):
    return isinstance(
        t, (SATypes.Numeric, SATypes.Float, SATypes.DECIMAL)
    ) or _is_integer_type(t)


def _is_bool_type(t):
    return isinstance(t, SATypes.Boolean)


def _is_datetime_type(t):
    return isinstance(t, SATypes.DateTime)


def _coerce_value_for_column(col_type, value, col_name: str):
    """Coerce incoming value (possibly a string) to a Python value compatible with the column type."""
    if col_type is None:
        # Fallback – treat as string
        return value

    if _is_numeric_type(col_type):
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            v = value.strip()
            try:
                if _is_integer_type(col_type):
                    return int(v)
                else:
                    return float(v)
            except ValueError:
                raise api_response(
                    400,
                    f"Column '{col_name}' expects a number; got '{value}'.",
                )
        raise api_response(400, f"Column '{col_name}' expects a number.")
    elif _is_bool_type(col_type):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ("true", "1", "yes"):
                return True
            if v in ("false", "0", "no"):
                return False
        raise api_response(400, f"Column '{col_name}' expects a boolean.")
    elif _is_datetime_type(col_type):
        if isinstance(value, str):
            # reuse your existing parse_date
            return parse_date(value)
        raise api_response(400, f"Column '{col_name}' expects a datetime string.")
    else:
        # string-like or other -> ensure string
        return str(value) if not isinstance(value, str) else value


def resolve_column(Model, col: str, statement):  # nested object filter
    """
    Given 'product.owner.role.title', return (attr, updated_statement).
    """
    parts = col.split(".")
    current_model = Model
    attr = None

    for i, part in enumerate(parts):  # enumerate = index + value in one go
        mapper_attr = getattr(current_model, part)

        if hasattr(mapper_attr, "property") and hasattr(mapper_attr.property, "mapper"):
            # It's a relationship -> join it
            related_model = mapper_attr.property.mapper.class_
            statement = statement.join(mapper_attr, isouter=True)
            current_model = related_model
        else:
            # It's a column
            attr = mapper_attr

    return attr, statement


def applyFilters(
    statement: SelectOfScalar,
    Model: type[SQLModel],
    searchTerm: Optional[str] = None,
    searchFields: Optional[List[str]] = None,
    columnFilters: Optional[List[List[str]]] = None,
    dateRange: Optional[List[str]] = None,
    numberRange: Optional[List[str]] = None,
    customFilters: Optional[List[List[str]]] = None,
    otherFilters=None,
    sort: Optional[str] = None,
):
    if otherFilters:
        # pass the current statement through the hook
        statement = otherFilters(statement, Model)
    # Global search
    if searchTerm and searchFields:
        # search_filters = [
        #     getattr(Model, field).ilike(f"%{searchTerm}%") for field in searchTerms
        # ]
        search_filters = []
        for col in searchFields:
            attr, statement = resolve_column(Model, col, statement)
            search_filters.append(attr.ilike(f"%{searchTerm}%"))
        statement = statement.where(or_(*search_filters))

    # Column-specific search
    if columnFilters:
        try:
            parsed_terms = ast.literal_eval(columnFilters)
            columnFilters = [tuple(sublist) for sublist in parsed_terms]

            # Group filters by column name
            grouped = {}
            for col, value in columnFilters:
                grouped.setdefault(col, []).append(value)

            filters = []
            for col, values in grouped.items():
                attr, statement = resolve_column(Model, col, statement)
                col_type = _get_column_type(attr)

                coerced_values = [
                    _coerce_value_for_column(col_type, v, col) for v in values
                ]

                # If multiple values → OR
                ors = []
                for v in coerced_values:
                    if isinstance(v, str):
                        ors.append(attr.ilike(f"%{v}%"))
                    else:
                        ors.append(attr == v)
                filters.append(or_(*ors))

            statement = statement.where(and_(*filters))
            return statement

        except Exception as e:
            return api_response(
                400,
                f" {e}",
            )

    if customFilters:
        filters = []
        for col, value in customFilters:
            attr, statement = resolve_column(Model, col, statement)
            # optional handling formats
            col_type = _get_column_type(attr)
            value = _coerce_value_for_column(col_type, value, col)

            if isinstance(value, str):
                filters.append(attr.ilike(f"%{value}%"))
            else:
                filters.append(attr == value)

        statement = statement.where(and_(*filters))

        return statement

    # Number range
    if numberRange:
        # number_range should be like ("amount", "0", "100000")
        parsed = tuple(json.loads(numberRange))
        column_name, *values = parsed  # first element is column name, rest are values

        # Assign safely
        min_val = float(values[0]) if len(values) >= 1 and values[0] else None
        max_val = float(values[1]) if len(values) >= 2 else None

        # Ensure numeric types

        column = getattr(Model, column_name)
        if min_val is not None and max_val is not None:
            statement = statement.where(column.between(min_val, max_val))
        elif min_val is not None:
            statement = statement.where(column >= min_val)
        elif max_val is not None:
            statement = statement.where(column <= max_val)

    # Date range
    if dateRange:
        dateRangeParse = json.loads(dateRange)
        dateRange = tuple(dateRangeParse)

        column_name = dateRange[0]  # e.g. "created_at"
        column = getattr(Model, column_name)  # map to SQLModel column

        start_date = parse_date(dateRange[1])
        end_date = (
            parse_date(dateRange[2])
            if len(dateRange) > 2 and dateRange[2]
            else datetime.now(timezone.utc)
        )

        # If user didn’t specify end time, set to 23:59:59
        if (
            end_date.hour == 0
            and end_date.minute == 0
            and end_date.second == 0
            and end_date.microsecond == 0
        ):
            end_date = end_date.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )

        statement = statement.where(and_(column >= start_date, column <= end_date))

        # Sorting

    if sort:
        try:
            column_name, direction = json.loads(sort)
            attr, statement = resolve_column(Model, column_name, statement)
            col_type = _get_column_type(attr)

            # Case-insensitive sorting for strings
            if _is_string_type(col_type):
                order_expr = func.lower(attr)
            else:
                order_expr = attr

            if direction.lower() in ["asc", "asc"]:
                statement = statement.order_by(asc(order_expr))
            elif direction.lower() in ["desc", "desc"]:
                statement = statement.order_by(desc(order_expr))
        except Exception as e:
            return api_response(
                400,
                f"Invalid sort parameter: {e}",
            )

    return statement
```

# Routing Methods

```py
router = APIRouter(prefix="/banner", tags=["Banner"])


@router.post("/create")
def create_role(
    request: BannerCreate,
    session: GetSession,
    user=requirePermission("banner"),
):
    banner = Banner(**request.model_dump())
    banner.slug = uniqueSlugify(
        session,
        Banner,
        banner.name,
    )
    session.add(banner)
    session.commit()
    session.refresh(banner)
    return api_response(
        200, "Banner Created Successfully", BannerRead.model_validate(banner)
    )


@router.put("/update/{id}", response_model=BannerRead)
def update_role(
    id: int,
    request: BannerUpdate,
    session: GetSession,
    user=requirePermission("banner"),
):
    banner = session.get(Banner, id)  # Like findById
    raiseExceptions((banner, 404, "Banner not found"))
    data = updateOp(banner, request, session)
    # if model have slug
    if data.name:
        data.slug = uniqueSlugify(session, Banner, data.name)
    session.commit()
    session.refresh(banner)
    return api_response(
        200, "Banner Update Successfully", BannerRead.model_validate(banner)
    )

#simple id if slug not in class
@router.get("/read/{id_slug}", description="Banner ID (int) or slug (str)")
def get_role(
    id_slug: str,
    session: GetSession,
):

    # Check if it's an integer ID
    if id_slug.isdigit():
        banner = session.get(Banner, int(id_slug))
    else:
        # Otherwise treat as slug
        banner = (
            session.exec(select(Banner).where(Banner.slug.ilike(id_slug)))
            .scalars()
            .first()
        )
    raiseExceptions((banner, 404, "Banner not found"))

    return api_response(200, "Banner Found", BannerRead.model_validate(banner))


# ❗ DELETE
@router.delete("/delete/{id}", response_model=dict)
def delete_role(
    id: int,
    session: GetSession,
    user=requirePermission("banner"),
):
    banner = session.get(Banner, id)
    raiseExceptions((banner, 404, "Banner not found"))

    session.delete(banner)
    session.commit()
    return api_response(404, f"Banner {banner.id} deleted")


```

# Models and pydantic Class

```py
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, List
from sqlmodel import JSON, Column, SQLModel, Field, Relationship
from src.api.models.category_model.categoryModel import CategoryRead
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel


if TYPE_CHECKING:
    from src.api.models import Category


class Banner(TimeStampedModel, table=True):
    __tablename__: Literal["banners"] = "banners"

    id: Optional[int] = Field(default=None, primary_key=True)
    category_id: Optional[int] = Field(foreign_key="categories.id")
    name: str = Field(max_length=191)
    slug: str = Field(max_length=191, index=True, unique=True)
    language: str = Field(default="en", max_length=191)
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    image: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
    )
    # Relationships
    category: Optional["Category"] = Relationship(back_populates="banners")


class BannerCreate(SQLModel):
    category_id: Optional[int] = None
    name: str
    description: str
    image: Optional[Dict[str, Any]] = None


class BannerUpdate(SQLModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[Dict[str, Any]] = None


class BannerRead(TimeStampReadModel):
    id: int
    name: str
    description: Optional[str] = None
    slug: str
    image: Optional[Dict[str, Any]] = None
    is_active: bool
    category: CategoryRead

    class Config:
        from_attributes = True

```

# response function

```py
def api_response(
    code: int,
    detail: str,
    data: Optional[Union[dict, list]] = None,
    total: Optional[int] = None,
):

    content = {
        "success": (1 if code < 300 else 0),
        "detail": detail,
        "data": jsonable_encoder(data),
    }

    if total is not None:
        content["total"] = total

    # Raise error if code >= 400
    if code >= 400:
        raise HTTPException(
            status_code=code,
            detail=detail,
        )

    return JSONResponse(
        status_code=code,
        content=content,
    )


def raiseExceptions(*conditions: tuple[Any, int | None, str | None, bool | None]):
    """
    Example usage:
        resp = raiseExceptions(
            (user, 404, "User not found"),
            (is_active, 403, "User is disabled",True),
        )
        if resp: return resp
    """
    for cond in conditions:
        # Unpack with defaults
        condition = cond[0] if len(cond) > 0 else False  # Condition
        code = cond[1] if len(cond) > 1 else 400
        detail = cond[2] if len(cond) > 2 else "error"
        isCond = cond[3] if len(cond) > 3 else False

        if isCond and condition:
            if condition:  # Fail if condition is True
                return api_response(code, detail)
        elif not condition and not isCond:  # Fail if condition is False
            return api_response(code, detail)
    return None  # everything passed

```

# reuse function

```py
date_formats = [
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%-d/%-m/%Y",
    "%d/%-m/%Y",
    "%-d/%m/%Y",
    "%d-%-m-%Y",
    "%-d-%m-%Y",
    "%-d-%-m-%Y",
    "%-d-%b-%y",
    "%d-%b-%y",
    "%-d-%b-%Y",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H",
    "%Y-%m-%d",
]


def parse_date(date_str: str) -> datetime:
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Date '{date_str}' is not in a valid UTC format.")


# slug = slugify("ACME Industries Inc.")
# print(slug)  # acme-industries-inc
def slugify(text: str) -> str:
    """
    Convert text into a URL-friendly slug.
    Example: "ACME Industries Inc." -> "acme-industries-inc"
    """
    if not text:
        return ""

    # Normalize unicode (e.g., remove accents like café → cafe)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

    # Lowercase
    text = text.lower()

    # Replace non-alphanumeric characters with hyphens
    text = re.sub(r"[^a-z0-9]+", "-", text)

    # Remove leading/trailing hyphens
    text = text.strip("-")

    return text


def uniqueSlugify(session, model, name: str, slug_field: str = "slug") -> str:
    base_slug = slugify(name)
    slug = base_slug
    counter = 1

    while session.query(model).filter(getattr(model, slug_field) == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


def Print(data, title="Result"):
    print(f"{title}\n", json.dumps(data, indent=2, default=str))

```

# Security function

```py

ALGORITHM = "HS256"

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


## get user
def exist_user(db: Session, email: str):
    user = db.exec(select(User).where(User.email == email)).first()
    return user


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_data: dict,
    refresh: Optional[bool] = False,
    expires: Optional[timedelta] = None,
):

    if refresh:
        expire = datetime.now(timezone.utc) + timedelta(days=30)
    else:
        expire = datetime.now(timezone.utc) + (
            expires or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

    payload = {
        "user": user_data,
        "exp": expire,
        "refresh": refresh,
    }
    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return token


def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def decode_token(
    token: str,
) -> Optional[Dict]:
    try:
        decode = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True},  # Ensure expiration is verified
        )

        return decode

    except JWTError as e:
        print(f"Token decoding failed: {e}")
        return None


def require_signin(
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer()),
) -> Dict:
    token = credentials.credentials  # Extract token from Authorization header

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user = payload.get("user")

        if user is None:
            api_response(
                status.HTTP_401_UNAUTHORIZED,
                "Invalid token: no user data",
            )

        if payload.get("refresh") is True:
            api_response(
                401,
                "Refresh token is not allowed for this route",
            )

        return user  # contains {"email": ..., "id": ...}

    except JWTError as e:
        print(e)
        return api_response(status.HTTP_401_UNAUTHORIZED, "Invalid token", data=str(e))


def require_admin(user: dict = Depends(require_signin)):
    roles: List[str] = user.get("roles", [])
    if "root" not in roles:
        api_response(status.HTTP_403_FORBIDDEN, "Root User only")
    return user


def require_permission(*permissions: str):
    def permission_checker(user: dict = Depends(require_signin)):
        user_permissions: List[str] = user.get("permissions", [])

        # ✅ system:* always passes
        if "system:*" in user_permissions:
            return user

        # ✅ OR logic: check if user has any required permission
        if any(p in user_permissions for p in permissions):
            return user

        # ❌ no match → deny
        api_response(status.HTTP_403_FORBIDDEN, "Permission denied")

    return permission_checker

```
