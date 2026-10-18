"""Nonprivileged checks: no packages, disks, services, or containers are changed."""
import json
import importlib.util
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent


class SetupTests(unittest.TestCase):
    def test_fresh_host_directories_override_private_umask(self):
        spec = importlib.util.spec_from_file_location("sisyphus_setup", ROOT / "scripts/setup.py")
        setup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(setup)
        with tempfile.TemporaryDirectory() as tmp:
            setup.DATA = Path(tmp) / "data"
            setup.BASE = Path(tmp) / "lab"
            relatives = ("configs/prometheus", "configs/loki", "configs/grafana/provisioning/datasources",
                         "configs/jellyfin/cache", "configs/joplin/postgres")
            for relative in (*relatives, "configs/bookmarksman"):
                (setup.BASE / "generated/data-dirs" / relative).mkdir(parents=True, exist_ok=True)
            owners = {}
            def simulate_root_install(args):
                # Actually create directories without sudo/chown in this temporary tree.
                path = Path(args[-1])
                path.mkdir(parents=True, exist_ok=True)
                path.chmod(int(args[args.index("-m") + 1], 8))
                owners[path] = args[args.index("-o") + 1]
            with mock.patch.object(setup, "run", side_effect=simulate_root_install), \
                    mock.patch.object(setup.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)):
                setup.initialize_host_dirs()
            for relative in relatives[:-1]:
                # A container's distinct UID must be able to traverse/read configs.
                self.assertEqual((setup.DATA / relative).stat().st_mode & 0o777, 0o755)
            self.assertEqual(owners[setup.DATA / "configs/jellyfin/cache"], str(setup.UID))
            self.assertEqual((setup.DATA / "configs/joplin/postgres").stat().st_mode & 0o777, 0o700)
            self.assertEqual((setup.DATA / "configs/bookmarksman").stat().st_mode & 0o777, 0o750)
            self.assertEqual(owners[setup.DATA / "configs/bookmarksman"], "999")

    def test_storage_guard_refuses_mounted_children_and_swap(self):
        script = (ROOT / "scripts/setup-storage.sh").read_text()
        guard = re.search(r"python3 - <<'PY'\n(.*?)\nPY", script, re.S)[1]
        for mount in ("/", "/data", "[SWAP]"):
            inventory = {"blockdevices": [{"name": "/dev/unused-test-disk", "mountpoints": [None],
                          "children": [{"name": "/dev/unused-test-part", "mountpoints": [mount]}]}]}
            with self.subTest(mount=mount), mock.patch.dict(os.environ, SISYPHUS_DATA_DISK="/dev/unused-test-disk"), \
                    mock.patch("subprocess.check_output", return_value=json.dumps(inventory).encode()):
                with self.assertRaisesRegex(SystemExit, "Refusing disk in use"):
                    exec(compile(guard, "storage-guard", "exec"), {})

    @unittest.skipUnless(shutil.which("docker"), "Docker Compose CLI required")
    def test_render_is_staged_and_compose_preserves_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            secret = 'password-$EXAMPLE-"quoted"-with-spaces'
            env = dict(os.environ, SETUP_USER=pwd.getpwuid(os.getuid()).pw_name,
                       DATA_ROOT=str(base / "untouched-data"), HOMELAB_ROOT=str(base / "lab"),
                       HOMARR_SECRET_ENCRYPTION_KEY="a" * 64, JOPLIN_DB_PASSWORD=secret,
                       ADGUARD_PASSWORD=secret, VAULTWARDEN_ADMIN_TOKEN=secret)
            subprocess.run(["python3", str(ROOT / "scripts/setup.py"), "render"], env=env,
                           check=True, capture_output=True)
            self.assertFalse((base / "untouched-data").exists())
            compose = base / "lab/generated/docker-compose.yml"
            self.assertEqual(compose.stat().st_mode & 0o777, 0o600)
            result = subprocess.run(["docker", "compose", "--profile", "*", "-f", str(compose),
                                     "config", "--format", "json"], check=True,
                                    env=env, capture_output=True, text=True)
            model = json.loads(result.stdout)
            # Compose serializes literal dollars escaped for a reusable config.
            actual = model["services"]["joplin-db"]["environment"]["POSTGRES_PASSWORD"]
            self.assertEqual(actual.replace("$$", "$"), secret)
            self.assertTrue({"homarr", "beets", "adguard", "grafana", "alloy", "prometheus", "loki"}
                            <= model["services"].keys())
            self.assertNotIn("bookmarks", model["services"])
            bookmarks = model["services"]["bookmarksman"]
            self.assertEqual(bookmarks["image"], "darshbhilwara/bookmarksman:1.0.0")
            self.assertEqual(bookmarks["environment"]["BOOKMARKSMAN_DATA"], "/data/profiles")
            self.assertEqual(bookmarks["ports"][0]["target"], 8080)
            self.assertEqual(str(bookmarks["ports"][0]["published"]), "1024")
            self.assertEqual(bookmarks["volumes"][0]["source"], str(base / "untouched-data/configs/bookmarksman"))
            self.assertEqual(bookmarks["volumes"][0]["target"], "/data")
            self.assertIn("/api/health", bookmarks["healthcheck"]["test"][-1])
            self.assertEqual(bookmarks["labels"]["traefik.http.routers.bookmarksman.rule"], "Host(`bookmarksman.home`)")
            self.assertEqual(bookmarks["labels"]["traefik.http.services.bookmarksman.loadbalancer.healthcheck.path"], "/api/health")
            env["JOPLIN_DB_PASSWORD"] = "updated-password"
            subprocess.run(["python3", str(ROOT / "scripts/setup.py"), "render"], env=env,
                           check=True, capture_output=True)
            self.assertIn("updated-password", compose.read_text())

    def test_backup_restarts_containers_after_borg_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bindir = base / "bin"
            bindir.mkdir()
            log = base / "docker.log"
            envfile = base / "backup.env"
            envfile.write_text('BORG_REPO=/backup\nBORG_PASSPHRASE=test\nDATA_ROOT=/data\nCOMPOSE_FILE=/compose.yml\n')
            mocks = {
                "docker": '#!/bin/bash\nprintf "%s\\n" "$*" >> "$TEST_DOCKER_LOG"\nif [[ $* == *" ps "* ]]; then printf "running-one\\nrunning-two\\n"; fi\n',
                "borg": '#!/bin/bash\nexit 2\n',
                "flock": '#!/bin/bash\nexit 0\n',
            }
            for name, content in mocks.items():
                file = bindir / name
                file.write_text(content)
                file.chmod(0o755)
            script = (ROOT / "scripts/backup.sh").read_text().replace(
                "/etc/sisyphus/backup.env", str(envfile)).replace(
                "/run/lock/sisyphus-backup.lock", str(base / "lock"))
            result = subprocess.run(["bash"], input=script, text=True, capture_output=True,
                                    env=dict(os.environ, PATH=str(bindir) + ":" + os.environ["PATH"],
                                             TEST_DOCKER_LOG=str(log)))
            self.assertEqual(result.returncode, 2)
            commands = log.read_text()
            self.assertIn("stop running-one running-two", commands)
            self.assertIn("start running-one running-two", commands)


if __name__ == "__main__":
    unittest.main()
