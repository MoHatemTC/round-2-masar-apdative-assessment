
def test_get_question_does_not_return_answer_keys(client, fake_db):
    question = fake_db.seed(
        "question_bank",
        {
            "body": "What is Python?",
            "tool_type": "mcq",
            "difficulty": 2,
            "is_active": True,
            "competency": {
                "id": "1",
                "name": "python",
                "code": "Python",
            },
            "payload": {
                "correct_id": "A",
                "answer_key": "A",
                "rubric": {},
                "test_cases": [],
            },
        },
    )

    response = client.get(f"/questions/{question['id']}")

    assert response.status_code == 200

    body = response.json()

    assert "payload" not in body