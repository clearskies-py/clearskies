import clearskies
from tests.test_base import TestBase


class ListBelongsToPreloadTest(TestBase):
    def cursor_models(self, readable_parent_columns=["id", "name"]):
        # fresh classes per test: the backend (and the cursor injected into it) lives on the model class
        cursor = clearskies.cursors.Sqlite(database=":memory:")
        cursor.connection.executescript(
            """
            CREATE TABLE categories (id TEXT PRIMARY KEY, name TEXT);
            CREATE TABLE products (id TEXT PRIMARY KEY, name TEXT, category_id TEXT);
            INSERT INTO categories VALUES ('c1', 'Toys'), ('c2', 'Auto');
            INSERT INTO products VALUES ('p1', 'Ball', 'c1'), ('p2', 'Tire', 'c2'), ('p3', 'Orphan', NULL);
            """
        )
        statements: list[str] = []
        cursor.connection.set_trace_callback(statements.append)

        class Category(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.CursorBackend()
            id = clearskies.columns.String()
            name = clearskies.columns.String()
            label = clearskies.columns.String(is_temporary=True)

            @classmethod
            def destination_name(cls):
                return "categories"

        class Product(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.CursorBackend()
            id = clearskies.columns.String()
            name = clearskies.columns.String()
            category_id = clearskies.columns.BelongsToId(Category, readable_parent_columns=readable_parent_columns)
            category = clearskies.columns.BelongsToModel("category_id")

            @classmethod
            def destination_name(cls):
                return "products"

        return Category, Product, cursor, statements

    def test_cursor_backend_loads_parents_with_the_list_query(self):
        Category, Product, cursor, statements = self.cursor_models()

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                model_class=Product,
                readable_column_names=["id", "name", "category_id", "category"],
                sortable_column_names=["id"],
                default_sort_column_name="id",
            ),
            classes=[Category, Product],
            bindings={"cursor": cursor},
        )
        status_code, response, _ = context()

        assert status_code == 200
        assert response["data"] == [
            {"id": "p1", "name": "Ball", "category_id": "c1", "category": {"id": "c1", "name": "Toys"}},
            {"id": "p2", "name": "Tire", "category_id": "c2", "category": {"id": "c2", "name": "Auto"}},
            {"id": "p3", "name": "Orphan", "category_id": None, "category": {"id": None, "name": None}},
        ]
        # the list query plus the count query, and no per-record parent lookups
        assert statements == [
            "SELECT `products`.*, categories_category_id.id AS categories_category_id_id, "
            "categories_category_id.name AS categories_category_id_name "
            "FROM `products` LEFT JOIN categories as categories_category_id "
            "on categories_category_id.id=products.category_id "
            "ORDER BY `products`.`id` ASC LIMIT 0, 50",
            "SELECT COUNT(*) AS count FROM `products` ",
        ]

    def test_sort_join_is_reused(self):
        Category, Product, cursor, statements = self.cursor_models()

        context = clearskies.contexts.Context(
            clearskies.endpoints.AdvancedSearch(
                model_class=Product,
                readable_column_names=["id", "category"],
                sortable_column_names=["id", "category.name"],
                searchable_column_names=["id"],
                default_sort_column_name="id",
            ),
            classes=[Category, Product],
            bindings={"cursor": cursor},
        )
        status_code, response, _ = context(
            request_method="POST",
            body={"sort": [{"column": "category.name", "direction": "asc"}]},
        )

        assert status_code == 200
        assert response["data"] == [
            {"id": "p3", "category": {"id": None, "name": None}},
            {"id": "p2", "category": {"id": "c2", "name": "Auto"}},
            {"id": "p1", "category": {"id": "c1", "name": "Toys"}},
        ]
        assert statements[0].count("JOIN") == 1
        assert len(statements) == 2

    def test_parent_columns_not_in_the_table_skip_the_preload(self):
        Category, Product, cursor, statements = self.cursor_models(readable_parent_columns=["id", "name", "label"])

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                model_class=Product,
                readable_column_names=["id", "category"],
                sortable_column_names=["id"],
                default_sort_column_name="id",
            ),
            classes=[Category, Product],
            bindings={"cursor": cursor},
        )
        status_code, response, _ = context()

        assert status_code == 200
        assert response["data"][0] == {"id": "p1", "category": {"id": "c1", "name": "Toys", "label": None}}
        assert "JOIN" not in statements[0]

    def test_memory_backend_still_loads_parents(self):
        class MemoryCategory(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = clearskies.columns.String()
            name = clearskies.columns.String()

        class MemoryProduct(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = clearskies.columns.String()
            category_id = clearskies.columns.BelongsToId(MemoryCategory, readable_parent_columns=["id", "name"])
            category = clearskies.columns.BelongsToModel("category_id")

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                model_class=MemoryProduct,
                readable_column_names=["id", "category"],
                sortable_column_names=["id"],
                default_sort_column_name="id",
            ),
            classes=[MemoryCategory, MemoryProduct],
            bindings={
                "memory_backend_default_data": [
                    {"model_class": MemoryCategory, "records": [{"id": "c1", "name": "Toys"}]},
                    {"model_class": MemoryProduct, "records": [{"id": "p1", "category_id": "c1"}, {"id": "p2"}]},
                ]
            },
        )
        status_code, response, _ = context()

        assert status_code == 200
        assert response["data"] == [
            {"id": "p1", "category": {"id": "c1", "name": "Toys"}},
            {"id": "p2", "category": {"id": None, "name": None}},
        ]

    def test_belongs_to_id_hook_still_adds_the_join(self):
        Category, Product, cursor, statements = self.cursor_models()
        products = clearskies.contexts.Context(
            lambda: None, classes=[Category, Product], bindings={"cursor": cursor}
        ).build(Product)

        category_id = products.get_columns()["category_id"]
        once = category_id.n_plus_one_add_joins(products)
        twice = category_id.n_plus_one_add_joins(once)

        assert once.get_query().selects == [
            "categories_category_id.id AS categories_category_id_id, "
            "categories_category_id.name AS categories_category_id_name"
        ]
        assert twice.get_query().selects == once.get_query().selects
        assert len(twice.get_query().joins) == 1
