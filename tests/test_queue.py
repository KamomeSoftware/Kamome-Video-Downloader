import copy
import queue
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace, MethodType
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import main

class Var:
    def __init__(self, value=None): self.value = value
    def get(self): return self.value
    def set(self, value): self.value = value
    def configure(self, **kwargs): pass

class Tree:
    def __init__(self): self.rows = {}; self.order = []; self.sel = ()
    def exists(self, key): return key in self.rows
    def insert(self, parent, index, iid, values): self.rows[iid] = values; self.order.append(iid)
    def item(self, key, **kwargs): self.rows[key] = kwargs.get('values', self.rows[key])
    def move(self, key, parent, index): self.order.remove(key); self.order.insert(index, key)
    def get_children(self): return tuple(self.order)
    def delete(self, key): self.order.remove(key); del self.rows[key]
    def selection(self): return self.sel
    def selection_set(self, keys): self.sel = tuple(keys) if not isinstance(keys, str) else (keys,)


def harness():
    a = SimpleNamespace(jobs=[], active_job=None, closing=False, job_serial=0, lang='ja',
        proc=None, proc_lock=threading.Lock(), q=queue.Queue(), job_tree=Tree(),
        video_info=None, analyzed_url=None, analysis_serial=0, url_after_id=None,
        progress_var=Var(0), status_var=Var(), cancel_btn=Var(), download_btn=Var(), analyze_btn=Var(),
        url_var=Var('https://www.instagram.com/reel/ABC123/?igsh=tracking'),
        dest_var=Var(), thumb_var=Var(True), cookie_var=Var('Firefox'))
    for name in ('_start','_pending_template','_download_command','_refresh_jobs','_selected_job',
                 '_remove_job','_move_job','_clear_finished','_start_next_job','_poll_queue',
                 '_common_ytdlp_args','_cookie_args','_worker','_cancel','_tr','_on_url_changed'):
        setattr(a,name,MethodType(getattr(main.App,name),a))
    a._terminate_process = main.App._terminate_process
    a._log = lambda text: None
    a._save_settings = lambda: None
    a._validate_tools = lambda: True
    a._selected_format = lambda: None
    a.after = lambda *args: None
    a._clear_formats = lambda: None
    a._schedule_analysis = lambda delay: None
    return a

class NamingTests(unittest.TestCase):
    def test_instagram_trailing_slash_query_fragment(self):
        info = {'title':'account','id':'numeric-id'}
        for url in ('https://www.instagram.com/reel/ABC_123/',
                    'https://www.instagram.com/reel/ABC_123?igsh=abc#fragment',
                    'https://www.instagram.com/reel/ABC_123///'):
            self.assertEqual(main.output_stem(info,url),'account_ABC_123')
    def test_distinct_posts_and_windows_symbols(self):
        a = main.output_stem({'title':'user:name'}, 'https://instagram.com/p/AAA/')
        b = main.output_stem({'title':'user:name'}, 'https://instagram.com/p/BBB/')
        self.assertEqual(a,'user_name_AAA'); self.assertNotEqual(a,b)
    def test_youtube_identifier_not_watch(self):
        self.assertEqual(main.output_stem({'title':'t','id':'VIDEO'},'https://youtube.com/watch?v=VIDEO'),'t_VIDEO')
    def test_instagram_spoof_host(self):
        self.assertEqual(main.output_stem({'title':'t','id':'safe'},'https://instagram.com.evil/reel/WRONG/'),'t_safe')
    def test_template_evaluation_and_carousel(self):
        from yt_dlp import YoutubeDL
        a=harness()
        with YoutubeDL({'quiet':True}) as y:
            template=a._pending_template(a.url_var.get())
            common={'title':'account','id':'numeric-id','ext':'mp4'}
            self.assertEqual(y.evaluate_outtmpl(template,common),'account_ABC123.mp4')
            self.assertEqual(y.evaluate_outtmpl(template,dict(common,playlist_index=2)),'account_ABC123_02.mp4')

