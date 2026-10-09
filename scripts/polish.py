"""Native Nuvio shell around the existing browser/native playback lifetimes."""
from pathlib import Path
import os
import shutil


def replace(path,old,new):
    source=path.read_text()
    if source.count(old)!=1:raise RuntimeError('Pinned polish anchor changed: '+str(path))
    path.write_text(source.replace(old,new))


def apply(evo,nuvio):
    app=evo/'projects/evoplayer'
    web=app/'src/evo_webui.c'
    # WebBrowserDialogParam carries an undocumented `animation` field that
    # upstream never sets. The 2026-10-03 investigation tries values here to
    # find out whether it softens the dialog's white first frame; 0 is upstream.
    animation=os.environ.get('NUVIO_WEBUI_ANIMATION','0')
    if not animation.isdigit():
        raise RuntimeError('NUVIO_WEBUI_ANIMATION must be a number')
    replace(web,'    LOG("Open url=%s ...", url);',
            '    s_param.animation = '+animation+';\n    LOG("Open url=%s ...", url);')
    replace(web,'static char s_hook_profile[16];','static int s_native_requested;\nstatic char s_hook_profile[16];')
    replace(web,'        s_close_req = 1;','        s_close_req = 1;\n        s_native_requested = 1;')
    replace(web,'    s_hook_seen = 0;', '    s_hook_seen = 0;\n    s_native_requested = 0;')
    web.write_text(web.read_text()+"\nint evo_webui_native_requested(void) {\n    pthread_mutex_lock(&s_mx);\n    int result = s_native_requested;\n    pthread_mutex_unlock(&s_mx);\n    return result;\n}\n")
    h=app/'include/evo_webui.h';h.write_text(h.read_text()+'\n#ifdef __cplusplus\nextern "C"\n#endif\nint evo_webui_native_requested(void);\n')
    replace(web,"b.textContent='Back to EVO'", "b.textContent='Player settings'")
    web.write_text(fix_playback_handoff(web.read_text()))
    header=app/'ui_rml/include/evo_rmlui_app.h'
    replace(header,'    void RenderLaunch(uint32_t* framebuffer, int width, int height);','    void RenderLaunch(uint32_t* framebuffer, int width, int height);\n    void RenderNuvio(uint32_t* framebuffer, int width, int height, const char* message);')
    replace(header,'    Rml::ElementDocument* m_launch_doc = nullptr;','    Rml::ElementDocument* m_nuvio_doc = nullptr;\n    Rml::ElementDocument* m_launch_doc = nullptr;')
    cpp=app/'ui_rml/src/evo_rmlui_app.cpp'
    replace(cpp,'        m_closed_doc,','        m_closed_doc, m_nuvio_doc,')
    replace(cpp,'        if (!m_launch_doc) {','        if (!m_nuvio_doc) {\n            m_nuvio_doc = m_context->LoadDocument(p + "nuvio.rml");\n            if (m_nuvio_doc) m_nuvio_doc->Hide();\n        }\n        if (!m_launch_doc) {')
    cpp.write_text(cpp.read_text()+r'''
void EvoRmlApp::RenderNuvio(uint32_t* framebuffer, int width, int height, const char* message) {
    if (!m_context || !m_nuvio_doc) return;
    ShowOnlyScreen(m_nuvio_doc);
    if (m_nav_doc) m_nav_doc->Hide();
    Rml::Element* status = m_nuvio_doc->GetElementById("nuvio-status");
    if (status && status->GetInnerRML() != (message ? message : "Opening Nuvio"))
        status->SetInnerRML(message ? message : "Opening Nuvio");
    m_context->Update();
    RenderCachedScreen(30, framebuffer, width, height);
}
''')
    bridge=app/'ui_rml/src/evo_rmlui_bridge.cpp'
    bridge.write_text(bridge.read_text()+'\nextern "C" void evo_rmlui_render_nuvio(uint32_t* framebuffer,int width,int height,const char* message) {\n    EvoRmlApp::Instance().RenderNuvio(framebuffer,width,height,message);\n}\n')
    h=app/'ui_rml/include/evo_rmlui_bridge.h'
    # This bridge header already scopes all declarations as extern C.
    replace(h,'void evo_rmlui_render_launch(uint32_t* framebuffer, int width, int height);','void evo_rmlui_render_launch(uint32_t* framebuffer, int width, int height);\nvoid evo_rmlui_render_nuvio(uint32_t* framebuffer, int width, int height, const char* message);')
    player=app/'core/src/screens/PlayerScreen.cpp'
    player.write_text(fix_player_back(player.read_text()))
    application=app/'core/src/Application.cpp'
    replace(application,'std::atomic<bool> g_web_done{false};','std::atomic<bool> g_web_done{false};\nbool g_nuvio_preparing = false;')
    replace(application,'        g_web_src = PlaybackSource();','        g_nuvio_preparing = true;\n        g_web_src = PlaybackSource();')
    replace(application,'        pthread_join(g_web_thread, nullptr);','        pthread_join(g_web_thread, nullptr);\n        g_nuvio_preparing = false;')
    replace(application,'        bool isSurround = (m_screenManager->getCurrentScreenId() == ScreenId::SurroundTest);','        bool nuvioShell = !isPlayer &&\n            !(m_playbackController && m_playbackController->isActive()) &&\n            !evo_webui_native_requested();\n        bool isSurround = (m_screenManager->getCurrentScreenId() == ScreenId::SurroundTest);')
    replace(application,'int uiActive = (frame < 10) || isPlayer || isSurround || hasInput || hasAnim ||','int uiActive = nuvioShell || (frame < 10) || isPlayer || isSurround || hasInput || hasAnim ||')
    source=application.read_text();anchor='                m_screenManager->render(m_uiScratch, DisplayWidth, DisplayHeight);'
    if source.count(anchor)!=2:raise RuntimeError('Pinned render branches changed')
    before,after=source.rsplit(anchor,1)
    application.write_text(before+'''                if (nuvioShell)
                    evo_rmlui_render_nuvio(m_uiScratch, DisplayWidth, DisplayHeight,
                        g_nuvio_preparing ? "Preparing playback" : "Opening Nuvio");
                else
                    m_screenManager->render(m_uiScratch, DisplayWidth, DisplayHeight);'''+after)
    asset=Path(__file__).resolve().parent.parent/'assets'
    shutil.copyfile(asset/'nuvio.rml',app/'assets/rml/nuvio.rml')
    shutil.copyfile(nuvio/'assets/brand/app_logo_wordmark.png',app/'assets/icons/nuvio-wordmark.png')
    # Fixed-size repository artwork: the title icon and the launch screens.
    shutil.copyfile(asset/'icon.png',app/'sce_sys/icon0.png')
    for name in ('pic0.png','pic1.png'):
        shutil.copyfile(asset/'launch.png',app/'sce_sys'/name)


