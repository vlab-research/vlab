import abc
from abc import ABC, abstractmethod

class HttpServiceInterface(ABC, metaclass=abc.ABCMeta):
    @abstractmethod
    def execute(self, url, method, request_options, headers, params): ...
