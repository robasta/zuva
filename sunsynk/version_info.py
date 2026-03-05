import os
import platform
import subprocess
import sys
import re

VERSION_FILENAME = os.path.abspath(os.path.join(os.path.dirname(__file__), 'version.py'))


class Version:
    @staticmethod
    def _normalize_version(value: str | None) -> str | None:
        if not value:
            return None

        candidate = value.strip()
        if not candidate:
            return None

        if candidate.startswith('v') and len(candidate) > 1:
            candidate = candidate[1:]

        if re.fullmatch(r'\d+(\.\d+)*', candidate):
            return candidate

        safe_local = re.sub(r'[^A-Za-z0-9]+', '.', candidate).strip('.')
        if not safe_local:
            return None
        return f'0.0.0+{safe_local}'

    @staticmethod
    def _read_existing_version() -> str | None:
        try:
            with open(VERSION_FILENAME, 'r', encoding='utf-8') as file:
                content = file.read()
            match = re.search(r'SUNSYNK_API_CLIENT_VERSION\s*=\s*"([^"]+)"', content)
            if match and match.group(1).strip():
                return Version._normalize_version(match.group(1).strip())
        except OSError:
            return None
        return None

    @staticmethod
    def generate() -> str:
        version = None
        with subprocess.Popen(["git", "describe", "--always", "--tags"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            stdout, _ = process.communicate()
            last_tag = stdout.decode('ascii').strip()
            if process.returncode == 0 and last_tag:
                raw_version = last_tag.split('-g', maxsplit=1)[0].replace('-', '.') if '-g' in last_tag else last_tag
                version = Version._normalize_version(raw_version)

        if not version:
            version = (
                Version._read_existing_version()
                or Version._normalize_version(os.getenv('SUNSYNK_API_CLIENT_VERSION'))
                or '0.0.0'
            )

        with open(VERSION_FILENAME, 'w', encoding='utf-8') as file:
            file.write(f'SUNSYNK_API_CLIENT_VERSION = "{version}"\n')
        return version

    @staticmethod
    def get(retry=True) -> str:
        try:
            # pylint: disable=C0415
            from sunsynk.version import SUNSYNK_API_CLIENT_VERSION
            return SUNSYNK_API_CLIENT_VERSION
        except ModuleNotFoundError:
            if retry:
                Version.generate()
                return Version.get(False)
            return 'unknown'
        except ImportError:
            if retry:
                Version.generate()
                return Version.get(False)
            return 'unknown'

    @staticmethod
    def get_env_info() -> str:
        os_info = f"Release: {platform.release()}, Platform: {platform.platform()}"
        return f"(Python: {platform.python_version()}), OS: ({os_info}). Default Encoding: {sys.getdefaultencoding()}"
