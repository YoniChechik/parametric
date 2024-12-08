class Override:
    def __init__(self, params):
        # NOTE import inside to avoid circular dependency
        from parametric import BaseParams

        if not isinstance(params, BaseParams):
            raise TypeError(f"Expected BaseParams instance, got {type(params)}")
        self._params = params

    def __enter__(self):
        self._params._is_frozen = False
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._params._is_frozen = True
