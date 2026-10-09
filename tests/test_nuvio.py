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


class LoopbackDiagnosticAdapterTests(unittest.TestCase):
    def test_proxy_reports_each_socket_stage_and_browser_connection(self):
        source = '''    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) { LOG("server: socket errno=%d", errno); return; }
    if (bind(fd, (struct sockaddr *)&a, sizeof a) != 0 || listen(fd, 16) != 0) {
        LOG("server: bind/listen 127.0.0.1:%d failed errno=%d", s_port, errno);
        close(fd);
        return;
    }
        int c = accept(s_listen_fd, NULL, NULL);
        if (c >= 0 && s_srv_stop) { close(c); break; }'''
        adapted = build.instrument_loopback_server(source)
        for result in ('socket failed errno=%d', 'socket ok fd=%d',
                       'bind failed port=%d errno=%d', 'bind ok 127.0.0.1:%d',
                       'listen failed port=%d errno=%d', 'listen ok port=%d',
                       'connection accepted'):
            self.assertIn(result, adapted)

    def test_proxy_diagnostic_refuses_moved_anchor(self):
        with self.assertRaises(RuntimeError):
            build.instrument_loopback_server('int fd = socket(AF_INET, SOCK_STREAM, 0);')

    def test_unpromoted_diagnostic_bypasses_only_the_missing_origin_preflight(self):
        source = '''    case P_CHECK:
        if (s_check_rc == 0) return;
        if (s_check_rc < 0) {
            char m[256];
'''
        adapted = build.bypass_loopback_origin_preflight(source)
        self.assertIn('preflight bypassed for unpromoted loopback diagnostic', adapted)
        self.assertNotIn('#ifdef NUVIO_UNPROMOTED_LOOPBACK_DIAGNOSTIC', adapted)
        self.assertIn('if (s_check_rc < 0) {\n            char m[256];', adapted)

    def test_unpromoted_diagnostic_refuses_moved_preflight_anchor(self):
        with self.assertRaises(RuntimeError):
            build.bypass_loopback_origin_preflight('case P_CHECK: break;')


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
        result=types.SimpleNamespace(returncode=0,stdout='NUVIO eboot stage=absent',stderr='')
        with patch.dict(installer.os.environ,{'PS5_READ_IDLE_TIMEOUT':'3'}), \
             patch.object(installer.subprocess,'run',return_value=result) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            installer.helper(5,'fixture.invalid')
            self.assertEqual(run.call_args.kwargs['env']['PS5_READ_IDLE_TIMEOUT'],'60.0')
            self.assertGreater(run.call_args.kwargs['timeout'],60+5+30+10)
        with patch.dict(installer.os.environ,{'PS5_READ_IDLE_TIMEOUT':'120'}), \
             patch.object(installer.subprocess,'run',return_value=result) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            installer.helper(5,'fixture.invalid')
            self.assertEqual(run.call_args.kwargs['env']['PS5_READ_IDLE_TIMEOUT'],'120.0')
            self.assertGreater(run.call_args.kwargs['timeout'],120+5+30+10)


class UpdateMetadataTests(unittest.TestCase):
    def test_update_allows_only_a_content_version_bump(self):
        import json
        import update
        before={'titleId':'PPSA99997','contentId':'UP9000-PPSA99997_00-NUVIOPS500000000',
                'contentVersion':'01.000.001','localizedParameters':{'en-US':{'titleName':'Nuvio'}}}
        after={**before,'contentVersion':'01.000.002'}
        self.assertTrue(update.safe_param_update(json.dumps(before).encode(),
                                                 json.dumps(after).encode()))
        for change in ({'titleId':'PPSA11111'},
                       {'contentId':'UP9000-PPSA11111_00-NUVIOPS500000000'},
                       {'localizedParameters':{'en-US':{'titleName':'Other'}}},
                       {'contentVersion':'01.000.000'}):
            self.assertFalse(update.safe_param_update(json.dumps(before).encode(),
                                                      json.dumps({**before,**change}).encode()))

    def test_console_eboot_report_requires_installed_backup_and_stage(self):
        import update
        installed='a'*64
        backup='a'*64
        stage='b'*64
        output=(f'NUVIO eboot installed bytes=100 sha256={installed}\n'
                f'NUVIO eboot backup bytes=100 sha256={backup}\n'
                f'NUVIO eboot stage bytes=101 sha256={stage}\n')
        self.assertEqual(update.parse_eboot_report(output), {
            'installed':(100,installed),'backup':(100,backup),'stage':(101,stage)})
        absent=output.replace(f'NUVIO eboot stage bytes=101 sha256={stage}',
                              'NUVIO eboot stage=absent')
        self.assertIsNone(update.parse_eboot_report(absent)['stage'])
        with self.assertRaises(RuntimeError):
            update.parse_eboot_report('NUVIO eboot installed=unknown')


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

    def test_ps5_index_keeps_the_stylesheet_render_blocking(self):
        source=('<html>\n  <head>\n'
                '    <link rel="stylesheet" href="css/bundle.css" />\n  </head>\n'
                '  <body></body>\n</html>\n')
        html=build.patch_index(source)
        # The console's browser renders Nuvio unstyled when the sheet loads
        # through a media switch, so the plain blocking link must survive.
        self.assertIn('<link rel="stylesheet" href="css/bundle.css" />',html)
        self.assertNotIn('media="print"',html)

    def test_ps5_index_refuses_moved_or_repeated_anchors(self):
        with self.assertRaises(RuntimeError):
            build.patch_index('<html><body>no head</body></html>')
        with self.assertRaises(RuntimeError):
            build.patch_index('<head></head><script src="ps5-input.js"></script>')


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


