class IsFreeze:
    res: bool = True


IS_FREEZE = IsFreeze()


class Override:
    def __init__(self):
        pass

    def __enter__(self):
        IS_FREEZE.res = False
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        IS_FREEZE.res = True
