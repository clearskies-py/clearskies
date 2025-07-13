from __future__ import annotations

import re
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Iterator, Self

from clearskies.autodoc.schema import Schema as AutoDocSchema
from clearskies.di import InjectableProperties, inject
from clearskies.functional import string
from clearskies.query import Condition, Join, Query, Sort
from clearskies.schema import Schema

if TYPE_CHECKING:
    from clearskies import Column
    from clearskies.backends import Backend


class Model(Schema, InjectableProperties):
    """
    A clearskies model.

    To be useable, a model class needs four things:

     1. The name of the id column
     2. A backend
     3. A destination name (equivalent to a table name for SQL backends)
     4. Columns

    In more detail:

    ### Id Column Name

    clearskies assumes that all models have a column that uniquely identifies each record.  This id column is
    provided where appropriate in the lifecycle of the model save process to help connect and find related records.
    It's defined as a simple class attribute called `id_column_name`.  There **MUST** be a column with the same name
    in the column definitions.  A simple approach to take is to use the Uuid column as an id column.  This will
    automatically provide a random UUID when the record is first created.  If you are using auto-incrementing integers,
    you can simply use an `Int` column type and define the column as auto-incrementing in your database.

    ### Backend

    Every model needs a backend, which is an object that extends clearskies.Backend and is attached to the
    `backend` attribute of the model class.  clearskies comes with a variety of backends in the `clearskies.backends`
    module that you can use, and you can also define your own or import more from additional packages.

    ### Destination Name

    The destination name is the equivalent of a table name in other frameworks, but the name is more generic to
    reflect the fact that clearskies is intended to work with a variety of backends - not just SQL databases.
    The exact meaning of the destination name depends on the backend: for a cursor backend it is in fact used
    as the table name when fetching/storing records.  For the API backend it is frequently appended to a base
    URL to reach the corect endpoint.

    This is provided by a class function call `destination_name`.  The base model class declares a generic method
    for this which takes the class name, converts it from title case to snake case, and makes it plural.  Hence,
    a model class called `User` will have a default destination name of `users` and a model class of `OrderProduct`
    will have a default destination name of `order_products`.  Of course, this system isn't pefect: your backend
    may have a different convention or you may have one of the many words in the english language that are
    exceptions to the grammatical rules of making words plural.  In this case you can simply extend the method
    and change it according to your needs, e.g.:

    ```
    from typing import Self
    import clearskies

    class Fish(clearskies.Model):
        @classmethod
        def destination_name(cls: type[Self]) -> str:
            return "fish"
    ```

    ### Columns

    Finally, columns are defined by attaching attributes to your model class that extend clearskies.Column.  A variety
    are provided by default in the clearskies.columns module, and you can always create more or import them from
    other packages.

    ### Fetching From the Di Container

    In order to use a model in your application you need to retrieve it from the dependency injection system.  Like
    everything, you can do this by either the name or with type hinting.  Models do have a special rule for
    injection-via-name: like all classes their dependency injection name is made by converting the class name from
    title case to snake case, but they are also available via the pluralized name.  Here's a quick example of all
    three approaches for dependency injection:

    ```
    import clearskies

    class User(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()

        id = clearskies.columns.Uuid()
        name = clearskies.columns.String()

    def my_application(user, users, by_type_hint: User):
        return {
            "all_are_user_models": isinstance(user, User) and isinstance(users, User) and isinstance(by_type_hint, User)
        }

    cli = clearskies.contexts.Cli(my_application, classes=[User])
    cli()
    ```

    Note that the `User` model class was provided in the `classes` list sent to the context: that's important as it
    informs the dependency injection system that this is a class we want to provide.  It's common (but not required)
    to put all models for a clearskies application in their own separate python module and then provide those to
    the depedency injection system via the `modules` argument to the context.  So you may have a directory structure
    like this:

    ```
    ├── app/
    │   └── models/
    │       ├── __init__.py
    │       ├── category.py
    │       ├── order.py
    │       ├── product.py
    │       ├── status.py
    │       └── user.py
    └── api.py
    ```

    Where `__init__.py` imports all the models:

    ```
    from app.models.category import Category
    from app.models.order import Order
    from app.models.proudct import Product
    from app.models.status import Status
    from app.models.user import User

    __all__ = ["Category", "Order", "Product", "Status", "User"]
    ```

    Then in your main application you can just import the whole `models` module into your context:

    ```
    import app.models

    cli = clearskies.contexts.cli(SomeApplication, modules=[app.models])
    ```

    ### Adding Dependencies

    The base model class extends `clearskies.di.InjectableProperties` which means that you can inject dependencies into your model
    using the `di.inject` classes.  Here's an example that demonstrates dependency injection for models:

    ```
    import datetime
    import clearskies

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

    cli = clearskies.contexts.Cli(
        my_application,
        classes=[User],
        bindings={
            "some_date": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1),
        }
    )
    cli()
    ```
    """

    _previous_data: dict[str, Any] = {}
    _data: dict[str, Any] = {}
    _next_data: dict[str, Any] = {}
    _transformed_data: dict[str, Any] = {}
    _touched_columns: dict[str, bool] = {}
    _query: Query | None = None
    _query_executed: bool = False
    _count: int | None = None
    _next_page_data: dict[str, Any] | None = None

    id_column_name: str = ""
    backend: Backend = None  # type: ignore

    _di = inject.Di()

    def __init__(self):
        if not self.id_column_name:
            raise ValueError(
                f"You must define the 'id_column_name' property for every model class, but this is missing for model '{self.__class__.__name__}'"
            )
        if not isinstance(self.id_column_name, str):
            raise TypeError(
                f"The 'id_column_name' property of a model must be a string that specifies the name of the id column, but that is not the case for model '{self.__class__.__name__}'."
            )
        if not self.backend:
            raise ValueError(
                f"You must define the 'backend' property for every model class, but this is missing for model '{self.__class__.__name__}'"
            )
        if not hasattr(self.backend, "documentation_pagination_parameters"):
            raise TypeError(
                f"The 'backend' property of a model must be an object that extends the clearskies.Backend class, but that is not the case for model '{self.__class__.__name__}'."
            )
        self._previous_data = {}
        self._data = {}
        self._next_data = {}
        self._transformed_data = {}
        self._touched_columns = {}
        self._query = None
        self._query_executed = False
        self._count = None
        self._next_page_data = None

    @classmethod
    def destination_name(cls: type[Self]) -> str:
        """
        Return the name of the destination that the model uses for data storage.

        For SQL backends, this would return the table name.  Other backends will use this
        same function but interpret it in whatever way it makes sense.  For instance, an
        API backend may treat it as a URL (or URL path), an SQS backend may expect a queue
        URL, etc...

        By default this takes the class name, converts from title case to snake case, and then
        makes it plural.
        """
        singular = string.camel_case_to_snake_case(cls.__name__)
        if singular[-1] == "y":
            return singular[:-1] + "ies"
        if singular[-1] == "s":
            return singular + "es"
        return f"{singular}s"

    def supports_n_plus_one(self: Self):
        return self.backend.supports_n_plus_one  #  type: ignore

    def __bool__(self: Self) -> bool:  # noqa: D105
        if self._query:
            return bool(self.__len__())

        return True if self._data else False

    def get_raw_data(self: Self) -> dict[str, Any]:
        self.no_queries()
        return self._data

    def set_raw_data(self: Self, data: dict[str, Any]) -> None:
        self.no_queries()
        self._data = {} if data is None else data
        self._transformed_data = {}

    def save(self: Self, data: dict[str, Any] | None = None, columns: dict[str, Column] = {}, no_data=False) -> bool:
        """
        Save data to the database and update the model.

        Executes an update if the model corresponds to a record already, or an insert if not.

        There are two supported flows.  One is to pass in a dictionary of data to save:

        ```python
        model.save({
            "some_column": "New Value",
            "another_column": 5,
        })
        ```

        And the other is to set new values on the columns attributes and then call save without data:

        ```python
        model.some_column = "New Value"
        model.another_column = 5
        model.save()
        ```

        You cannot combine these methods.  If you set a value on a column attribute and also pass
        in a dictionary of data to the save, then an exception will be raised.
        """
        self.no_queries()
        if not data and not self._next_data and not no_data:
            raise ValueError("You have to pass in something to save, or set no_data=True in your call to save/create.")
        if data and self._next_data:
            raise ValueError(
                "Save data was provided to the model class by both passing in a dictionary and setting new values on the column attributes.  This is not allowed.  You will have to use just one method of specifying save data."
            )
        if not data:
            data = {**self._next_data}
            self._next_data = {}

        save_columns = self.get_columns()
        if columns is not None:
            for column in columns.values():
                save_columns[column.name] = column

        old_data = self.get_raw_data()
        data = self.columns_pre_save(data, save_columns)
        data = self.pre_save(data)
        if data is None:
            raise ValueError("pre_save forgot to return the data array!")

        [to_save, temporary_data] = self.columns_to_backend(data, save_columns)
        to_save = self.to_backend(to_save, save_columns)
        if self:
            new_data = self.backend.update(self._data[self.id_column_name], to_save, self)  # type: ignore
        else:
            new_data = self.backend.create(to_save, self)  # type: ignore
        id = self.backend.column_from_backend(save_columns[self.id_column_name], new_data[self.id_column_name])  # type: ignore

        # if we had any temporary columns add them back in
        new_data = {
            **temporary_data,
            **new_data,
        }

        data = self.columns_post_save(data, id, save_columns)
        self.post_save(data, id)

        self.set_raw_data(new_data)
        self._transformed_data = {}
        self._previous_data = old_data
        self._touched_columns = {key: True for key in data.keys()}

        self.columns_save_finished(save_columns)
        self.save_finished()

        return True

    def is_changing(self: Self, key: str, data: dict[str, Any]) -> bool:
        """
        Return True/False to denote if the given column is being modified by the active save operation.

        Pass in the name of the column to check and the data dictionary from the save in progress
        """
        self.no_queries()
        has_old_value = key in self._data
        has_new_value = key in data

        if not has_new_value:
            return False
        if not has_old_value:
            return True

        return getattr(self, key) != data[key]

    def latest(self: Self, key: str, data: dict[str, Any]) -> Any:
        """
        Return the 'latest' value for a column during the save operation.

        Return either the column value from the data dictionary or the current value stored in the model
        Basically, shorthand for the optimized version of:  `data.get(key, default=getattr(self, key))` (which is
        less than ideal because it always builds the default value, even when not necessary)

        Pass in the name of the column to check and the data dictionary from the save in progress
        """
        self.no_queries()
        if key in data:
            return data[key]
        return getattr(self, key)

    def was_changed(self: Self, key: str) -> bool:
        """Return True/False to denote if a column was changed in the last save."""
        self.no_queries()
        if self._previous_data is None:
            raise ValueError("was_changed was called before a save was finished - you must save something first")
        if key not in self._touched_columns:
            return False

        has_old_value = bool(self._previous_data.get(key))
        has_new_value = bool(self._data.get(key))

        if has_new_value != has_old_value:
            return True

        if not has_old_value:
            return False

        columns = self.get_columns()
        new_value = self._data[key]
        old_value = self._previous_data[key]
        if key not in columns:
            return old_value != new_value
        return not columns[key].values_match(old_value, new_value)

    def previous_value(self: Self, key: str):
        """Return the value of a column from before the most recent save."""
        self.no_queries()
        return getattr(self.__class__, key).transform(self._previous_data.get(key))

    def delete(self: Self, except_if_not_exists=True) -> bool:
        """Delete a record."""
        self.no_queries()
        if not self:
            if except_if_not_exists:
                raise ValueError("Cannot delete model that already exists")
            return True

        columns = self.get_columns()
        self.columns_pre_delete(columns)
        self.pre_delete()

        self.backend.delete(self._data[self.id_column_name], self)  # type: ignore

        self.columns_post_delete(columns)
        self.post_delete()
        return True

    def columns_pre_save(self: Self, data: dict[str, Any], columns) -> dict[str, Any]:
        """Use the column information present in the model to make any necessary changes before saving."""
        iterate = True
        changed = {}
        while iterate:
            iterate = False
            for column in columns.values():
                data = column.pre_save(data, self)
                if data is None:
                    raise ValueError(
                        f"Column {column.name} of type {column.__class__.__name__} did not return any data for pre_save"
                    )

                # if we have newly chnaged data then we want to loop through the pre-saves again
                if data and column.name not in changed:
                    changed[column.name] = True
                    iterate = True
        return data

    def columns_to_backend(self: Self, data: dict[str, Any], columns) -> Any:
        backend_data = {**data}
        temporary_data = {}
        for column in columns.values():
            if column.is_temporary:
                if column.name in backend_data:
                    temporary_data[column.name] = backend_data[column.name]
                    del backend_data[column.name]
                continue

            backend_data = self.backend.column_to_backend(column, backend_data)  # type: ignore
            if backend_data is None:
                raise ValueError(
                    f"Column {column.name} of type {column.__class__.__name__} did not return any data for to_database"
                )

        return [backend_data, temporary_data]

    def to_backend(self: Self, data: dict[str, Any], columns) -> dict[str, Any]:
        return data

    def columns_post_save(self: Self, data: dict[str, Any], id: str | int, columns) -> dict[str, Any]:
        """Use the column information present in the model to make additional changes as needed after saving."""
        for column in columns.values():
            column.post_save(data, self, id)
        return data

    def columns_save_finished(self: Self, columns) -> None:
        """Call the save_finished method on all of our columns."""
        for column in columns.values():
            column.save_finished(self)

    def post_save(self: Self, data: dict[str, Any], id: str | int) -> None:
        """
        Create a hook to extend so you can provide additional pre-save logic as needed.

        It is passed in the data being saved as well as the id.  It should take action as needed and then return
        either the original data array or an adjusted one if appropriate.
        """
        pass

    def pre_save(self: Self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a hook to extend so you can provide additional pre-save logic as needed.

        It is passed in the data being saved and it should return the same data with adjustments as needed
        """
        return data

    def save_finished(self: Self) -> None:
        """
        Create a hook to extend so you can provide additional logic after a save operation has fully completed.

        It has no retrun value and is passed no data.  By the time this fires the model has already been
        updated with the new data.  You can decide on the necessary actions using the `was_changed` and
        the `previous_value` functions.
        """
        pass

    def columns_pre_delete(self: Self, columns: dict[str, Column]) -> None:
        """Use the column information present in the model to make any necessary changes before deleting."""
        for column in columns.values():
            column.pre_delete(self)

    def pre_delete(self: Self) -> None:
        """Create a hook to extend so you can provide additional pre-delete logic as needed."""
        pass

    def columns_post_delete(self: Self, columns: dict[str, Column]) -> None:
        """Use the column information present in the model to make any necessary changes after deleting."""
        for column in columns.values():
            column.post_delete(self)

    def post_delete(self: Self) -> None:
        """Create a hook to extend so you can provide additional post-delete logic as needed."""
        pass

    def where_for_request(
        self: Self,
        models: Self,
        routing_data: dict[str, str],
        authorization_data: dict[str, Any],
        input_output: Any,
        overrides: dict[str, Column] = {},
    ) -> Self:
        """Create a hook to automatically apply filtering whenever the model makes an appearance in a get/update/list/search handler."""
        for column in self.get_columns(overrides=overrides).values():
            models = column.where_for_request(models, routing_data, authorization_data, input_output)  # type: ignore
        return models

    ##############################################################
    ### From here down is functionality related to list/search ###
    ##############################################################
    def has_query(self) -> bool:
        """Whether or not this model instance represents a query."""
        return bool(self._query)

    def get_query(self) -> Query:
        """Fetch the query object in the model."""
        return self._query if self._query else Query(self.__class__)

    def as_query(self) -> Self:
        """
        Make the model queryable.

        This is used to remove the ambiguity of attempting execute a query against a model object that stores a record.

        The reason this exists is because the model class is used both to query as well as to operate on single records, which can cause
        subtle bugs if a developer accidentally confuses the two usages.  Consider the following (partial) example:

        ```python
        def some_function(models):
            model = models.find("id=5")
            if model:
                models.save({"test": "example"})
            other_record = model.find("id=6")
        ```

        In the above example it seems likely that the intention was to use `model.save()`, not `models.save()`.  Similarly, the last line
        should be `models.find()`, not `model.find()`.  To minimize these kinds of issues, clearskies won't let you execute a query against
        an individual model record, nor will it let you execute a save against a model being used to make a query.  In both cases, you'll
        get an exception from clearskies, as the models track exactly how they are being used.

        In some rare cases though, you may want to start a new query aginst a model that represents a single record.  This is most common
        if you have a function that was passed an individual model, and you'd like to use it to fetch more records without having to
        inject the model class more generally.  That's where the `as_query()` method comes in.  It's basically just a way of telling clearskies
        "yes, I really do want to start a query using a model that represents a record".  So, for example:

        ```python
        def some_function(models):
            model = models.find("id=5")
            more_models = model.where("test=example")  # throws an exception.
            more_models = model.as_query().where("test=example")  # works as expected.
        ```
        """
        new_model = self._di.build(self.__class__, cache=False)
        new_model.set_query(Query(self.__class__))
        return new_model

    def set_query(self, query: Query) -> Self:
        """Set the query object."""
        self._query = query
        self._query_executed = False
        return self

    def with_query(self, query: Query) -> Self:
        return self._di.build(self.__class__, cache=False).set_query(query)

    def select(self: Self, select: str) -> Self:
        """
        Add some additional columns to the select part of the query.

        This method returns a new object with the updated query.  The original model object is unmodified.
        Multiple calls to this method add together.  The following:

        ```python
        models.select("column_1 column_2").select("column_3")
        ```

        will select column_1, column_2, column_3 in the final query.
        """
        self.no_single_model()
        return self.with_query(self.get_query().add_select(select))

    def select_all(self: Self, select_all=True) -> Self:
        """
        Set whether or not to select all columns with the query.

        This method returns a new object with the updated query.  The original model object is unmodified.
        """
        self.no_single_model()
        return self.with_query(self.get_query().set_select_all(select_all))

    def where(self: Self, where: str | Condition) -> Self:
        """
        Add a condition to a query.

        The `where` method (in combination with the `find` method) is typically the starting point for query records in
        a model.  You don't *have* to add a condition to a model in order to fetch records, but of course it's a very
        common use case.  Conditions in clearskies can be built from the columns or can be constructed as SQL-like
        string conditions, e.g. `model.where("name=Bob")` or `model.where(model.name.equals("Bob"))`.  The latter
        provides strict type-checking, while the former does not.  Either way they have the same result.  The list of
        supported operators for a given column can be seen by checking the `_allowed_search_operators` attribute of the
        column class.  Most columns accept all allowed operators, which are:

         - "<=>"
         - "!="
         - "<="
         - ">="
         - ">"
         - "<"
         - "="
         - "in"
         - "is not null"
         - "is null"
         - "like"

        When working with string conditions, it is safe to inject user input into the condition.  The allowed
        format for conditions is very simple: `f"{column_name}\\s?{operator}\\s?{value}"`.  This makes it possible to
        unambiguously separate all three pieces from eachother.  It's not possible to inject malicious payloads into either
        the column names or operators because both are checked against a strict allow list (e.g. the columns declared in the
        model or the list of allowed operators above).  The value is then extracted from the leftovers, and this is
        provided to the backend separately so it can use it appropriately (e.g. using prepared statements for the cursor
        backend).  Of course, you generally shouldn't have to inject user input into conditions very often because, most
        often, the various list/search endpoints do this for you, but if you have to do it there are no security
        concerns.

        When you call the `where` method it returns a new model object with it's query configured to include the additional
        condition.  The original model object remains unchanged.  Multiple conditions are always joined with AND.  There is
        no explicit option for OR.  The closest is using an IN condition.

        To access over the results you have to iterate over the resulting model.  If you are only expecting one result
        and want to work directly with it, then you can use `model.find(condition)` or `model.where(condition).first()`.

        Example:
        ```python
        import clearskies

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

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[Order],
        )
        cli()
        ```

        Which, if ran, returns: `["Jane"]`

        """
        self.no_single_model()
        return self.with_query(self.get_query().add_where(where if isinstance(where, Condition) else Condition(where)))

    def join(self: Self, join: str) -> Self:
        """Add a join clause to the query."""
        self.no_single_model()
        return self.with_query(self.get_query().add_join(Join(join)))

    def is_joined(self: Self, table_name: str, alias: str = "") -> bool:
        """
        Check if a given table was already joined.

        If you provide an alias then it will also verify if the table was joined with the specific alias name.
        """
        for join in self.get_query().joins:
            if join.unaliased_table_name != table_name:
                continue

            if alias and join.alias != alias:
                continue

            return True
        return False

    def group_by(self: Self, group_by_column_name: str) -> Self:
        """Add a group by clause to the query."""
        self.no_single_model()
        return self.with_query(self.get_query().set_group_by(group_by_column_name))

    def sort_by(
        self: Self,
        primary_column_name: str,
        primary_direction: str,
        primary_table_name: str = "",
        secondary_column_name: str = "",
        secondary_direction: str = "",
        secondary_table_name: str = "",
    ) -> Self:
        """
        Add a sort by clause to the query.  You can sort by up to two columns at once.

        Example:
        ```
        import clearskies

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

        cli = clearskies.contexts.Cli(
            clearskies.endpoints.Callable(
                my_application,
                model_class=Order,
                readable_column_names=["user_id", "total"],
            ),
            classes=[Order],
        )
        cli()
        ```
        """
        self.no_single_model()
        sort = Sort(primary_table_name, primary_column_name, primary_direction)
        secondary_sort = None
        if secondary_column_name and secondary_direction:
            secondary_sort = Sort(secondary_table_name, secondary_column_name, secondary_direction)
        return self.with_query(self.get_query().set_sort(sort, secondary_sort))

    def limit(self: Self, limit: int) -> Self:
        """Set the number of records to return."""
        self.no_single_model()
        return self.with_query(self.get_query().set_limit(limit))

    def pagination(self: Self, **pagination_data) -> Self:
        self.no_single_model()
        error = self.backend.validate_pagination_data(pagination_data, str)
        if error:
            raise ValueError(
                f"Invalid pagination data for model {self.__class__.__name__} with backend "
                + f"{self.backend.__class__.__name__}. {error}"
            )
        return self.with_query(self.get_query().set_pagination(pagination_data))

    def find(self: Self, where: str | Condition) -> Self:
        """
        Return the first model matching a given where condition.

        This is just shorthand for `models.where("column=value").find()`.  Example:

        ```python
        import clearskies

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

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[Order],
        )
        cli()
        ```
        """
        self.no_single_model()
        return self.where(where).first()

    def __len__(self: Self):  # noqa: D105
        self.no_single_model()
        if self._count is None:
            self._count = self.backend.count(self.get_query())
        return self._count

    def __iter__(self: Self) -> Iterator[Self]:  # noqa: D105
        self.no_single_model()
        self._next_page_data = {}
        raw_rows = self.backend.records(
            self.get_query(),
            next_page_data=self._next_page_data,
        )
        return iter([self.model(row) for row in raw_rows])

    def paginate_all(self: Self) -> list[Self]:
        """
        Loop through all available pages of results and returns a list of all models that match the query.

        NOTE: this loads up all records in memory before returning (e.g. it isn't using generators yet), so
        expect delays for large record sets.

        ```python
        for model in models.where("column=value").paginate_all():
            print(model.id)
        ```
        """
        self.no_single_model()
        next_models = self.with_query(self.get_query())
        results = list(next_models.__iter__())
        next_page_data = next_models.next_page_data()
        while next_page_data:
            next_models = self.pagination(**next_page_data)
            results.extend(next_models.__iter__())
            next_page_data = next_models.next_page_data()
        return results

    def model(self: Self, data: dict[str, Any] = {}) -> Self:
        """
        Create a new model object and populates it with the data in `data`.

        NOTE: the difference between this and `model.create` is that model.create() actually saves a record in the backend,
        while this method just creates a model object populated with the given data.
        """
        model = self._di.build(self.__class__, cache=False)
        model.set_raw_data(data)
        return model

    def empty(self: Self) -> Self:
        """
        An alias for self.model({})
        """
        return self.model({})

    def create(self: Self, data: dict[str, Any] = {}, columns: dict[str, Column] = {}, no_data=False) -> Self:
        """
        Create a new record in the backend using the information in `data`.

        new_model = models.create({"column": "value"})
        """
        empty = self.model()
        empty.save(data, columns=columns, no_data=no_data)
        return empty

    def first(self: Self) -> Self:
        """
        Return the first model for a given query.

        The `where` method returns an object meant to be iterated over.  If you are expecting your query to return a single
        record, then you can use first to turn that directly into the matching model so you don't have to iterate over it:

        ```
        import clearskies

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

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[Order],
        )
        cli()

        ```
        """
        self.no_single_model()
        iter = self.__iter__()
        try:
            return iter.__next__()
        except StopIteration:
            return self.model()

    def allowed_pagination_keys(self: Self) -> list[str]:
        return self.backend.allowed_pagination_keys()

    def validate_pagination_data(self, kwargs: dict[str, Any], case_mapping: Callable[[str], str]) -> str:
        return self.backend.validate_pagination_data(kwargs, case_mapping)

    def next_page_data(self: Self):
        return self._next_page_data

    def documentation_pagination_next_page_response(self: Self, case_mapping: Callable) -> list[Any]:
        return self.backend.documentation_pagination_next_page_response(case_mapping)

    def documentation_pagination_next_page_example(self: Self, case_mapping: Callable) -> dict[str, Any]:
        return self.backend.documentation_pagination_next_page_example(case_mapping)

    def documentation_pagination_parameters(self: Self, case_mapping: Callable) -> list[tuple[AutoDocSchema, str]]:
        return self.backend.documentation_pagination_parameters(case_mapping)

    def no_queries(self) -> None:
        if self._query:
            raise ValueError(
                "You attempted to save/read record data for a model being used to make a query.  This is not allowed, as it is typically a sign of a bug in your application code."
            )

    def no_single_model(self):
        if self._data:
            raise ValueError(
                "You have attempted to execute a query against a model that represents an individual record.  This is not allowed, as it is typically a sign of a bug in your application code.  If this is intentional, call model.as_query() before executing your query."
            )


class ModelClassReference:
    @abstractmethod
    def get_model_class(self) -> type[Model]:
        pass
