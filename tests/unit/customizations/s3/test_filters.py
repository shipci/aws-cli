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
import os
from awscli.testutils import unittest
import platform

from awscli.customizations.s3.filegenerator import FileStat
from awscli.customizations.s3.filters import Filter


def platform_path(filepath):
    # Convert posix platforms to windows platforms.
    if platform.system().lower() == 'windows':
        filepath = filepath.replace('/', os.sep)
        filepath = 'C:' + filepath
    return filepath


class FiltersTest(unittest.TestCase):
    def setUp(self):
        self.local_files = [
            self.file_stat('test.txt'),
            self.file_stat('test.jpg'),
            self.file_stat(os.path.join('directory', 'test.jpg')),
        ]
        self.s3_files = [
            self.file_stat('bucket/test.txt', src_type='s3'),
            self.file_stat('bucket/test.jpg', src_type='s3'),
            self.file_stat('bucket/key/test.jpg', src_type='s3'),
        ]

    def file_stat(self, filename, src_type='local'):
        if src_type == 'local':
            filename = os.path.abspath(filename)
            dest_type = 's3'
        else:
            dest_type = 'local'
        return FileStat(src=filename, dest='',
                        compare_key='', size=10,
                        last_update=0, src_type=src_type,
                        dest_type=dest_type, operation_name='')

    def create_filter(self, filters=None, root=None, dst_root=None):
        if root is None:
            root = os.getcwd()
        if filters is None:
            filters = {}
        if dst_root is None:
            dst_root = 'bucket'
        return Filter(filters, root, dst_root)

    def test_no_filter(self):
        exc_inc_filter = self.create_filter()
        matched_files = list(exc_inc_filter.call(self.local_files))
        self.assertEqual(matched_files, self.local_files)

        matched_files2 = list(exc_inc_filter.call(self.s3_files))
        self.assertEqual(matched_files2, self.s3_files)

    def test_include(self):
        patterns = [['include', '*.txt']]
        include_filter = self.create_filter([['include', '*.txt']])
        matched_files = list(include_filter.call(self.local_files))
        self.assertEqual(matched_files, self.local_files)

        matched_files2 = list(include_filter.call(self.s3_files))
        self.assertEqual(matched_files2, self.s3_files)

    def test_exclude(self):
        exclude_filter = self.create_filter([['exclude', '*']])
        matched_files = list(exclude_filter.call(self.local_files))
        self.assertEqual(matched_files, [])

        matched_files = list(exclude_filter.call(self.s3_files))
        self.assertEqual(matched_files, [])

    def test_exclude_with_dst_root(self):
        exclude_filter = self.create_filter([['exclude', '*.txt']],
                                            dst_root='bucket')
        matched_files = list(exclude_filter.call(self.local_files))
        b = os.path.basename
        self.assertNotIn('test.txt', [b(f.src) for f in matched_files])
        # Same filter should match the dst files.
        matched_files = list(exclude_filter.call(self.s3_files))
        self.assertNotIn('test.txt', [b(f.src) for f in matched_files])

    def test_exclude_include(self):
        patterns = [['exclude', '*'], ['include', '*.txt']]
        exclude_include_filter = self.create_filter(patterns)
        matched_files = list(exclude_include_filter.call(self.local_files))
        self.assertEqual(matched_files, [self.local_files[0]])

        matched_files = list(exclude_include_filter.call(self.s3_files))
        self.assertEqual(matched_files, [self.s3_files[0]])

    def test_include_exclude(self):
        patterns = [['include', '*.txt'], ['exclude', '*']]
        exclude_all_filter = self.create_filter(patterns)
        matched_files = list(exclude_all_filter.call(self.local_files))
        self.assertEqual(matched_files, [])

        matched_files = list(exclude_all_filter.call(self.s3_files))
        self.assertEqual(matched_files, [])

    def test_prefix_filtering_consistent(self):
        # The same filter should work for both local and remote files.
        # So if I have a directory with 2 files:
        local_files = [
            self.file_stat('test1.txt'),
            self.file_stat('nottest1.txt'),
        ]
        # And the same 2 files remote (note that the way FileStat objects
        # are constructed, we'll have the bucket name but no leading '/'
        # character):
        remote_files = [
            self.file_stat('bucket/test1.txt', src_type='s3'),
            self.file_stat('bucket/nottest1.txt', src_type='s3'),
        ]
        # If I apply the filter to the local to the local files.
        exclude_filter = self.create_filter([['exclude', 't*']])
        filtered_files = list(exclude_filter.call(local_files))
        self.assertEqual(len(filtered_files), 1)
        self.assertEqual(os.path.basename(filtered_files[0].src),
                         'nottest1.txt')

        # I should get the same result if I apply the same filter to s3
        # objects.
        exclude_filter = self.create_filter([['exclude', 't*']], root='bucket')
        same_filtered_files = list(exclude_filter.call(remote_files))
        self.assertEqual(len(same_filtered_files), 1)
        self.assertEqual(os.path.basename(same_filtered_files[0].src),
                         'nottest1.txt')

    def test_bucket_exclude_with_prefix(self):
        s3_files = [
            self.file_stat('bucket/dir1/key1.txt', src_type='s3'),
            self.file_stat('bucket/dir1/key2.txt', src_type='s3'),
            self.file_stat('bucket/dir1/notkey3.txt', src_type='s3'),
        ]
        filtered_files = list(
            self.create_filter([['exclude', 'dir1/*']],
                               root='bucket').call(s3_files))
        self.assertEqual(filtered_files, [])

        key_files = list(
            self.create_filter([['exclude', 'dir1/key*']],
                               root='bucket').call(s3_files))
        self.assertEqual(len(key_files), 1)
        self.assertEqual(key_files[0].src, 'bucket/dir1/notkey3.txt')

    def test_root_dir(self):
        p = platform_path
        local_files = [self.file_stat(p('/foo/bar/baz.txt'), src_type='local')]
        local_filter = self.create_filter([['exclude', 'baz.txt']],
                                          root=p('/foo/bar/'))
        filtered = list(local_filter.call(local_files))
        self.assertEqual(filtered, [])

        # However, if we're at the root of /foo', then this filter won't match.
        local_filter = self.create_filter([['exclude', 'baz.txt']],
                                          root=p('/foo/'))
        filtered = list(local_filter.call(local_files))
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].src, p('/foo/bar/baz.txt'))


if __name__ == "__main__":
    unittest.main()