class UIServerTests(unittest.TestCase):
    """Exercise the console UI server's path, MIME and HTTP behavior on the host."""

    def test_path_confinement_mime_and_http_serve(self):
        import shutil
        import subprocess
        import time
        compiler=shutil.which('clang') or shutil.which('cc')
        if not compiler:
            self.skipTest('No host C compiler')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'webui'
            (root/'css').mkdir(parents=True)
            (root/'index.html').write_bytes(b'<html>NUVIO</html>')
            (root/'css'/'bundle.css').write_bytes(b'body{color:#000}')
            harness=Path(tmp)/'harness.c'
            harness.write_text('#include "'+str(APP/'ui_server.c')+'"\n'+r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
int main(int argc, char **argv) {
    char out[4096];
    assert(nuvio_ui_path("/root","/",out,sizeof out)==0 && !strcmp(out,"/root/index.html"));
    assert(nuvio_ui_path("/root","/css/bundle.css",out,sizeof out)==0 && !strcmp(out,"/root/css/bundle.css"));
    assert(nuvio_ui_path("/root","/index.html?v=1",out,sizeof out)==0 && !strcmp(out,"/root/index.html"));
    assert(nuvio_ui_path("/root","/sub/",out,sizeof out)==0 && !strcmp(out,"/root/sub/index.html"));
    assert(nuvio_ui_path("/root","/a/./b",out,sizeof out)==0 && !strcmp(out,"/root/a/b"));
    assert(nuvio_ui_path("/root","/%2e%2e/secret",out,sizeof out)!=0);
    assert(nuvio_ui_path("/root","/a/../../secret",out,sizeof out)!=0);
    assert(nuvio_ui_path("/root","/a%00b",out,sizeof out)!=0);
    assert(strstr(nuvio_ui_mime("css/bundle.css"),"text/css")!=NULL);
    assert(strstr(nuvio_ui_mime("app.bundle.js"),"javascript")!=NULL);
    assert(!strcmp(nuvio_ui_mime("x.bin"),"application/octet-stream"));
    if (argc > 2) {
        if (nuvio_ui_server_open(argv[1], atoi(argv[2])) != 0) return 1;
        for (;;) nuvio_ui_server_poll(250);
    }
    return 0;
}
''')
            binary=Path(tmp)/'harness'
            subprocess.run([compiler,'-std=c11','-Wall','-Wextra','-Werror','-pthread',str(harness),'-o',str(binary)],check=True,timeout=20)
            subprocess.run([str(binary)],check=True,timeout=10)
            server=subprocess.Popen([str(binary),str(root),'45917'])
            try:
                base='http://127.0.0.1:45917'
                for _ in range(60):
                    try:
                        with urllib.request.urlopen(base+'/css/bundle.css',timeout=0.5) as response:
                            self.assertEqual(response.read(),b'body{color:#000}')
                            self.assertEqual(response.headers['Content-Type'],'text/css; charset=utf-8')
                            break
                    except OSError:
                        time.sleep(0.1)
                else:
                    self.fail('server did not answer')
                with urllib.request.urlopen(base+'/',timeout=1) as response:
                    self.assertEqual(response.read(),b'<html>NUVIO</html>')
                with self.assertRaises(urllib.error.HTTPError) as exc:
                    urllib.request.urlopen(base+'/%2e%2e/secret',timeout=1)
                self.assertEqual(exc.exception.code,403)
                with self.assertRaises(urllib.error.HTTPError) as exc:
                    urllib.request.urlopen(base+'/missing.js',timeout=1)
                self.assertEqual(exc.exception.code,404)
            finally:
                server.terminate()
                server.wait(timeout=5)
