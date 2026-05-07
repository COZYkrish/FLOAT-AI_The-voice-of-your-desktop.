# # float.py — FLOAT AI Desktop Assistant
# # Main entry point: wires all modules together and launches the event loop.

# import sys
# import queue
# import logging
# import threading

# from config import log, FLOAT_VERSION
# from voice  import speak, WakeWordListener
# from brain  import route_intent, extract_entities, ask_groq

# logger = logging.getLogger("FLOAT")

# # ─── Shared inter-thread queue ────────────────────────────────────────────────
# _gui_queue: queue.Queue = queue.Queue(maxsize=200)

# # ─── Lazy module imports (graceful degradation) ───────────────────────────────
# import system_control as sc
# import messaging      as msg
# import web            as web_mod
# import media          as media_mod
# import files          as files_mod
# import expenses       as exp_mod

# # Give files module access to speak (avoids circular import)
# files_mod.set_speak_callback(lambda text: speak(text, blocking=False))


# # ─── GUI update helpers ───────────────────────────────────────────────────────
# def _q(kind: str, data: str) -> None:
#     """Non-blocking push to the GUI queue."""
#     try:
#         _gui_queue.put_nowait((kind, data))
#     except queue.Full:
#         pass


# def set_status(s: str) -> None:
#     _q("status", s)


# def show_user(text: str) -> None:
#     _q("user_msg", text)


# def show_float(text: str) -> None:
#     _q("float_msg", text)


# def show_sys(text: str) -> None:
#     _q("sys_msg", text)


# # ─── Response pipeline ────────────────────────────────────────────────────────
# def respond(text: str) -> None:
#     """Speak + display a FLOAT response."""
#     show_float(text)
#     speak(text, blocking=False)


# # ─── Command dispatcher ───────────────────────────────────────────────────────
# def dispatch(command_text: str) -> None:
#     """
#     Resolve intent, call the right module function, speak the reply.
#     Runs in a worker thread (Thread-3).
#     """
#     logger.info(f"Dispatch: {command_text}")
#     set_status("Thinking...")

#     intent   = route_intent(command_text)
#     entities = extract_entities(command_text, intent) if intent else {"raw": command_text}

#     result = ""
#     try:
#         # ── System Control ──────────────────────────────────────────────────
#         if intent == "wifi":
#             result = sc.toggle_wifi(entities.get("state", "on"))

#         elif intent == "bluetooth":
#             result = sc.toggle_bluetooth(entities.get("state", "on"))

#         elif intent == "volume":
#             result = sc.set_volume(
#                 level=entities.get("level"),
#                 direction=entities.get("direction"),
#             )

#         elif intent == "brightness":
#             lvl = entities.get("level", 50)
#             result = sc.set_brightness(lvl)

#         elif intent == "open_app":
#             result = sc.open_app(entities.get("app", command_text))

#         elif intent == "screenshot":
#             result = sc.take_screenshot()

#         elif intent == "lock":
#             result = sc.lock_screen()

#         elif intent == "shutdown":
#             result = sc.power_action("shutdown")

#         elif intent == "restart":
#             result = sc.power_action("restart")

#         elif intent == "sleep":
#             result = sc.power_action("sleep")

#         elif intent == "clipboard":
#             result = sc.get_clipboard()

#         # ── Messaging ───────────────────────────────────────────────────────
#         elif intent == "whatsapp":
#             if entities.get("is_group"):
#                 group   = entities.get("group", "")
#                 message = entities.get("message", "")
#                 if group and message:
#                     result = msg.send_whatsapp_group(group, message)
#                 else:
#                     result = "Please tell me the group name and the message."
#             else:
#                 contact = entities.get("contact", "")
#                 message = entities.get("message", "")
#                 if contact and message:
#                     result = msg.send_whatsapp(contact, message)
#                 elif contact:
#                     result = f"What message should I send to {contact}?"
#                 else:
#                     result = "Please tell me who to text and what message to send."

#         elif intent == "save_contact":
#             name  = entities.get("name", "")
#             phone = entities.get("phone", "")
#             if name and phone:
#                 result = msg.add_contact(name, phone)
#             else:
#                 result = ("Please say something like: save Mom's number as "
#                           "plus 91 9876543210.")

#         elif intent == "lookup_contact":
#             name = entities.get("name", "")
#             if name:
#                 result = msg.lookup_contact(name)
#             else:
#                 result = "Whose number would you like me to look up?"

#         elif intent == "email":
#             # For email, ask Groq to parse it conversationally
#             result = ask_groq(command_text)

#         elif intent == "read_email":
#             result = msg.read_emails()

#         # ── Media ───────────────────────────────────────────────────────────
#         elif intent == "play_music":
#             song   = entities.get("song", command_text)
#             source = entities.get("source", "auto")
#             result = media_mod.play_music(song, source)

#         elif intent == "pause_music":
#             result = media_mod.pause_music()

#         elif intent == "next_track":
#             result = media_mod.next_track()

#         elif intent == "prev_track":
#             result = media_mod.prev_track()

