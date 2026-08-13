import unittest

from clausis.models import Risk
from clausis.router import OfflineRouter


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.router = OfflineRouter()

    def test_german_launch(self):
        request = self.router.route("Öffne firefox")
        self.assertEqual((request.action, request.target), ("app.launch", "firefox"))

    def test_english_volume(self):
        request = self.router.route("volume 42 percent")
        self.assertEqual(request.arguments["percent"], 42)

    def test_reboot_is_critical(self):
        request = self.router.route("Rechner neu starten")
        self.assertEqual(request.risk, Risk.CRITICAL)
        self.assertFalse(request.reversible)

    def test_stop_is_local(self):
        self.assertEqual(self.router.route("Stopp Hermes").action, "voice.stop")
        self.assertEqual(self.router.route("Stopp Clausis").action, "voice.stop")

    def test_orientation_commands_are_local_and_semantic(self):
        self.assertEqual(
            self.router.route("Wo bin ich").action, "desktop.context.describe"
        )
        self.assertEqual(
            self.router.route("Was kann ich hier tun").action,
            "desktop.controls.list",
        )
        self.assertEqual(
            self.router.route("Lies das Textfeld vor").action,
            "desktop.text.read_focused",
        )
        progress = self.router.route("Lies Fortschritt Download vor")
        self.assertEqual(
            (progress.action, progress.target),
            ("desktop.progress.read_named", "Download"),
        )
        numbered = self.router.route("Nummer drei")
        self.assertEqual(
            (numbered.action, numbered.target, numbered.risk),
            ("desktop.control.activate", "3", Risk.MEDIUM),
        )

    def test_correction_commands_do_not_need_hermes(self):
        self.assertEqual(self.router.route("Zurück").action, "desktop.navigate.back")
        self.assertEqual(self.router.route("Wiederholen").action, "voice.repeat")
        self.assertEqual(self.router.route("Abbrechen").action, "voice.cancel")
        self.assertEqual(self.router.route("Korrigieren").action, "voice.correct")

    def test_clipboard_clear_is_confirmation_gated_and_irreversible(self):
        for phrase in ("Zwischenablage leeren", "clear the clipboard"):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.clipboard.clear")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertFalse(request.reversible)

    def test_clipboard_read_is_confirmation_gated(self):
        for phrase in ("Lies die Zwischenablage vor", "read the clipboard"):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.clipboard.read_text")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)

    def test_clipboard_write_is_typed_confirmed_and_irreversible(self):
        for phrase, text in (
            ("Schreibe in die Zwischenablage private Wörter", "private Wörter"),
            ("write to the clipboard private words", "private words"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.clipboard.write_text")
            self.assertEqual(request.target, text)
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertFalse(request.reversible)

    def test_focused_text_copy_is_confirmation_gated_and_irreversible(self):
        for phrase in ("Kopiere das Textfeld", "copy the text field"):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.copy_focused")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertFalse(request.reversible)

    def test_text_selection_copy_is_confirmation_gated_and_irreversible(self):
        for phrase in ("Kopiere die Textauswahl", "copy the text selection"):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.copy_selection")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertFalse(request.reversible)

    def test_text_selection_read_is_confirmation_gated_and_reversible(self):
        for phrase in ("Lies die Textauswahl vor", "read the text selection"):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.read_selection")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)

    def test_select_all_text_is_local_low_risk_and_reversible(self):
        for phrase in (
            "Wähle den ganzen Text im Textfeld aus",
            "alles im Textfeld auswählen",
            "select all the text in the text field",
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.select_all")
            self.assertEqual(request.risk, Risk.LOW)
            self.assertTrue(request.reversible)

    def test_clear_text_selection_is_local_low_risk_and_reversible(self):
        for phrase in (
            "Hebe die Textauswahl auf",
            "Textauswahl aufheben",
            "clear the text selection",
            "deselect text",
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.clear_selection")
            self.assertEqual(request.risk, Risk.LOW)
            self.assertTrue(request.reversible)

    def test_delete_text_selection_is_confirmation_gated_and_reversible(self):
        for phrase in (
            "Lösche die Textauswahl",
            "ausgewählten Text löschen",
            "delete the selected text",
            "delete text selection",
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.delete_selection")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)

    def test_insert_at_caret_is_typed_confirmation_gated_and_reversible(self):
        for phrase in (
            "Füge am Textcursor wichtige Wörter ein",
            "füge an dem Cursor Text ein",
            "insert important words at the text cursor",
            "insert text at cursor",
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.insert_at_caret")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)
            self.assertTrue(request.target)

    def test_character_deletions_are_confirmation_gated_and_parameterless(self):
        for phrase, action in (
            ("Lösche das Zeichen vor dem Textcursor", "desktop.text.delete_previous_character"),
            ("lösche rückwärts am Cursor", "desktop.text.delete_previous_character"),
            ("delete the character before the text cursor", "desktop.text.delete_previous_character"),
            ("backspace at cursor", "desktop.text.delete_previous_character"),
            ("Lösche das Zeichen nach dem Textcursor", "desktop.text.delete_next_character"),
            ("lösche vorwärts am Cursor", "desktop.text.delete_next_character"),
            ("delete the character after the text cursor", "desktop.text.delete_next_character"),
            ("delete forward at cursor", "desktop.text.delete_next_character"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)
            self.assertEqual(request.target, "")

    def test_word_deletions_are_confirmation_gated_and_parameterless(self):
        for phrase, action in (
            ("Lösche das Wort vor dem Textcursor", "desktop.text.delete_previous_word"),
            ("delete the word before the text cursor", "desktop.text.delete_previous_word"),
            ("Lösche das Wort nach dem Textcursor", "desktop.text.delete_next_word"),
            ("delete the word after the text cursor", "desktop.text.delete_next_word"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)
            self.assertEqual(request.target, "")

    def test_word_replacements_are_typed_confirmation_gated_and_reversible(self):
        for phrase, action, target in (
            ("Ersetze das Wort vor dem Textcursor durch neue Wörter", "desktop.text.replace_previous_word", "neue Wörter"),
            ("replace the word before the text cursor with new words", "desktop.text.replace_previous_word", "new words"),
            ("Ersetze das Wort nach dem Textcursor durch neue Wörter", "desktop.text.replace_next_word", "neue Wörter"),
            ("replace the word after the text cursor with new words", "desktop.text.replace_next_word", "new words"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.target, target)
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)

    def test_character_selections_are_local_low_risk_and_parameterless(self):
        for phrase, action in (
            ("Wähle das Zeichen vor dem Textcursor aus", "desktop.text.select_previous_character"),
            ("select the character before the text cursor", "desktop.text.select_previous_character"),
            ("Wähle das Zeichen nach dem Textcursor aus", "desktop.text.select_next_character"),
            ("select the character after the text cursor", "desktop.text.select_next_character"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.risk, Risk.LOW)
            self.assertTrue(request.reversible)
            self.assertEqual(request.target, "")

    def test_word_selections_are_local_low_risk_and_parameterless(self):
        for phrase, action in (
            ("Wähle das Wort vor dem Textcursor aus", "desktop.text.select_previous_word"),
            ("select the word before the text cursor", "desktop.text.select_previous_word"),
            ("Wähle das Wort nach dem Textcursor aus", "desktop.text.select_next_word"),
            ("select the word after the text cursor", "desktop.text.select_next_word"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.risk, Risk.LOW)
            self.assertTrue(request.reversible)
            self.assertEqual(request.target, "")

    def test_current_line_selection_is_local_low_risk_and_parameterless(self):
        for phrase in (
            "Wähle die aktuelle Zeile aus",
            "Wähle die Zeile am Textcursor aus",
            "select the current line",
            "select the line at the text cursor",
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.select_current_line")
            self.assertEqual(request.risk, Risk.LOW)
            self.assertTrue(request.reversible)
            self.assertEqual(request.target, "")

    def test_current_line_deletion_is_confirmed_and_parameterless(self):
        for phrase in (
            "Lösche die aktuelle Zeile",
            "Lösche die Zeile am Textcursor",
            "delete the current line",
            "delete the line at the text cursor",
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.delete_current_line")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)
            self.assertEqual(request.target, "")

    def test_current_line_replacement_is_confirmed_and_typed(self):
        for phrase, target in (
            ("Ersetze die aktuelle Zeile durch neue Wörter", "neue Wörter"),
            ("Ersetze die Zeile am Textcursor durch neuen Text", "neuen Text"),
            ("replace the current line with new words", "new words"),
            ("replace the line at the text cursor with new text", "new text"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.replace_current_line")
            self.assertEqual(request.target, target)
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)

    def test_line_insertions_are_confirmed_and_typed(self):
        for phrase, action, target in (
            ("Füge die Zeile neue Wörter oberhalb der aktuellen Zeile ein", "desktop.text.insert_line_above", "neue Wörter"),
            ("Füge unterhalb der aktuellen Zeile neuer Text ein", "desktop.text.insert_line_below", "neuer Text"),
            ("insert the line new words above the current line", "desktop.text.insert_line_above", "new words"),
            ("insert the line new text below the current line", "desktop.text.insert_line_below", "new text"),
        ):
            request = self.router.route(phrase)
            self.assertEqual((request.action, request.target), (action, target))
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)

    def test_line_duplications_are_confirmed_and_parameterless(self):
        for phrase, action in (
            ("Dupliziere die aktuelle Zeile oberhalb", "desktop.text.duplicate_line_above"),
            ("Dupliziere die aktuelle Zeile nach unten", "desktop.text.duplicate_line_below"),
            ("duplicate the current line above", "desktop.text.duplicate_line_above"),
            ("duplicate the current line below", "desktop.text.duplicate_line_below"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.target, "")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)

    def test_line_moves_are_confirmed_and_parameterless(self):
        for phrase, action in (
            ("Verschiebe die aktuelle Zeile nach oben", "desktop.text.move_line_up"),
            ("Verschiebe die aktuelle Zeile nach unten", "desktop.text.move_line_down"),
            ("move the current line up", "desktop.text.move_line_up"),
            ("move the current line down", "desktop.text.move_line_down"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.target, "")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)

    def test_line_joins_are_confirmed_and_parameterless(self):
        for phrase, action in (
            ("Verbinde die aktuelle Zeile mit der vorherigen", "desktop.text.join_previous_line"),
            ("Verbinde die aktuelle Zeile mit der nächsten", "desktop.text.join_next_line"),
            ("join the current line with the previous line", "desktop.text.join_previous_line"),
            ("join the current line with the next line", "desktop.text.join_next_line"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.target, "")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)

    def test_line_split_is_confirmed_and_parameterless(self):
        for phrase in (
            "Teile die aktuelle Zeile am Textcursor",
            "split the current line at the text cursor",
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.split_line_at_caret")
            self.assertEqual(request.target, "")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)

    def test_line_indentation_is_confirmed_and_parameterless(self):
        for phrase, action in (
            ("Rücke die aktuelle Zeile ein", "desktop.text.indent_current_line"),
            ("Rücke die aktuelle Zeile aus", "desktop.text.outdent_current_line"),
            ("indent the current line", "desktop.text.indent_current_line"),
            ("outdent the current line", "desktop.text.outdent_current_line"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.target, "")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)

    def test_character_reads_are_confirmation_gated_and_parameterless(self):
        for phrase, action in (
            ("Lies das Zeichen vor dem Textcursor vor", "desktop.text.read_previous_character"),
            ("read the character before the text cursor", "desktop.text.read_previous_character"),
            ("Lies das Zeichen nach dem Textcursor vor", "desktop.text.read_next_character"),
            ("read the character after the text cursor", "desktop.text.read_next_character"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)
            self.assertEqual(request.target, "")

    def test_word_reads_are_confirmation_gated_and_parameterless(self):
        for phrase, action in (
            ("Lies das Wort vor dem Textcursor vor", "desktop.text.read_previous_word"),
            ("read the word before the text cursor", "desktop.text.read_previous_word"),
            ("Lies das Wort nach dem Textcursor vor", "desktop.text.read_next_word"),
            ("read the word after the text cursor", "desktop.text.read_next_word"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)
            self.assertEqual(request.target, "")

    def test_selection_replacement_is_typed_confirmation_gated_and_reversible(self):
        for phrase, target in (
            ("Ersetze die Textauswahl durch neue Wörter", "neue Wörter"),
            ("replace the text selection with new words", "new words"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.replace_selection")
            self.assertEqual(request.target, target)
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertTrue(request.reversible)

    def test_caret_boundary_moves_are_local_low_risk_and_reversible(self):
        for phrase, action in (
            ("Cursor an den Anfang", "desktop.text.caret_start"),
            ("Bewege den Textcursor an das Ende", "desktop.text.caret_end"),
            ("move the cursor to the beginning", "desktop.text.caret_start"),
            ("move the text cursor to the end", "desktop.text.caret_end"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.risk, Risk.LOW)
            self.assertTrue(request.reversible)

    def test_single_character_caret_moves_are_local_low_risk_and_reversible(self):
        for phrase, action in (
            ("Cursor ein Zeichen zurück", "desktop.text.caret_previous"),
            ("Bewege den Textcursor nach links", "desktop.text.caret_previous"),
            ("Cursor ein Zeichen vor", "desktop.text.caret_next"),
            ("Bewege den Textcursor nach rechts", "desktop.text.caret_next"),
            ("move the cursor one character back", "desktop.text.caret_previous"),
            ("move the text cursor right", "desktop.text.caret_next"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.risk, Risk.LOW)
            self.assertTrue(request.reversible)

    def test_word_caret_moves_are_local_low_risk_and_parameterless(self):
        for phrase, action in (
            ("Cursor ein Wort zurück", "desktop.text.caret_previous_word"),
            ("Bewege den Textcursor zum vorherigen Wort", "desktop.text.caret_previous_word"),
            ("move the cursor one word back", "desktop.text.caret_previous_word"),
            ("Cursor ein Wort vor", "desktop.text.caret_next_word"),
            ("Bewege den Textcursor zum nächsten Wort", "desktop.text.caret_next_word"),
            ("move the text cursor one word forward", "desktop.text.caret_next_word"),
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.risk, Risk.LOW)
            self.assertTrue(request.reversible)
            self.assertEqual(request.target, "")

    def test_caret_position_read_is_local_low_risk_and_reversible(self):
        for phrase in (
            "Wo ist der Textcursor",
            "Lies die Cursorposition vor",
            "where is the text cursor",
            "read the cursor position",
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.caret_describe")
            self.assertEqual(request.risk, Risk.LOW)
            self.assertTrue(request.reversible)

    def test_focused_text_paste_is_confirmation_gated_and_irreversible(self):
        for phrase in (
            "Füge die Zwischenablage in das Textfeld ein",
            "paste the clipboard into the text field",
        ):
            request = self.router.route(phrase)
            self.assertEqual(request.action, "desktop.text.paste_focused")
            self.assertEqual(request.risk, Risk.MEDIUM)
            self.assertFalse(request.reversible)

    def test_semantic_window_management_commands(self):
        expected = {
            "Fenster minimieren": "desktop.window.minimize",
            "maximize the window": "desktop.window.maximize",
            "Fenster wiederherstellen": "desktop.window.restore",
            "close the window": "desktop.window.close",
            "Fenster auf die vorherige Arbeitsfläche verschieben": "desktop.window.workspace_previous",
            "move the window to the next workspace": "desktop.window.workspace_next",
        }
        for phrase, action in expected.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(self.router.route(phrase).action, action)
        self.assertEqual(self.router.route("close the window").risk, Risk.MEDIUM)

    def test_accessibility_enable_commands_are_confirmation_gated(self):
        expected = {
            "Bildschirmtastatur einschalten": "accessibility.screen_keyboard.enable",
            "enable the screen reader": "accessibility.screen_reader.enable",
            "Lupe einschalten": "accessibility.screen_magnifier.enable",
            "Lupe ausschalten": "accessibility.screen_magnifier.disable",
            "disable the screen magnifier": "accessibility.screen_magnifier.disable",
        }
        for phrase, action in expected.items():
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.risk, Risk.MEDIUM)

    def test_magnifier_percentage_command_is_typed_and_confirmation_gated(self):
        request = self.router.route("Bildschirmvergrößerung 225 Prozent")
        self.assertEqual(request.action, "accessibility.screen_magnifier.set_percent")
        self.assertEqual(request.arguments, {"percent": 225})
        self.assertEqual(request.risk, Risk.MEDIUM)

    def test_magnifier_inversion_commands_are_typed_and_confirmation_gated(self):
        expected = {
            "Farbinvertierung einschalten": "accessibility.screen_magnifier.invert_lightness.enable",
            "Farbinvertierung ausschalten": "accessibility.screen_magnifier.invert_lightness.disable",
        }
        for phrase, action in expected.items():
            request = self.router.route(phrase)
            self.assertEqual(request.action, action)
            self.assertEqual(request.risk, Risk.MEDIUM)

    def test_magnifier_saturation_command_is_typed_and_confirmation_gated(self):
        request = self.router.route("Farbsättigung 35 Prozent")
        self.assertEqual(request.action, "accessibility.screen_magnifier.set_saturation")
        self.assertEqual(request.arguments, {"percent": 35})
        self.assertEqual(request.risk, Risk.MEDIUM)

    def test_magnifier_brightness_and_contrast_are_signed_and_confirmation_gated(self):
        expected = {
            "Helligkeit minus 30 Prozent": (
                "accessibility.screen_magnifier.set_brightness", -30
            ),
            "Lupe Helligkeit plus 20 Prozent": (
                "accessibility.screen_magnifier.set_brightness", 20
            ),
            "magnifier contrast negative 45 percent": (
                "accessibility.screen_magnifier.set_contrast", -45
            ),
            "Kontrast 0 Prozent": (
                "accessibility.screen_magnifier.set_contrast", 0
            ),
        }
        for phrase, (action, percent) in expected.items():
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertEqual(
                    (request.action, request.arguments, request.risk),
                    (action, {"percent": percent}, Risk.MEDIUM),
                )

    def test_magnifier_screen_position_is_typed_and_confirmation_gated(self):
        expected = {
            "Lupe Vollbild": "full-screen",
            "Bildschirmvergrößerung obere Hälfte": "top-half",
            "magnifier bottom half": "bottom-half",
            "screen magnifier left half": "left-half",
            "Lupe rechte Hälfte": "right-half",
        }
        for phrase, position in expected.items():
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertEqual(
                    (request.action, request.arguments, request.risk),
                    (
                        "accessibility.screen_magnifier.set_screen_position",
                        {"position": position},
                        Risk.MEDIUM,
                    ),
                )

    def test_magnifier_cross_hair_commands_are_confirmation_gated(self):
        expected = {
            "Fadenkreuz einschalten": "accessibility.screen_magnifier.cross_hairs.enable",
            "Lupe Fadenkreuz ausschalten": "accessibility.screen_magnifier.cross_hairs.disable",
            "enable magnifier crosshairs": "accessibility.screen_magnifier.cross_hairs.enable",
            "disable crosshairs": "accessibility.screen_magnifier.cross_hairs.disable",
        }
        for phrase, action in expected.items():
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertEqual(request.action, action)
                self.assertEqual(request.risk, Risk.MEDIUM)

    def test_orca_speech_recovery_restart_is_confirmation_gated(self):
        for phrase in ("Orca neu starten", "restart the screen reader"):
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertEqual(
                    (request.action, request.arguments, request.risk),
                    ("accessibility.screen_reader.restart_with_speech", {}, Risk.MEDIUM),
                )
                self.assertEqual(request.arguments, {})

    def test_magnifier_cross_hair_opacity_is_typed_and_confirmation_gated(self):
        for phrase in (
            "Fadenkreuz Deckkraft 42 Prozent",
            "magnifier crosshairs opacity 42 percent",
        ):
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertEqual(
                    (request.action, request.arguments, request.risk),
                    (
                        "accessibility.screen_magnifier.cross_hairs.set_opacity",
                        {"percent": 42},
                        Risk.MEDIUM,
                    ),
                )

    def test_magnifier_cross_hair_clip_commands_are_confirmation_gated(self):
        expected = {
            "Fadenkreuz Mitte aussparen": "accessibility.screen_magnifier.cross_hairs.clip.enable",
            "Fadenkreuz Mitte nicht aussparen": "accessibility.screen_magnifier.cross_hairs.clip.disable",
            "clip magnifier crosshairs at the center": "accessibility.screen_magnifier.cross_hairs.clip.enable",
            "do not clip crosshairs at center": "accessibility.screen_magnifier.cross_hairs.clip.disable",
        }
        for phrase, action in expected.items():
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertEqual(request.action, action)
                self.assertEqual(request.risk, Risk.MEDIUM)
                self.assertEqual(request.arguments, {})

    def test_magnifier_cross_hair_length_is_typed_and_confirmation_gated(self):
        for phrase in (
            "Fadenkreuz Länge 640 Pixel",
            "magnifier crosshairs length 640 pixels",
        ):
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertEqual(
                    (request.action, request.arguments, request.risk),
                    (
                        "accessibility.screen_magnifier.cross_hairs.set_length",
                        {"pixels": 640},
                        Risk.MEDIUM,
                    ),
                )

    def test_magnifier_cross_hair_thickness_is_typed_and_confirmation_gated(self):
        for phrase in (
            "Fadenkreuz Dicke 12 Pixel",
            "magnifier crosshairs thickness 12 pixels",
        ):
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertEqual(
                    (request.action, request.arguments, request.risk),
                    (
                        "accessibility.screen_magnifier.cross_hairs.set_thickness",
                        {"pixels": 12},
                        Risk.MEDIUM,
                    ),
                )

    def test_magnifier_cross_hair_color_is_typed_and_confirmation_gated(self):
        expected = {
            "Fadenkreuz Farbe rot": {"red": 255, "green": 0, "blue": 0},
            "magnifier crosshairs color cyan": {"red": 0, "green": 255, "blue": 255},
            "Fadenkreuz Farbe RGB 12 34 56": {"red": 12, "green": 34, "blue": 56},
            "crosshairs color RGB 255 128 0": {"red": 255, "green": 128, "blue": 0},
        }
        for phrase, arguments in expected.items():
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertEqual(
                    (request.action, request.arguments, request.risk),
                    (
                        "accessibility.screen_magnifier.cross_hairs.set_color",
                        arguments,
                        Risk.MEDIUM,
                    ),
                )

    def test_magnifier_focus_tracking_is_typed_and_confirmation_gated(self):
        expected = {
            "Fokusverfolgung aus": "none",
            "Lupe Fokusverfolgung zentriert": "centered",
            "magnifier focus tracking proportional": "proportional",
            "magnifier focus tracking push": "push",
        }
        for phrase, mode in expected.items():
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertEqual(
                    (request.action, request.arguments, request.risk),
                    (
                        "accessibility.screen_magnifier.set_focus_tracking",
                        {"mode": mode},
                        Risk.MEDIUM,
                    ),
                )

    def test_magnifier_caret_and_mouse_tracking_are_typed_and_confirmation_gated(self):
        expected = {
            "Textcursorverfolgung aus": (
                "accessibility.screen_magnifier.set_caret_tracking", "none"
            ),
            "Lupe Textcursorverfolgung zentriert": (
                "accessibility.screen_magnifier.set_caret_tracking", "centered"
            ),
            "magnifier mouse tracking proportional": (
                "accessibility.screen_magnifier.set_mouse_tracking", "proportional"
            ),
            "Mausverfolgung schiebend": (
                "accessibility.screen_magnifier.set_mouse_tracking", "push"
            ),
        }
        for phrase, (action, mode) in expected.items():
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertEqual(
                    (request.action, request.arguments, request.risk),
                    (action, {"mode": mode}, Risk.MEDIUM),
                )

    def test_magnifier_lens_mode_and_edge_scrolling_are_confirmation_gated(self):
        expected = {
            "Linsenmodus einschalten": "accessibility.screen_magnifier.lens_mode.enable",
            "Lupe Linsenmodus ausschalten": "accessibility.screen_magnifier.lens_mode.disable",
            "enable magnifier scrolling at the edges": "accessibility.screen_magnifier.scroll_at_edges.enable",
            "Randscrollen ausschalten": "accessibility.screen_magnifier.scroll_at_edges.disable",
        }
        for phrase, action in expected.items():
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertEqual(
                    (request.action, request.arguments, request.risk),
                    (action, {}, Risk.MEDIUM),
                )

    def test_semantic_dialog_commands(self):
        named = self.router.route("select Cancel")
        self.assertEqual(
            (named.action, named.target, named.risk),
            ("desktop.control.activate_named", "Cancel", Risk.MEDIUM),
        )
        self.assertEqual(self.router.route("next control").action, "desktop.focus.next")
        self.assertEqual(
            self.router.route("previous control").action,
            "desktop.focus.previous",
        )
        named_focus = self.router.route("fokussiere Details")
        self.assertEqual(
            (named_focus.action, named_focus.target),
            ("desktop.focus.named", "Details"),
        )
        typed = self.router.route("type into the field quarterly report")
        self.assertEqual(
            (typed.action, typed.target, typed.risk),
            ("desktop.text.set", "quarterly report", Risk.MEDIUM),
        )
        self.assertEqual(
            self.router.route("clear the text field").action,
            "desktop.text.clear",
        )
        selected = self.router.route("select list item Documents")
        self.assertEqual(
            (selected.action, selected.target, selected.risk),
            ("desktop.selection.select_named", "Documents", Risk.MEDIUM),
        )
        visible_file = self.router.route("select visible file report.pdf")
        self.assertEqual(
            (visible_file.action, visible_file.target, visible_file.risk),
            ("desktop.file_dialog.select_visible", "report.pdf", Risk.MEDIUM),
        )
        file_name = self.router.route("set file name report.pdf")
        self.assertEqual(
            (file_name.action, file_name.target, file_name.risk),
            ("desktop.file_dialog.set_name", "report.pdf", Risk.MEDIUM),
        )
        location = self.router.route("set the file location /home/clausis/Documents")
        self.assertEqual(
            (location.action, location.target, location.risk),
            (
                "desktop.file_dialog.set_location",
                "/home/clausis/Documents",
                Risk.MEDIUM,
            ),
        )
        folder = self.router.route("open visible folder Documents")
        self.assertEqual(
            (folder.action, folder.target, folder.risk),
            (
                "desktop.file_dialog.open_visible_folder",
                "Documents",
                Risk.MEDIUM,
            ),
        )
        accept_dialog = self.router.route("bestätige den Dateidialog")
        cancel_dialog = self.router.route("cancel the file dialog")
        self.assertEqual(
            (accept_dialog.action, accept_dialog.target, accept_dialog.risk),
            ("desktop.file_dialog.decide", "accept", Risk.MEDIUM),
        )
        self.assertEqual(
            (cancel_dialog.action, cancel_dialog.target, cancel_dialog.risk),
            ("desktop.file_dialog.decide", "cancel", Risk.MEDIUM),
        )
        accept_standard = self.router.route("bestätige den Dialog")
        cancel_standard = self.router.route("cancel the dialog")
        retry_standard = self.router.route("wiederhole den Dialog")
        apply_standard = self.router.route("apply the dialog")
        read_standard = self.router.route("lies den Dialog vor")
        dismiss_standard = self.router.route("close the dialog")
        self.assertEqual(
            (
                accept_standard.action,
                accept_standard.target,
                accept_standard.risk,
                accept_standard.reversible,
            ),
            ("desktop.standard_dialog.decide", "accept", Risk.HIGH, False),
        )
        self.assertEqual(
            (
                cancel_standard.action,
                cancel_standard.target,
                cancel_standard.risk,
                cancel_standard.reversible,
            ),
            ("desktop.standard_dialog.decide", "cancel", Risk.HIGH, False),
        )
        self.assertEqual(
            (retry_standard.action, retry_standard.target, retry_standard.risk,
             retry_standard.reversible),
            ("desktop.standard_dialog.decide", "retry", Risk.HIGH, False),
        )
        self.assertEqual(
            (apply_standard.action, apply_standard.target, apply_standard.risk,
             apply_standard.reversible),
            ("desktop.standard_dialog.decide", "apply", Risk.HIGH, False),
        )
        self.assertEqual(
            (read_standard.action, read_standard.target, read_standard.risk),
            ("desktop.standard_dialog.read", "", Risk.MEDIUM),
        )
        self.assertEqual(
            (dismiss_standard.action, dismiss_standard.target, dismiss_standard.risk,
             dismiss_standard.reversible),
            ("desktop.standard_dialog.dismiss", "", Risk.HIGH, False),
        )
        expanded = self.router.route("expand tree item Documents")
        collapsed = self.router.route("klappe Baumelement Documents zu")
        self.assertEqual(
            (expanded.action, expanded.target, expanded.risk),
            ("desktop.tree.expand_named", "Documents", Risk.MEDIUM),
        )
        self.assertEqual(
            (collapsed.action, collapsed.target, collapsed.risk),
            ("desktop.tree.collapse_named", "Documents", Risk.MEDIUM),
        )
        row = self.router.route("select table row Quarterly")
        self.assertEqual(
            (row.action, row.target, row.risk),
            ("desktop.table.select_row", "Quarterly", Risk.MEDIUM),
        )
        tab = self.router.route("wähle Registerkarte Privacy")
        self.assertEqual(
            (tab.action, tab.target, tab.risk),
            ("desktop.tabs.select_named", "Privacy", Risk.MEDIUM),
        )
        slider = self.router.route("setze Schieberegler Zoom auf 60 Prozent")
        self.assertEqual(
            (slider.action, slider.target, slider.arguments, slider.risk),
            ("desktop.slider.set_percent", "Zoom", {"percent": 60}, Risk.MEDIUM),
        )
        checked = self.router.route("aktiviere Kontrollkästchen Updates")
        unchecked = self.router.route("uncheck the checkbox Updates")
        radio = self.router.route("wähle Optionsfeld Dark")
        self.assertEqual(
            (checked.action, checked.target, checked.arguments, checked.risk),
            ("desktop.checkbox.set_checked", "Updates", {"checked": True}, Risk.MEDIUM),
        )
        self.assertEqual(
            (unchecked.action, unchecked.target, unchecked.arguments, unchecked.risk),
            ("desktop.checkbox.set_checked", "Updates", {"checked": False}, Risk.MEDIUM),
        )
        switch_on = self.router.route("schalte Schalter Wi-Fi ein")
        switch_off = self.router.route("turn switch Wi-Fi off")
        self.assertEqual(
            (switch_on.action, switch_on.target, switch_on.arguments, switch_on.risk),
            ("desktop.switch.set_enabled", "Wi-Fi", {"checked": True}, Risk.MEDIUM),
        )
        self.assertEqual(
            (switch_off.action, switch_off.target, switch_off.arguments, switch_off.risk),
            ("desktop.switch.set_enabled", "Wi-Fi", {"checked": False}, Risk.MEDIUM),
        )
        self.assertEqual(
            (radio.action, radio.target, radio.risk),
            ("desktop.radio.select_named", "Dark", Risk.MEDIUM),
        )
        combo = self.router.route("wähle in Auswahlliste Language den Eintrag Deutsch")
        self.assertEqual(
            (combo.action, combo.target, combo.arguments, combo.risk),
            ("desktop.combo.select_item", "Language", {"item": "Deutsch"}, Risk.MEDIUM),
        )
        spin = self.router.route("setze Zahlenfeld Vergrößerung auf 2,5")
        self.assertEqual(
            (spin.action, spin.target, spin.arguments, spin.risk),
            ("desktop.spin_button.set_value", "Vergrößerung", {"value": 2.5}, Risk.MEDIUM),
        )
        menu = self.router.route("aktiviere Menüeintrag Speichern")
        self.assertEqual(
            (menu.action, menu.target, menu.risk),
            ("desktop.menu.activate_item", "Speichern", Risk.MEDIUM),
        )
        allow = self.router.route("Berechtigung erlauben")
        deny = self.router.route("deny the permission")
        self.assertEqual(
            (allow.action, allow.target, allow.risk),
            ("desktop.permission_dialog.decide", "allow", Risk.MEDIUM),
        )
        self.assertEqual(
            (deny.action, deny.target, deny.risk),
            ("desktop.permission_dialog.decide", "deny", Risk.MEDIUM),
        )

    def test_semantic_gnome_shell_commands(self):
        self.assertEqual(
            self.router.route("Zeige die Übersicht").action, "desktop.overview"
        )
        self.assertEqual(
            self.router.route("show applications").action, "desktop.applications"
        )
        self.assertEqual(
            self.router.route("open quick settings").action,
            "desktop.quick_settings",
        )
        self.assertEqual(
            self.router.route("show notifications").action,
            "desktop.notifications",
        )
        read = self.router.route("lies die Benachrichtigungen vor")
        self.assertEqual(
            (read.action, read.target, read.risk),
            ("desktop.notifications.read", "", Risk.MEDIUM),
        )
        dismiss = self.router.route("verwirf Benachrichtigung Nummer zwei")
        self.assertEqual(
            (dismiss.action, dismiss.target, dismiss.risk, dismiss.reversible),
            ("desktop.notifications.dismiss", "2", Risk.HIGH, False),
        )

    def test_unknown_returns_none(self):
        self.assertIsNone(self.router.route("Schreibe mir ein Gedicht"))

    def test_twenty_or_more_commands_exist(self):
        self.assertGreaterEqual(len(self.router._commands), 20)


if __name__ == "__main__":
    unittest.main()
