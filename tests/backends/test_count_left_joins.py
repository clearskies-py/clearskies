import clearskies
from clearskies.contexts import Context


def build_models(backend_class, cursor=None):
    class Category(clearskies.Model):
        id_column_name = "id"
        backend = backend_class()
        id = clearskies.columns.String()
        name = clearskies.columns.String()

        @classmethod
        def destination_name(cls):
            return "categories"

    class Product(clearskies.Model):
        id_column_name = "id"
        backend = backend_class()
        id = clearskies.columns.String()
        name = clearskies.columns.String()
        category_id = clearskies.columns.String()

        @classmethod
        def destination_name(cls):
            return "products"

    return Category, Product


def test_cursor_count_keeps_left_join_used_by_a_condition():
    cursor = clearskies.cursors.Sqlite(database=":memory:")
    cursor.connection.executescript(
        """
        CREATE TABLE categories (id TEXT PRIMARY KEY, name TEXT);
        CREATE TABLE products (id TEXT PRIMARY KEY, name TEXT, category_id TEXT);
        INSERT INTO categories VALUES ('c1', 'Toys'), ('c2', 'Auto');
        INSERT INTO products VALUES ('p1', 'Ball', 'c1'), ('p2', 'Tire', 'c2'), ('p3', 'Kite', 'c1');
        """
    )
    Category, Product = build_models(clearskies.backends.CursorBackend)
    products = Context(lambda: None, classes=[Category, Product], bindings={"cursor": cursor}).build(Product)
    joined = products.join("LEFT JOIN categories AS cats ON cats.id=products.category_id")

    assert len(joined.where("cats.name=Toys")) == 2
    # an unused LEFT join is still left out of the count
    assert products.backend.as_count_sql(joined.get_query())[0] == "SELECT COUNT(*) AS count FROM `products`"


def test_memory_count_keeps_left_join_used_by_a_condition_and_leaves_query_alone():
    Category, Product = build_models(clearskies.backends.MemoryBackend)
    context = Context(lambda: None, classes=[Category, Product])
    categories = context.build(Category)
    products = context.build(Product)
    categories.create({"id": "c1", "name": "Toys"})
    categories.create({"id": "c2", "name": "Auto"})
    products.create({"id": "p1", "name": "Ball", "category_id": "c1"})
    products.create({"id": "p2", "name": "Tire", "category_id": "c2"})

    search = products.join("LEFT JOIN categories AS cats ON cats.id=products.category_id").where("cats.name=Toys")
    query = search.get_query()

    assert products.backend.count(query).count == 1
    assert len(query.joins) == 1
