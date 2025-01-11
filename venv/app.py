from random import randint
from flask import Flask, request
from opentelemetry import trace
from opentelemetry import metrics
import logging
import json

# Acquire a tracer
tracer = trace.get_tracer("diceroller.tracer")

# Acquire a meter
meter = metrics.get_meter("diceroller.meter")

# Create a counter instrument to track measurements
roll_counter = meter.create_counter(
    "dice.rolls",
    description="The number of rolls by roll value",
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/rolldice")
def roll_dice():
    player = request.args.get('player', default=None, type=str)
    result = str(roll())
    if player:
        logger.warning("%s is rolling the dice: %s", player, result)
    else:
        logger.warning("Anonymous player is rolling the dice: %s", result)
    return result


def roll():
    # This creates a new span that's the child of the current one
    with tracer.start_as_current_span("roll") as rollspan:
        hasAdvantage = randint(0, 2)
        if hasAdvantage == 2:  # one-third of the time
            res = roll1 = roll2 = randint(1, 20)
            rawRollsDict = { "res": res}
            
        else:
            roll1 = randint(1, 20)
            roll2 = randint(1, 20)
            res = max(roll1, roll2)
            rawRollsDict = { "roll1": roll1, "roll2": roll2}
            if (roll1 == roll2):
                rollspan.set_attribute("roll.tag", "Both rolls were the same; isn't that interesting?")

        # store the raw rolls, which could be 1 or 2 values in a serialized dictionary
        rawRolls = json.dumps(rawRollsDict)
        rollspan.set_attribute("roll.rawRolls", rawRolls)

        rollspan.set_attribute("roll.value", res)
        rollspan.set_attribute("roll.crit", 1 if res == 20 else 0)
        rollspan.set_attribute("roll.rolledWithAdvantage", hasAdvantage)
        roll_counter.add(1, {"roll.value": res})

        try:
            if (hasAdvantage and ((roll1 == 1)  or (roll2 == 1))):
                raise AssertionError("The player rolled a 1, but thankfully, it didn't count")
            elif (res == 1):
                raise AssertionError("The player rolled a 1!")
        except AssertionError as e:
            rollspan.record_exception(e, attributes={"roll.value": 1})
            rollspan.set_status(trace.status.Status(trace.status.StatusCode.ERROR, str(e)))

        return f"{roll1}, {roll2} = {res}" if hasAdvantage else str(res)