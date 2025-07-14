import datetime
import unittest
from unittest.mock import MagicMock, call
from pytest import raises  # type: ignore

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
                "all_are_user_models": (
                    isinstance(user, User) and isinstance(users, User) and isinstance(by_type_hint, User)
                )
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
            },
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

    def test_limit(self):
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

            return orders.limit(2)

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                my_application,
                model_class=Order,
                readable_column_names=["user_id", "total"],
            ),
            classes=[Order],
        )
        (status_code, response, response_headers) = context()
        assert len(response["data"]) == 2
        assert response["pagination"]["limit"] == 2

    def test_pagination(self):
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

            return orders.sort_by("total", "asc").pagination(start=2)

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                my_application,
                model_class=Order,
                readable_column_names=["user_id", "total"],
            ),
            classes=[Order],
        )
        (status_code, response, response_headers) = context()
        assert response["data"] == [{"user_id": "Bob", "total": 26}, {"user_id": "Alice", "total": 30}]

        with raises(ValueError) as exception:
            context = clearskies.contexts.Context(lambda orders: orders.pagination(start="asdfer"), classes=[Order])
            context()
        assert "'start' must be a number" in str(exception.value)

        with raises(ValueError) as exception:
            context = clearskies.contexts.Context(lambda orders: orders.pagination(thingy=10), classes=[Order])
            context()
        assert "'thingy'.  Only 'start' is allowed" in str(exception.value)

    def test_paginate_all(self):
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

            return orders.limit(1).paginate_all()

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                my_application,
                model_class=Order,
                readable_column_names=["user_id", "total"],
            ),
            classes=[Order],
        )
        (status_code, response, response_headers) = context()
        assert len(response["data"]) == 4

    def test_join(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        class Order(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            user_id = clearskies.columns.BelongsToId(User, readable_parent_columns=["id", "name"])
            user = clearskies.columns.BelongsToModel("user_id")
            status = clearskies.columns.Select(["Pending", "In Progress"])
            total = clearskies.columns.Float()

        def my_application(users, orders):
            jane = users.create({"name": "Jane"})
            another_jane = users.create({"name": "Jane"})
            bob = users.create({"name": "Bob"})

            # Jane's orders
            orders.create({"user_id": jane.id, "status": "Pending", "total": 25})
            orders.create({"user_id": jane.id, "status": "Pending", "total": 30})
            orders.create({"user_id": jane.id, "status": "In Progress", "total": 35})

            # Another Jane's orders
            orders.create({"user_id": another_jane.id, "status": "Pending", "total": 15})

            # Bob's orders
            orders.create({"user_id": bob.id, "status": "Pending", "total": 28})
            orders.create({"user_id": bob.id, "status": "In Progress", "total": 35})

            # return all orders for anyone named Jane that have a status o Pending
            return (
                orders.join("join users on users.id=orders.user_id")
                .where("users.name=Jane")
                .sort_by("total", "asc")
                .where("status=Pending")
            )

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                my_application,
                model_class=Order,
                readable_column_names=["user", "total"],
            ),
            classes=[Order, User],
        )
        (status_code, response, response_headers) = context()
        assert [order["total"] for order in response["data"]] == [15, 25, 30]
