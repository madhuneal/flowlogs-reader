#  Copyright 2015 Observable Networks
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import division, print_function

from datetime import datetime
from unittest import TestCase

try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

from flowlogs_reader import FlowRecord, FlowLogsReader


SAMPLE_RECORDS = [
    (
        '2 123456789010 eni-102010ab 198.51.100.1 192.0.2.1 '
        '443 49152 6 10 840 1439387263 1439387264 ACCEPT OK'
    ),
    (
        '2 123456789010 eni-102010ab 192.0.2.1 198.51.100.1 '
        '49152 443 6 20 1680 1439387264 1439387265 ACCEPT OK'
    ),
    (
        '2 123456789010 eni-102010ab 192.0.2.1 198.51.100.1 '
        '49152 443 6 20 1680 1439387265 1439387266 REJECT OK'
    ),
    (
        '2 123456789010 eni-1a2b3c4d - - - - - - - '
        '1431280876 1431280934 - NODATA'
    ),
    (
        '2 123456789010 eni-4b118871 - - - - - - - '
        '1431280876 1431280934 - SKIPDATA'
    ),
]


class FlowRecordTestCase(TestCase):
    def test_parse(self):
        flow_record = FlowRecord({'message': SAMPLE_RECORDS[0]})
        actual = {x: getattr(flow_record, x) for x in FlowRecord.__slots__}
        expected = {
            'account_id': '123456789010',
            'action': 'ACCEPT',
            'bytes': 840,
            'dstaddr': '192.0.2.1',
            'dstport': 49152,
            'end': datetime(2015, 8, 12, 13, 47, 44),
            'interface_id': 'eni-102010ab',
            'log_status': 'OK',
            'packets': 10,
            'protocol': 6,
            'srcaddr': '198.51.100.1',
            'srcport': 443,
            'start': datetime(2015, 8, 12, 13, 47, 43),
            'version': 2,
        }
        self.assertEqual(actual, expected)

    def test_eq(self):
        flow_record = FlowRecord({'message': SAMPLE_RECORDS[1]})
        actual = {x: getattr(flow_record, x) for x in FlowRecord.__slots__}
        expected = {
            'account_id': '123456789010',
            'action': 'ACCEPT',
            'bytes': 1680,
            'dstaddr': '198.51.100.1',
            'dstport': 443,
            'end': datetime(2015, 8, 12, 13, 47, 45),
            'interface_id': 'eni-102010ab',
            'log_status': 'OK',
            'packets': 20,
            'protocol': 6,
            'srcaddr': '192.0.2.1',
            'srcport': 49152,
            'start': datetime(2015, 8, 12, 13, 47, 44),
            'version': 2,
        }
        self.assertEqual(actual, expected)

    def test_hash(self):
        record_set = {
            FlowRecord.from_message(SAMPLE_RECORDS[0]),
            FlowRecord.from_message(SAMPLE_RECORDS[0]),
            FlowRecord.from_message(SAMPLE_RECORDS[1]),
            FlowRecord.from_message(SAMPLE_RECORDS[1]),
            FlowRecord.from_message(SAMPLE_RECORDS[2]),
            FlowRecord.from_message(SAMPLE_RECORDS[2]),
        }
        self.assertEqual(len(record_set), 3)

    def test_str(self):
        flow_record = FlowRecord({'message': SAMPLE_RECORDS[0]})
        actual = str(flow_record)
        expected = (
            'version: 2, account_id: 123456789010, '
            'interface_id: eni-102010ab, srcaddr: 198.51.100.1, '
            'dstaddr: 192.0.2.1, srcport: 443, dstport: 49152, protocol: 6, '
            'packets: 10, bytes: 840, start: 2015-08-12 13:47:43, '
            'end: 2015-08-12 13:47:44, action: ACCEPT, log_status: OK'
        )
        self.assertEqual(actual, expected)

    def test_to_dict(self):
        flow_record = FlowRecord({'message': SAMPLE_RECORDS[2]})
        actual = flow_record.to_dict()
        expected = {
            'account_id': '123456789010',
            'action': 'REJECT',
            'bytes': 1680,
            'dstaddr': '198.51.100.1',
            'dstport': 443,
            'end': datetime(2015, 8, 12, 13, 47, 46),
            'interface_id': 'eni-102010ab',
            'log_status': 'OK',
            'packets': 20,
            'protocol': 6,
            'srcaddr': '192.0.2.1',
            'srcport': 49152,
            'start': datetime(2015, 8, 12, 13, 47, 45),
            'version': 2,
        }
        self.assertEqual(actual, expected)

    def test_to_message(self):
        for message in SAMPLE_RECORDS:
            message_record = FlowRecord.from_message(message)
            self.assertEqual(message_record.to_message(), message)

    def test_from_message(self):
        event_record = FlowRecord({'message': SAMPLE_RECORDS[1]})
        message_record = FlowRecord.from_message(SAMPLE_RECORDS[1])
        self.assertEqual(event_record, message_record)