#         # ── Web ─────────────────────────────────────────────────────────────
#         elif intent == "weather":
#             city = entities.get("city")
#             result = web_mod.get_weather(city)

#         elif intent == "news":
#             result = web_mod.get_news()

#         elif intent == "search":
#             query  = entities.get("query", command_text)
#             result = web_mod.google_search(query)

#         elif intent == "wikipedia":
#             query  = entities.get("query", command_text)
#             result = web_mod.wikipedia_search(query)

#         elif intent == "open_site":
#             result = web_mod.open_site(command_text)

#         # ── Files & Productivity ────────────────────────────────────────────
#         elif intent == "reminder":
#             task   = entities.get("task", "task")
#             amount = entities.get("amount", 1)
#             unit   = entities.get("unit", "minute")
#             result = files_mod.set_reminder(task, amount, unit)

#         elif intent == "todo":
#             raw = entities.get("raw", command_text).lower()
#             if "list" in raw or "show" in raw or "read" in raw:
#                 result = files_mod.list_todos()
#             else:
#                 # Extract what to add
#                 import re
#                 m = re.search(
#                     r"(?:add|remind|put)\s+(.+?)\s+(?:to|in)\s+(?:my\s+)?to-?do",
#                     raw, re.I
#                 )
#                 item = m.group(1) if m else raw
#                 result = files_mod.add_todo(item)

#         elif intent == "calculate":
#             expr   = entities.get("expression", command_text)
#             result = files_mod.calculate(expr)

#         elif intent == "timer":
#             amount = entities.get("amount", 1)
#             unit   = entities.get("unit", "minute")
#             result = files_mod.set_timer(amount, unit)

#         elif intent == "stopwatch":
#             if "stop" in command_text.lower():
#                 result = files_mod.stop_stopwatch()
#             else:
#                 result = files_mod.start_stopwatch()

#         elif intent == "read_file":
#             filename = entities.get("filename", "")
#             result   = files_mod.read_file(filename)

#         # ── Financial Tracking ──────────────────────────────────────────────
#         elif intent == "add_expense":
#             amt = entities.get("amount", 0)
#             cat = entities.get("category", "other")
#             result = exp_mod.add_expense(amt, cat)

#         elif intent == "expense_summary":
#             period = entities.get("period", "month")
#             result = exp_mod.get_summary(period)

#         # ── Language Switching ──────────────────────────────────────────────
#         elif intent == "language":
#             from voice import set_language
#             raw = command_text.lower()
#             if "hindi" in raw or "हिंदी" in raw or "हिन्दी" in raw:
#                 set_language("hi")
#                 result = "ठीक है सर, मैं अब हिंदी में बात करूँगा।"
#             elif "english" in raw or "इंग्लिश" in raw or "अंग्रेजी" in raw:
#                 set_language("en")
#                 result = "Sure sir, I will speak in English now."
#             else:
#                 result = "Which language should I switch to?"

#         # ── Groq fallback ────────────────────────────────────────────────────
#         else:
#             result = ask_groq(command_text)

#     except Exception as e:
#         logger.error(f"Dispatch error for '{command_text}': {e}", exc_info=True)
#         result = "I couldn't complete that, sorry."

#     if not result:
#         result = "Done."

#     respond(result)
#     set_status("Sleeping...")


# def _dispatch_thread(command_text: str) -> None:
#     """Spawn a worker thread for each command."""
#     t = threading.Thread(
#         target=dispatch, args=(command_text,), daemon=True, name="CmdThread"
#     )
#     t.start()


# # ─── Wake word callbacks ──────────────────────────────────────────────────────
# def _on_wake() -> None:
#     show_sys("Wake word detected!")
#     set_status("Listening...")


# def _on_command(text: str) -> None:
#     show_user(text)
#     _dispatch_thread(text)


# # ─── Text input callback (from GUI) ──────────────────────────────────────────
# def _on_text_command(text: str) -> None:
#     show_user(text)
#     _dispatch_thread(text)


# # ─── Entry point ─────────────────────────────────────────────────────────────
# def main() -> None:
#     logger.info(f"FLOAT v{FLOAT_VERSION} starting...")

#     # Start reminder scheduler
#     files_mod.start_scheduler()

#     # Start wake word listener
#     ww = WakeWordListener(
#         on_wake_callback=_on_wake,
#         on_command_callback=_on_command,
#         status_queue=_gui_queue,
#     )
#     ww.start()

#     # Launch GUI (must be on main thread)
#     from gui import FloatGUI
#     app = FloatGUI(
#         gui_queue=_gui_queue, 
#         on_text_command=_on_text_command,
#         on_mic_command=ww.trigger_wake
#     )

#     # Greeting
#     greeting = "Hey! I'm Float, your personal AI assistant. How can I help you, sir?"
#     show_float(greeting)
#     speak(greeting, blocking=False)

#     logger.info("GUI event loop starting")
#     try:
#         app.mainloop()
#     except KeyboardInterrupt:
#         pass
#     finally:
#         ww.stop()
#         logger.info("FLOAT shut down cleanly.")
#         sys.exit(0)


# if __name__ == "__main__":
#     main()
