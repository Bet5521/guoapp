import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from build_mirrors import china_mirror_environment, mirrored_pub_lockfile
from app_build import BuildVariant, add_variant_argument

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--cn-mirrors', action='store_true', help='使用 Flutter 中国镜像')
add_variant_argument(parser)
options = parser.parse_args()
variant = BuildVariant(options.all_sources)
environment = os.environ.copy()
environment.setdefault('GOPROXY', 'https://goproxy.cn,direct')
environment.setdefault('GOSUMDB', 'off')
flutter = shutil.which('flutter')
if not flutter:
    raise SystemExit('请先将 Flutter SDK 的 bin 目录加入 PATH。')
with china_mirror_environment(environment, options.cn_mirrors, gradle=False) as env:
    with mirrored_pub_lockfile(root, env):
        subprocess.run([sys.executable, str(root / 'scripts' / 'build_native.py'), '--platform', 'windows', *variant.arguments],
                       cwd=root, env=env, check=True)
        # 不用 --enforce-lockfile：提交的 pubspec.lock 在 Windows 平台上无法严格满足
        # pubspec.yaml（含 Windows 专属 path 依赖 media_kit_libs_windows_video 等），
        # 强制校验会直接失败（退出码 65）。与 build_android.py 保持一致，由 pub get 自行
        # 解析/刷新锁文件，避免跨平台锁文件不一致导致 CI 失败。
        subprocess.run([flutter, 'pub', 'get'], cwd=root, env=env, check=True)
        subprocess.run([flutter, 'build', 'windows', '--release', '--no-pub', *variant.flutter_arguments], cwd=root, env=env, check=True)
        subprocess.run([sys.executable, str(root / 'scripts' / 'package_release.py'), '--platform', 'windows', *variant.arguments],
                       cwd=root, env=env, check=True)
