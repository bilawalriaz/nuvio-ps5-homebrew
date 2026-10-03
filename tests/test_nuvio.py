"""Exercise range playback and confinement on the actual host HTTP handler."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

APP = Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(APP))
spec = importlib.util.spec_from_file_location('nuvio_build', APP/'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
# serve's sibling import is isolated to this module load.
spec = importlib.util.spec_from_file_location('nuvio_serve', APP/'serve.py')
serve = importlib.util.module_from_spec(spec)
old = sys.modules.get('build')
sys.modules['build'] = build
try:
    spec.loader.exec_module(serve)
finally:
    if old is None:
        del sys.modules['build']
    else:
        sys.modules['build'] = old


class NuvioHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)/'ui'
        root.mkdir()
        (root/'index.html').write_bytes(b'NUVIO fixture')
        outside = Path(self.tmp.name)/'outside.txt'
        outside.write_bytes(b'not served')
        (root/'escape.txt').symlink_to(outside)
        self.clip = Path(self.tmp.name)/'clip.mp4'
        self.clip.write_bytes(bytes(range(256)))
        self.server = serve.server(root, self.clip, '127.0.0.1', 0, 'http://fixture.invalid')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:'+str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def get(self, path, value=None, method='GET'):
        headers = {'Range': value} if value else {}
        return urllib.request.urlopen(urllib.request.Request(self.url+path, headers=headers, method=method), timeout=2)

    def test_seek_ranges_and_head(self):
        for value, expected in [('bytes=10-19',bytes(range(10,20))),('bytes=250-',bytes(range(250,256))),('bytes=-3',bytes(range(253,256)))]:
            with self.get('/ps5-test/clip.mp4', value) as response:
                self.assertEqual(response.status, 206)
                self.assertEqual(response.read(), expected)
        with self.get('/ps5-test/clip.mp4','bytes=10-19','HEAD') as response:
            self.assertEqual(response.headers['Content-Length'],'10')
            self.assertEqual(response.read(),b'')

    def test_invalid_ranges_and_confinement(self):
        for value in ('bytes=256-', 'bytes=20-10', 'bytes=-0', 'bytes=1-2,4-5', 'bytes=-'):
            with self.assertRaises(urllib.error.HTTPError) as exc:
                self.get('/ps5-test/clip.mp4',value)
            self.assertEqual(exc.exception.code,416)
        for path in ('/%2e%2e/outside.txt','/escape.txt'):
            with self.assertRaises(urllib.error.HTTPError) as exc:
                self.get(path)
            self.assertEqual(exc.exception.code,403)

    def test_catalog_and_stream_contract(self):
        import json
        with self.get('/ps5-test/catalog/movie/ps5-test.json') as response:
            item = json.load(response)['metas'][0]
        with self.get('/ps5-test/stream/movie/'+item['id']+'.json') as response:
            self.assertEqual(json.load(response)['streams'][0]['url'], 'http://fixture.invalid/ps5-test/clip.mp4')
            self.assertEqual(response.headers['Access-Control-Allow-Origin'],'*')
        with self.get('/') as response:
            self.assertEqual(response.read(),b'NUVIO fixture')


class PS5InputTests(unittest.TestCase):
    def test_x_uses_dpad_focus_instead_of_pointer(self):
        import shutil
        import subprocess
        node = shutil.which('node')
        if not node:
            self.skipTest('Node unavailable; HTTP tests still run without it')
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let listener,focused=null,clicks=0,stopped=0;
const context={window:{},document:{addEventListener:(name,fn)=>{listener=fn;},querySelector:()=>focused}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
const target={};
const e=()=>({button:0,target,preventDefault(){stopped++;},stopImmediatePropagation(){stopped++;}});
listener(e()); assert.equal(stopped,0); // A page without app focus retains its click.
focused={contains:t=>t===focused,click(){clicks++;listener(e());}};
listener(e());assert.equal(clicks,1);assert.equal(stopped,2); // Background or another button activates focus once.
listener({...e(),target:focused});assert.equal(clicks,1); // Actual focused target is not double-activated.
listener({...e(),button:2});assert.equal(clicks,1); // Secondary browser click retains its behavior.
"""
        subprocess.run([node, '-e', script, str(APP/'ps5-input.js')], check=True, timeout=10)


