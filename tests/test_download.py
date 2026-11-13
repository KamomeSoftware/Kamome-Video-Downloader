"""Exercise the real Windows engines against a local, generated video."""
import functools
import http.server
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from test_queue import harness
import main

@unittest.skipUnless(sys.platform=='win32' and main.FFMPEG.exists(), 'Windows engine integration')
class RealDownload(unittest.TestCase):
    def test_two_sequential_downloads_and_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); dest=root/'saved'; dest.mkdir()
            subprocess.run([str(main.FFMPEG),'-v','error','-f','lavfi','-i','color=c=blue:s=160x120:r=10',
                            '-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-t','1','-c:v','libx264',
                            '-c:a','aac','-shortest',str(root/'clip.mp4')],check=True)
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=tmp))
            threading.Thread(target=server.serve_forever,daemon=True).start()
            try:
                a=harness();a.cookie_var.set('None')
                url=f'http://127.0.0.1:{server.server_port}/clip.mp4'
                from types import MethodType
                a._prepare_formats = MethodType(main.App._prepare_formats, a)
                a._format_size = MethodType(main.App._format_size, a)
                main.App._analyze_worker(a, url, 1, tuple(a._common_ytdlp_args()))
                kind, payload = a.q.get_nowait()
                self.assertEqual(kind, "analysis", payload)
                self.assertTrue(payload[1].get("id"))
                for code in ['FIRST','SECOND','FIRST']:
                    url=f'http://127.0.0.1:{server.server_port}/clip.mp4'
                    cmd=a._download_command(url,str(dest),None,'account_'+code+'.%(ext)s',False)
                    job=main.DownloadJob(code,url,str(dest),'account',code,tuple(cmd),'auto')
                    a._worker(job)
                    result=None
                    while not a.q.empty():
                        event=a.q.get()
                        if event[0]=='done': result=event[1]
                    self.assertTrue(result[1],result)
                    if code=='FIRST' and 'stamp' not in locals(): stamp=(dest/'account_FIRST.mp4').stat().st_mtime_ns
                self.assertEqual((dest/'account_FIRST.mp4').stat().st_mtime_ns,stamp)
                self.assertTrue((dest/'account_SECOND.mp4').exists())
            finally:
                server.shutdown(); server.server_close()
