from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SERVER = REPO / "workspaces" / "operations" / "server"


def load_script(name: str):
    path = SERVER / name
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DIARY = load_script("migrate-diary-into-room.py")
MEMORY = load_script("install-memory-layout.py")
CHECK = load_script("check-memory-layout.py")


class DiaryMigrationTests(unittest.TestCase):
    def test_candidates_include_both_sources_and_skip_other_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            world = Path(temporary)
            room = world / "room"
            (world / "diary").mkdir()
            (room / "diary-待迁").mkdir(parents=True)
            (world / "diary" / "2026-11-17.md").write_text("old", encoding="utf-8")
            (room / "diary-待迁" / "2026-11-18.md").write_text("staged", encoding="utf-8")
            (world / "diary" / "notes.md").write_text("keep", encoding="utf-8")

            planned, skipped = DIARY.candidates(world)

            self.assertEqual(
                [(source.name, target.name) for source, target in planned],
                [("2026-11-17.md", "2026-11-17.md"), ("2026-11-18.md", "2026-11-18.md")],
            )
            self.assertEqual([path.name for path in skipped], ["notes.md"])

    def test_copy_is_dry_run_by_default_and_never_overwrites_conflicts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.md"
            target = root / "target.md"
            source.write_text("same", encoding="utf-8")

            self.assertEqual(DIARY.copy_without_overwrite(source, target, False), "copy")
            self.assertFalse(target.exists())
            self.assertEqual(DIARY.copy_without_overwrite(source, target, True), "copied")
            self.assertEqual(DIARY.copy_without_overwrite(source, target, True), "same")

            target.write_text("different", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "conflict"):
                DIARY.copy_without_overwrite(source, target, False)

    def test_world_config_is_updated_once_with_a_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            room = root / "world" / "room"
            diary = room / "diary"
            diary.mkdir(parents=True)
            config = root / "cordis.patch.yml"
            config.write_text(
                "- id: dsh-world\n"
                "  config:\n"
                "    worldId: ds\n"
                "- id: other\n"
                "  config:\n"
                "    diaryDir: keep-me\n",
                encoding="utf-8",
            )

            self.assertTrue(DIARY.update_world_config(config, diary, True))
            text = config.read_text(encoding="utf-8")
            self.assertIn("    diaryDir: '" + diary.resolve().as_posix() + "'", text)
            self.assertIn("    diaryDir: keep-me", text)
            self.assertFalse(DIARY.update_world_config(config, diary, True))
            backups = list(root.glob(config.name + ".before-diary-room-*"))
            self.assertEqual(len(backups), 1)


class MemoryLayoutTests(unittest.TestCase):
    def test_install_creates_scene_files_and_preserves_existing_memory(self):
        with tempfile.TemporaryDirectory() as temporary:
            world = Path(temporary) / "world"
            existing = world / "room" / "memory" / "qq.md"
            existing.parent.mkdir(parents=True)
            existing.write_text("custom QQ memory\n", encoding="utf-8")

            MEMORY.install(
                world,
                REPO / "workspaces" / "platform" / "config" / "memory",
                REPO / "workspaces" / "platform" / "config" / "workspace-AGENTS.md",
            )

            self.assertEqual(existing.read_text(encoding="utf-8"), "custom QQ memory\n")
            for relative in (
                "shared.md",
                "room/memory/qq-style.md",
                "bili-duty/AGENTS.md",
                "bili-duty/memory.md",
                "live/AGENTS.md",
                "live/memory.md",
                "service/AGENTS.md",
                "service/memory.md",
                "room/AGENTS.md",
            ):
                self.assertTrue((world / relative).is_file(), relative)

    def test_legacy_self_and_persona_text_are_migrated_with_backups(self):
        with tempfile.TemporaryDirectory() as temporary:
            world = Path(temporary)
            room = world / "room"
            room.mkdir()
            self_path = room / "我是谁.md"
            self_path.write_text(MEMORY.OLD_SELF_INTRO + "\n" + MEMORY.OLD_SELF_BILI, encoding="utf-8")
            persona = world / "persona.md"
            persona.write_text(MEMORY.OLD_PERSONA_STATUS, encoding="utf-8")

            MEMORY.migrate_self(world)
            MEMORY.migrate_persona(world)

            self.assertIn(MEMORY.NEW_SELF_INTRO, self_path.read_text(encoding="utf-8"))
            self.assertIn(MEMORY.NEW_SELF_BILI, self_path.read_text(encoding="utf-8"))
            self.assertEqual(persona.read_text(encoding="utf-8"), MEMORY.NEW_PERSONA_STATUS)
            self.assertTrue((room / "我是谁.legacy-2026-11-17.md").is_file())
            self.assertTrue((world / "persona.legacy-2026-11-17.md").is_file())

    def test_config_block_value_reads_the_requested_block_only(self):
        text = (
            "- id: dsh-world\n"
            "  config:\n"
            "    diaryDir: D:/world/room/diary\n"
            "- id: bili-scroll\n"
            "  config:\n"
            "    workspace: D:/world/bili-duty\n"
        )
        self.assertEqual(CHECK.block_value(text, "dsh-world", "diaryDir"), "D:/world/room/diary")
        self.assertEqual(CHECK.block_value(text, "bili-scroll", "workspace"), "D:/world/bili-duty")
        self.assertIsNone(CHECK.block_value(text, "missing", "workspace"))

    def test_normalized_paths_ignore_drive_case_and_slashes(self):
        self.assertEqual(CHECK.normalized(r"D:\\PRJ\\Demo\\"), "d:/prj/demo")


if __name__ == "__main__":
    unittest.main()