class ProviderSeekTests(unittest.TestCase):
    def test_provider_without_local_path_queues_seek(self):
        import shutil
        import subprocess
        compiler=shutil.which('clang') or shutil.which('cc')
        if not compiler:
            self.skipTest('No host C compiler')
        demux=(APP.parent/'tests/fixtures/nuvio_seek.c.txt').read_text()
        controller='    prospero_request_inplace_seek(targetSeconds, 0);\n    pp_playback_notify_seek_begin(&g_pp_pb, targetUs);'
        fixed,_=build.fix_provider_seek(demux,controller)
        harness=r"""
#include <assert.h>
#include <pthread.h>
static void *play_fmt=(void *)1;
static int video_stream_index=0,audio_stream_index=-1;
static char current_media_path[1]={0};
static double media_duration_sec=100,prospero_seek_target_seconds;
static int player_paused,controls_last_used_ms,prospero_seek_restore_paused,prospero_seek_pending;
static pthread_mutex_t prospero_seek_mutex=PTHREAD_MUTEX_INITIALIZER;
static int now_ms(void) {return 1;}
"""+fixed+r"""
int main(void) {
 (void)controls_last_used_ms;
 assert(current_media_path[0]==0);
 assert(prospero_request_inplace_seek(30,0)==1);
 assert(prospero_seek_pending==1 && prospero_seek_target_seconds==30 && player_paused);
 assert(prospero_request_inplace_seek(200,1)==1);
 assert(prospero_seek_target_seconds==99 && prospero_seek_restore_paused==1);
 play_fmt=0;prospero_seek_pending=0;player_paused=0;
 assert(prospero_request_inplace_seek(40,0)==0);
 assert(!prospero_seek_pending && !player_paused);
 play_fmt=(void *)1;video_stream_index=-1;
 assert(prospero_request_inplace_seek(40,0)==0);
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'seek.c';source.write_text(harness)
            binary=Path(tmp)/'seek'
            subprocess.run([compiler,'-std=c11','-Wall','-Wextra','-Werror','-pthread',str(source),'-o',str(binary)],check=True,timeout=20)
            subprocess.run([str(binary)],check=True,timeout=10)


class ControlEvidenceTests(unittest.TestCase):
    def test_upload_success_does_not_mask_launch_refusal(self):
        import contextlib
        import io
        import types
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('nuvio_install',APP/'install.py')
        installer=importlib.util.module_from_spec(spec)
        previous=sys.modules.get('build');sys.modules['build']=build
        try:spec.loader.exec_module(installer)
        finally:
            if previous is None:del sys.modules['build']
            else:sys.modules['build']=previous
        for text in ('NUVIO launch refused: close the running title', 'NUVIO launch_result=0x80940004', 'sent bytes'):
            result=types.SimpleNamespace(returncode=0,stdout=text,stderr='')
            with patch.object(installer.subprocess,'run',return_value=result),contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(RuntimeError):installer.helper(3,'fixture.invalid')
        result=types.SimpleNamespace(returncode=0,stdout='NUVIO launch_result=0x8018',stderr='')
        with patch.object(installer.subprocess,'run',return_value=result),contextlib.redirect_stdout(io.StringIO()):
            self.assertIn('0x8018',installer.helper(3,'fixture.invalid'))


class RouteResumeTests(unittest.TestCase):
    def test_ps5_retains_previous_route_across_player_and_reload(self):
        import subprocess
        import shutil
        import polish
        node=shutil.which('node')
        if not node:self.skipTest('Node unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/'js/ui/navigation/routerMethods-02-complete-route-return-back-guard.js'
            target.parent.mkdir(parents=True)
            target.write_text((APP.parent/'tests/fixtures/router_resume.js.txt').read_text())
            polish.patch_nuvio(root)
            script=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const store=new Map(),ctx={__NUVIO_PS5__:true,Platform:{isWebOS:()=>false},LocalStore:{set:(k,v)=>store.set(k,v),get:(k,d)=>store.get(k)||d,remove:k=>store.delete(k)},WEBOS_RESUME_ROUTE_KEY:'resume',WEBOS_RESUME_ROUTE_TTL_MS:60000,WEBOS_NON_RESTORABLE_ROUTES:new Set(['player']),console};
const router=vm.runInNewContext('({'+fs.readFileSync(process.argv[1],'utf8')+'})',ctx);
router.routes={streams:{},player:{},home:{}};
router.persistWebOsResumeRoute('streams',{id:'fixture'});
router.persistWebOsResumeRoute('player',{});
let restored=router.consumeWebOsResumeRoute();assert.equal(restored.route,'streams');assert.equal(restored.params.id,'fixture');
store.get('resume').savedAt=Date.now()-61000;assert.equal(router.consumeWebOsResumeRoute(),null);
ctx.__NUVIO_PS5__=false;router.persistWebOsResumeRoute('home',{});assert.equal(store.size,0);
"""
            subprocess.run([node,'-e',script,str(target)],check=True,timeout=10)


