from random import randint
from flask import Flask, request, render_template, jsonify
from opentelemetry import trace
from opentelemetry import metrics
from opentelemetry.metrics import Observation
import logging
import json

success_count_this_session = 0;
failure_count_this_session = 0;

# Acquire a tracer
tracer = trace.get_tracer("diceroller.tracer")

# Acquire a meter
meter = metrics.get_meter("diceroller.meter")

# Create a counter instrument to track measurements
roll_counter = meter.create_counter(
    "dice.rolls",
    description="The number of rolls by roll value",
)

# Create a counter to track some stats about the rolls
crit_counter = meter.create_counter(
    "dice.crits",
    description="The number of critical success rolls",
)

def success_rate_callback(options):
    try:
        total = success_count_this_session + failure_count_this_session
        if total > 0:
            return [Observation(success_count_this_session / total)]
        else:
            return [Observation(0)]
    except Exception as e:
        logger.error(f"Error in success_rate_callback: {e}")
        return [Observation(0)]

# Create a gauge to expose different visualization
roll_success_gauge = meter.create_observable_gauge(
    name="dice.roll_success_gauge",
    description="How often the rolls were likely successful",
    unit="1",
    callbacks=[success_rate_callback]
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/")
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Enable debug mode
    app.run(debug=True)

@app.route("/rolldice")
def roll_dice():
    global success_count_this_session, failure_count_this_session
    player = request.args.get('player', default=None, type=str)
    result = str(roll())
    if player:
        logger.warning("%s is rolling the dice: %s", player, result)
    else:
        logger.warning("Anonymous player is rolling the dice: %s", result)
    return result

def roll():
    global success_count_this_session, failure_count_this_session

    # This creates a new span that's the child of the current one
    with tracer.start_as_current_span("roll") as rollspan:
        hasAdvantage = (randint(0, 2) == 2)
        if hasAdvantage:  #one-third of the time
            roll1 = randint(1, 20)
            roll2 = randint(1, 20)
            res = max(roll1, roll2)
            rawRollsDict = { "roll1": roll1, "roll2": roll2}
            if (roll1 == roll2):
                rollspan.set_attribute("roll.tag", "Both rolls were the same; isn't that interesting?")
        else:
            res = roll1 = roll2 = randint(1, 20)
            rawRollsDict = { "res": res}

        # store the raw rolls, which could be 1 or 2 values in a serialized dictionary
        rawRolls = json.dumps(rawRollsDict)
        rollspan.set_attribute("roll.rawRolls", rawRolls)

        rollspan.set_attribute("roll.value", res)
        if res == 20:
            crit_counter.add(1, {"roll.rolledWithAdvantage": hasAdvantage})
        rollspan.set_attribute("roll.rolledWithAdvantage", hasAdvantage)
        if res >= 15:
            success_count_this_session += 1
        else:
            failure_count_this_session += 1
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