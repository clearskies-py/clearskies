from __future__ import annotations

from typing import TYPE_CHECKING, Self

from clearskies.di.injectable import Injectable

if TYPE_CHECKING:
    from clearskies.di import Di


class InjectableProperties:
    """
    Fetch dependencies via properties rather than constructor arguments.

    This class allows you to specify dependencies by setting them as class properties instead of constructor
    arguments.  This is common in clearskies as it helps make easily reusable classes - configuration can
    go in the constructor of the class, allowing the developer to directly instantiate it, and then the DI system
    will come by afterwards and provide the necessary dependencies.

    After adding InjectableProperties as a parent of your class, you have two ways to specify your dependencies:

     1. By using the classes in the `clearskies.di.inject.*`module.
     2. By directly attaching objects which also use the `InjectableProperties` class.

    The following table shows the dependencies that can be injected as properties via the clearskies.di.inject module:

    | Class                            | Type                                 | Result                                          |
    |----------------------------------|--------------------------------------|-------------------------------------------------|
    | clearskies.di.inject.ByClass     | N/A                                  | The specified class will be built               |
    | clearskies.di.inject.ByName      | N/A                                  | The specified dependnecy name will be built     |
    | clearskies.di.inject.Cursor      | N/A                                  | The PyMySQL cursor                              |
    | clearskies.di.inject.Di          | N/A                                  | The dependency injection container itself       |
    | clearskies.di.inject.Environment | clearskies.Environment               | The environment helper                          |
    | clearskies.di.inject.InputOutput | clearskies.input_outputs.InputOutput | The InputOutput object for the current request  |
    | clearskies.di.inject.Now         | datetime.datetime                    | The current time (no timezone)                  |
    | clearskies.di.inject.Requests    | requests.Session                     | A requests session                              |
    | clearskies.di.inject.Utcnow      | datetime.datetime                    | The current time (tzinfo=datetime.timezone.utc) |

    Note: now/utcnow are not cached, so you'll get the current time everytime you get a value out of the class property,
    unless a specific time has been set on the dependency injection container.

    Here's an example:

    ```python
    import clearskies
    import time
    import clearskies.decorators


    class MyOtherThing(clearskies.di.InjectableProperties):
        now = clearskies.di.inject.Now()


    class ReusableClass(clearskies.Configurable, clearskies.di.InjectableProperties):
        my_int = clearskies.configs.Integer(required=True)
        some_number = clearskies.di.inject.ByName("some_number")
        my_other_thing = clearskies.di.inject.ByClass(MyOtherThing)

        @clearskies.decorators.parameters_to_properties
        def __init__(self, my_int: int):
            self.finalize_and_validate_configuration()

        def my_value(self) -> int:
            return self.my_int * self.some_number


    class MyClass(clearskies.di.InjectableProperties):
        reusable = ReusableClass(5)


    class MyOtherClass(clearskies.di.InjectableProperties):
        reusable = ReusableClass(10)


    di = clearskies.di.Di(
        bindings={
            "some_number": 10,
        }
    )

    my_class = di.build(MyClass)
    print(my_class.reusable.my_value())  # prints 50

    my_other_class = di.build(MyOtherClass)
    print(my_other_class.reusable.my_value())  # prints 100

    start = my_class.reusable.my_other_thing.now
    time.sleep(1)
    stop = my_class.reusable.my_other_thing.now
    print((stop - start).seconds)  # prints 1
    ```
    """

    _injectables_loaded: str = ""

    @classmethod
    def injectable_properties(cls, di: Di):
        cache_name = str(cls) + str(di._serial)
        if cache_name == cls._injectables_loaded:
            return

        injectable_properties: list[Self] = []
        for attribute_name in dir(cls):
            # Per the docs above, we want to inject properties for one of two things: the injectables from clearskies.di.inject,
            # and any object that itself extends this class.  This is mildly tricky because the injectables are descriptors, and
            # so we get them using getattr on the class, while if it's not a descriptor, then we want to use getattr on self.
            # The important part here is that we modify descriptors at the class level, so the actual injected values have to
            # be stored in self, and not in the descriptor object.  When it's not a descriptor, then we can modify the object
            # directly (since we're operating at the object level, not class level).  Either way, while we go, let's keep track
            # of what our dependencies are and which ones are cached, so we only have to list the objects attributes the first time.
            attribute = getattr(cls, attribute_name)

            override = di.get_class_override(attribute.__class__, context=cls)
            if override is not None:
                if not hasattr(cls, "__overridden__"):
                    cls.__overridden__ = {}
                cls.__overridden__[attribute_name] = attribute
                setattr(cls, attribute_name, di.get_override_by_class(attribute, context=cls))
                continue

            # This exists to cover a common edge case in testing.  If we override an attribute with a new class (common when
            # we override a backend with the memory backend) then the next time we run a test the backend will already be
            # overridden by the memory backend so, unless you have overridden the memory backend, you won't trigger the above
            # condition and you'lljust leave the old memory backend in place.  Therefore, when we override an attribute, we
            # also keep track of what the attribute *used* to be so that we can override it every time.
            if hasattr(cls, "__overridden__") and attribute_name in cls.__overridden__:
                setattr(cls, attribute_name, di.get_override_by_class(cls.__overridden__[attribute_name], context=cls))

            # Check for config overrides — patches specific config values on existing Configurable instances.
            # We store the original so re-runs apply to the unpatched original, not the already-patched copy.
            config_patches = di.get_config_override(attribute.__class__, context=cls)
            if config_patches:
                if not hasattr(cls, "__config_overridden__"):
                    cls.__config_overridden__ = {}
                if attribute_name not in cls.__config_overridden__:
                    cls.__config_overridden__[attribute_name] = attribute
                patched = di.apply_config_overrides(cls.__config_overridden__[attribute_name], config_patches)
                setattr(cls, attribute_name, patched)
                if hasattr(patched, "injectable_properties"):
                    patched.injectable_properties(di)
                continue

            if hasattr(cls, "__config_overridden__") and attribute_name in cls.__config_overridden__:
                config_patches = di.get_config_override(
                    cls.__config_overridden__[attribute_name].__class__, context=cls
                )
                if config_patches:
                    patched = di.apply_config_overrides(cls.__config_overridden__[attribute_name], config_patches)
                    setattr(cls, attribute_name, patched)
                    if hasattr(patched, "injectable_properties"):
                        patched.injectable_properties(di)

            if issubclass(attribute.__class__, Injectable):
                attribute.set_di(di)
                continue

            if hasattr(attribute, "injectable_properties"):
                attribute.injectable_properties(di)

        cls._injectables_loaded = cache_name
