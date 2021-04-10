from __future__ import annotations

from functools import update_wrapper
from typing import Callable, Iterable, List, Optional, Type, TYPE_CHECKING, Union

from .scaffold import Scaffold

if TYPE_CHECKING:
    from .app import Quart  # noqa

DeferredSetupFunction = Callable[["BlueprintSetupState"], Callable]


class Blueprint(Scaffold):
    """A blueprint is a collection of application properties.

    The application properties include routes, error handlers, and
    before and after request functions. It is useful to produce
    modular code as it allows the properties to be defined in a
    blueprint thereby deferring the addition of these properties to the
    app.

    Attributes:
        url_prefix: An additional prefix to every route rule in the
            blueprint.
    """

    warn_on_modifications = False
    _got_registered_once = False

    def __init__(
        self,
        name: str,
        import_name: str,
        static_folder: Optional[str] = None,
        static_url_path: Optional[str] = None,
        template_folder: Optional[str] = None,
        url_prefix: Optional[str] = None,
        subdomain: Optional[str] = None,
        url_defaults: Optional[dict] = None,
        root_path: Optional[str] = None,
        cli_group: Optional[str] = Ellipsis,  # type: ignore
    ) -> None:
        super().__init__(import_name, static_folder, static_url_path, template_folder, root_path)
        self.name = name
        self.url_prefix = url_prefix
        self.deferred_functions: List[DeferredSetupFunction] = []
        self.subdomain = subdomain
        if url_defaults is None:
            url_defaults = {}
        self.url_values_defaults = url_defaults
        self.cli_group = cli_group

    def _is_setup_finished(self) -> bool:
        return self.warn_on_modifications and self._got_registered_once

    def add_url_rule(
        self,
        rule: str,
        endpoint: Optional[str] = None,
        view_func: Optional[Callable] = None,
        *,
        methods: Optional[Iterable[str]] = None,
        defaults: Optional[dict] = None,
        host: Optional[str] = None,
        subdomain: Optional[str] = None,
        provide_automatic_options: Optional[bool] = None,
        is_websocket: bool = False,
        strict_slashes: Optional[bool] = None,
    ) -> None:
        """Add a route/url rule to the blueprint.

        This is designed to be used on the blueprint directly, and
        has the same arguments as
        :meth:`~quart.Quart.add_url_rule`. An example usage,

        .. code-block:: python

            def route():
                ...

            blueprint = Blueprint(__name__)
            blueprint.add_url_rule('/', route)
        """
        endpoint = endpoint or view_func.__name__
        if "." in endpoint:
            raise ValueError("Blueprint endpoints should not contain periods")
        self.record(
            lambda state: state.add_url_rule(
                rule,
                endpoint,
                view_func,
                methods=methods,
                defaults=defaults,
                host=host,
                subdomain=subdomain or self.subdomain,
                provide_automatic_options=provide_automatic_options,
                is_websocket=is_websocket,
                strict_slashes=strict_slashes,
            )
        )

    def websocket(
        self,
        rule: str,
        endpoint: Optional[str] = None,
        defaults: Optional[dict] = None,
        host: Optional[str] = None,
        subdomain: Optional[str] = None,
        *,
        strict_slashes: Optional[bool] = None,
    ) -> Callable:
        """Add a websocket to the blueprint.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.websocket`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.websocket('/')
            async def route():
                ...
        """

        def decorator(func: Callable) -> Callable:
            self.add_websocket(
                rule,
                endpoint,
                func,
                defaults=defaults,
                host=host,
                subdomain=subdomain,
                strict_slashes=strict_slashes,
            )
            return func

        return decorator

    def add_websocket(
        self,
        rule: str,
        endpoint: Optional[str] = None,
        view_func: Optional[Callable] = None,
        defaults: Optional[dict] = None,
        host: Optional[str] = None,
        subdomain: Optional[str] = None,
        *,
        strict_slashes: Optional[bool] = None,
    ) -> None:
        """Add a websocket rule to the blueprint.

        This is designed to be used on the blueprint directly, and
        has the same arguments as
        :meth:`~quart.Quart.add_websocket`. An example usage,

        .. code-block:: python

            def route():
                ...

            blueprint = Blueprint(__name__)
            blueprint.add_websocket('/', route)
        """
        return self.add_url_rule(
            rule,
            endpoint,
            view_func,
            methods={"GET"},
            defaults=defaults,
            host=host,
            subdomain=subdomain,
            provide_automatic_options=False,
            is_websocket=True,
            strict_slashes=strict_slashes,
        )

    def app_template_filter(self, name: Optional[str] = None) -> Callable:
        """Add an application wide template filter.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.template_filter`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_template_filter()
            def filter(value):
                ...
        """

        def decorator(func: Callable) -> Callable:
            self.add_app_template_filter(func, name=name)
            return func

        return decorator

    def add_app_template_filter(self, func: Callable, name: Optional[str] = None) -> None:
        """Add an application wide template filter.

        This is designed to be used on the blueprint directly, and
        has the same arguments as
        :meth:`~quart.Quart.add_template_filter`. An example usage,

        .. code-block:: python

            def filter():
                ...

            blueprint = Blueprint(__name__)
            blueprint.add_app_template_filter(filter)
        """
        self.record_once(lambda state: state.register_template_filter(func, name))

    def app_template_test(self, name: Optional[str] = None) -> Callable:
        """Add an application wide template test.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.template_test`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_template_test()
            def test(value):
                ...
        """

        def decorator(func: Callable) -> Callable:
            self.add_app_template_test(func, name=name)
            return func

        return decorator

    def add_app_template_test(self, func: Callable, name: Optional[str] = None) -> None:
        """Add an application wide template test.

        This is designed to be used on the blueprint directly, and
        has the same arguments as
        :meth:`~quart.Quart.add_template_test`. An example usage,

        .. code-block:: python

            def test():
                ...

            blueprint = Blueprint(__name__)
            blueprint.add_app_template_test(test)
        """
        self.record_once(lambda state: state.register_template_test(func, name))

    def app_template_global(self, name: Optional[str] = None) -> Callable:
        """Add an application wide template global.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.template_global`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_template_global()
            def global(value):
                ...
        """

        def decorator(func: Callable) -> Callable:
            self.add_app_template_global(func, name=name)
            return func

        return decorator

    def add_app_template_global(self, func: Callable, name: Optional[str] = None) -> None:
        """Add an application wide template global.

        This is designed to be used on the blueprint directly, and
        has the same arguments as
        :meth:`~quart.Quart.add_template_global`. An example usage,

        .. code-block:: python

            def global():
                ...

            blueprint = Blueprint(__name__)
            blueprint.add_app_template_global(global)
        """
        self.record_once(lambda state: state.register_template_global(func, name))

    def before_app_request(self, func: Callable) -> Callable:
        """Add a before request function to the app.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.before_request`. It applies to all requests to the
        app this blueprint is registered on. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.before_app_request
            def before():
                ...
        """
        self.record_once(lambda state: state.app.before_request(func))
        return func

    def before_app_websocket(self, func: Callable) -> Callable:
        """Add a before websocket to the App.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.before_websocket`. It applies to all requests to the
        app this blueprint is registered on. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.before_app_websocket
            def before():
                ...

        """
        self.record_once(lambda state: state.app.before_websocket(func))
        return func

    def before_app_serving(self, func: Callable) -> Callable:
        """Add a before serving to the App.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.before_serving`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.before_app_serving
            def before():
                ...

        """
        self.record_once(lambda state: state.app.before_serving(func))
        return func

    def before_app_first_request(self, func: Callable) -> Callable:
        """Add a before request first function to the app.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.before_first_request`. It is
        triggered before the first request to the app this blueprint
        is registered on. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.before_app_first_request
            def before_first():
                ...

        """
        self.record_once(lambda state: state.app.before_first_request(func))
        return func

    def after_app_request(self, func: Callable) -> Callable:
        """Add a after request function to the app.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.after_request`. It applies to all requests to the
        app this blueprint is registered on. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.after_app_request
            def after():
                ...
        """
        self.record_once(lambda state: state.app.after_request(func))
        return func

    def after_app_websocket(self, func: Callable) -> Callable:
        """Add an after websocket function to the App.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.after_websocket`. It applies to all requests to the
        ppe this blueprint is registerd on. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.after_app_websocket
            def after():
                ...
        """
        self.record_once(lambda state: state.app.after_websocket(func))
        return func

    def after_app_serving(self, func: Callable) -> Callable:
        """Add an after serving function to the App.

        This is designed to be used as a decorator, and has the same arguments
        as :meth:`~quart.Quart.after_serving`. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.after_app_serving
            def after():
                ...
        """
        self.record_once(lambda state: state.app.after_websocket(func))
        return func

    def teardown_app_request(self, func: Callable) -> Callable:
        """Add a teardown request function to the app.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.teardown_request`. It applies
        to all requests to the app this blueprint is registered on. An
        example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.teardown_app_request
            def teardown():
                ...
        """
        self.record_once(lambda state: state.app.teardown_request(func))
        return func

    def teardown_app_websocket(self, func: Callable) -> Callable:
        """Add a teardown websocket function to the app.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.teardown_websocket`. It applies
        to all requests to the app this blueprint is registered on. An
        example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.teardown_app_websocket
            def teardown():
                ...
        """
        self.record_once(lambda state: state.app.teardown_websocket(func))
        return func

    def app_errorhandler(self, error: Union[Type[Exception], int]) -> Callable:
        """Add an error handler function to the App.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.errorhandler`. It applies
        only to all errors. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_errorhandler(404)
            def not_found():
                ...
        """

        def decorator(func: Callable) -> Callable:
            self.record_once(lambda state: state.app.register_error_handler(error, func))
            return func

        return decorator

    def app_context_processor(self, func: Callable) -> Callable:
        """Add a context processor function to the app.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.context_processor`. This will
        add context to all templates rendered. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_context_processor
            def processor():
                ...
        """
        self.record_once(lambda state: state.app.context_processor(func))
        return func

    def app_url_value_preprocessor(self, func: Callable) -> Callable:
        """Add a url value preprocessor.

        This is designed to be used as a decorator, and has the same
        arguments as
        :meth:`~quart.Quart.app_url_value_preprocessor`. This will
        apply to all URLs. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_url_value_preprocessor
            def processor(endpoint, view_args):
                ...

        """
        self.record_once(lambda state: state.app.url_value_preprocessor(func))
        return func

    def app_url_defaults(self, func: Callable) -> Callable:
        """Add a url default preprocessor.

        This is designed to be used as a decorator, and has the same
        arguments as :meth:`~quart.Quart.url_defaults`. This will
        apply to all urls. An example usage,

        .. code-block:: python

            blueprint = Blueprint(__name__)
            @blueprint.app_url_defaults
            def default(endpoint, values):
                ...

        """
        self.record_once(lambda state: state.app.url_defaults(func))
        return func

    def record(self, func: DeferredSetupFunction) -> None:
        """Used to register a deferred action."""
        self.deferred_functions.append(func)

    def record_once(self, func: DeferredSetupFunction) -> None:
        """Used to register a deferred action that happens only once."""

        def wrapper(state: "BlueprintSetupState") -> None:
            if state.first_registration:
                func(state)

        self.record(update_wrapper(wrapper, func))

    def register(self, app: "Quart", options: dict, first_registration: bool = False) -> None:
        """Register this blueprint on the app given.

        Arguments:
            app: The application this blueprint is being registered with.
            options: Keyword arguments forwarded from
                :meth:`~quart.Quart.register_blueprint`.
            first_registration: Whether this is the first time this
                blueprint has been registered on the application.
        """
        self._got_registered_once = True
        state = self.make_setup_state(app, options, first_registration)

        if self.has_static_folder:
            state.add_url_rule(
                self.static_url_path + "/<path:filename>",
                view_func=self.send_static_file,
                endpoint="static",
            )

        app.view_functions.update(self.view_functions)

        _merge_dict_of_lists(self.name, self.before_request_funcs, app.before_request_funcs)
        _merge_dict_of_lists(self.name, self.after_request_funcs, app.after_request_funcs)
        _merge_dict_of_lists(self.name, self.teardown_request_funcs, app.teardown_request_funcs)
        _merge_dict_of_lists(self.name, self.url_default_functions, app.url_default_functions)
        _merge_dict_of_lists(self.name, self.url_value_preprocessors, app.url_value_preprocessors)
        _merge_dict_of_lists(
            self.name, self.template_context_processors, app.template_context_processors
        )

        _merge_dict_of_dicts(self.name, self.error_handler_spec, app.error_handler_spec)

        for func in self.deferred_functions:
            func(state)

        if not self.cli.commands:
            return

        cli_resolved_group = options.get("cli_group", self.cli_group)

        if cli_resolved_group is None:
            app.cli.commands.update(self.cli.commands)
        elif cli_resolved_group is Ellipsis:
            self.cli.name = self.name
            app.cli.add_command(self.cli)
        else:
            self.cli.name = cli_resolved_group
            app.cli.add_command(self.cli)

    def make_setup_state(
        self, app: "Quart", options: dict, first_registration: bool = False
    ) -> "BlueprintSetupState":
        """Return a blueprint setup state instance.

        Arguments:
            first_registration: True if this is the first registration
                of this blueprint on the app.
            options: Keyword arguments forwarded from
                :meth:`~quart.Quart.register_blueprint`.
            first_registration: Whether this is the first time this
                blueprint has been registered on the application.
        """
        return BlueprintSetupState(self, app, options, first_registration)


