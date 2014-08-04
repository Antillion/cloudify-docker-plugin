from cloudify import exceptions

from docker_plugin import docker_wrapper

from TestCaseBase import TestCaseBase


_BUILD_ID = 'ba5877dc9bec'
_EMPTY_STREAM_LIST = []
_VALID_STREAM_LIST = [
    '{{"stream":" ---\u003e {}\\n"}}\n'.format(_BUILD_ID),
    '{{"stream":"Successfully built {}\\n"}}\n'.format(_BUILD_ID)
]
_INVALID_STREAM_LIST = [
    '{{"stream":"Successfully built {}\\n"}}\n'.format(_BUILD_ID),
    '{{"stream":" ---\u003e {}\\n"}}\n'.format(_BUILD_ID)
]


class TestGetBuildImageId(TestCaseBase):
    def _gen_stream(self, stream_list):
        for s in stream_list:
            yield s

    def empty_stream(self):
        self.assertRaises(
            exceptions.RecoverableError,
            docker_wrapper._get_build_image_id,
            self.ctx,
            self.client,
            self._gen_stream(_EMPTY_STREAM_LIST)
        )

    def valid_stream(self):
        self.assertEqual(
            _BUILD_ID,
            docker_wrapper._get_build_image_id(
                self.ctx,
                self.client,
                self._gen_stream(_VALID_STREAM_LIST)
            )
        )

    def invalid_stream(self):
        self.assertRaises(
            exceptions.NonRecoverableError,
            docker_wrapper._get_build_image_id,
            self.ctx,
            self.client,
            self._gen_stream(_INVALID_STREAM_LIST)
        )

    def tearDown(self):
        pass