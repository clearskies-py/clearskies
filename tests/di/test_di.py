import datetime
import os
import unittest

import requests

import clearskies.configs
import clearskies.decorators
from clearskies.di import AdditionalConfig, Di, InjectableProperties, inject
from clearskies.exceptions import MissingDependency


class SomeClass:
    def __init__(self, my_value: int):
        self.my_value = my_value


class MyClass:
    def __init__(self, some_specific_value: int, some_class: SomeClass):
        self.final_value = some_specific_value * some_class.my_value


class VeryNeedy:
    def __init__(self, my_class, some_other_value: str):
        self.my_class = my_class
        self.some_other_value = some_other_value


class MyOtherProvider(AdditionalConfig):
    def provide_some_specific_value(self):
        return 10


class MyProvider(AdditionalConfig):
    def provide_some_specific_value(self):
        return 5

    def can_build_class(self, class_to_check: type) -> bool:
        return class_to_check == SomeClass

    def build_class(self, class_to_provide: type, argument_name: str, di, context: str = ""):
        if class_to_provide == SomeClass:
            return SomeClass(5)
        raise ValueError(f"I was asked to build a class I didn't expect '{class_to_provide.__name__}'")


def my_function(this_uses_type_hinting_exclusively: VeryNeedy):
    return f"Jane owns {this_uses_type_hinting_exclusively.my_class.final_value} {this_uses_type_hinting_exclusively.some_other_value}s"


