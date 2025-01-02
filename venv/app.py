from random import randint
from flask import Flask, request
from opentelemetry import trace
from opentelemetry import metrics
import logging

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
        pass
        #logger.warning("%s is rolling the dice: %s", player, result)
    else:
        pass
        #logger.warning("Anonymous player is rolling the dice: %s", result)
    return result


def roll():
    # This creates a new span that's the child of the current one
    with tracer.start_as_current_span("roll") as rollspan:
        res = randint(1, 20)
        rollspan.set_attribute("roll.value", res)
        rollspan.set_attribute("roll.crit", 1 if res == 20 else 0)
        roll_counter.add(1, {"roll.value": res})

        if (res == 1):
            rollspan.record_exception(Exception("Critical fail!"))

        return res