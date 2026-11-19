"""ImageSink reassembly, filename safety, retention bounds, and ACL image topic."""
import base64
import os
import tempfile
import unittest
from pathlib import Path
from changan_ugv.nodes.image_sink import ImageSink
from changan_ugv.nodes.inventory import defaults, render_acl


def chunk(node_id, image_id, seq, count, data, name=None):
    return dict(v=1, type='image', node_id=node_id, image_id=image_id,
                name=name or image_id, seq=seq, count=count,
                data=base64.b64encode(data).decode('ascii'))


class ImageSinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.sink = ImageSink(Path(self.temp.name))

    def test_reassembles_and_saves(self):
        raw = b'\x00\x01\x02' * 2000
        count = 4
        step = len(raw) // count
        for i in range(count):
            self.sink.consume('micro-001', chunk('micro-001', 'fig-001.jpg', i, count, raw[i * step:(i + 1) * step]))
        target = Path(self.temp.name) / 'micro-001' / 'fig-001.jpg'
        self.assertEqual(target.read_bytes(), raw)

    def test_out_of_order_chunks_reassemble(self):
        raw = b'hello world'
        self.sink.consume('micro-001', chunk('micro-001', 'o.jpg', 1, 2, raw[6:]))
        self.sink.consume('micro-001', chunk('micro-001', 'o.jpg', 0, 2, raw[:6]))
        self.assertEqual((Path(self.temp.name) / 'micro-001' / 'o.jpg').read_bytes(), raw)

    def test_rejects_path_traversal(self):
        self.sink.consume('micro-001', chunk('micro-001', '../evil', 0, 1, b'x'))
        self.sink.consume('micro-001', chunk('micro-001', 'good.jpg', 0, 1, b'y', name='../../evil.jpg'))
        directory = Path(self.temp.name) / 'micro-001'
        self.assertEqual([p.name for p in directory.iterdir()], ['good.jpg'])

    def test_ignores_retained_and_bad_base64(self):
        body = chunk('micro-001', 'a.jpg', 0, 1, b'x')
        body['data'] = '!!!not-base64!!!'
        self.sink.consume('micro-001', body)
        self.sink.consume('micro-001', chunk('micro-001', 'b.jpg', 0, 1, b'y'), retained=True)
        self.assertFalse((Path(self.temp.name) / 'micro-001').exists())

    def test_rejects_bad_seq_count(self):
        self.sink.consume('micro-001', chunk('micro-001', 'c.jpg', 2, 1, b'z'))
        self.sink.consume('micro-001', chunk('micro-001', 'c.jpg', 0, 0, b'z'))
        self.assertFalse((Path(self.temp.name) / 'micro-001').exists())

    def test_prunes_oldest_files_above_size_cap(self):
        directory = Path(self.temp.name) / 'micro-001'
        sink = ImageSink(Path(self.temp.name), max_bytes=10)
        sink.consume('micro-001', chunk('micro-001', 'a.jpg', 0, 1, b'12345'))
        os.utime(directory / 'a.jpg', (1000, 1000))
        sink.consume('micro-001', chunk('micro-001', 'b.jpg', 0, 1, b'12345'))
        os.utime(directory / 'b.jpg', (2000, 2000))
        sink.consume('micro-001', chunk('micro-001', 'c.jpg', 0, 1, b'12345'))
        self.assertEqual(sorted(p.name for p in directory.iterdir()), ['b.jpg', 'c.jpg'])

    def test_drops_stale_partial_uploads(self):
        now = [0.0]
        sink = ImageSink(Path(self.temp.name), pending_ttl=10, clock=lambda: now[0])
        sink.consume('micro-001', chunk('micro-001', 'slow.jpg', 0, 2, b'half'))
        now[0] = 11
        sink.consume('micro-001', chunk('micro-001', 'new.jpg', 0, 2, b'other'))
        self.assertNotIn(('micro-001', 'slow.jpg'), sink.pending)
        self.assertIn(('micro-001', 'new.jpg'), sink.pending)

    def test_bounds_partial_upload_count(self):
        sink = ImageSink(Path(self.temp.name), max_pending=1)
        sink.consume('micro-001', chunk('micro-001', 'first.jpg', 0, 2, b'a'))
        sink.consume('micro-001', chunk('micro-001', 'second.jpg', 0, 2, b'b'))
        self.assertNotIn(('micro-001', 'first.jpg'), sink.pending)
        self.assertIn(('micro-001', 'second.jpg'), sink.pending)


class ImageACLTests(unittest.TestCase):
    def test_image_topic_granted(self):
        acl = render_acl(defaults())
        self.assertIn('topic write mesh/v1/nodes/micro-001/image', acl)
        self.assertIn('topic read mesh/v1/nodes/+/image', acl)


if __name__ == '__main__':
    unittest.main()
