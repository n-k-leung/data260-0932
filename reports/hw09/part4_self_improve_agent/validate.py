from part4_agents import load_json, load_lessons, question_topic, run_question, save_lessons

def run_set(items, reference, lessons):
    results = {}
    for item in items:
        results[item["id"]] = run_question(item, reference, use_repair=False, lessons=lessons)
    return results

def main():
    reference = load_json("reference_data.json")
    validation = load_json("validation_data.json")
    lessons = load_lessons()
    if not lessons:
        print("lessons.json has no lessons. Run train.py first.")
        return
    print("Validation before (no lessons)")
    before = run_set(validation, reference, [])
    for lesson in lessons:
        print(f"\nValidating lesson {lesson['lesson_id']}: {lesson['correction']}")
        after = run_set(validation, reference, [lesson])

        fixed = 0
        regressions = 0
        for item in validation:
            result_before = before[item["id"]]["final_result"]
            result_after = after[item["id"]]["final_result"]
            if result_before == "REVISE" and result_after == "PASS":
                fixed += 1
            if result_before == "PASS" and result_after == "REVISE":
                regressions += 1
            print(f"{item['id']} ({question_topic(item['question'])}): before {result_before}, after {result_after}")

        lesson["validated"] = regressions == 0
        lesson["validation_result"] = f"fixed {fixed}, regressions {regressions}"
        if lesson["validated"]:
            print(f"Keep {lesson['lesson_id']}: fixed {fixed}, regressions {regressions}")
        else:
            print(f"Remove {lesson['lesson_id']}: fixed {fixed}, regressions {regressions} (it made a correct answer fail)")
    save_lessons(lessons)
    print("\nSaved the validation result for each lesson in lessons.json")

if __name__ == "__main__":
    main()
