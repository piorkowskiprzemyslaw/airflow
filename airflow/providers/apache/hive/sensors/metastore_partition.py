#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from typing import TYPE_CHECKING, Any, Sequence

from airflow.sensors.sql import SqlSensor

if TYPE_CHECKING:
    from airflow.utils.context import Context


class MetastorePartitionSensor(SqlSensor):
    """
    An alternative to the HivePartitionSensor that talk directly to the
    MySQL db. This was created as a result of observing sub optimal
    queries generated by the Metastore thrift service when hitting
    subpartitioned tables. The Thrift service's queries were written in a
    way that wouldn't leverage the indexes.

    :param schema: the schema
    :type schema: str
    :param table: the table
    :type table: str
    :param partition_name: the partition name, as defined in the PARTITIONS
        table of the Metastore. Order of the fields does matter.
        Examples: ``ds=2016-01-01`` or
        ``ds=2016-01-01/sub=foo`` for a sub partitioned table
    :type partition_name: str
    :param mysql_conn_id: a reference to the MySQL conn_id for the metastore
    :type mysql_conn_id: str
    """

    template_fields: Sequence[str] = ('partition_name', 'table', 'schema')
    ui_color = '#8da7be'
    poke_context_fields = ('partition_name', 'table', 'schema', 'mysql_conn_id')

    def __init__(
        self,
        *,
        table: str,
        partition_name: str,
        schema: str = "default",
        mysql_conn_id: str = "metastore_mysql",
        **kwargs: Any,
    ):

        self.partition_name = partition_name
        self.table = table
        self.schema = schema
        self.first_poke = True
        self.conn_id = mysql_conn_id
        # TODO(aoen): We shouldn't be using SqlSensor here but MetastorePartitionSensor.
        # The problem is the way apply_defaults works isn't compatible with inheritance.
        # The inheritance model needs to be reworked in order to support overriding args/
        # kwargs with arguments here, then 'conn_id' and 'sql' can be passed into the
        # constructor below and apply_defaults will no longer throw an exception.
        super().__init__(**kwargs)

    def poke(self, context: "Context") -> Any:
        if self.first_poke:
            self.first_poke = False
            if '.' in self.table:
                self.schema, self.table = self.table.split('.')
            self.sql = """
            SELECT 'X'
            FROM PARTITIONS A0
            LEFT OUTER JOIN TBLS B0 ON A0.TBL_ID = B0.TBL_ID
            LEFT OUTER JOIN DBS C0 ON B0.DB_ID = C0.DB_ID
            WHERE
                B0.TBL_NAME = '{self.table}' AND
                C0.NAME = '{self.schema}' AND
                A0.PART_NAME = '{self.partition_name}';
            """.format(
                self=self
            )
        return super().poke(context)
