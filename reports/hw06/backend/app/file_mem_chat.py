from app import file_mem as fm
from app import llm_adapter


def main():
    messages = [{"role": "system", "content": fm.build_system_prompt()}]

    needed, reason = fm.needs_consolidation(fm.read_file(fm.MEMORY_FILE))
    if needed:
        print("[memory] consolidation needed:", reason, "-> type /compact")

    print("Paste code to review. Type /help for commands.")
    while True:
        try:
            user_input = input("you> ").strip()
        except EOFError:
            break
        if not user_input:
            continue
        if user_input == "/exit":
            break
        if user_input == "/help":
            print(fm.help_text())
            continue
        if user_input == "/memory":
            print(fm.show_memory())
            continue
        if user_input == "/compact":
            messages, text = fm.run_compact(messages)
            print(text)
            continue
        if user_input == "/dream":
            added = fm.run_dream(messages[-10:])
            print(f"[/dream] facts added to MEMORY.md: {len(added)}")
            for line in added:
                print(" ", line)
            messages[0] = {"role": "system", "content": fm.build_system_prompt()}
            needed, reason = fm.needs_consolidation(fm.read_file(fm.MEMORY_FILE))
            if needed:
                print("[memory] consolidation needed:", reason, "-> type /compact")
            continue

        messages.append({"role": "user", "content": user_input})
        try:
            reply, in_tokens, out_tokens = llm_adapter.chat(messages)
        except RuntimeError as e:
            print("model error:", e)
            messages.pop()
            continue
        messages.append({"role": "assistant", "content": reply})
        print("assistant>", reply)
        print(f"[tokens] input={in_tokens} output={out_tokens}")


if __name__ == "__main__":
    main()
