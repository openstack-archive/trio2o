#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import migrate
import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    cascaded_pod_state = sql.Table(
        'cascaded_pod_state', meta,
        sql.Column('pod_state_id', sql.String(length=64),
                   primary_key=True),
        sql.Column('pod_id', sql.String(length=36),
                   nullable=False),
        sql.Column('count', sql.Integer, nullable=False),
        sql.Column('vcpus', sql.Integer, nullable=False),
        sql.Column('vcpus_used', sql.Integer, nullable=False),
        sql.Column('memory_mb', sql.Integer, nullable=False),
        sql.Column('memory_mb_used', sql.Integer, nullable=False),
        sql.Column('local_gb', sql.Integer, nullable=False),
        sql.Column('local_gb_used', sql.Integer, nullable=False),
        sql.Column('free_ram_mb', sql.Integer, nullable=False),
        sql.Column('free_disk_gb', sql.Integer, nullable=False),
        sql.Column('current_workload', sql.Integer),
        sql.Column('running_vms', sql.Integer),
        sql.Column('disk_available_least', sql.Integer,
                   nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    pod_affinity_tag = sql.Table(
        'pod_affinity_tag', meta,
        sql.Column('affinity_tag_id',
                   sql.String(length=64),
                   primary_key=True),
        sql.Column('key', sql.String(255), nullable=False),
        sql.Column('value', sql.String(255)),
        sql.Column('pod_id', sql.String(length=36),
                   nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    tables = [cascaded_pod_state, pod_affinity_tag]
    for table in tables:
        table.create()

    cascaded_pods = sql.Table('cascaded_pods', meta, autoload=True)

    fkeys = [{'columns': [cascaded_pod_state.c.pod_id],
              'references': [cascaded_pods.c.pod_id]},
             {'columns': [pod_affinity_tag.c.pod_id],
              'references': [cascaded_pods.c.pod_id]}]
    for fkey in fkeys:
        migrate.ForeignKeyConstraint(columns=fkey['columns'],
                                     refcolumns=fkey['references'],
                                     name=fkey.get('name')).create()


def downgrade(migrate_engine):
    raise NotImplementedError('downgrade not support')
