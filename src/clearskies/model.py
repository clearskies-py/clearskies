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
        Save data to the database and create/update the underlying record.

        ### Lifecycle of a Save

        Before discussing the mechanics of how to save a model, it helps to understand the full lifecycle of a save
        operation.  Of course you can ignore this lifecycle and simply use the save process to send data to a
        backend, but then you miss out on one of the key advantages of clearskies - supporting a state machine
        flow for defining your applications.  The save process is controlled not just by the model but also by
        the columns, with equivalent hooks for both.  This creates a lot of flexibility for how to control and
        organize an application.  The overall save process looks like this:

         1. The `pre_save` hook in each column is called (including the `on_change_pre_save` actions attached to the columns)
         2. The `pre_save` hook for the model is called
         3. The `to_backend` hook for each column is called and temporary data is removed from the save dictionary
         4. The `to_backend` hook for the model is called
         5. The data is persisted to the backend via a create or update call as appropriate
         6. The `post_save` hook in each column is called (including the `on_change_post_save` actions attached to the columns)
         7. The `post_save` hook in the model is called
         8. Any data returned by the backend during the create/update operation is saved to the model along with the temporary data
         9. The `save_finished` hook in each column is called (including the `on_change_save_finished` actions attached to the columns)
         10. The `save_finished` hook in the model is called

        Note that pre/post/finished hooks for all columns are called - not just the ones with data in the save.
        Thus, any column attached to a model can always influence the save process.

        From this we can see how to use these hooks.  In particular:

         1. The `pre_save` hook is used to modify the data before it is persisted to the backend.  This means that changes
            can be made to the data dictionary in the `pre_save` step and there will still only be a single save operation
            with the backend.  For columns, the `on_change_pre_save` methods *MUST* be stateless - they can return data to
            change the save but should not make any changes themselves.  This is because they may be called more than once
            in a given save operation.
         2. `to_backend` is used to modify data on its way to the backend.  Consider dates: in python these are typically represented
            by datetime objects but, to persist this to (for instance) an SQL database, it usually has to be converted to a string
            format first.  That happens in the `to_backend` method of the datetime column.
         3. The `post_save` hook is called after the backend is updated.  Therefore, if you are using auto-incrementing ids,
            the id will only be available in ths hook.  For consistency with this, clearskies doesn't directly provide the record id
            until the `post_save` hook.  If you need to make more data changes in this hook, an additional operation will
            be required.  Since the backend has already been updated, this hook does not require a return value (and anything
            returned will be ignored).
         4. The save finished hook happens after the save is fully completed. The backend is updated and the model has been
            updated and the model state reflects the new backend state.

        The following table summarizes some key details of these hooks:

        | Name            | Stateful | Return Value   | Id Present | Backend Updated | Model Updated |
        |-----------------|----------|----------------|------------|-----------------|---------------|
        | `pre_save`      | No       | dict[str, Any] | No         | No              | No            |
        | `post_save`     | Yes      | None           | Yes        | Yes             | No            |
        | `save_finished` | Yes      | None           | Yes        | Yes             | Yes           |

        ### How to Create/Update a Model

        There are two supported flows.  One is to pass in a dictionary of data to save:

        ```python
        import clearskies

        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(user):
            user.save({
                "name": "Awesome Person",
            })
            return {"id": user.id, "name": user.name}

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```

        And the other is to set new values on the columns attributes and then call save without data:

        ```python
        import clearskies

        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(user):
            user.name = "Awesome Person"
            user.save()
            return {"id": user.id, "name": user.name}

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```

        The primray difference is that setting attributes provides strict type checking capabilities, while passing a
        dictionary can be done in one line.  Note that you cannot combine these methods: if you set a value on a
        column attribute and also pass in a dictionary of data to the save, then an exception will be raised.
        In either case the save operation acts in place  on the model object.  The return value is always True - in
        the event of an error an exception will be raised.

        If a record already exists in the model being saved, then an update operation will be executed.  Otherwise,
        a new record will be inserted.  To understand the difference yourself, you can convert a model to a boolean
        value - it will return True if a record has been loaded and false otherwise.  You can see that with this
        example, where all the `if` statements will evaluate to `True`:

        ```
        import clearskies

        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(user):

            if not user:
                print("We will execute a create operation")

            user.save({"name": "Test One"})
            new_id = user.id

            if user:
                print("We will execute an update operation")

            user.save({"name": "Test Two"})

            final_id = user.id

            if new_id == final_id:
                print("The id did not chnage because the second save performed an update")

            return {"id": user.id, "name": user.name}

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```

        occassionaly, you may want to execute a save operation without actually providing any data.  This may happen,
        for instance, if you want to create a record in the database that will be filled in later, and so just need
        an auto-generated id.  By default if you call save without setting attributes on the model and without
        providing data to the `save` call, this will raise an exception, but you can make this happen with the
        `no_data` kwarg:

        ```
        import clearskies

        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(user):
            # create a record with just an id
            user.save(no_data=True)

            # and now we can set the name
            user.save({"name": "Test"})

            return {"id": user.id, "name": user.name}

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```
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

        A column is considered to be changing if:

         - During a create operation
           - It is present in the data array, even if a null value
         - During an update operation
           - It is present in the data array and the value is changing

        Note whether or not the value is changing is typically evaluated with a simple `=` comparison,
        but columns can optionally implement their own custom logic.

        Pass in the name of the column to check and the data dictionary from the save in progress.  This only
        returns meaningful results during a save, which typically happens in the pre-save/post-save hooks
        (either on the model class itself or in a column).  Here's an examle that extends the `pre_save` hook
        on the model to demonstrate how `is_changing` works:

        ```
        from typing import Any, Self
        import clearskies

        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            age = clearskies.columns.Integer()

            def pre_save(self: Self, data: dict[str, Any]) -> dict[str, Any]:
                if self.is_changing("name", data) and self.is_changing("age", data):
                    print("My name and age have changed!")
                elif self.is_changing("name", data):
                    print("Only my name is changing")
                elif self.is_changing("age", data):
                    print("Only my age is changing")
                else:
                    print("Nothing changed")
                return data

        def my_application(users):
            jane = users.create({"name": "Jane"})
            jane.save({"age": 22})
            jane.save({"name": "Anon", "age": 23})
            jane.save({"name": "Anon", "age": 23})

            return {"id": jane.id, "name": jane.name}

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```

        If you run the above example it will print out:

        ```
        Only my name is changing
        Only my age is changing
        My name and age have changed
        Nothing changed
        ```

        The first message is printed out when the record is created - during a create operation, any column that
        is being set to a non-null value is considered to be changing.  We then set the age, and since it changes
        from a null value (we didn't originally set an age with the create operation, so the age was null) to a
        non-null value, `is_changed` returns True.  We perform another update operation and set both
        name and age to new values, so both change.  Finally we repeat the same save operation.  This will result
        in another update operation on the backend, but `is_changed` reflects the fact that the values haven't
        actually changed from their previous values.

        """
        self.no_queries()
        has_old_value = key in self._data
        has_new_value = key in data

        if not has_new_value:
            return False

        if not has_old_value:
            return True

        columns = self.get_columns()
        new_value = data[key]
        old_value = self._data[key]
        if key not in columns:
            return old_value != new_value
        return not columns[key].values_match(old_value, new_value)

    def latest(self: Self, key: str, data: dict[str, Any]) -> Any:
        """
        Return the 'latest' value for a column during the save operation.

        During the pre_save and post_save hooks, the model is not yet updated with the latest data.
        In these hooks, it's common to want the "latest" data for the model - e.g. either the column value
        from the model or from the data dictionary (if the column is being updated in the save).  This happens
        via slightly verbose lines like: `data.get(column_name, getattr(self, column_name))`.  The `latest`
        method is just a substitue for this:

        ```
        from typing import Any, Self
        import clearskies

        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            age = clearskies.columns.Integer()

            def pre_save(self: Self, data: dict[str, Any]) -> dict[str, Any]:
                if not self:
                    print("Create operation in progress!")
                else:
                    print("Update operation in progress!")

                print("Latest name: " + str(self.latest("name", data)))
                print("Latest age: " + str(self.latest("age", data)))
                return data

        def my_application(users):
            jane = users.create({"name": "Jane"})
            jane.save({"age": 25})
            return {"id": jane.id, "name": jane.name}

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```
        The above example will print:

        ```
        Create operation in progress!
        Latest name: Jane
        Latest age: None
        Update operation in progress!
        Latest name: Jane
        Latest age: 25
        ```

        e.g. `latest` returns the value in the data array (if present), the value for the column in the model, or None.

        """
        self.no_queries()
        if key in data:
            return data[key]
        return getattr(self, key)

    def was_changed(self: Self, key: str) -> bool:
        """
        Return True/False to denote if a column was changed in the last save.

        To emphasize, the difference between this and `is_changing` is that `is_changing` is available during
        the save prcess while `was_changed` is available after the save has finished.  Otherwise, the logic for
        deciding if a column has changed is identical as for `is_changing`.

        ```
        import clearskies

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

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```

        In the above example the name is changed while the age is not.

        """
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

    def previous_value(self: Self, key: str, silent=False):
        """
        Return the value of a column from before the most recent save.

        ```
        import clearskies

        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(users):
            jane = users.create({"name": "Jane"})
            jane.save({"name": "Jane Doe"})
            return {"name": jane.name, "previous_name": jane.previous_value("name")}

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```

        The above example returns `{"name": "Jane Doe", "previous_name": "Jane"}`

        If you request a key that is neither a column nor was present in the previous data array,
        then you'll receive a key error.  You can suppress this by setting `silent=True` in your call to
        previous_value.
        """
        self.no_queries()
        if key not in self.get_columns() and key not in self._previous_data:
            raise KeyError(f"Unknown previous data key: {key}")
        if key not in self.get_columns():
            return self._previous_data.get(key)
        return getattr(self.__class__, key).from_backend(self._previous_data.get(key))

    def delete(self: Self, except_if_not_exists=True) -> bool:
        """
        Delete a record.

        If you try to delete a record that doesn't exist, an exception will be thrown unless you set
        `except_if_not_exists=False`.  After the record is deleted from the backend, the model instance
        is left unchanged and can be used to fetch the data previously stored.  In the following example
        both statements will be printed and the id and name in the "Alice" record will be returned,
        even though the record no longer exists:

        ```
        import clearskies

        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        def my_application(users):
            alice = users.create({"name": "Alice"})

            if users.find("name=Alice"):
                print("Alice exists")

            alice.delete()

            if not users.find("name=Alice"):
                print("No more Alice")

            return {"id": alice.id, "name": alice.name}

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()

        ```
        """
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

    def pre_save(self: Self, data: dict[str, Any]) -> dict[str, Any]:
        """
        A hook to add additional logic in the pre-save step of the save process.

        The pre/post/finished steps of the model are directly analogous to the pre/post/finished steps for the columns.

        pre-save is inteneded to be a stateless hook (e.g. you should not make changes to the backend) where you can
        adjust the data being saved to the model.  It is called before any data is persisted to the backend and
        must return a dictionary of data that will be added to the save, potentially over-writing the save data.
        Since pre-save happens before communicating with the backend, the record itself will not yet exist in the
        event of a create operation, and so the id will not be-present for auto-incrementing ids.  As a result, the
        record id is not provided during the pre-save hook.  See the breakdown of the save lifecycle in the `save`
        documentation above for more details.

        An here's an example of using it to set some additional data during a save:

        ```
        from typing import Any, Self
        import clearskies

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

            jane.save({"name":""})
            is_anonymous_after_first_update = jane.is_anonymous

            jane.save({"name": "Jane Doe"})
            is_anonymous_after_last_update = jane.is_anonymous

            return {
                "is_anonymous_after_create": is_anonymous_after_create,
                "is_anonymous_after_first_update": is_anonymous_after_first_update,
                "is_anonymous_after_last_update": is_anonymous_after_last_update,
            }

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```

        In our pre-save hook we set the `is_anonymous` field to either True or False depending on whether or
        not there is a value in the incoming `name` column.  As a result, after the original create operation
        (when the `name` is `"Jane"`, `is_anonymous` is False.  We then update the name and set it to an empty
        string, and `is_anonymous` becomes True.  We then update one last time to set a name again and
        `is_anonymous` becomes False.

        """
        return data

    def post_save(self: Self, data: dict[str, Any], id: str | int) -> None:
        """
        A hook to add additional logic in the post-save step of the save process.

        It is passed in the data being saved as well as the id of the record.  Keep in mind that the post save
        hook happens after the backend has been updated (but before the model is updated) so if you need to make
        any changes to the backend you must execute another save operation.  Since the backend is already updated,
        the return value from this function is ignored (it should return None):

        ```
        from typing import Any, Self
        import clearskies

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

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User, History],
        )
        cli()
        ```
        """
        pass

    def save_finished(self: Self) -> None:
        """
        A hook to add additional logicin the save_finished step of the save process.

        It has no retrun value and is passed no data.  By the time this fires the model has already been
        updated with the new data.  You can decide on the necessary actions using the `was_changed` and
        the `previous_value` functions.

        ```
        from typing import Any, Self
        import clearskies

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

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User, History],
        )
        cli()
        ```
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

    def where_for_request_all(
        self: Self,
        model: Self,
        input_output: Any,
        routing_data: dict[str, str],
        authorization_data: dict[str, Any],
        overrides: dict[str, Column] = {},
    ) -> Self:
        """
        A hook to automatically apply filtering whenever the model makes an appearance in a get/update/list/search handler.
        """
        for column in self.get_columns(overrides=overrides).values():
            models = column.where_for_request(model, input_output, routing_data, authorization_data)  # type: ignore
        return self.where_for_request(
            model, input_output, routing_data=routing_data, authorization_data=authorization_data, overrides=overrides
        )

    def where_for_request(
        self: Self,
        model: Self,
        input_output: Any,
        routing_data: dict[str, str],
        authorization_data: dict[str, Any],
        overrides: dict[str, Column] = {},
    ) -> Self:
        """
        A hook to automatically apply filtering whenever the model makes an appearance in a get/update/list/search handler.

        Note that this automatically affects the behavior of the various list endpoints, but won't be called when you create your
        own queries directly.  Here's an example where the model restricts the list endpoint so that it only returns users with
        an age over 18:

        ```
        from typing import Any, Self
        import clearskies

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

        wsgi = clearskies.contexts.WsgiRef(
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
        wsgi()
        ```
        """
        return model

    ##############################################################
    ### From here down is functionality related to list/search ###
    ##############################################################
    def has_query(self) -> bool:
        """
        Whether or not this model instance represents a query.

        The model class is used for both querying records and modifying individual records.  As a result, each model class instance
        keeps track of whether it is being used to query things, or whether it represents an individual record.  This distinction
        is not usually very important to the developer (because there's no good reason to use one model for both), but it may
        occassionaly be useful to tell how a given model is being used.  Clearskies itself does use this to ensure that you
        can't accidentally use a single model instance for both purposes, mostly because when this happens it's usually a sign
        of a bug.

        ```
        import clearskies

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

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```

        Which if you run will return:

        ```
        {
            "jane_instance_has_query": false,
            "some_search_has_query": true,
            "invalid_request_error": "You attempted to save/read record data for a model being used to make a query.  This is not allowed, as it is typically a sign of a bug in your application code."
        }
        ```

        """
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

        You can include a table name before the column name, with the two separated by a period.  As always, if you do this,
        ensure that you include a supporting join statement (via the `join` method - see it for examples).

        When you call the `where` method it returns a new model object with it's query configured to include the additional
        condition.  The original model object remains unchanged.  Multiple conditions are always joined with AND.  There is
        no explicit option for OR.  The closest is using an IN condition.

        To access the results you have to iterate over the resulting model.  If you are only expecting one result
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
        """
        Add a join clause to the query.

        As with the `where` method, this expects a string which is parsed accordingly.  The syntax is not as flexible as
        SQL and expects a format of:

        ```
        [left|right|inner]? join [right_table_name] ON [right_table_name].[right_column_name]=[left_table_name].[left_column_name].
        ```

        This is case insensitive.  Aliases are allowed.  If you don't specify a join type it defaults to inner.
        Here are two examples of valid join statements:

         - `join orders on orders.user_id=users.id`
         - `left join user_orders as orders on orders.id=users.id`

        Note that joins are not strictly limited to SQL-like backends, but of course no all backends will support joining.

        A basic example:

        ```
        import clearskies

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

            # return all orders for anyone named Jane that have a status of Pending
            return orders.join("join users on users.id=orders.user_id").where("users.name=Jane").sort_by("total", "asc").where("status=Pending")

        cli = clearskies.contexts.Cli(
            clearskies.endpoints.Callable(
                my_application,
                model_class=Order,
                readable_column_names=["user", "total"],
            ),
            classes=[Order, User],
        )
        cli()

        ```
        """
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
        """
        Add a group by clause to the query.

        You just provide the name of the column to group by.  Of course, not all backends support a group by clause.
        """
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
        """
        Set the number of records to return.

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

            return orders.limit(2)

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
        return self.with_query(self.get_query().set_limit(limit))

    def pagination(self: Self, **pagination_data) -> Self:
        """
        Set the pagination parameter(s) for the query.

        The exact details of how pagination work depend on the backend.  For instance, the cursor and memory backend
        expect to be given a `start` parameter, while an API backend will vary with the API, and the dynamodb backend
        expects a kwarg called `cursor`.  As a result, it's necessary to check the backend documentation to understand
        how to properly set pagination.  The endpoints automatically account for this because backends are required
        to declare pagination details via the `allowed_pagination_keys` method.  If you attempt to set invalid
        pagination data via this method, clearskies will raise a ValueError.

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

            return orders.sort_by("total", "asc").pagination(start=2)

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

        However, if the return line in `my_application` is switched for either of these:

        ```
        return orders.sort_by("total", "asc").pagination(start="asdf")
        return orders.sort_by("total", "asc").pagination(something_else=5)
        ```

        Will result in an exception that explains exactly what is wrong.

        """
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

        If you don't set a limit on a query, some backends will return all records but some backends have a
        default maximum number of results that they will return.  In the latter case, you can use `paginate_all`
        to fetch all records by instructing clearskies to iterate over all pages.  This is possible because backends
        are required to define how pagination works in a way that clearskies can automatically understand and
        use.  To demonstrate this, the following example sets a limit of 1 which stops the memory backend
        from returning everything, and then uses `paginate_all` to fetch all records.  The memory backend
        doesn't have a default limit, so in practice the `paginate_all` is unnecessary here, but this is done
        for demonstration purposes.

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

            return orders.limit(1).paginate_all()

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

        NOTE: this loads up all records in memory before returning (e.g. it isn't using generators yet), so
        expect delays for large record sets.
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
        while this method just creates a model object populated with the given data.  This can be helpful if you have record
        data loaded up in some alternate way and want to wrap a model around it.  Calling the `model` method does not result
        in any interactions with the backend.

        In the following example we create a record in the backend and then make a new model instance using `model`, which
        we then use to udpate the record.  The returned name will be `Jane Doe`.

        ```
        import clearskies

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

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```
        """
        model = self._di.build(self.__class__, cache=False)
        model.set_raw_data(data)
        return model

    def empty(self: Self) -> Self:
        """
        An alias for self.model({})

        This just provides you a fresh, empty model instance that you can use for populating with data or creating
        a new record.  Here's a simple exmaple.  Both print statements will be printed and it will return the id
        for the Alice record, and then null for `blank_id`:

        ```
        import clearskies

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

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```
        """
        return self.model({})

    def create(self: Self, data: dict[str, Any] = {}, columns: dict[str, Column] = {}, no_data=False) -> Self:
        """
        Create a new record in the backend using the information in `data`.

        The `save` method always operates changes the model directly rather than creating a new model instance.
        Often, when creating a new record, you will need to both create a new (empty) model instance and save
        data to it.  You can do this via `model.empty().save({"data": "here"})`, and this method provides a simple,
        unambiguous shortcut to do exactly that.  So, you pass your save data to the `create` method and you will get
        back a new model:

        ```
        import clearskies

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

        cli = clearskies.contexts.Cli(
            my_application,
            classes=[User],
        )
        cli()
        ```

        Like with `save`, you can set `no_data=True` to create a record without specifying any model data.
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
