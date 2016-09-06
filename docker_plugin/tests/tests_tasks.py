########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# Built-in Imports
import testtools
import json

# Third Party Imports
import docker
from mock import patch, MagicMock

# Cloudify Imports is imported and used in operations
from cloudify.mocks import MockCloudifyContext
from docker_plugin import tasks
from cloudify.state import current_ctx
from cloudify.exceptions import NonRecoverableError
from docker_plugin.tests import TEST_IMAGE


class TestTasks(testtools.TestCase):

    def setUp(self):
        super(TestTasks, self).setUp()

    def get_mock_context(self, test_name):

        test_node_id = test_name
        test_properties = {
            'use_external_resource': False,
            'name': test_name,
            'image': {
                'repository': TEST_IMAGE
            }
        }

        operation = {
            'retry_number': 0
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties,
            operation=operation
        )

        return ctx

    def get_bad_image_id(self):
        return 'z0000000z000z0zzzzz0zzzz000000' \
               '0000zzzzz0zzz00000z0zz0000000000zz'

    def get_bad_container_id(self):
        return 'z0zz0z000z00'

    def get_docker_client(self):
        return docker.Client()

    def pull_image(self, client):
        output = []
        for line in client.pull(TEST_IMAGE, stream=True):
            output.append(json.dumps(json.loads(line)))
        return output

    def create_container(self, client, name, image_id):
        return client.create_container(
            name=name, stdin_open=True, tty=True,
            image=image_id, command='/bin/sh')

    def get_docker_images(self, client):
        return [image for image in client.images()]

    def get_tags_for_docker_image(self, image):
        return [tag for tag in image.get('RepoTags')]

    def get_id_from_image(self, image):
        return image.get('Id')

    def test_create_container_external_no_name(self):
        name = 'test_create_container_external_no_name'
        ctx = self.get_mock_context(name)
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        del(ctx.node.properties['name'])
        params = dict()
        ex = self.assertRaises(
            NonRecoverableError, tasks.create_container, params, ctx=ctx)
        self.assertIn('Use external resource, but', ex.message)

    def test_pull_with_args(self):
        name = 'test_create_with_dockerpy_params'
        ctx = self.get_mock_context(name)
        fake_image_id = '10101010101'
        current_ctx.set(ctx=ctx)

        arguments = {
            'repository': name, 'tag': 'latest', 'insecure_registry': True
        }

        mock_client = MagicMock()
        mock_client.pull.return_value = [json.dumps(
            {'id': 'the-id',
             'status': 'Complete'})]
        mock_client.images.return_value = [
            {'RepoTags': ['{}:latest'.format(arguments['repository'])],
             'Id': fake_image_id}
        ]


        tasks.pull(mock_client, arguments)

        mock_client.pull.assert_called_with(**arguments)

    @patch('docker_plugin.tasks.docker_client.get_client')
    def test_create_with_dockerpy_params(self, get_client_mock):
        name = 'test_create_with_dockerpy_params'
        ctx = self.get_mock_context(name)
        fake_image_id = '10101010101'
        current_ctx.set(ctx=ctx)
        ctx.node.properties['image']['insecure_registry'] = True

        mock_client = MagicMock()

        mock_client.create_container.return_value = {
            'Id': 'mocked-create_container-return-value-id'}
        mock_client.images.return_value = [
            {'RepoTags': ['{}:latest'.format(TEST_IMAGE)],
             'Id': fake_image_id}]
        mock_client.pull.return_value = [json.dumps(
            {'id': 'the-id', 'status': 'Complete'})]

        get_client_mock.return_value = mock_client

        tasks.create_container({}, ctx=ctx)

        mock_client.create_container.assert_called_with(
            name=name, image=fake_image_id)
        mock_client.pull.assert_called_with(
            repository=TEST_IMAGE, stream=True, tag='latest',
            insecure_registry=True)




    def test_get_image_no_src_or_repo(self):
        name = 'test_get_image_no_src_or_repo'
        ctx = self.get_mock_context(name)
        current_ctx.set(ctx=ctx)
        ctx.node.properties['image']['src'] = None
        ctx.node.properties['image']['repository'] = None
        client = self.get_docker_client()
        ex = self.assertRaises(
            NonRecoverableError, tasks.get_image,
            client)
        self.assertIn('You must provide', ex.message)

    def test_start_wait_for_processes(self):

        name = 'test_start_wait_for_processes'
        client = self.get_docker_client()
        self.pull_image(client)
        ctx = self.get_mock_context(name)
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True

        for image in self.get_docker_images(client):
            if '{0}:latest'.format(TEST_IMAGE) in \
                    self.get_tags_for_docker_image(image):
                image_id = self.get_id_from_image(image)

        container = self.create_container(client, name, image_id)
        self.addCleanup(client.remove_container, container=container)
        self.addCleanup(client.stop, container=container, timeout=1)
        ctx.instance.runtime_properties['container_id'] = container.get('Id')

        processes = ['/bin/sh']
        params = dict()

        tasks.start(params, processes, 1, {}, ctx=ctx)
