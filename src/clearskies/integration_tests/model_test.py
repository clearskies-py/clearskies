import datetime
import unittest
from unittest.mock import MagicMock, call

import clearskies
from clearskies.contexts import Context
from clearskies.test_base import TestBase


class ModelTest(TestBase):
    def test_overview(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(user, users, by_type_hint: User):
            return {
                "all_are_user_models": isinstance(user, User) and isinstance(users, User) and isinstance(by_type_hint, User)
            }

        context = clearskies.contexts.Context(my_application, classes=[User])
        (status_code, response, response_headers) = context()

        assert response == {"all_are_user_models": True}

    def test_overview_di(self):
        class SomeClass:
            # Since this will be built by the DI system directly, we can declare dependencies in the __init__
            def __init__(self, some_date):
                self.some_date = some_date

        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            utcnow = clearskies.di.inject.Utcnow()
            some_class = clearskies.di.inject.ByClass(SomeClass)

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

            def some_date_in_the_past(self):
                return self.some_class.some_date < self.utcnow

        def my_application(user):
            return user.some_date_in_the_past()

        context = clearskies.contexts.Context(
            my_application,
            classes=[User],
            bindings={
                "some_date": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1),
            }
        )
        (status_code, response, response_headers) = context()
        assert response == True

    def test_where(self):
        class Order(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            user_id = clearskies.columns.String()
            status = clearskies.columns.Select(["Pending", "In Progress"])
            total = clearskies.columns.Float()

        def my_application(orders):
            orders.create({"user_id": "Bob", "status": "Pending", "total": 25})
            orders.create({"user_id": "Alice", "status": "In Progress", "total": 15})
            orders.create({"user_id": "Jane", "status": "Pending", "total": 30})

            return [order.user_id for order in orders.where("status=Pending").where(Order.total.greater_than(25))]

        context = clearskies.contexts.Context(
            my_application,
            classes=[Order],
        )
        (status_code, response, response_headers) = context()
        assert response == ["Jane"]

    def test_first(self):
        class Order(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            user_id = clearskies.columns.String()
            status = clearskies.columns.Select(["Pending", "In Progress"])
            total = clearskies.columns.Float()

        def my_application(orders):
            orders.create({"user_id": "Bob", "status": "Pending", "total": 25})
            orders.create({"user_id": "Alice", "status": "In Progress", "total": 15})
            orders.create({"user_id": "Jane", "status": "Pending", "total": 30})

            jane = orders.where("status=Pending").where(Order.total.greater_than(25)).first()
            jane.total = 35
            jane.save()

            return {
                "user_id": jane.user_id,
                "total": jane.total,
            }

        context = clearskies.contexts.Context(
            my_application,
            classes=[Order],
        )
        (status_code, response, response_headers) = context()
        assert response == {"user_id": "Jane", "total": 35}

    def test_find(self):
        class Order(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            user_id = clearskies.columns.String()
            status = clearskies.columns.Select(["Pending", "In Progress"])
            total = clearskies.columns.Float()

        def my_application(orders):
            orders.create({"user_id": "Bob", "status": "Pending", "total": 25})
            orders.create({"user_id": "Alice", "status": "In Progress", "total": 15})
            orders.create({"user_id": "Jane", "status": "Pending", "total": 30})

            jane = orders.find("user_id=Jane")
            jane.total = 35
            jane.save()

            return {
                "user_id": jane.user_id,
                "total": jane.total,
            }

        context = clearskies.contexts.Context(
            my_application,
            classes=[Order],
        )
        (status_code, response, response_headers) = context()
        assert response == {"user_id": "Jane", "total": 35}

    def test_sort_by(self):
        class Order(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            user_id = clearskies.columns.String()
            status = clearskies.columns.Select(["Pending", "In Progress"])
            total = clearskies.columns.Float()

        def my_application(orders):
            orders.create({"user_id": "Bob", "status": "Pending", "total": 25})
            orders.create({"user_id": "Alice", "status": "In Progress", "total": 15})
            orders.create({"user_id": "Alice", "status": "Pending", "total": 30})
            orders.create({"user_id": "Bob", "status": "Pending", "total": 26})

            return orders.sort_by("user_id", "asc", secondary_column_name="total", secondary_direction="desc")

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                my_application,
                model_class=Order,
                readable_column_names=["user_id", "total"],
            ),
            classes=[Order],
        )
        (status_code, response, response_headers) = context()
        assert response["data"] == [
            {"user_id": "Alice", "total": 30},
            {"user_id": "Alice", "total": 15},
            {"user_id": "Bob", "total": 26},
            {"user_id": "Bob", "total": 25},
        ]
