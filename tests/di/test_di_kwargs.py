import unittest

from clearskies import Configurable, configs, decorators
from clearskies.di import Di, InjectableProperties, inject
from clearskies.exceptions import MissingDependency


class SimpleDependency(InjectableProperties, Configurable):
    """A simple class with no dependencies."""

    environment = inject.Environment()

    test_param = configs.String(default="test_value")

    @decorators.parameters_to_properties
    def __init__(
        self,
        test_param: str | None = None,
    ):
        self.finalize_and_validate_configuration()


class ClassWithDependencies:
    """A class that itself has dependencies."""

    def __init__(self, simple_dependency: SimpleDependency):
        self.dep = simple_dependency


class DiKwargsTest(unittest.TestCase):
    """Tests for build_class handling of kwargs with defaults."""

    def test_optional_kwarg_with_none_default(self):
        """Test that optional kwargs with None defaults use None."""

        class MyClass:
            def __init__(self, required_arg: str, optional: str | None = None):
                self.required_arg = required_arg
                self.optional = optional

        di = Di(bindings={"required_arg": "hello"})
        instance = di.build_class(MyClass)
        assert instance.required_arg == "hello"
        assert instance.optional is None

    def test_optional_kwarg_with_string_default(self):
        """Test that optional kwargs with string defaults use their default value."""

        class MyClass:
            def __init__(self, required_arg: str, optional: str = "default_value"):
                self.required_arg = required_arg
                self.optional = optional

        di = Di(bindings={"required_arg": "hello"})
        instance = di.build_class(MyClass)
        assert instance.required_arg == "hello"
        assert instance.optional == "default_value"

    def test_optional_kwarg_with_int_default(self):
        """Test that optional kwargs with integer defaults use their default value."""

        class MyClass:
            def __init__(self, required_arg: str, port: int = 8080):
                self.required_arg = required_arg
                self.port = port

        di = Di(bindings={"required_arg": "hello"})
        instance = di.build_class(MyClass)
        assert instance.required_arg == "hello"
        assert instance.port == 8080

    def test_optional_kwarg_with_bool_default(self):
        """Test that optional kwargs with boolean defaults use their default value."""

        class MyClass:
            def __init__(self, required_arg: str, debug: bool = False):
                self.required_arg = required_arg
                self.debug = debug

        di = Di(bindings={"required_arg": "hello"})
        instance = di.build_class(MyClass)
        assert instance.required_arg == "hello"
        assert instance.debug is False

    def test_optional_kwarg_with_class_default_no_dependencies(self):
        """Test that optional kwargs with class defaults are built with DI."""

        class MyClass:
            def __init__(self, required_arg: str, optional: type = SimpleDependency):
                self.required_arg = required_arg
                self.optional = optional

        di = Di(bindings={"required_arg": "hello"})
        instance = di.build_class(MyClass)
        assert instance.required_arg == "hello"
        assert isinstance(instance.optional, SimpleDependency)
        assert instance.optional.test_param == "test_value"

    def test_optional_kwarg_with_class_default_with_dependencies(self):
        """Test that optional kwargs with class defaults that have dependencies are built with DI."""

        class MyClass:
            def __init__(self, required_arg: str, optional: type = ClassWithDependencies):
                self.required_arg = required_arg
                self.optional = optional

        # Need to add SimpleDependency so DI can build ClassWithDependencies
        di = Di(classes=[SimpleDependency], bindings={"required_arg": "hello"})
        instance = di.build_class(MyClass)
        assert instance.required_arg == "hello"
        assert isinstance(instance.optional, ClassWithDependencies)
        assert isinstance(instance.optional.dep, SimpleDependency)
        assert instance.optional.dep.test_param == "test_value"

    def test_multiple_optional_kwargs_mixed_types(self):
        """Test multiple optional kwargs with different default types."""

        class MyClass:
            def __init__(
                self,
                required_arg: str,
                str_opt: str = "default",
                int_opt: int = 42,
                none_opt: str | None = None,
                class_opt: type = SimpleDependency,
            ):
                self.required_arg = required_arg
                self.str_opt = str_opt
                self.int_opt = int_opt
                self.none_opt = none_opt
                self.class_opt = class_opt

        di = Di(bindings={"required_arg": "hello"})
        instance = di.build_class(MyClass)
        assert instance.required_arg == "hello"
        assert instance.str_opt == "default"
        assert instance.int_opt == 42
        assert instance.none_opt is None
        assert isinstance(instance.class_opt, SimpleDependency)

    def test_only_optional_kwargs_no_required_args(self):
        """Test class with only optional kwargs and no required args."""

        class MyClass:
            def __init__(self, optional1: str = "default1", optional2: int = 10):
                self.optional1 = optional1
                self.optional2 = optional2

        di = Di()
        instance = di.build_class(MyClass)
        assert instance.optional1 == "default1"
        assert instance.optional2 == 10

    def test_multiple_none_defaults(self):
        """Test the original use case - multiple optional kwargs all with None defaults."""

        class MyClass:
            def __init__(
                self,
                required_arg: str,
                opt1: str | None = None,
                opt2: int | None = None,
                opt3: bool | None = None,
            ):
                self.required_arg = required_arg
                self.opt1 = opt1
                self.opt2 = opt2
                self.opt3 = opt3

        di = Di(bindings={"required_arg": "hello"})
        instance = di.build_class(MyClass)
        assert instance.required_arg == "hello"
        assert instance.opt1 is None
        assert instance.opt2 is None
        assert instance.opt3 is None

    def test_class_with_varargs_raises_error(self):
        """Test that constructors with *args are rejected."""

        class MyClass:
            def __init__(self, required_arg: str, *args):
                self.required_arg = required_arg
                self.args = args

        di = Di(bindings={"required_arg": "hello"})
        with self.assertRaises(ValueError) as context:
            di.build_class(MyClass)
        assert "has *args in its constructor" in str(context.exception)

    def test_class_with_varkw_raises_error(self):
        """Test that constructors with **kwargs are rejected."""

        class MyClass:
            def __init__(self, required_arg: str, **kwargs):
                self.required_arg = required_arg
                self.kwargs = kwargs

        di = Di(bindings={"required_arg": "hello"})
        with self.assertRaises(ValueError) as context:
            di.build_class(MyClass)
        assert "has **kwargs in its constructor" in str(context.exception)

    def test_class_with_both_args_and_kwargs_raises_error(self):
        """Test that constructors with both *args and **kwargs are rejected."""

        class MyClass:
            def __init__(self, required_arg: str, *args, **kwargs):
                self.required_arg = required_arg
                self.args = args
                self.kwargs = kwargs

        di = Di(bindings={"required_arg": "hello"})
        # Should fail on *args check first
        with self.assertRaises(ValueError) as context:
            di.build_class(MyClass)
        assert "*args" in str(context.exception) or "**kwargs" in str(context.exception)

    def test_class_default_with_missing_dependencies_fails(self):
        """Test that if a class default has unresolvable dependencies, it fails appropriately."""

        class NeedsDependency:
            def __init__(self, unresolvable_dep):
                self.dep = unresolvable_dep

        class MyClass:
            def __init__(self, required_arg: str, optional: type = NeedsDependency):
                self.required_arg = required_arg
                self.optional = optional

        di = Di(bindings={"required_arg": "hello"})
        with self.assertRaises(MissingDependency):
            di.build_class(MyClass)


if __name__ == "__main__":
    unittest.main()