class BlueprintSetupState:
    """This setups the blueprint on the app.

    When used it can apply the deferred functions on the Blueprint to
    the app. Override if you wish for blueprints to have be registered
    in different ways.

    Attributes:
        first_registration: True if this is the first registration
            of this blueprint on the app.
    """

    def __init__(
        self, blueprint: Blueprint, app: "Quart", options: dict, first_registration: bool
    ) -> None:
        self.blueprint = blueprint
        self.app = app
        self.options = options
        self.url_prefix = options.get("url_prefix") or blueprint.url_prefix
        self.first_registration = first_registration
        self.subdomain = options.get("subdomain") or blueprint.subdomain
        self.url_defaults = dict(self.blueprint.url_values_defaults)
        self.url_defaults.update(options.get("url_defaults", {}) or {})

    def add_url_rule(
        self,
        path: str,
        endpoint: Optional[str] = None,
        view_func: Optional[Callable] = None,
        *,
        methods: Optional[Iterable[str]] = None,
        defaults: Optional[dict] = None,
        host: Optional[str] = None,
        subdomain: Optional[str] = None,
        provide_automatic_options: Optional[bool] = None,
        is_websocket: bool = False,
        strict_slashes: Optional[bool] = None,
    ) -> None:
        if self.url_prefix is not None:
            path = f"{self.url_prefix.rstrip('/')}/{path.lstrip('/')}"
        if subdomain is None:
            subdomain = self.subdomain
        endpoint = f"{self.blueprint.name}.{endpoint}"
        url_defaults = self.url_defaults
        if defaults is not None:
            url_defaults = {**url_defaults, **defaults}
        self.app.add_url_rule(
            path,
            endpoint,
            view_func,
            provide_automatic_options=provide_automatic_options,
            methods=methods,
            defaults=url_defaults,
            host=host,
            subdomain=subdomain,
            is_websocket=is_websocket,
            strict_slashes=strict_slashes,
        )

    def register_template_filter(self, func: Callable, name: Optional[str]) -> None:
        self.app.add_template_filter(func, name)

    def register_template_test(self, func: Callable, name: Optional[str]) -> None:
        self.app.add_template_test(func, name)

    def register_template_global(self, func: Callable, name: Optional[str]) -> None:
        self.app.add_template_global(func, name)


def _merge_dict_of_lists(name: str, self_dict: dict, app_dict: dict) -> None:
    for key, values in self_dict.items():
        key = name if key is None else f"{name}.{key}"
        app_dict[key].extend(values)


def _merge_dict_of_dicts(name: str, self_dict: dict, app_dict: dict) -> None:
    for key, value in self_dict.items():
        key = name if key is None else f"{name}.{key}"
        app_dict[key] = value
