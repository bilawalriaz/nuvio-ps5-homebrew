#!/usr/bin/env python3
"""Build the pinned Nuvio UI and an EVO-derived PS5 native title on macOS.

Host only. Generated upstream sources, modules and binaries remain outside Git.
"""
from pathlib import Path
import argparse
import base64
import re
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
import polish
import patches

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(os.environ.get('NUVIO_CACHE_DIR', str(ROOT/'.cache')))
WORK = Path(os.environ.get('NUVIO_WORK_DIR', str(ROOT/'build')))
TITLE = 'PPSA99997'  # Repository-assigned app identity, not a firmware constant.


def run(args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def sdk_install_auth_profile(makefile):
    """Read the public SDK install_app sample's exact signing metadata."""
    joined = makefile.replace('\\\n', ' ')
    authority = re.findall(r'^AUTHID\s*:=\s*(0x[0-9A-Fa-f]+)\s*$', joined, re.MULTILINE)
    info = re.findall(r'^AUTHINFO\s*:=\s*([0-9A-Fa-f \t]+)$', joined, re.MULTILINE)
    if len(authority) != 1 or len(info) != 1:
        raise RuntimeError('Pinned SDK signing profile declarations changed')
    values = info[0].split()
    if len(values) != 0x88 or any(not re.fullmatch('[0-9A-Fa-f]{2}', value) for value in values):
        raise RuntimeError('SDK authentication info must contain exactly 136 bytes')
    if not 0 <= int(authority[0], 16) <= 0xffffffffffffffff:
        raise RuntimeError('SDK authority exceeds its 64-bit field')
    return {'authority': authority[0], 'auth_info': ''.join(values).lower()}


def lld_available():
    """prospero-lld resolves ld.lld from the LLVM prefix or the lld formula prefix."""
    if shutil.which('ld.lld'):
        return True
    try:
        prefix = subprocess.check_output(['brew', '--prefix', 'lld'], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return False
    return bool(prefix) and (Path(prefix)/'bin/ld.lld').is_file()


def fetch(key):
    pin = next(p for p in json.loads((ROOT/'deps.lock').read_text())['artifacts'] if p['id'] == key)
    p = CACHE / pin.get('cache_file', key+'.zip')
    if not p.exists():
        tmp = p.with_suffix('.download')
        try:
            with urllib.request.urlopen(pin['url'], timeout=60) as r, tmp.open('wb') as f:
                shutil.copyfileobj(r, f)
            if digest(tmp) != pin['sha256']:
                raise RuntimeError('Downloaded checksum mismatch: '+key)
            tmp.replace(p)
        finally:
            tmp.unlink(missing_ok=True)
    if digest(p) != pin['sha256']:
        raise RuntimeError('Cached checksum mismatch: '+key)
    return pin, p


def source(key):
    pin, archive = fetch(key)
    dest = WORK / pin['directory']
    if dest.exists():
        shutil.rmtree(dest)
    with tarfile.open(archive) as t:
        t.extractall(WORK, filter='data')
    return dest


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError('Pinned source anchor changed: '+str(path))
    path.write_text(text.replace(old, new))


# EVO v0.12.0 includes a Dolby Vision component that mirrors FFmpeg 7.1.1 and
# refuses any other libavcodec, while the pinned pacbrew prefix carries the
# 7.0-era 61.3 headers. Build FFmpeg 7.1.1 with EVO's 'minimal' configuration
# (minus --enable-libdav1d: this port ships no dav1d, so AV1 remains
# unsupported) and install it over the sysroot copy, replacing the pacbrew
# libav* libraries - the same step EVO's own build performs. The result is
# cached in .cache/ so ordinary rebuilds skip the compile.
FFMPEG_FLAGS = (
    # EVO scripts/build-ffmpeg.sh, profile 'minimal', libdav1d removed.
    '--enable-cross-compile',
    '--cross-prefix={sdk}/bin/prospero-',
    '--enable-static',
    '--disable-shared',
    '--arch=x86_64',
    '--target-os=freebsd',
    '--cc=prospero-clang',
    '--cxx=prospero-clang++',
    '--nm=prospero-nm',
    '--strip=prospero-strip',
    '--ar=prospero-ar',
    '--ranlib=prospero-ranlib',
    '--pkg-config=prospero-pkg-config',
    '--disable-debug',
    '--disable-doc',
    '--disable-everything',
    '--disable-programs',
    '--disable-avdevice',
    '--disable-postproc',
    '--disable-encoders',
    '--disable-muxers',
    '--disable-bsfs',
    '--disable-devices',
    '--disable-filters',
    '--enable-network',
    '--enable-openssl',
    '--disable-iconv',
    '--disable-xlib',
    '--disable-sdl2',
    '--enable-swresample',
    '--enable-swscale',
    '--enable-decoder=aac',
    '--enable-decoder=aac_latm',
    '--enable-decoder=ac3',
    '--enable-decoder=eac3',
    '--enable-decoder=dca',
    '--enable-decoder=truehd',
    '--enable-decoder=mlp',
    '--enable-decoder=mp3',
    '--enable-decoder=mp2',
    '--enable-decoder=flac',
    '--enable-decoder=opus',
    '--enable-decoder=vorbis',
    '--enable-decoder=alac',
    '--enable-decoder=pcm_s16le',
    '--enable-decoder=pcm_s16be',
    '--enable-decoder=pcm_s24le',
    '--enable-decoder=pcm_f32le',
    '--enable-decoder=aac_fixed',
    '--enable-decoder=ac3_fixed',
    '--enable-decoder=acelp_kelvin',
    '--enable-decoder=als',
    '--enable-decoder=amrnb',
    '--enable-decoder=amrwb',
    '--enable-decoder=apac',
    '--enable-decoder=ape',
    '--enable-decoder=aptx',
    '--enable-decoder=aptx_hd',
    '--enable-decoder=atrac1',
    '--enable-decoder=atrac3',
    '--enable-decoder=atrac3al',
    '--enable-decoder=atrac3p',
    '--enable-decoder=atrac3pal',
    '--enable-decoder=atrac9',
    '--enable-decoder=binkaudio_dct',
    '--enable-decoder=binkaudio_rdft',
    '--enable-decoder=bmv_audio',
    '--enable-decoder=bonk',
    '--enable-decoder=cook',
    '--enable-decoder=dfpwm',
    '--enable-decoder=dolby_e',
    '--enable-decoder=dsd_lsbf',
    '--enable-decoder=dsd_lsbf_planar',
    '--enable-decoder=dsd_msbf',
    '--enable-decoder=dsd_msbf_planar',
    '--enable-decoder=dsicinaudio',
    '--enable-decoder=dss_sp',
    '--enable-decoder=dst',
    '--enable-decoder=evrc',
    '--enable-decoder=fastaudio',
    '--enable-decoder=ffwavesynth',
    '--enable-decoder=ftr',
    '--enable-decoder=g723_1',
    '--enable-decoder=g729',
    '--enable-decoder=gsm',
    '--enable-decoder=gsm_ms',
    '--enable-decoder=hca',
    '--enable-decoder=hcom',
    '--enable-decoder=iac',
    '--enable-decoder=ilbc',
    '--enable-decoder=imc',
    '--enable-decoder=interplay_acm',
    '--enable-decoder=mace3',
    '--enable-decoder=mace6',
    '--enable-decoder=metasound',
    '--enable-decoder=misc4',
    '--enable-decoder=mp1',
    '--enable-decoder=mp1float',
    '--enable-decoder=mp2float',
    '--enable-decoder=mp3adu',
    '--enable-decoder=mp3adufloat',
    '--enable-decoder=mp3float',
    '--enable-decoder=mp3on4',
    '--enable-decoder=mp3on4float',
    '--enable-decoder=mpc7',
    '--enable-decoder=mpc8',
    '--enable-decoder=msnsiren',
    '--enable-decoder=nellymoser',
    '--enable-decoder=on2avc',
    '--enable-decoder=osq',
    '--enable-decoder=paf_audio',
    '--enable-decoder=qcelp',
    '--enable-decoder=qdm2',
    '--enable-decoder=qdmc',
    '--enable-decoder=qoa',
    '--enable-decoder=ra_144',
    '--enable-decoder=ra_288',
    '--enable-decoder=ralf',
    '--enable-decoder=sbc',
    '--enable-decoder=shorten',
    '--enable-decoder=sipr',
    '--enable-decoder=siren',
    '--enable-decoder=smackaud',
    '--enable-decoder=sonic',
    '--enable-decoder=tak',
    '--enable-decoder=truespeech',
    '--enable-decoder=tta',
    '--enable-decoder=twinvq',
    '--enable-decoder=vmdaudio',
    '--enable-decoder=wavarc',
    '--enable-decoder=wavpack',
    '--enable-decoder=wmalossless',
    '--enable-decoder=wmapro',
    '--enable-decoder=wmav1',
    '--enable-decoder=wmav2',
    '--enable-decoder=wmavoice',
    '--enable-decoder=ws_snd1',
    '--enable-decoder=xma1',
    '--enable-decoder=xma2',
    '--enable-decoder=pcm_alaw',
    '--enable-decoder=pcm_bluray',
    '--enable-decoder=pcm_dvd',
    '--enable-decoder=pcm_f16le',
    '--enable-decoder=pcm_f24le',
    '--enable-decoder=pcm_f32be',
    '--enable-decoder=pcm_f64be',
    '--enable-decoder=pcm_f64le',
    '--enable-decoder=pcm_lxf',
    '--enable-decoder=pcm_mulaw',
    '--enable-decoder=pcm_s16be_planar',
    '--enable-decoder=pcm_s16le_planar',
    '--enable-decoder=pcm_s24be',
    '--enable-decoder=pcm_s24daud',
    '--enable-decoder=pcm_s24le_planar',
    '--enable-decoder=pcm_s32be',
    '--enable-decoder=pcm_s32le',
    '--enable-decoder=pcm_s32le_planar',
    '--enable-decoder=pcm_s64be',
    '--enable-decoder=pcm_s64le',
    '--enable-decoder=pcm_s8',
    '--enable-decoder=pcm_s8_planar',
    '--enable-decoder=pcm_sga',
    '--enable-decoder=pcm_u16be',
    '--enable-decoder=pcm_u16le',
    '--enable-decoder=pcm_u24be',
    '--enable-decoder=pcm_u24le',
    '--enable-decoder=pcm_u32be',
    '--enable-decoder=pcm_u32le',
    '--enable-decoder=pcm_u8',
    '--enable-decoder=pcm_vidc',
    '--enable-decoder=adpcm_4xm',
    '--enable-decoder=adpcm_adx',
    '--enable-decoder=adpcm_afc',
    '--enable-decoder=adpcm_agm',
    '--enable-decoder=adpcm_aica',
    '--enable-decoder=adpcm_argo',
    '--enable-decoder=adpcm_ct',
    '--enable-decoder=adpcm_dtk',
    '--enable-decoder=adpcm_ea',
    '--enable-decoder=adpcm_ea_maxis_xa',
    '--enable-decoder=adpcm_ea_r1',
    '--enable-decoder=adpcm_ea_r2',
    '--enable-decoder=adpcm_ea_r3',
    '--enable-decoder=adpcm_ea_xas',
    '--enable-decoder=adpcm_g722',
    '--enable-decoder=adpcm_g726',
    '--enable-decoder=adpcm_g726le',
    '--enable-decoder=adpcm_ima_acorn',
    '--enable-decoder=adpcm_ima_alp',
    '--enable-decoder=adpcm_ima_amv',
    '--enable-decoder=adpcm_ima_apc',
    '--enable-decoder=adpcm_ima_apm',
    '--enable-decoder=adpcm_ima_cunning',
    '--enable-decoder=adpcm_ima_dat4',
    '--enable-decoder=adpcm_ima_dk3',
    '--enable-decoder=adpcm_ima_dk4',
    '--enable-decoder=adpcm_ima_ea_eacs',
    '--enable-decoder=adpcm_ima_ea_sead',
    '--enable-decoder=adpcm_ima_iss',
    '--enable-decoder=adpcm_ima_moflex',
    '--enable-decoder=adpcm_ima_mtf',
    '--enable-decoder=adpcm_ima_oki',
    '--enable-decoder=adpcm_ima_qt',
    '--enable-decoder=adpcm_ima_rad',
    '--enable-decoder=adpcm_ima_smjpeg',
    '--enable-decoder=adpcm_ima_ssi',
    '--enable-decoder=adpcm_ima_wav',
    '--enable-decoder=adpcm_ima_ws',
    '--enable-decoder=adpcm_ms',
    '--enable-decoder=adpcm_mtaf',
    '--enable-decoder=adpcm_psx',
    '--enable-decoder=adpcm_sbpro_2',
    '--enable-decoder=adpcm_sbpro_3',
    '--enable-decoder=adpcm_sbpro_4',
    '--enable-decoder=adpcm_swf',
    '--enable-decoder=adpcm_thp',
    '--enable-decoder=adpcm_thp_le',
    '--enable-decoder=adpcm_vima',
    '--enable-decoder=adpcm_xa',
    '--enable-decoder=adpcm_xmd',
    '--enable-decoder=adpcm_yamaha',
    '--enable-decoder=adpcm_zork',
    '--enable-decoder=cbd2_dpcm',
    '--enable-decoder=derf_dpcm',
    '--enable-decoder=gremlin_dpcm',
    '--enable-decoder=interplay_dpcm',
    '--enable-decoder=roq_dpcm',
    '--enable-decoder=sdx2_dpcm',
    '--enable-decoder=sol_dpcm',
    '--enable-decoder=wady_dpcm',
    '--enable-decoder=xan_dpcm',
    '--enable-decoder=vc1',
    '--enable-decoder=wmv1',
    '--enable-decoder=wmv2',
    '--enable-decoder=wmv3',
    '--enable-decoder=msmpeg4v1',
    '--enable-decoder=msmpeg4v2',
    '--enable-decoder=msmpeg4v3',
    '--enable-decoder=mpeg1video',
    '--enable-decoder=flv',
    '--enable-decoder=vp6',
    '--enable-decoder=vp6a',
    '--enable-decoder=vp6f',
    '--enable-decoder=h263',
    '--enable-decoder=h263i',
    '--enable-decoder=h263p',
    '--enable-decoder=msvideo1',
    '--enable-decoder=cinepak',
    '--enable-decoder=indeo3',
    '--enable-decoder=indeo4',
    '--enable-decoder=indeo5',
    '--enable-decoder=huffyuv',
    '--enable-decoder=ffv1',
    '--enable-decoder=utvideo',
    '--enable-decoder=qtrle',
    '--enable-decoder=rpza',
    '--enable-decoder=smc',
    '--enable-decoder=svq1',
    '--enable-decoder=svq3',
    '--enable-decoder=mjpegb',
    '--enable-decoder=theora',
    '--enable-decoder=prores',
    '--enable-decoder=dnxhd',
    '--enable-decoder=dvvideo',
    '--enable-decoder=cavs',
    '--enable-decoder=rv10',
    '--enable-decoder=rv20',
    '--enable-decoder=rv30',
    '--enable-decoder=rv40',
    '--enable-decoder=webp',
    '--enable-decoder=webvtt',
    '--enable-decoder=text',
    '--enable-decoder=microdvd',
    '--enable-decoder=sami',
    '--enable-decoder=subviewer',
    '--enable-decoder=subviewer1',
    '--enable-decoder=mpl2',
    '--enable-decoder=vplayer',
    '--enable-decoder=pjs',
    '--enable-decoder=jacosub',
    '--enable-decoder=realtext',
    '--enable-decoder=stl',
    '--enable-decoder=xsub',
    '--enable-decoder=ccaption',
    '--enable-decoder=h264',
    '--enable-decoder=hevc',
    '--enable-decoder=vp9',
    '--enable-decoder=vp8',
    '--enable-decoder=mpeg2video',
    '--enable-decoder=mpeg4',
    '--enable-decoder=subrip',
    '--enable-decoder=ass',
    '--enable-decoder=srt',
    '--enable-decoder=movtext',
    '--enable-decoder=pgssub',
    '--enable-decoder=dvdsub',
    '--enable-decoder=dvbsub',
    '--enable-decoder=mjpeg',
    '--enable-decoder=png',
    '--enable-demuxer=matroska',
    '--enable-demuxer=mov',
    '--enable-demuxer=mpegts',
    '--enable-demuxer=mpegps',
    '--enable-demuxer=avi',
    '--enable-demuxer=flac',
    '--enable-demuxer=mp3',
    '--enable-demuxer=ogg',
    '--enable-demuxer=wav',
    '--enable-demuxer=aac',
    '--enable-demuxer=ac3',
    '--enable-demuxer=eac3',
    '--enable-demuxer=dts',
    '--enable-demuxer=truehd',
    '--enable-demuxer=h264',
    '--enable-demuxer=hevc',
    '--enable-demuxer=srt',
    '--enable-demuxer=ass',
    '--enable-demuxer=image2',
    '--enable-demuxer=ivf',
    '--enable-demuxer=obu',
    '--enable-demuxer=av1',
    '--enable-bsf=av1_frame_merge',
    '--enable-demuxer=hls',
    '--enable-demuxer=dash',
    '--enable-libxml2',
    '--enable-demuxer=adx',
    '--enable-demuxer=aiff',
    '--enable-demuxer=amr',
    '--enable-demuxer=amrnb',
    '--enable-demuxer=amrwb',
    '--enable-demuxer=apac',
    '--enable-demuxer=ape',
    '--enable-demuxer=aptx',
    '--enable-demuxer=aptx_hd',
    '--enable-demuxer=argo_asf',
    '--enable-demuxer=asf',
    '--enable-demuxer=ast',
    '--enable-demuxer=au',
    '--enable-demuxer=bfstm',
    '--enable-demuxer=bonk',
    '--enable-demuxer=brstm',
    '--enable-demuxer=caf',
    '--enable-demuxer=codec2',
    '--enable-demuxer=dfpwm',
    '--enable-demuxer=dsf',
    '--enable-demuxer=dtshd',
    '--enable-demuxer=g723_1',
    '--enable-demuxer=g729',
    '--enable-demuxer=gsm',
    '--enable-demuxer=hca',
    '--enable-demuxer=hcom',
    '--enable-demuxer=iff',
    '--enable-demuxer=ilbc',
    '--enable-demuxer=ircam',
    '--enable-demuxer=mlp',
    '--enable-demuxer=mpc',
    '--enable-demuxer=mpc8',
    '--enable-demuxer=nistsphere',
    '--enable-demuxer=oma',
    '--enable-demuxer=osq',
    '--enable-demuxer=pcm_alaw',
    '--enable-demuxer=pcm_f32be',
    '--enable-demuxer=pcm_f32le',
    '--enable-demuxer=pcm_f64be',
    '--enable-demuxer=pcm_f64le',
    '--enable-demuxer=pcm_mulaw',
    '--enable-demuxer=pcm_s16be',
    '--enable-demuxer=pcm_s16le',
    '--enable-demuxer=pcm_s24be',
    '--enable-demuxer=pcm_s24le',
    '--enable-demuxer=pcm_s32be',
    '--enable-demuxer=pcm_s32le',
    '--enable-demuxer=pcm_s8',
    '--enable-demuxer=pcm_u16be',
    '--enable-demuxer=pcm_u16le',
    '--enable-demuxer=pcm_u24be',
    '--enable-demuxer=pcm_u24le',
    '--enable-demuxer=pcm_u32be',
    '--enable-demuxer=pcm_u32le',
    '--enable-demuxer=pcm_u8',
    '--enable-demuxer=pcm_vidc',
    '--enable-demuxer=pvf',
    '--enable-demuxer=qoa',
    '--enable-demuxer=rso',
    '--enable-demuxer=rm',
    '--enable-demuxer=sbc',
    '--enable-demuxer=shorten',
    '--enable-demuxer=sln',
    '--enable-demuxer=sox',
    '--enable-demuxer=spdif',
    '--enable-demuxer=tak',
    '--enable-demuxer=tta',
    '--enable-demuxer=voc',
    '--enable-demuxer=vqf',
    '--enable-demuxer=w64',
    '--enable-demuxer=wavarc',
    '--enable-demuxer=wv',
    '--enable-demuxer=wve',
    '--enable-demuxer=xa',
    '--enable-demuxer=xwma',
    '--enable-demuxer=asf',
    '--enable-demuxer=asf_o',
    '--enable-demuxer=flv',
    '--enable-demuxer=live_flv',
    '--enable-demuxer=rm',
    '--enable-demuxer=dv',
    '--enable-demuxer=mxf',
    '--enable-demuxer=webvtt',
    '--enable-demuxer=microdvd',
    '--enable-demuxer=sami',
    '--enable-demuxer=subviewer',
    '--enable-demuxer=subviewer1',
    '--enable-demuxer=mpl2',
    '--enable-demuxer=vplayer',
    '--enable-demuxer=pjs',
    '--enable-demuxer=jacosub',
    '--enable-demuxer=realtext',
    '--enable-demuxer=stl',
    '--enable-demuxer=vc1',
    '--enable-demuxer=vc1t',
    '--enable-demuxer=m4v',
    '--enable-demuxer=ivf',
    '--enable-demuxer=mpegvideo',
    '--enable-parser=h264',
    '--enable-parser=hevc',
    '--enable-parser=vp9',
    '--enable-parser=av1',
    '--enable-parser=aac',
    '--enable-parser=aac_latm',
    '--enable-parser=ac3',
    '--enable-parser=dca',
    '--enable-parser=mlp',
    '--enable-parser=flac',
    '--enable-parser=opus',
    '--enable-parser=vorbis',
    '--enable-parser=mpegaudio',
    '--enable-parser=mpegvideo',
    '--enable-parser=mpeg4video',
    '--enable-parser=adx',
    '--enable-parser=amr',
    '--enable-parser=cook',
    '--enable-parser=dolby_e',
    '--enable-parser=dvaudio',
    '--enable-parser=ftr',
    '--enable-parser=g723_1',
    '--enable-parser=g729',
    '--enable-parser=gsm',
    '--enable-parser=misc4',
    '--enable-parser=sbc',
    '--enable-parser=sipr',
    '--enable-parser=tak',
    '--enable-parser=xma',
    '--enable-parser=vc1',
    '--enable-parser=h263',
    '--enable-parser=webp',
    '--enable-bsf=h264_mp4toannexb',
    '--enable-bsf=hevc_mp4toannexb',
    '--enable-bsf=extract_extradata',
    '--enable-bsf=aac_adtstoasc',
    '--enable-bsf=vp9_superframe',
    '--enable-filter=aformat',
    '--enable-filter=aresample',
    '--enable-filter=anull',
    '--enable-filter=format',
    '--enable-filter=scale',
    '--enable-filter=null',
    '--enable-protocol=file',
    '--enable-protocol=pipe',
    '--enable-protocol=http',
    '--enable-protocol=https',
    '--enable-protocol=tcp',
    '--enable-protocol=tls',
    '--enable-protocol=ftp',
    '--enable-protocol=crypto',
)


def install_ffmpeg(sdk):
    """Build the pinned FFmpeg over the sysroot homebrew prefix (cached)."""
    pin, archive = fetch('ffmpeg-source')
    config_id = hashlib.sha256('\n'.join([pin['sha256'], *FFMPEG_FLAGS]).encode()).hexdigest()[:16]
    cached = CACHE / ('ffmpeg-' + config_id)
    stamp = {'source_sha256': pin['sha256'], 'config_id': config_id, 'directory': pin['directory']}
    stamp_file = cached / 'stamp.json'
    if stamp_file.is_file() and json.loads(stamp_file.read_text()) == stamp:
        shutil.copytree(cached / 'homebrew', sdk / 'target/user/homebrew', dirs_exist_ok=True)
        print('FFmpeg', pin['directory'], 'installed from cache')
        return
    src = WORK / pin['directory']
    if src.exists():
        shutil.rmtree(src)
    with tarfile.open(archive) as t:
        t.extractall(WORK, filter='data')
    stage = WORK / 'ffmpeg-stage'
    if stage.exists():
        shutil.rmtree(stage)
    env = os.environ.copy()
    llvm = subprocess.check_output(['brew', '--prefix', 'llvm'], text=True).strip()
    core = subprocess.check_output(['brew', '--prefix', 'coreutils'], text=True).strip()
    env.update(PS5_PAYLOAD_SDK=str(sdk),
               PATH=os.pathsep.join([str(sdk / 'bin'), llvm + '/bin', core + '/libexec/gnubin', env['PATH']]))

    def logged(args, name, **kwargs):
        log = WORK / ('ffmpeg-' + name + '.log')
        with log.open('w') as f:
            proc = subprocess.run([str(a) for a in args], stdout=f, stderr=subprocess.STDOUT, **kwargs)
        if proc.returncode != 0:
            raise RuntimeError('FFmpeg ' + name + ' failed; tail of ' + str(log) + ':\n' + log.read_text()[-2000:])

    print('Building FFmpeg', pin['directory'], '(first build is slow; cached afterwards)')
    flags = [flag.format(sdk=sdk) for flag in FFMPEG_FLAGS]
    logged([src / 'configure', '--prefix=/user/homebrew', *flags], 'configure', cwd=src, env=env)
    logged(['make', '-j' + str(os.cpu_count() or 4)], 'build', cwd=src, env=env)
    logged(['make', 'install', 'DESTDIR=' + str(stage)], 'install', cwd=src, env=env)
    for lib in ('libavcodec.a', 'libavformat.a', 'libavutil.a', 'libswresample.a', 'libswscale.a'):
        if not (stage / 'user/homebrew/lib' / lib).is_file():
            raise RuntimeError('FFmpeg did not produce ' + lib)
    tmp = cached.with_name(cached.name + '.staging')
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(stage / 'user/homebrew', tmp / 'homebrew')
    (tmp / 'stamp.json').write_text(json.dumps(stamp, indent=2) + '\n')
    if cached.exists():
        shutil.rmtree(cached)
    tmp.rename(cached)
    shutil.copytree(cached / 'homebrew', sdk / 'target/user/homebrew', dirs_exist_ok=True)
    print('FFmpeg', pin['directory'], 'built and installed over the sysroot')


def provide_hui(evo):
    """Install the pinned EVO UI kit where the Makefile expects its submodule.

    EVO v0.12.0 records third_party/ps5-homebrew-ui as a git submodule, and a
    pinned codeload archive contains only the empty directory. The adapter
    unpacks the kit's own pinned archive instead (see deps.lock)."""
    pin, archive = fetch('ps5-homebrew-ui-source')
    dest = evo / 'third_party/ps5-homebrew-ui'
    if dest.exists():
        shutil.rmtree(dest)
    with tarfile.open(archive) as t:
        t.extractall(evo / 'third_party', filter='data')
    (evo / 'third_party' / pin['directory']).rename(dest)
    for rel in ('src/gfx/draw_list.cpp', 'src/gfx/font.cpp', 'src/gfx/triangulate.cpp',
                'src/audio/cues.cpp', 'src/audio/mixer.cpp', 'src/audio/wav.cpp'):
        if not (dest / rel).is_file():
            raise RuntimeError('ps5-homebrew-ui is missing ' + rel + ' - layout changed')
    for sub in ('src/ui', 'src/ui/components', 'src/core'):
        if not any((dest / sub).glob('*.cpp')):
            raise RuntimeError('ps5-homebrew-ui has no sources under ' + sub)


def fix_network_reader(text):
    """Keep provider range reads on FFmpeg's bounded single-connection reader."""
    start = text.index('    /*\n     * A big file over HTTP is fetched by several connections at once.')
    end = text.index('    int rc = avformat_open_input', start)
    block = text[start:end]
    if block.count('ctx->pio = evo_pio_open(') != 1 or block.count('AVFMT_FLAG_CUSTOM_IO') != 1:
        raise RuntimeError('Pinned parallel reader block changed')
    text = text[:start] + '''    /* Six range readers caused HTTP429 storms after provider seeks (#4).
     * Use FFmpeg's reader: one connection, provider headers, range seeks and
     * the bounded retry policy below. The custom reader bypassed that policy. */
    if (ctx->is_network)
        SIO_BC("P8_01d1_HTTP_READER", "single connection");

''' + text[end:]
    anchor = '    av_dict_set(opts, "reconnect_delay_max", "2", 0);'
    if text.count(anchor) != 1:
        raise RuntimeError('Pinned network retry policy changed')
    return text.replace(anchor, anchor + '\n'
        '    av_dict_set(opts, "reconnect_on_http_error", "429,503", 0);\n'
        '    av_dict_set(opts, "respect_retry_after", "1", 0);')


def fix_provider_seek(demux, controller):
    # EVO v0.12.0 handles provider seeks itself: the demuxer guard does not
    # require a local media path, and the controller resumes instead of
    # announcing a refused seek (hardware sessions, 2026-10-01). Verify the
    # pinned forms and leave both sources unchanged.
    guard = '(video_stream_index < 0 && audio_stream_index < 0)\n    ) {'
    if demux.count(guard) != 1:
        raise RuntimeError('Pinned provider seek guard changed')
    refused = '    if (!prospero_request_inplace_seek(targetSeconds, 0)) {'
    handled = '        return;\n    }\n    pp_playback_notify_seek_begin(&g_pp_pb, targetUs);'
    if controller.count(refused) != 1 or controller.count(handled) != 1:
        raise RuntimeError('Pinned provider seek controller changed')
    return demux, controller


def instrument_loopback_server(source):
    """Log proxy socket, bind, listen and browser accept as separate results."""
    replacements = (
        ('    int fd = socket(AF_INET, SOCK_STREAM, 0);\n'
         '    if (fd < 0) { LOG("server: socket errno=%d", errno); return; }',
         '    int fd = socket(AF_INET, SOCK_STREAM, 0);\n'
         '    if (fd < 0) { LOG("server: socket failed errno=%d", errno); return; }\n'
         '    LOG("server: socket ok fd=%d", fd);'),
        ('    if (bind(fd, (struct sockaddr *)&a, sizeof a) != 0 || listen(fd, 16) != 0) {\n'
         '        LOG("server: bind/listen 127.0.0.1:%d failed errno=%d", s_port, errno);\n'
         '        close(fd);\n'
         '        return;\n'
         '    }',
         '    if (bind(fd, (struct sockaddr *)&a, sizeof a) != 0) {\n'
         '        int error = errno;\n'
         '        LOG("server: bind failed port=%d errno=%d", s_port, error);\n'
         '        close(fd);\n'
         '        return;\n'
         '    }\n'
         '    LOG("server: bind ok 127.0.0.1:%d", s_port);\n'
         '    if (listen(fd, 16) != 0) {\n'
         '        int error = errno;\n'
         '        LOG("server: listen failed port=%d errno=%d", s_port, error);\n'
         '        close(fd);\n'
         '        return;\n'
         '    }\n'
         '    LOG("server: listen ok port=%d", s_port);'),
        ('        int c = accept(s_listen_fd, NULL, NULL);\n'
         '        if (c >= 0 && s_srv_stop) { close(c); break; }',
         '        int c = accept(s_listen_fd, NULL, NULL);\n'
         '        if (c >= 0 && s_srv_stop) { close(c); break; }\n'
         '        if (c >= 0) LOG("server: connection accepted");'),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise RuntimeError('Pinned EVO loopback server anchor changed')
        source = source.replace(old, new)
    return source


def bypass_loopback_origin_preflight(source):
    """Open EVO's browser so it can probe the local proxy without its UI server."""
    old = '''        if (s_check_rc < 0) {
            char m[256];
'''
    # adapt() inserts this only for a diagnostic build. A preprocessor guard
    # would also need a compiler definition; the earlier guard had none and
    # silently left the missing-server preflight active.
    new = '''        if (s_check_rc < 0) {
            LOG("preflight bypassed for unpromoted loopback diagnostic");
            s_check_rc = 1;
        }
        if (s_check_rc < 0) {
            char m[256];
'''
    if source.count(old) != 1:
        raise RuntimeError('Pinned EVO preflight anchor changed')
    return source.replace(old, new)


def title_ui_sources(web, provider):
    """Serve the packaged page on EVO's existing listener for the Nuvio profile."""
    replacements = (
        ('#include "evo_webui.h"', '#include "evo_webui.h"\n#include "local_ui.h"'),
        ('        else\n            proxy_request(fd, req, got, hl, method, path);',
         '''        else if (!strcmp(s_hook_profile, "nuvio")) {
            char tag[96];
            size_t tag_len = is_html_entry(path) ? hook_tag(tag, sizeof tag) : 0;
            int status = nuvio_local_ui_send(fd,
                "/data/homebrew/PPSA99997/webui", method, path, tag, tag_len);
            LOG("title-ui: response status=%d", status);
        } else
            proxy_request(fd, req, got, hl, method, path);'''),
        ('    s_check_rc = 0;\n    pthread_t t;',
         '''    /* Packaged Nuvio files need no second HTTP process. Keep the
     * configured origin as the browser-storage key for existing profiles. */
    if (!strcmp(s_hook_profile, "nuvio")) {
        s_check_rc = 1;
        s_state = P_CHECK;
        s_frames = 0;
        LOG("title-ui: packaged assets selected");
        return 0;
    }
    s_check_rc = 0;
    pthread_t t;'''),
    )
    for old, new in replacements:
        if web.count(old) != 1:
            raise RuntimeError('Pinned title-local UI anchor changed')
        web = web.replace(old, new)
    # Fresh installations must be configured before any external helper runs.
    old = "    g_host[0] = '\\0';\n    g_port = NUVIO_DEFAULT_PORT;"
    if provider.count(old) != 1:
        raise RuntimeError('Pinned Nuvio provider initialization changed')
    provider = provider.replace(old, '    snprintf(g_host, sizeof g_host, "127.0.0.1");\n    g_port = 4173;')
    return web, provider


def adapt(evo, loopback_diagnostic=False, title_ui=False, auto_bootstrap=False):
    """Keep the native player; open its existing Nuvio bridge at startup."""
    app = evo/'projects/evoplayer'
    param_path = app/'sce_sys/param.json'
    # The published title identity and content version live in one file so the
    # store catalog can read them from a release tag.
    identity = json.loads((ROOT/'sce_sys/param.json').read_text())
    if identity['titleId'] != TITLE:
        raise RuntimeError('sce_sys/param.json titleId does not match '+TITLE)
    param = json.loads(param_path.read_text())
    param['titleId'] = identity['titleId']
    param['conceptId'] = identity['conceptId']
    param['contentId'] = identity['contentId']
    param['contentVersion'] = identity['contentVersion']
    param['localizedParameters']['en-US']['titleName'] = identity['localizedParameters']['en-US']['titleName']
    param_path.write_text(json.dumps(param, indent=2)+'\n')
    # Separate settings from an installed EVO. All persistent writes stay /data.
    for p in app.rglob('*'):
        if p.suffix in ('.c', '.h', '.cpp', '.hpp'):
            s = p.read_text()
            if '/data/evoplayer' in s or '/download0/evoplayer' in s:
                p.write_text(s.replace('/data/evoplayer', '/data/nuvio').replace('/download0/evoplayer', '/download0/nuvio'))
    replace_once(app/'core/src/Application.cpp',
                 '        evo_webui_pump();   /* #101: the system browser, when a web UI is open */',
                 '''        /* Nuvio starts once its durable settings are reachable. Existing
         * EVO code owns browser, playback handoff and shutdown lifetimes. */
        static bool nuvio_opened = false;
        if (!nuvio_opened && evo_jailbreak_is_open()) {
            const evo_provider_t *nv = evo_provider_find("nuvio");
            if (nv && nv->is_configured() &&
                evo_webui_open_ex(nv->web_ui_url(), "/", "nuvio") == 0)
                nuvio_opened = true;
        }
        evo_webui_pump();   /* #101: the system browser, when a web UI is open */''')
    replace_once(app/'src/evo_webui.c',
                 '2, 108,  0, 1812, 1080, 0x0, 0x0',
                 '2,   0,  0, 1920, 1080, 0x0, 0x0')
    web = app/'src/evo_webui.c'
    web_source = instrument_loopback_server(web.read_text())
    if loopback_diagnostic:
        web_source = bypass_loopback_origin_preflight(web_source)
    if title_ui:
        provider = app/'addons/src/provider_nuvio.c'
        web_source, provider_source = title_ui_sources(web_source, provider.read_text())
        provider.write_text(provider_source)
        for name in ('local_ui.c', 'local_ui.h'):
            shutil.copyfile(ROOT/'scripts'/name, app/'src'/name)
        # Reuse the payload server's path and MIME helpers. Its listener is
        # never called by the title; requests use EVO's existing connection.
        shutil.copyfile(ROOT/'scripts/ui_server.c', app/'src/nuvio_ui_files.c')
        replace_once(app/'Makefile',
                     'C_SRCS := $(PP_SRCS) $(UI_SRCS) $(MEDIA_SRCS) $(ADDON_SRCS)',
                     'C_SRCS := $(PP_SRCS) $(UI_SRCS) $(MEDIA_SRCS) $(ADDON_SRCS) src/local_ui.c src/nuvio_ui_files.c')
    if auto_bootstrap:
        web_source = web_source.replace('#include "evo_webui.h"', '#include "evo_webui.h"\n#include "bootstrap.h"')
        anchor = '    if (s_listen_fd >= 0) return;\n    int fd = socket(AF_INET, SOCK_STREAM, 0);'
        if web_source.count(anchor) != 1:
            raise RuntimeError('Pinned server bootstrap anchor changed')
        web_source = web_source.replace(anchor, '''    if (s_listen_fd >= 0) return;
    if (!strcmp(s_hook_profile, "nuvio")) {
        LOG("bootstrap: promotion requested");
        int rc = nuvio_bootstrap();
        if (rc == 0) LOG("bootstrap: promotion verified errno=0");
        else LOG("bootstrap: promotion failed stage=%s errno=%d", nuvio_bootstrap_stage(), errno);
        if (rc != 0) return;
    }
    int fd = socket(AF_INET, SOCK_STREAM, 0);''')
        for name in ('bootstrap.c', 'bootstrap.h'):
            shutil.copyfile(ROOT/'scripts'/name, app/'src'/name)
        replace_once(app/'Makefile', 'src/local_ui.c src/nuvio_ui_files.c',
                     'src/local_ui.c src/nuvio_ui_files.c src/bootstrap.c')
    web.write_text(web_source)
    # Provider sources intentionally have no local path. Check the demuxer,
    # and never announce an unqueued seek to the playback state machine.
    demux = app/'media/src/evo_demux.c'
    controller = app/'core/src/services/PlaybackController.cpp'
    fixed = fix_provider_seek(demux.read_text(), controller.read_text())
    demux.write_text(fixed[0]); controller.write_text(fixed[1])
    stream_io = app/'media/src/evo_stream_io.c'
    stream_io.write_text(fix_network_reader(stream_io.read_text()))
    # Keep diagnostics available without a USB stick on this console.
    replace_once(app/'src/evo_boot_log.c', '"/mnt/usb0/evo.log"', '"/data/nuvio/evo.log"')
    # Omit the unused AV1 add-on archive from the baseline pacbrew build.
    # No stub decoder is substituted; FFmpeg's available decoders are unchanged.
    script = evo/'scripts/package-app.sh'
    s = script.read_text()
    start = s.index('    # Auto-install libdav1d into sysroot if missing')
    end = s.index('    # Static archives EVO links', start)
    s = s[:start]+s[end:]
    s = s.replace('libswscale libdav1d \\', 'libswscale \\')
    # The host converter can link macOS's zlib SDK stub. No console libc change.
    s = s.replace('eval "$("${SCRIPTS_DIR}/setup-native-app-deps.sh")"',
                  'ZLIB_INCLUDE="${NUVIO_MAC_SDK}/usr/include"\nZLIB_ARCHIVE="${NUVIO_MAC_SDK}/usr/lib/libz.tbd"')
    s = s.replace('clang++ -std=c++20', '/usr/bin/clang++ -std=c++20')
    s = s.replace('-I "${ZLIB_INCLUDE}"', '')
    s = '\n'.join('echo "Installable inventory is recorded in build.json."'
                  if line.startswith('find "${APPDIR}" -type f -printf') else line
                  for line in s.splitlines()) + '\n'
    s = s.replace('BUILD_SHA="$(git -C "${EVO}" rev-parse --short=8 HEAD 2>/dev/null || echo unknown)"',
                  'BUILD_SHA="'+fetch('evo-player-nuvio-source')[0]['commit'][:8]+'-nuvio"')
    script.write_text(s)


def patch_index(html):
    """Add the PS5 input bridge and a black first paint to Nuvio's index page.

    The PS5 browser paints its own document background before the Nuvio CSS
    applies. The white default flashes the whole screen when the browser
    reopens after playback, so the served page must be black from the first
    byte of <head>.

    The stylesheet stays a plain render-blocking <link>. A `media="print"`
    link switched to `all` on load paints earlier, but the console's browser
    then renders Nuvio unstyled, so the pattern is not usable here.
    """
    if html.count('<head>') != 1 or html.count('</head>') != 1:
        raise RuntimeError('Pinned UI index head anchors changed')
    if 'ps5-input.js' in html:
        raise RuntimeError('UI index already carries the PS5 bridge')
    html = html.replace('<head>',
                        '<head>\n    <style>html,body{background-color:#000;margin:0}</style>')
    return html.replace('</head>', '<script src="ps5-input.js"></script></head>')


def configure_ui(ui):
    # Official release ships the publishable browser key; never use a privileged
    # Supabase service key or copy unrelated release client settings into Git.
    _, package = fetch('nuvio-official-tv-config')
    with zipfile.ZipFile(package) as z:
        raw = z.read('nuvio.env.js').decode()
    match = re.search(r'var values = (\{.*?\});', raw, re.S)
    if not match:
        raise RuntimeError('Pinned public runtime config changed')
    official = json.loads(match[1])
    key = official.get('NUVIO_SUPABASE_ANON_KEY', '')
    if not key.startswith('sb_publishable_'):
        parts = key.split('.')
        if len(parts) != 3 or json.loads(base64.urlsafe_b64decode(parts[1]+'='*(-len(parts[1])%4))).get('role') != 'anon':
            raise RuntimeError('Release does not contain an anonymous publishable key')
    path = ui/'nuvio.env.js'
    source = path.read_text()
    for name in ('NUVIO_SUPABASE_URL', 'NUVIO_SUPABASE_ANON_KEY',
                 'NUVIO_SUPABASE_FALLBACK_URL', 'TV_LOGIN_WEB_BASE_URL',
                 'DEVICE_LOGIN_WEB_BASE_URL', 'AVATAR_PUBLIC_BASE_URL'):
        value = official.get(name, '')
        if name != 'NUVIO_SUPABASE_ANON_KEY' and value and not value.startswith('https://'):
            raise RuntimeError('Official public configuration must use HTTPS')
        source, count = re.subn(r'"'+name+r'":\s*"[^"\n]*"', lambda m: json.dumps(name)+': '+json.dumps(value), source)
        if count != 1:
            raise RuntimeError('Pinned UI runtime config anchor changed')
    path.write_text(source)
    shutil.copyfile(ROOT/'scripts/ps5-input.js', ui/'ps5-input.js')
    index = ui/'index.html'
    index.write_text(patch_index(index.read_text()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ui-only', action='store_true')
    ap.add_argument('--auto-bootstrap', type=int, metavar='LOADER_PORT',
                    help='Embed promotion helper and submit it to the specified loopback loader port')
    ap.add_argument('--auth-profile', choices=('default', 'sdk-install-app'), default='default',
                    help='Signing metadata for a controlled permission test')
    ap.add_argument('--title-ui', action='store_true',
                    help='Serve packaged UI files inside the title for a single-install test')
    args = ap.parse_args()
    if args.auto_bootstrap is not None and (not args.title_ui or not 1 <= args.auto_bootstrap <= 65535):
        ap.error('--auto-bootstrap requires --title-ui and a valid loader port')
    loopback_diagnostic = os.environ.get('NUVIO_UNPROMOTED_LOOPBACK_DIAGNOSTIC') == '1'
    CACHE.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    nv = source('nuvio-tv-source')
    polish.patch_nuvio(nv)
    run(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=nv)
    run(['npm', 'run', 'build'], cwd=nv)
    ui = WORK/'ui'
    shutil.copytree(nv/'dist', ui, dirs_exist_ok=True)
    configure_ui(ui)
    if args.ui_only:
        print('Host UI built:', ui)
        return
    if os.uname().sysname != 'Darwin':
        raise RuntimeError('This native host adapter currently requires macOS.')
    if not lld_available():
        raise RuntimeError('ld.lld not found. Install LLVM and the lld formula: brew install llvm lld')
    sdk = WORK/'sdk/ps5-payload-sdk'
    _, sdk_zip = fetch('ps5-payload-sdk-prebuilt')
    with zipfile.ZipFile(sdk_zip) as z:
        z.extractall(WORK/'sdk')
    _, ports = fetch('nuvio-pacbrew')
    with tarfile.open(ports) as t:
        prefix = 'opt/ps5-payload-sdk/target/user/homebrew/'
        t.extractall(WORK/'ports', members=[m for m in t.getmembers() if m.name.startswith(prefix)], filter='data')
    shutil.copytree(WORK/'ports/opt/ps5-payload-sdk/target/user/homebrew', sdk/'target/user/homebrew', dirs_exist_ok=True)
    # v0.43's ZIP does not preserve executable permissions for all host wrappers.
    for p in (sdk/'bin').iterdir():
        if p.is_file():
            p.chmod(p.stat().st_mode | 0o111)
    install_ffmpeg(sdk)
    evo = source('evo-player-nuvio-source')
    provide_hui(evo)
    adapt(evo, loopback_diagnostic=loopback_diagnostic, title_ui=args.title_ui, auto_bootstrap=args.auto_bootstrap is not None)
    polish.apply(evo, nv)
    patches.write_patch(fetch('evo-player-nuvio-source')[1], evo, ROOT/'patches/evo.patch')
    patches.write_patch(fetch('nuvio-tv-source')[1], nv, ROOT/'patches/nuvio.patch')
    env = os.environ.copy()
    llvm = subprocess.check_output(['brew', '--prefix', 'llvm'], text=True).strip()
    core = subprocess.check_output(['brew', '--prefix', 'coreutils'], text=True).strip()
    env.update(PS5_PAYLOAD_SDK=str(sdk), LLVM_CONFIG=llvm+'/bin/llvm-config',
               PS5_LLD=shutil.which('ld.lld') or '',
               NUVIO_MAC_SDK=subprocess.check_output(['xcrun', '--show-sdk-path'], text=True).strip())
    env['PATH'] = ':'.join([core+'/libexec/gnubin', llvm+'/bin', str(sdk/'bin'), env['PATH']])
    bootstrap_metadata = None
    if args.auto_bootstrap is not None:
        payload = WORK/'bootstrap-promote.elf'
        run([sdk/'bin/prospero-clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
             ROOT/'scripts/promote.c', '-lkernel_sys', '-lkernel_web', '-o', payload], env=env)
        import elfcheck
        elfcheck.validate(str(payload))
        raw = payload.read_bytes()
        if len(raw) > 1048576:
            raise RuntimeError('Bootstrap ELF exceeds the transfer bound')
        blob = evo/'projects/evoplayer/src/nuvio_bootstrap_blob.h'
        blob.write_text('#define NUVIO_BOOTSTRAP_PORT '+str(args.auto_bootstrap)+'\n'+
                        'static const unsigned char nuvio_bootstrap_elf[] = {\n'+
                        ',\n'.join(','.join('0x'+raw[i:i+16][j:j+1].hex() for j in range(len(raw[i:i+16])))
                                    for i in range(0,len(raw),16))+'\n};\n')
        bootstrap_metadata = {'loader_port': args.auto_bootstrap, 'payload_sha256': digest(payload),
                              'payload_bytes': len(raw)}
    # The app link expands "${PS5_SYSROOT}/lib"/*.so and relies on libkernel.so
    # coming before libkernel_web.so: with --as-needed the first stub that
    # satisfies a symbol is the one recorded in DT_NEEDED, and the module
    # imports exactly that library. A UTF-8 collation puts libkernel.so last,
    # so the title imported libkernel_web.prx and never started on the console.
    # C collation restores libkernel.prx. Do not remove this.
    env['LC_ALL'] = 'C'
    run(['bash', evo/'scripts/package-app.sh'], cwd=evo, env=env)
    auth_profile = None
    if args.auth_profile == 'sdk-install-app':
        # This is metadata from a pinned public example, not inferred capability
        # bits. Hardware must establish whether the resident HEN honours it.
        profile_source = sdk/'samples/install_app/Makefile'
        auth_profile = sdk_install_auth_profile(profile_source.read_text())
        tool = evo/'output/app/.build/host/ps5-native-tool'
        run([tool, 'self', '--sign', '--in', evo/'output/app/.build/eboot.elf',
             '--out', evo/'output/app'/TITLE/'eboot.bin', '--magic', '0x1D3D154F',
             '--authority', auth_profile['authority'], '--auth-info', auth_profile['auth_info']])
        run([tool, 'self', '--inspect', '--file', evo/'output/app'/TITLE/'eboot.bin'])
        auth_profile = {**auth_profile, 'source': 'SDK samples/install_app/Makefile',
                        'source_sha256': digest(profile_source)}
    # Reuse the reviewed, fixed-purpose controls with Nuvio's own identity.
    control = (ROOT/'vendor/control.c').read_text().replace('AURORA', 'NUVIO').replace('Aurora', 'Nuvio').replace('aurora', 'nuvio').replace('PPSA99998', TITLE)
    control = control.replace('../../payloads/common/sha256.h', str(ROOT/'vendor/sha256.h'))
    (WORK/'control.c').write_text(control)
    for action in (1, 2, 3, 4, 5):
        inputs = [WORK/'control.c'] + ([ROOT/'vendor/sha256.c'] if action in (4, 5) else [])
        run([sdk/'bin/prospero-clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
             '-DNUVIO_CONTROL_ACTION='+str(action), *inputs, '-lkernel_sys', '-lkernel_web',
             '-lSceUserService', '-lSceSystemService', '-o', WORK/('control-'+str(action)+'.elf')], env=env)
    run([sdk/'bin/prospero-clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
         ROOT/'scripts/close.c', '-lkernel_sys', '-lkernel_web', '-o', WORK/'close.elf'], env=env)
    run([sdk/'bin/prospero-clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
         ROOT/'scripts/promote.c', '-lkernel_sys', '-lkernel_web',
         '-o', WORK/'promote.elf'], env=env)
    # One boot payload: it grants the title its network privilege and serves the
    # browser UI from the installed title folder (scripts/ui_server.c). That is
    # why no computer has to run an HTTP server on the same network.
    run([sdk/'bin/prospero-clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
         '-DNUVIO_WATCH', ROOT/'scripts/promote.c', ROOT/'scripts/ui_server.c',
         '-lkernel_sys', '-lkernel_web', '-o', WORK/'nuvio.elf'], env=env)
    dist = evo/'output/app'/TITLE
    (dist/'portable.txt').touch()
    # The UI travels inside the title folder, so one archive installs a working
    # app and the payload serves it over loopback with no LAN origin.
    shutil.rmtree(dist/'webui', ignore_errors=True)
    shutil.copytree(WORK/'ui', dist/'webui')
    receipt = {'title_id': TITLE, 'firmware_validation': '[UNKNOWN]',
               'ui_hosting': 'title' if args.title_ui else 'boot-payload',
               'automatic_bootstrap': bootstrap_metadata, 'auth_profile': args.auth_profile, 'auth_profile_metadata': auth_profile,
               'diagnostic_mode': 'unpromoted_loopback' if loopback_diagnostic else None,
               # Explicit names, not a glob: a stale helper from an earlier
               # build in the same work directory must not enter the receipt.
               'helpers': {name: digest(WORK/name) for name in (
                   'control-1.elf', 'control-2.elf', 'control-3.elf', 'control-4.elf', 'control-5.elf',
                   'promote.elf', 'nuvio.elf', 'close.elf')},
               'source_pins': {k: fetch(k)[0]['sha256'] for k in ('nuvio-tv-source','evo-player-nuvio-source','nuvio-pacbrew','ps5-payload-sdk-prebuilt','nuvio-official-tv-config','ffmpeg-source','ps5-homebrew-ui-source')},
               'files': {str(p.relative_to(dist)): digest(p) for p in dist.rglob('*') if p.is_file()}}
    (WORK/'build.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('Native title:', dist, '\nReceipt:', WORK/'build.json')


if __name__ == '__main__':
    main()