class QueueTests(unittest.TestCase):
    def setUp(self): self.a=harness()
    def job(self,key): return main.DownloadJob(key,'https://example.com/'+key,'dest',key,key,('engine',), 'auto')
    def test_one_worker_then_failure_advances(self):
        a=self.a; a.jobs=[self.job('1'),self.job('2'),self.job('3')]
        with patch.object(main.threading,'Thread') as th:
            a._start_next_job(); a._start_next_job()
            self.assertEqual(th.call_count,1); self.assertIs(a.active_job,a.jobs[0])
            a.q.put(('done',('1',False,'failure'))); a._poll_queue()
            self.assertEqual(a.jobs[0].state,'failed'); self.assertIs(a.active_job,a.jobs[1])
            self.assertEqual(th.call_count,2)
            a.q.put(('done',('2',True,''))); a._poll_queue()
            self.assertIs(a.active_job,a.jobs[2]); self.assertEqual(th.call_count,3)
    def test_cancel_before_process_start(self):
        a=self.a; job=self.job('1'); a.active_job=job
        a._cancel()
        with patch.object(main.subprocess,'Popen') as pop:
            a._worker(job)
            pop.assert_not_called()
        self.assertEqual(a.q.get()[0],'done')
    def test_command_snapshot_and_add_while_active(self):
        import tempfile
        a=self.a
        with tempfile.TemporaryDirectory() as dest, patch.object(main.threading,'Thread'):
            a.dest_var.set(dest); a._start(); original=a.jobs[0].command
            a.cookie_var.set('Edge'); a.thumb_var.set(False)
            a.url_var.set('https://instagram.com/reel/SECOND/'); a._start()
            self.assertEqual(len(a.jobs),2)
            self.assertEqual(a.jobs[0].command,original)
            self.assertIn('firefox',original); self.assertIn('edge',a.jobs[1].command)
            self.assertIn('--embed-thumbnail',original); self.assertNotIn('--embed-thumbnail',a.jobs[1].command)
            self.assertEqual(a.jobs[1].state,'waiting')
    def test_reorder_remove_keeps_running(self):
        a=self.a; a.jobs=[self.job(str(i)) for i in range(3)]; a.jobs[0].state='running'
        a._refresh_jobs(); a.job_tree.sel=('2',); a._move_job(-1)
        self.assertEqual([j.key for j in a.jobs],['0','2','1'])
        a._remove_job(); self.assertEqual([j.key for j in a.jobs],['0','1'])
        a.job_tree.sel=('0',); a._remove_job(); self.assertEqual(len(a.jobs),2)
    def test_url_edit_invalidates_old_analysis_immediately(self):
        a=self.a; a.video_info={'title':'old'}; a.analyzed_url='old'; a._on_url_changed()
        self.assertIsNone(a.video_info); self.assertIsNone(a.analyzed_url)
        self.assertEqual(a.analysis_serial,1)
    def test_worker_reports_after_process_reaped(self):
        a=self.a; job=self.job('1')
        job.command=(sys.executable,'-c',"print('[download] 100.0%')")
        a._worker(job)
        events=[]
        while not a.q.empty(): events.append(a.q.get())
        self.assertEqual(events[-1],('done',('1',True,'[download] 100.0%')))
        self.assertIsNone(a.proc)
    def test_close_guard_prevents_next(self):
        a=self.a; a.jobs=[self.job('1')]; a.closing=True
        with patch.object(main.threading,'Thread') as th:
            a._start_next_job(); th.assert_not_called()

@unittest.skipUnless(sys.platform=='win32', 'Windows UI smoke test')
class WindowsUI(unittest.TestCase):
    def test_queue_controls_and_window(self):
        with patch.object(main.App,'_load_settings'), patch.object(main.App,'_save_settings'), \
             patch.object(main.App,'_background_startup_tasks'):
            a=main.App()
            try:
                a.update(); self.assertEqual(a.title(),main.APP_NAME+' v0.6.6')
                self.assertEqual(str(a.download_btn['state']),'normal')
                self.assertEqual(len(a.job_tree['columns']),4)
                self.assertTrue(a.job_tree.winfo_ismapped())
            finally: a.destroy()

if __name__=='__main__': unittest.main()
