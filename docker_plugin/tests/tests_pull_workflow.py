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
import os

# Third Party Imports
import testtools
from docker import Client

# Cloudify Imports is imported and used in operations
from cloudify.workflows import local
from docker_plugin.tests import TEST_IMAGE

IGNORED_LOCAL_WORKFLOW_MODULES = (
    'worker_installer.tasks',
    'plugin_installer.tasks',
    'cloudify_agent.operations',
    'cloudify_agent.installer.operations',
)




# OLLIE:

# 1. insecure_registry flag
#For some reason the insecure_registry flag is not doing anything on a
#pull. It could be that the code isn't actually passing the flag to the
# correct place! Implement a blueprint test to validate it's being passed
# correctly before trying out the stupid deployment.

# 2. You're also trying to get the Pip deploy working
# Edge forwards to a working system, then tear it down and start from fresh.
# You did put some Docker install outside of the blueprint, but it's actually
# in the blueprint already!
# Before running the PIP, check that the SSH key is present. Also host writing
# of the privatey docker registry may not be working so well :(

# 3. Annnnd in parallel: JIRA
#
# Continue to add Epics and User Stories to the JIRA in Ravello. Try to use
# the hostname of the JIRA box rather than IP so that 1Password doesn't
# get confused. Also consider a blueprint for it.


class TestPullWorkflow(testtools.TestCase):

    def setUp(self):
        super(TestPullWorkflow, self).setUp()
        # build blueprint path
        blueprint_path = os.path.join(os.path.dirname(__file__),
                                      'blueprint',
                                      'test_pull-blueprint.yaml')

        inputs = {
            'test_repo': TEST_IMAGE,
            'test_tag': 'latest',
            'test_container_name': 'test-container'
        }

        # setup local workflow execution environment
        self.env = local.init_env(
            blueprint_path, name=self._testMethodName, inputs=inputs,
            ignored_modules=IGNORED_LOCAL_WORKFLOW_MODULES)

    def get_client(self, daemon_client):

        return Client(**daemon_client)

    def tests_pull_workflow(self):
        """ Tests the install workflow using the built in
            workflows.
        """
        daemon_client = {}
        client = self.get_client(daemon_client)

        for container in client.containers(all=True):
            if 'test-container' in \
                    ''.join([name for name in container.get('Names')]):
                client.remove_container('test-container')

        if ['{0}:latest'.format(TEST_IMAGE)] in \
                [i.get('RepoTags') for i in client.images()]:
            client.remove_image(TEST_IMAGE, force=True)

        # execute install workflow
        self.env.execute('install', task_retries=0)

        container_instance = {}

        for instance in self.env.storage.get_node_instances():
            if 'container_id' in instance.runtime_properties.keys():
                container_instance = instance

        self.assertTrue(container_instance is not None,
                        'Failed getting container.')

        container_id = container_instance.runtime_properties.get(
            'container_id')
        containers = client.containers(all=True)
        self.assertTrue(container_id in [c.get('Id') for c in containers])

        self.env.execute('uninstall', task_retries=3)
        repotags = []
        for i in client.images():
            repotags.append(i.get('RepoTags'))

        self.assertFalse(TEST_IMAGE in [tag for tag in repotags])
        if ['{0}:latest'.format(TEST_IMAGE)] in \
                [i.get('RepoTags') for i in client.images()]:
            client.remove_image(TEST_IMAGE, force=True)
