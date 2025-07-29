import datetime
import unittest
from unittest.mock import MagicMock, call
from pytest import raises  # type: ignore
from typing import Any, Self

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

    def test_has_query(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(users):
            jane = users.create({"name": "Jane"})
            jane_instance_has_query = jane.has_query()

            some_search = users.where("name=Jane")
            some_search_has_query = some_search.has_query()

            invalid_request_error = ""
            try:
                some_search.save({"not": "valid"})
            except ValueError as e:
                invalid_request_error = str(e)

            return {
                "jane_instance_has_query": jane_instance_has_query,
                "some_search_has_query": some_search_has_query,
                "invalid_request_error": invalid_request_error,
            }

        context = clearskies.contexts.Context(
            my_application,
            classes=[User],
        )
        (status_code, response, response_headers) = context()

        assert not response["jane_instance_has_query"]
        assert response["some_search_has_query"]
        assert "This is not allowed" in response["invalid_request_error"]

    def test_create(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(user):
            # let's create a new record
            user.save({"name": "Alice"})

            # and now use `create` to both create a new record and get a new model instance
            bob = user.create({"name": "Bob"})

            return {
                "Alice": user.name,
                "Bob": bob.name,
            }

        context = clearskies.contexts.Context(
            my_application,
            classes=[User],
        )
        (status_code, response, response_headers) = context()
        assert response == {"Alice": "Alice", "Bob": "Bob"}

    def test_delete(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(users):
            alice = users.create({"name": "Alice"})

            pre_delete_exists = bool(users.find("name=Alice"))

            alice.delete()

            post_delete_exists = not users.find("name=Alice")

            return {"id": alice.id, "name": alice.name, "pre": pre_delete_exists, "post": post_delete_exists}

        context = clearskies.contexts.Context(
            my_application,
            classes=[User],
        )
        (status_code, response, response_headers) = context()
        assert response["name"] == "Alice"
        assert response["pre"] == True
        assert response["post"] == True

    def test_blank(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(users):
            alice = users.create({"name": "Alice"})

            if users.find("name=Alice"):
                print("Alice exists")

            blank = alice.empty()

            if not blank:
                print("Fresh instance, ready to go")

            return {"alice_id": alice.id, "blank_id": blank.id}

        context = clearskies.contexts.Context(
            my_application,
            classes=[User],
        )
        (status_code, response, response_headers) = context()
        assert len(response["alice_id"]) == 36
        assert response["blank_id"] == None

    def test_model(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(users):
            jane = users.create({"name": "Jane"})

            # This effectively makes a new model instance that points to the jane record in the backend
            another_jane_object = users.model({"id": jane.id, "name": jane.name})
            # and we can perform an update operation like usual
            another_jane_object.save({"name": "Jane Doe"})

            return {"id": another_jane_object.id, "name": another_jane_object.name}

        context = clearskies.contexts.Context(
            my_application,
            classes=[User],
        )
        (status_code, response, response_headers) = context()
        assert response["name"] == "Jane Doe"

    def test_was_changed(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            age = clearskies.columns.Integer()

        def my_application(users):
            jane = users.create({"name": "Jane"})
            return {
                "name_changed": jane.was_changed("name"),
                "age_changed": jane.was_changed("age"),
            }

        context = clearskies.contexts.Context(
            my_application,
            classes=[User],
        )
        (status_code, response, response_headers) = context()
        assert response == {"name_changed": True, "age_changed": False}

    def test_previous_data(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(users):
            jane = users.create({"name": "Jane"})
            jane.save({"name": "Jane Doe"})
            return {"name": jane.name, "previous_name": jane.previous_value("name")}

        context = clearskies.contexts.Context(
            my_application,
            classes=[User],
        )
        (status_code, response, response_headers) = context()
        assert response == {"name": "Jane Doe", "previous_name": "Jane"}

    def test_pre_save(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            is_anonymous = clearskies.columns.Boolean()

            def pre_save(self: Self, data: dict[str, Any]) -> dict[str, Any]:
                additional_data = {}

                if self.is_changing("name", data):
                    additional_data["is_anonymous"] = not bool(data["name"])

                return additional_data

        def my_application(users):
            jane = users.create({"name": "Jane"})
            is_anonymous_after_create = jane.is_anonymous

            jane.save({"name": ""})
            is_anonymous_after_first_update = jane.is_anonymous

            jane.save({"name": "Jane Doe"})
            is_anonymous_after_last_update = jane.is_anonymous

            return {
                "is_anonymous_after_create": is_anonymous_after_create,
                "is_anonymous_after_first_update": is_anonymous_after_first_update,
                "is_anonymous_after_last_update": is_anonymous_after_last_update,
            }

        context = clearskies.contexts.Context(
            my_application,
            classes=[User],
        )
        (status_code, response, response_headers) = context()
        assert response == {
            "is_anonymous_after_create": False,
            "is_anonymous_after_first_update": True,
            "is_anonymous_after_last_update": False,
        }

    def test_post_save(self):
        class History(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            message = clearskies.columns.String()
            created_at = clearskies.columns.Created(date_format="%Y-%m-%d %H:%M:%S.%f")

        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            histories = clearskies.di.inject.ByClass(History)

            id = clearskies.columns.Uuid()
            age = clearskies.columns.Integer()
            name = clearskies.columns.String()

            def post_save(self: Self, data: dict[str, Any], id: str | int) -> None:
                if not self.is_changing("age", data):
                    return

                name = self.latest("name", data)
                age = self.latest("age", data)
                self.histories.create({"message": f"My name is {name} and I am {age} years old"})

        def my_application(users, histories):
            jane = users.create({"name": "Jane"})
            jane.save({"age": 25})
            jane.save({"age": 26})
            jane.save({"age": 30})

            return [history.message for history in histories.sort_by("created_at", "ASC")]

        context = clearskies.contexts.Context(
            my_application,
            classes=[User, History],
        )
        (status_code, response, response_headers) = context()
        assert response == [
            "My name is Jane and I am 25 years old",
            "My name is Jane and I am 26 years old",
            "My name is Jane and I am 30 years old",
        ]

    def test_save_finished(self):
        class History(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            message = clearskies.columns.String()
            created_at = clearskies.columns.Created(date_format="%Y-%m-%d %H:%M:%S.%f")

        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            histories = clearskies.di.inject.ByClass(History)

            id = clearskies.columns.Uuid()
            age = clearskies.columns.Integer()
            name = clearskies.columns.String()

            def save_finished(self: Self) -> None:
                if not self.was_changed("age"):
                    return

                self.histories.create({"message": f"My name is {self.name} and I am {self.age} years old"})

        def my_application(users, histories):
            jane = users.create({"name": "Jane"})
            jane.save({"age": 25})
            jane.save({"age": 26})
            jane.save({"age": 30})

            return [history.message for history in histories.sort_by("created_at", "ASC")]

        context = clearskies.contexts.Context(
            my_application,
            classes=[User, History],
        )
        (status_code, response, response_headers) = context()
        assert response == [
            "My name is Jane and I am 25 years old",
            "My name is Jane and I am 26 years old",
            "My name is Jane and I am 30 years old",
        ]

    def test_where_for_request(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            age = clearskies.columns.Integer()

            def where_for_request(
                self: Self,
                model: Self,
                input_output: Any,
                routing_data: dict[str, str],
                authorization_data: dict[str, Any],
                overrides: dict[str, clearskies.Column] = {},
            ) -> Self:
                return model.where("age>=18")

        list_users = clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["id", "name", "age"],
            sortable_column_names=["id", "name", "age"],
            default_sort_column_name="name",
        )

        context = clearskies.contexts.Context(
            list_users,
            classes=[User],
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": User,
                        "records": [
                            {"id": "1-2-3-4", "name": "Bob", "age": 20},
                            {"id": "1-2-3-5", "name": "Jane", "age": 17},
                            {"id": "1-2-3-6", "name": "Greg", "age": 22},
                        ],
                    },
                ]
            },
        )
        (status_code, response, response_headers) = context()

        assert [user["name"] for user in response["data"]] == ["Bob", "Greg"]
