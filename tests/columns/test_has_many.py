import pytest

import clearskies
from tests.test_base import TestBase


class HasManyTest(TestBase):
    def test_default(self):
        class Product(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            category_id = clearskies.columns.String()

        class Category(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            products = clearskies.columns.HasMany(Product)

        def test_has_many(products: Product, categories: Category):
            toys = categories.create({"name": "Toys"})
            auto = categories.create({"name": "Auto"})

            # create some toys
            ball = products.create({"name": "Ball", "category_id": toys.id})
            fidget_spinner = products.create({"name": "Fidget Spinner", "category_id": toys.id})
            crayon = products.create({"name": "Crayon", "category_id": toys.id})

            # the HasMany column is an interable of matching records
            toy_names = [product.name for product in toys.products]

            # it specifically returns a models object so you can do more filtering/transformations
            return toys.products.sort_by("name", "asc")

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                test_has_many,
                model_class=Product,
                readable_column_names=["id", "name"],
            ),
            classes=[Category, Product],
        )
        status_code, response_data, response_headers = context()
        assert ["Ball", "Crayon", "Fidget Spinner"] == [product["name"] for product in response_data["data"]]

    def test_foreign_column_name(self):
        class Product(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            my_parent_category_id = clearskies.columns.String()

        class Category(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            products = clearskies.columns.HasMany(Product, foreign_column_name="my_parent_category_id")

        def test_has_many(products: Product, categories: Category):
            toys = categories.create({"name": "Toys"})

            fidget_spinner = products.create({"name": "Fidget Spinner", "my_parent_category_id": toys.id})
            ball = products.create({"name": "Ball", "my_parent_category_id": toys.id})

            return toys.products.sort_by("name", "asc")

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                test_has_many,
                model_class=Product,
                readable_column_names=["id", "name"],
            ),
            classes=[Category, Product],
        )
        status_code, response_data, response_headers = context()
        assert ["Ball", "Fidget Spinner"] == [product["name"] for product in response_data["data"]]

    def test_readable_child_column_names(self):
        class Order(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            total = clearskies.columns.Float()
            status = clearskies.columns.Select(["Open", "In Progress", "Closed"])
            user_id = clearskies.columns.String()

        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            orders = clearskies.columns.HasMany(Order, readable_child_column_names=["id", "status"])
            large_open_orders = clearskies.columns.HasMany(
                Order,
                readable_child_column_names=["id", "status"],
                where=[Order.status.equals("Open"), "total>100"],
            )

        def test_has_many(users: User, orders: Order):
            user = users.create({"name": "Bob"})

            order_1 = orders.create({"status": "Open", "total": 25.50, "user_id": user.id})
            order_2 = orders.create({"status": "Closed", "total": 35.50, "user_id": user.id})
            order_3 = orders.create({"status": "Open", "total": 125, "user_id": user.id})
            order_4 = orders.create({"status": "In Progress", "total": 25.50, "user_id": user.id})

            return user.large_open_orders

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                test_has_many,
                model_class=Order,
                readable_column_names=["id", "total", "status"],
                return_records=True,
            ),
            classes=[Order, User],
        )
        status_code, response_data, response_headers = context()
        assert [125] == [order["total"] for order in response_data["data"]]

    def test_write(self):
        class Product(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            category_id = clearskies.columns.String()

        class Category(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            products = clearskies.columns.HasMany(Product)

        di = clearskies.di.Di(classes=[Product, Category])
        categories = di.build(Category)
        products = di.build(Product)

        category = categories.create(
            {
                "name": "test",
                "products": [
                    {"name": "car"},
                    {"name": "truck"},
                ],
            }
        )

        car = products.find("name=car")
        assert [product.name for product in products.where(f"category_id={category.id}").sort_by("name", "asc")] == [
            "car",
            "truck",
        ]

        category.save(
            {
                "products": [
                    {"id": car.id, "name": "cool car"},
                    {"name": "suv"},
                ]
            }
        )

        assert [product.name for product in products.where(f"category_id={category.id}").sort_by("name", "asc")] == [
            "cool car",
            "suv",
        ]
        assert [product.name for product in category.products.sort_by("name", "asc")] == ["cool car", "suv"]

        with pytest.raises(ValueError, match="not allowed because allow_child_reassignment=False"):
            category.create(
                {
                    "name": "Toys",
                    "products": [
                        {"name": "Ball"},
                        {"name": "doll", "id": car.id},
                    ],
                }
            )

    def test_integer_child_ids_typed_in_to_json_and_no_key_bleed(self):
        """HasMany.to_json returns int ids for Integer children, no key bleed between items."""

        class Product(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Integer()
            name = clearskies.columns.String()
            category_id = clearskies.columns.Integer()

        class Category(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Integer()
            name = clearskies.columns.String()
            products = clearskies.columns.HasMany(Product, readable_child_column_names=["id", "name"])

        di = clearskies.di.Di(classes=[Category, Product])
        categories = di.build(Category)
        products = di.build(Product)

        category = categories.create({"id": 1, "name": "Toys"})
        products.create({"id": 10, "name": "Ball", "category_id": 1})
        products.create({"id": 20, "name": "Kite", "category_id": 1})

        column = category.__class__.products
        result = column.to_json(category)
        items = result["products"]

        assert len(items) == 2
        assert all(isinstance(product["id"], int) for product in items)
        # no key bleed: each item has exactly the same set of keys
        assert items[0].keys() == items[1].keys()

    def test_integer_id_post_save_normalises_incoming_string_ids(self):
        """HasMany.post_save doesn't spuriously delete children when ids arrive as strings."""

        class Product(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Integer()
            name = clearskies.columns.String()
            category_id = clearskies.columns.Integer()

        class Category(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Integer()
            name = clearskies.columns.String()
            products = clearskies.columns.HasMany(
                Product,
                readable_child_column_names=["id", "name"],
                writeable_child_column_names=["id", "name"],
            )

        di = clearskies.di.Di(classes=[Category, Product])
        categories = di.build(Category)
        products = di.build(Product)

        # Create the parent first, then create children separately so they already exist
        category = categories.create({"id": 1, "name": "Toys"})
        products.create({"id": 10, "name": "Ball", "category_id": 1})
        products.create({"id": 20, "name": "Kite", "category_id": 1})

        # Save with string ids — simulates values arriving from a JSON endpoint body.
        # Without normalisation the set-diff would see {"10"} vs {10} and delete+recreate.
        category.save({"products": [{"id": "10", "name": "Big Ball"}, {"id": "20", "name": "Kite"}]})

        names = sorted(product.name for product in products.where("category_id=1"))
        assert names == ["Big Ball", "Kite"]