class DiTest(unittest.TestCase):
    def test_di_class_examples(self):
        di = Di(
            classes=[MyClass, VeryNeedy, SomeClass],
            additional_configs=[MyProvider(), MyOtherProvider()],
            bindings={
                "some_other_value": "dog",
            },
        )

        assert di.call_function(my_function) == "Jane owns 50 dogs"

    def test_add_classes_example(self):
        class MyClass:
            name = "Simple Demo"

        def my_function(my_class):
            return my_class.name

        di = Di(classes=[MyClass])
        assert "Simple Demo" == di.call_function(my_function)

        di = Di()
        di.add_classes(MyClass)
        assert "Simple Demo" == di.call_function(my_function)

    def test_add_modules_example(self):
        from . import my_module

        def my_function(my_class):
            return my_class.count

        di = Di(modules=my_module)
        assert di.call_function(my_function) == 5

        di = Di()
        di.add_modules([my_module])
        assert di.call_function(my_function) == 5

    def test_add_additional_config(self):
        class MyConfig(AdditionalConfig):
            def provide_some_value(self):
                return 2

            def provide_another_value(self, some_value):
                return some_value * 2

        def my_function(another_value):
            return another_value

        di = Di()
        di.add_additional_configs([MyConfig()])
        assert di.call_function(my_function) == 4

        di = Di(additional_configs=[MyConfig()])
        assert di.call_function(my_function) == 4

    def test_add_binding(self):
        def my_function(my_name):
            return my_name

        di = Di()
        di.add_binding("my_name", 12345)
        assert di.call_function(my_function) == 12345

        di = Di(bindings={"my_name": 12345})
        assert di.call_function(my_function) == 12345

    def test_add_class_override(self):
        class TypeHintedClass:
            my_value = 5

        class ReplacementClass:
            my_value = 10

        di = Di()
        di.add_classes(TypeHintedClass)
        di.add_class_override(TypeHintedClass, ReplacementClass)

        def my_function(some_value: TypeHintedClass):
            return some_value.my_value

        assert di.call_function(my_function) == 10

        di = Di(classes=[TypeHintedClass], class_overrides={TypeHintedClass: ReplacementClass})
        assert di.call_function(my_function) == 10

    def test_now(self):
        di = Di()
        now = datetime.datetime.now()
        also_now = di.build("now")
        assert now.year == also_now.year
        assert now.month == also_now.month
        assert now.day == also_now.day
        assert also_now.tzinfo == None

        di.set_now(now)
        assert now == di.build("now")
        assert now != also_now

    def test_utcnow(self):
        di = Di()
        utcnow = datetime.datetime.now(datetime.timezone.utc)
        also_utcnow = di.build("utcnow")
        assert utcnow.year == also_utcnow.year
        assert utcnow.month == also_utcnow.month
        assert utcnow.day == also_utcnow.day
        assert also_utcnow.tzinfo == datetime.timezone.utc

        di.set_utcnow(utcnow)
        assert utcnow == di.build("utcnow")
        assert utcnow != also_utcnow

    def test_requests(self):
        di = Di()
        assert isinstance(di.build("requests"), requests.Session)
        assert di.build("requests", cache=True) == di.build("requests", cache=True)
        assert di.build("requests", cache=True) != di.build(requests.Session, cache=True)
        assert di.build(requests.Session, cache=True) == di.build(requests.Session, cache=True)

    def test_inject(self):
        class MySubDep(InjectableProperties):
            requests = inject.Requests()
            value = inject.ByName("asdfer")

        class MyClass(InjectableProperties):
            di = inject.Di()
            now = inject.Now()
            my_sub_dep = inject.ByClass(MySubDep)

        di = Di(bindings={"asdfer": "hey"})
        now = datetime.datetime.now()
        di.set_now(now)
        my_class = di.build_class(MyClass)
        assert now == my_class.now
        assert di == my_class.di
        assert isinstance(my_class.my_sub_dep, MySubDep)
        assert isinstance(my_class.my_sub_dep.requests, requests.Session)
        assert my_class.my_sub_dep.value == "hey"

    def test_injectable_example(self):
        class MyOtherThing(InjectableProperties):
            now = inject.Now()

        class ReusableClass(clearskies.Configurable, InjectableProperties):
            my_int = clearskies.configs.Integer(required=True)
            some_number = inject.ByName("some_number")
            my_other_thing = inject.ByClass(MyOtherThing)

            @clearskies.decorators.parameters_to_properties
            def __init__(self, my_int: int):
                self.finalize_and_validate_configuration()

            def my_value(self) -> int:
                return self.my_int * self.some_number

        class MyClass(InjectableProperties):
            reusable = ReusableClass(5)

        class MyOtherClass(InjectableProperties):
            reusable = ReusableClass(10)

        di = Di(
            bindings={
                "some_number": 10,
            }
        )

        my_class = di.build(MyClass)
        assert my_class.reusable.my_value() == 50

        my_other_class = di.build(MyOtherClass)
        assert my_other_class.reusable.my_value() == 100

        assert isinstance(my_class.reusable.my_other_thing.now, datetime.datetime)

    def test_build_standard_lib_simple_module(self):
        """Test that build_standard_lib can import simple modules like 'os' and 'sys'."""
        di = Di()

        # Test importing 'os' module
        os_module = di.build_standard_lib("os")
        assert os_module is not None
        assert hasattr(os_module, "environ")
        assert hasattr(os_module, "path")

        # Test importing 'sys' module
        sys_module = di.build_standard_lib("sys")
        assert sys_module is not None
        assert hasattr(sys_module, "version")

    def test_build_standard_lib_dotted_attribute(self):
        """Test that build_standard_lib can handle dotted names like 'os.environ'."""
        di = Di()

        # Test getting os.environ
        environ = di.build_standard_lib("os.environ")
        assert environ is not None
        assert environ is os.environ
        assert isinstance(environ, os._Environ)

        # Test getting os.path
        path_module = di.build_standard_lib("os.path")
        assert path_module is not None
        assert hasattr(path_module, "join")
        assert hasattr(path_module, "exists")

    def test_build_standard_lib_caches_result(self):
        """Test that build_standard_lib caches the result when cache=True."""
        di = Di()

        # First call should import and cache
        environ1 = di.build_standard_lib("os.environ", cache=True)
        # Second call should return cached value
        environ2 = di.build_standard_lib("os.environ", cache=True)

        assert environ1 is environ2
        assert environ1 is os.environ

    def test_build_standard_lib_raises_for_invalid_module(self):
        """Test that build_standard_lib raises MissingDependency for invalid modules."""
        di = Di()

        with self.assertRaises(MissingDependency):
            di.build_standard_lib("nonexistent_module_xyz")

    def test_build_standard_lib_raises_for_invalid_attribute(self):
        """Test that build_standard_lib raises MissingDependency for invalid attributes."""
        di = Di()

        with self.assertRaises(MissingDependency):
            di.build_standard_lib("os.nonexistent_attribute_xyz")

    def test_build_standard_lib_deep_dotted_path(self):
        """Test that build_standard_lib can handle deeper dotted paths."""
        di = Di()

        # Test getting os.path.join (a function)
        join_func = di.build_standard_lib("os.path.join")
        assert join_func is not None
        assert callable(join_func)
        assert join_func("a", "b") == os.path.join("a", "b")

    def test_inject_by_standard_lib_with_dotted_name(self):
        """Test that ByStandardLib injectable works with dotted names like 'os.environ'."""

        class MyClassWithEnv(InjectableProperties):
            os_environ = inject.ByStandardLib("os.environ")

        di = Di()
        my_instance = di.build_class(MyClassWithEnv)

        assert my_instance.os_environ is os.environ
        assert isinstance(my_instance.os_environ, os._Environ)

    def test_inject_by_standard_lib_with_simple_module(self):
        """Test that ByStandardLib injectable works with simple module names."""

        class MyClassWithOs(InjectableProperties):
            os_module = inject.ByStandardLib("os")

        di = Di()
        my_instance = di.build_class(MyClassWithOs)

        assert my_instance.os_module is not None
        assert hasattr(my_instance.os_module, "environ")
        assert hasattr(my_instance.os_module, "path")
