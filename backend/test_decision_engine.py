from decision_engine import DecisionEngine


engine = DecisionEngine()

print("Testing access granted...")

for _ in range(15):
    decision = engine.update(["helmet", "vest"])

print(decision)
assert decision.status == "ACCESS GRANTED"


engine.reset()

print("Testing access denied...")

for _ in range(15):
    decision = engine.update(["Person", "no_helmet", "vest"])

print(decision)
assert decision.status == "ACCESS DENIED"


engine.reset()

print("Testing manager review...")

for frame_number in range(15):
    if frame_number % 2 == 0:
        classes = ["helmet", "vest"]
    else:
        classes = ["Person"]

    decision = engine.update(classes)

print(decision)
assert decision.status == "MANAGER REVIEW"

print("All decision-engine tests passed!")