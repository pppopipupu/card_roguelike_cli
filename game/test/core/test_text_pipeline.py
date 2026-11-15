import unittest

import msgspec

from game.core.text.events import JoinedText, LocaleText, RenderedText, ScreenText, TextDocument
from game.core.text.pipeline import render_text
from game.data.locale_data import get_locale_text


class TestTextPipeline(unittest.TestCase):
    def test_sections_aggregate_in_layout_order(self):
        seen = {}

        def screen(scene, notice):
            seen["scene"] = scene
            seen["notice"] = notice
            return "SCREEN"

        document: TextDocument = [
            LocaleText(key="i18n_outer_plane.ending.arrive", section="ending"),
            LocaleText(
                key="i18n_outer_plane.ui.card_gain",
                params={"name": "测试牌"},
                section="notice",
            ),
            RenderedText(text="RAW", section="body"),
            ScreenText(
                screen="outer_plane",
                section="screen",
                scene=[LocaleText(key="i18n_outer_plane.ending.fuse_done", section="scene")],
                notice=[
                    LocaleText(
                        key="i18n_outer_plane.ui.card_gain",
                        params={"name": "甲"},
                        section="notice",
                    )
                ],
            ),
        ]

        text = render_text(document, "outer_plane", {"outer_plane": screen})

        expected = "\n\n".join([
            get_locale_text("i18n_outer_plane.ending.arrive"),
            get_locale_text("i18n_outer_plane.ui.card_gain", name="测试牌"),
            "RAW",
            "SCREEN",
        ])
        self.assertEqual(text, expected)
        self.assertEqual(seen["scene"], get_locale_text("i18n_outer_plane.ending.fuse_done"))
        self.assertEqual(
            seen["notice"],
            get_locale_text("i18n_outer_plane.ui.card_gain", name="甲"),
        )

    def test_nested_joined_params_render_in_battle_layout(self):
        document: TextDocument = [
            LocaleText(
                key="i18n_explore_core.turn_waiting_others",
                params={
                    "logs": JoinedText(parts=[
                        LocaleText(
                            key="i18n_battle_core.end_player_phase_log",
                            params={"name": "甲"},
                        )
                    ]),
                    "count": 1,
                    "total": 2,
                    "names": "甲",
                },
            )
        ]

        text = render_text(document, "battle")

        expected = get_locale_text(
            "i18n_explore_core.turn_waiting_others",
            logs=get_locale_text("i18n_battle_core.end_player_phase_log", name="甲"),
            count=1,
            total=2,
            names="甲",
        )
        self.assertEqual(text, expected)

    def test_document_round_trips_through_msgspec(self):
        document: TextDocument = [
            LocaleText(key="i18n_outer_plane.ending.arrive", section="ending"),
            RenderedText(text="RAW", section="body"),
            JoinedText(parts=[RenderedText(text="A"), RenderedText(text="B")]),
            ScreenText(screen="outer_plane", section="screen"),
        ]
        payload = msgspec.json.encode(document)
        decoded = msgspec.json.decode(payload, type=TextDocument)
        self.assertEqual(decoded, document)


if __name__ == "__main__":
    unittest.main()
