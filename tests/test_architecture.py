import datetime
import json
import unittest
from importlib.metadata import version
from types import SimpleNamespace
from unittest.mock import Mock, patch

import azure.functions as func

import function_app
from telegram_handler import TelegramHandler


class TransformersCompatibilityTests(unittest.TestCase):
    def test_summarization_pipeline_task_is_supported_without_model_download(self):
        from transformers.pipelines import check_task

        self.assertEqual(version("transformers"), "4.57.2")
        normalized_task, _, _ = check_task("summarization")
        self.assertEqual(normalized_task, "summarization")


class FakeRequest:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def get_json(self):
        if self.error:
            raise self.error
        return self.payload


class WebhookTests(unittest.TestCase):
    def test_malformed_payload_returns_400(self):
        response = function_app.telegram_webhook(
            FakeRequest(error=ValueError("bad json"))
        )

        self.assertEqual(response.status_code, 400)

    def test_valid_update_is_processed(self):
        update = {"update_id": 123}
        handler = SimpleNamespace(process_update=lambda value: self.assertEqual(value, update))

        with patch.object(function_app, "get_telegram_handler", return_value=handler):
            response = function_app.telegram_webhook(FakeRequest(payload=update))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.get_body()), {"ok": True})

    def test_internal_error_returns_sanitized_500(self):
        handler = SimpleNamespace(
            process_update=lambda value: (_ for _ in ()).throw(RuntimeError("secret detail"))
        )

        with patch.object(function_app, "get_telegram_handler", return_value=handler):
            response = function_app.telegram_webhook(
                FakeRequest(payload={"update_id": 123})
            )

        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b"secret detail", response.get_body())


class TelegramHandlerTests(unittest.TestCase):
    def test_telebot_runs_handlers_synchronously(self):
        bot = Mock()
        bot.message_handler.return_value = lambda handler: handler

        with patch("telegram_handler.telebot.TeleBot", return_value=bot) as telebot:
            TelegramHandler("token", Mock())

        telebot.assert_called_once_with("token", threaded=False)

    def setUp(self):
        self.handler = TelegramHandler.__new__(TelegramHandler)
        self.handler.target_chat_id = -1003957784086
        self.handler.sent_messages = []
        self.handler.sent_summaries = []
        self.handler.saved_messages = []
        self.handler.send_message = lambda chat, text: self.handler.sent_messages.append(
            (chat, text)
        )
        self.handler.send_summary = lambda summary, chat=None: self.handler.sent_summaries.append(
            (chat, summary)
        )
        self.handler.save_message = lambda message: self.handler.saved_messages.append(message)

    def message(self, text, chat_id=-1003957784086):
        return SimpleNamespace(
            text=text,
            chat=SimpleNamespace(id=chat_id, type="supergroup"),
        )

    def test_normal_message_is_stored_without_response(self):
        message = self.message("Eine normale Nachricht")

        self.handler._handle_message(message)

        self.assertEqual(self.handler.saved_messages, [message])
        self.assertEqual(self.handler.sent_messages, [])

    def test_commands_are_not_stored(self):
        self.handler._handle_message(self.message("/dailysummary"))

        self.assertEqual(self.handler.saved_messages, [])

    def test_wrong_chat_is_ignored(self):
        self.handler._handle_message(self.message("Text", chat_id=-1000000000000))

        self.assertEqual(self.handler.saved_messages, [])

    def test_daily_summary_sends_progress_and_summary_to_same_chat(self):
        events = []
        self.handler.request_summary = lambda chat: events.append(("enqueue", chat))
        self.handler.send_message = lambda chat, text: events.append(("send", chat))

        self.handler._handle_daily_summary(self.message("/dailysummary"))

        self.assertEqual(
            events,
            [
                ("enqueue", -1003957784086),
                ("send", -1003957784086),
            ],
        )


class TimerTests(unittest.TestCase):
    def test_vienna_summer_and_winter_time(self):
        summer = datetime.datetime(2026, 8, 18, 18, tzinfo=datetime.timezone.utc)
        winter = datetime.datetime(2026, 1, 18, 19, tzinfo=datetime.timezone.utc)
        wrong_hour = datetime.datetime(2026, 8, 18, 20, tzinfo=datetime.timezone.utc)

        self.assertTrue(function_app.is_daily_summary_time(summer))
        self.assertTrue(function_app.is_daily_summary_time(winter))
        self.assertFalse(function_app.is_daily_summary_time(wrong_hour))


class SummaryExecutionTests(unittest.TestCase):
    def test_shared_summary_path_generates_and_sends(self):
        handler = SimpleNamespace(send_summary=unittest.mock.Mock())

        with patch.object(function_app, "create_daily_summary", return_value="Summary"):
            with patch.object(function_app, "get_telegram_handler", return_value=handler):
                result = function_app.generate_and_send_daily_summary(-1003957784086)

        self.assertEqual(result, "Summary")
        handler.send_summary.assert_called_once_with("Summary", -1003957784086)

    def test_queue_trigger_runs_summary_for_configured_chat(self):
        message = SimpleNamespace(
            get_json=lambda: {"chat_id": function_app.TARGET_CHAT_ID}
        )

        with patch.object(function_app, "generate_and_send_daily_summary") as generate:
            function_app.daily_summary_queue(message)

        generate.assert_called_once_with(
            function_app.TARGET_CHAT_ID,
            notify_if_empty=True,
        )


class DiscoveryTests(unittest.TestCase):
    def test_required_functions_are_registered(self):
        functions = {
            item.get_function_name(): item
            for item in function_app.app.get_functions()
        }

        self.assertIn("telegram_webhook", functions)
        self.assertIn("health_check", functions)
        self.assertIn("daily_summary_timer", functions)
        self.assertIn("daily_summary_queue", functions)
        self.assertIsNone(function_app._summarizer)


if __name__ == "__main__":
    unittest.main()