from part4_agents import create_lesson, load_json, print_run, run_question, save_lessons

REPEATED = 2

def main():
    reference = load_json("reference_data.json")
    training = load_json("training_data.json")
    lessons = []
    save_lessons(lessons)
    print("Controlled test case (4.1): the first answer is intentionally incomplete")
    run = run_question(training[0], reference, use_repair=True, lessons=[],
                       first_answer="Upgrade lodash to a newer version.")
    print_run(run)
    print("\nTraining run (4.2)")
    pattern_counts = {}
    for item in training:
        run = run_question(item, reference, use_repair=True, lessons=lessons)
        print_run(run)

        pattern = run["first_failure_pattern"]
        if pattern is not None:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            already_saved = any(lesson["pattern"] == pattern for lesson in lessons)
            if pattern_counts[pattern] >= REPEATED and not already_saved:
                lesson = create_lesson(pattern, lessons)
                print(f"New lesson {lesson['lesson_id']} (failure pattern seen {pattern_counts[pattern]} times): {lesson['correction']}")
        save_lessons(lessons)
    print("\nFailure patterns in training:", pattern_counts)
    print(f"Saved {len(lessons)} lesson(s) in lessons.json")
    for lesson in lessons:
        print(f"{lesson['lesson_id']}: {lesson['failure_pattern']} (use_count {lesson['use_count']})")

if __name__ == "__main__":
    main()
