# estimate_level Contract

Owner:
Estimator Lane

Status:
Frozen

The estimate_level function is a pure deterministic function.

It must not:
- access database
- call APIs
- mutate global state
- depend on timestamps


## Input

score:
- integer 0-5

difficulty:
- question difficulty

posterior:
- current probability distribution over levels


## Output

Returns:

{
    level: 1-5,
    confidence: float,
    posterior: dict,
    level_history
}


## Algorithm

1. Convert score+difficulty into likelihood.
2. Multiply posterior by likelihood.
3. Normalize probabilities.
4. Pick argmax level.
5. Calculate confidence.


## Confidence

Confidence must be:

1 - normalized spread


## Stop Conditions

Stop when:

- confidence >= 0.90

OR

- same level appears 3 times consecutively

OR

- question count reaches 10

If stopped by cap:

low_confidence=true


This contract must remain stable.
Any changes require agreement from estimator owner.