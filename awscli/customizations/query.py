# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import logging

from awscli.arguments import CustomArgument
import jmespath

LOG = logging.getLogger(__name__)

QUERY_HELP = ('<p>A JSON Path query that will be applied to the '
              'JSON data returned by the command.</p>')


def register_query_commands(cli):
    qp = QueryProcessor(cli)
    qp.register()


class QueryProcessor(object):

    def __init__(self, cli):
        self._cli = cli
        self._path = None

    def register(self):
        self._cli.register('building-top-level-params', self._add_option)
        self._cli.register('top-level-args-parsed', self._check_query)
        
    def _add_option(self, argument_table, **kwargs):
        query_arg = CustomArgument('query', help_text=QUERY_HELP)
        query_arg.add_to_arg_table(argument_table)

    def _check_query(self, parsed_args, **kwargs):
        query = parsed_args.query
        if query:
            try:
                self._path = jmespath.compile(query)
            except:
                msg = 'The value (%s) is not a valid query string' % query
                raise ValueError(msg)
            self._cli.register('after-call.*.*', self._run_query)

    def _run_query(self, http_response, parsed, operation, **kwargs):
        result = self._path.search(parsed)
        print(result)