def patch_resume_router(text):
    # Reuse Nuvio's route-resume semantics without enabling webOS services.
    guard='if (!Platform.isWebOS()) {'
    if text.count(guard)!=2:raise RuntimeError('Pinned route resume guards changed')
    text=text.replace(guard,'if (!Platform.isWebOS() && !globalThis.__NUVIO_PS5__) {')
    old='      if (!this.isWebOsResumeRouteRestorable(route)) {\n        LocalStore.remove(WEBOS_RESUME_ROUTE_KEY);'
    if text.count(old)!=1:raise RuntimeError('Pinned route exclusion changed')
    text=text.replace(old, '      if (!this.isWebOsResumeRouteRestorable(route)) {\n        if (globalThis.__NUVIO_PS5__) return;\n        LocalStore.remove(WEBOS_RESUME_ROUTE_KEY);')
    if text.count('!WEBOS_NON_RESTORABLE_ROUTES.has(route)') != 1:
        raise RuntimeError('Pinned restorable route predicate changed')
    text=text.replace('!WEBOS_NON_RESTORABLE_ROUTES.has(route)',
        '(!WEBOS_NON_RESTORABLE_ROUTES.has(route) || (globalThis.__NUVIO_PS5__ && ["detail", "stream"].includes(route)))')
    return text


def patch_nuvio(nuvio):
    router=nuvio/'js/ui/navigation/routerMethods-02-complete-route-return-back-guard.js'
    router.write_text(patch_resume_router(router.read_text()))
    app=nuvio/'js/app.js'
    replace(app, 'let hasSelectedProfileThisSession = false;',
        'let hasSelectedProfileThisSession = false;\n' +
        (Path(__file__).parent/'ps5-resume.js').read_text())
    replace(app, '  if (hasSelectedProfileThisSession) {',
        '  if (hasSelectedProfileThisSession || canResumePs5Playback()) {')
    replace(app, '          ProfileManager.isRememberLastProfileEnabled() &&\n          ProfileManager.hasEverSelectedProfile()',
        '          canResumePs5Playback() || (\n'
        '            ProfileManager.isRememberLastProfileEnabled() &&\n'
        '            ProfileManager.hasEverSelectedProfile()\n'
        '          )')


def fix_player_back(source):
    include='#include "evo/screens/PlayerScreen.hpp"'
    old='        // Stop playback confirmation prompt\n        if (screenMgr) {'
    if source.count(include)!=1 or source.count(old)!=1:raise RuntimeError('Pinned player Back anchors changed')
    source=source.replace(include,include+'\n#include "evo_webui.h"')
    return source.replace(old,'''        // Nuvio Back stops the native session; the existing bridge reopens it.
        // Native-only playback retains confirmation and the other overlays.
        if (!evo_webui_native_requested()) {
            playback->stopPlayback();
            if (screenMgr) screenMgr->returnFromPlayback();
            return true;
        }
        // Stop playback confirmation prompt
        if (screenMgr) {''')


def fix_playback_handoff(source):
    # Save synchronously before EVO closes the browser. Mark only its return URL.
    old = '" function go(t){if(done)return;done=1;saveNow(1);"'
    end = "encodeURIComponent(good));}"
    if source.count(old) != 1 or source.count(end) != 1:
        raise RuntimeError('Pinned playback handoff anchors changed')
    new = ('" function go(t){if(done)return;done=1;var back=good;"\n'
           '" if(NUVIO){if(window.__nuvioSavePlaybackReturn)window.__nuvioSavePlaybackReturn();"\n'
           '" var ret=new URL(good,location.href);ret.searchParams.set(\\"nuvioPlaybackReturn\\",\\"1\\");back=ret.href;}saveNow(1);"')
    return source.replace(old, new).replace(end, 'encodeURIComponent(back));}')