class FlowLogsReaderTestCase(TestCase):
    @patch('flowlogs_reader.flowlogs_reader.boto3', autospec=True)
    def setUp(self, mock_boto3):
        self.mock_client = MagicMock()
        mock_boto3.client.return_value = self.mock_client

        self.start_time = datetime(2015, 8, 12, 12, 0, 0)
        self.end_time = datetime(2015, 8, 12, 13, 0, 0)

        self.inst = FlowLogsReader(
            'group_name',
            start_time=self.start_time,
            end_time=self.end_time,
            only_complete=False,
        )

    def test_init(self):
        self.assertEqual(self.inst.log_group_name, 'group_name')

        self.assertFalse(self.inst.only_complete)

        self.assertEqual(
            datetime.utcfromtimestamp(self.inst.start_ms // 1000),
            self.start_time
        )

        self.assertEqual(
            datetime.utcfromtimestamp(self.inst.end_ms // 1000),
            self.end_time
        )

    def test_get_ready_streams(self):
        ancient = self.inst.end_ms
        earlier = self.inst.end_ms
        modern = self.inst.end_ms + 1
        later = self.inst.end_ms + 2

        response_list = [
            # log_2 will be returned
            {
                'logStreams': [
                    {'logStreamName': 'log_0', 'lastIngestionTime': ancient},
                    {'logStreamName': 'log_1', 'lastIngestionTime': earlier},
                    {'logStreamName': 'log_2', 'lastIngestionTime': modern},
                ],
                'nextToken': 'some_token'
            },
            # log_4 will be returned
            {
                'logStreams': [
                    {'logStreamName': 'log_3', 'lastIngestionTime': earlier},
                    {'logStreamName': 'log_4', 'lastIngestionTime': later},
                ],
            },
            # Unreachable because the last entry had no nextToken
            {
                'logStreams': [
                    {'logStreamName': 'log_5', 'lastIngestionTime': modern},
                ],
            },
        ]

        def mock_describe(*args, **kwargs):
            return response_list.pop(0)

        self.mock_client.describe_log_streams.side_effect = mock_describe

        actual = self.inst._get_ready_streams()
        expected = ['log_2', 'log_4']
        self.assertEqual(actual, expected)

    def test_read_streams(self):
        response_list = [
            {'events': [0], 'nextToken': 'token_0'},
            {'events': [1, 2], 'nextToken': 'token_1'},
            {'events': [3, 4, 5], 'nextToken': None},
            {'events': [6], 'nextForwardToken': 'token_2'},  # Unreachable
        ]

        def mock_filter(*args, **kwargs):
            return response_list.pop(0)

        self.mock_client.filter_log_events.side_effect = mock_filter

        actual = list(self.inst._read_streams())
        expected = [0, 1, 2, 3, 4, 5]
        self.assertEqual(actual, expected)

    def test_iteration(self):
        response_list = [
            {
                'events': [
                    {'logStreamName': 'log_0', 'message': SAMPLE_RECORDS[0]},
                    {'logStreamName': 'log_0', 'message': SAMPLE_RECORDS[1]},
                ],
                'nextToken': 'token_0',
            },
            {
                'events': [
                    {'logStreamName': 'log_0', 'message': SAMPLE_RECORDS[2]},
                    {'logStreamName': 'log_1', 'message': SAMPLE_RECORDS[3]},
                    {'logStreamName': 'log_2', 'message': SAMPLE_RECORDS[4]},
                ],
            },
        ]

        def mock_filter(*args, **kwargs):
            return response_list.pop(0)

        self.mock_client.filter_log_events.side_effect = mock_filter

        # Calling list on the instance causes it to iterate through all records
        actual = list(self.inst)
        expected = [FlowRecord.from_message(x) for x in SAMPLE_RECORDS]
        self.assertEqual(actual, expected)

    def test_iteration_only_complete(self):
        # Make sure when only_complete is set that we call filter_log_events
        # with the proper keyword argument
        self.inst.only_complete = True

        self.inst._get_ready_streams = lambda: ['log_0', 'log_1']
        self.mock_client.filter_log_events.return_value = {'events': []}

        list(self.inst)

        self.mock_client.filter_log_events.assert_called_once_with(
            logGroupName=self.inst.log_group_name,
            startTime=self.inst.start_ms,
            endTime=self.inst.end_ms,
            interleaved=True,
            logStreamNames=['log_0', 'log_1'],
        )