class UIIndexTests(unittest.TestCase):
    def test_ps5_index_paints_black_before_the_app_css(self):
        source=('<!doctype html>\n<html lang="en">\n  <head>\n'
                '    <link rel="stylesheet" href="css/bundle.css" />\n  </head>\n  <body></body>\n</html>\n')
        html=build.patch_index(source)
        self.assertLess(html.index('background-color:#000'),html.index('css/bundle.css'))
        self.assertEqual(html.count('ps5-input.js'),1)
        self.assertLess(html.index('ps5-input.js'),html.index('</head>'))

    def test_ps5_index_loads_the_stylesheet_without_blocking_the_first_paint(self):
        source=('<html>\n  <head>\n'
                '    <link rel="stylesheet" href="css/bundle.css" />\n  </head>\n'
                '  <body></body>\n</html>\n')
        html=build.patch_index(source)
        self.assertIn('media="print"',html)
        self.assertIn("this.media='all'",html)
        self.assertIn('<noscript><link rel="stylesheet" href="css/bundle.css"></noscript>',html)
        # The blocking form must be gone, or the first paint still waits.
        self.assertNotIn('href="css/bundle.css" />',html)

    def test_ps5_index_refuses_moved_or_repeated_anchors(self):
        with self.assertRaises(RuntimeError):
            build.patch_index('<html><body>no head</body></html>')
        with self.assertRaises(RuntimeError):
            build.patch_index('<head></head><script src="ps5-input.js"></script>')
        with self.assertRaises(RuntimeError):
            build.patch_index('<head><link rel="stylesheet" href="css/other.css" /></head>')


class PlayerBackTests(unittest.TestCase):
    def test_nuvio_back_stops_session_native_back_retains_confirmation(self):
        import subprocess
        import shutil
        import polish
        compiler=shutil.which('clang++') or shutil.which('c++')
        if not compiler:self.skipTest('No host C++ compiler')
        fixed=polish.fix_player_back((APP.parent/'tests/fixtures/player_back.cpp.txt').read_text())
        body='\n'.join(l for l in fixed.splitlines() if not l.startswith('#include'))
        source=r"""
#include <cassert>
#include <cstdint>
namespace PadButtons { const uint32_t Circle=1; }
enum class ScreenId { ExitConfirm };
int nativeRequested=0;int evo_webui_native_requested(){return nativeRequested;}
struct Playback {int stopped=0;void stopPlayback(){stopped++;}} pb;
struct Screens {int returned=0,confirmed=0;void returnFromPlayback(){returned++;}void navigateTo(ScreenId){confirmed++;}} sm;
bool back(uint32_t pressed, Playback* playback, Screens* screenMgr) {
"""+body+r"""
return false;
}
int main(){
 assert(back(1,&pb,&sm));assert(pb.stopped==1 && sm.returned==1 && sm.confirmed==0);
 nativeRequested=1;assert(back(1,&pb,&sm));assert(pb.stopped==1 && sm.returned==1 && sm.confirmed==1);
 nativeRequested=0;assert(back(1,&pb,nullptr));assert(pb.stopped==2);
 assert(!back(0,&pb,&sm));assert(pb.stopped==2);
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'back.cpp';p.write_text(source);binary=Path(tmp)/'back'
            subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror',str(p),'-o',str(binary)],check=True,timeout=20)
            subprocess.run([str(binary)],check=True,timeout=10)
