import pygame
import pytest

from src.utils.spritesheet import SpriteSheet, SpriteSheetError


def test_loads_nine_frames_and_removes_background(test_sheet):
    path, rects = test_sheet
    sheet = SpriteSheet.load(path, rects, background_tolerance=10)
    assert sheet.frame_count == 9
    assert sheet.frame(0).get_size() == (20, 30)
    assert sheet.frame(0).get_at((0, 0)).a == 255


def test_left_frame_is_mirrored(test_sheet):
    path, rects = test_sheet
    sheet = SpriteSheet.load(path, rects)
    assert sheet.frame(2, -1).get_size() == sheet.frame(2, 1).get_size()
    assert sheet.anchor(2, 1)[0] + sheet.anchor(2, -1)[0] == 20


def test_missing_file_names_path(tmp_path, test_sheet):
    _, rects = test_sheet
    bad = tmp_path / "nope.png"
    with pytest.raises(SpriteSheetError, match="nope.png"):
        SpriteSheet.load(bad, rects)


def test_wrong_frame_count(test_sheet):
    path, rects = test_sheet
    with pytest.raises(SpriteSheetError, match="9"):
        SpriteSheet.load(path, rects[:8])


def test_rect_outside_image(test_sheet):
    path, rects = test_sheet
    rects = list(rects)
    rects[4] = rects[4].__class__(290, 90, 50, 50, 0, 0)
    with pytest.raises(SpriteSheetError, match="frame 5"):
        SpriteSheet.load(path, rects)


def test_real_sheet_loads(config):
    sheet = SpriteSheet.load(config.sheet_path, config.frames, config.background_tolerance,
                             config.sprite_scale, extras={"projectile": config.projectile_sprite})
    assert sheet.frame_count == 9
    assert isinstance(sheet.extra("projectile"), pygame.Surface)
