"""In-process background function registry."""


class JobRegistry:
    def __init__(self):
        self._jobs = {}

    def register(self, function_id, handler):
        if function_id in self._jobs:
            raise RuntimeError(f"duplicate_background_function:{function_id}")
        self._jobs[function_id] = handler

    def get(self, function_id):
        return self._jobs[function_id]

    def inventory(self):
        return tuple(sorted(self._jobs))


job_registry = JobRegistry()
