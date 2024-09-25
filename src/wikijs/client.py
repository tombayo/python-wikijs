from typing import Any, TYPE_CHECKING
from functools import cached_property
import logging

from gql import gql, Client

from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError
from graphql.error.graphql_error import GraphQLError
from graphql.execution.execute import ExecutionResult

from .exceptions import ClientError, raise_exc, WikiJsException

from .asset import AssetMixin
from .page import PageMixin
from .system import SystemMixin
from .user import UserMixin

if TYPE_CHECKING:
    from typing import Dict, Optional

log = logging.getLogger(__name__)


class WikiJs(AssetMixin, PageMixin, SystemMixin, UserMixin):
    def __init__(self, endpoint, api_key, schema_fetch=True) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.schema_fetch = schema_fetch

    @cached_property
    def client(self) -> Client:
        headers = {'Authorization': f'Bearer {self.api_key}'}
        transport = AIOHTTPTransport(url=self.endpoint, headers=headers)
        return Client(transport=transport, fetch_schema_from_transport=self.schema_fetch)

    def execute(self, query: str, params: 'Optional[Dict[str, Any]]' = None) -> ExecutionResult:
        log.debug('Query: %s / Params: %s', query, params)
        try:
            return self.client.execute(gql(query), variable_values=params)
        except TransportQueryError as gql_err:
            try:
                err = gql_err.errors[0]  # Only care about the first error (unlikely multiple)
                raise_exc(err['extensions']['exception']['code'], err['message'])
            except KeyError:
                # This error is not related to Wiki.js, and we'll re-raise as a client error
                raise ClientError from gql_err
            except WikiJsException as js_err:
                # This error is related to Wiki.js, 
                # let it bubble up with it's specific type to be handled elsewhere.
                raise js_err from None

    def check_response_result(self, result: 'Dict[str, Any]') -> bool:
        """TODO: This function might be unecessary"""
        if not result['succeeded']:
            raise_exc(result['errorCode'], result['message'])
        return True
