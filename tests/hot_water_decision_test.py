"""Renders the real hot water decision template with stubbed states.

Run inside the HA image so Jinja2 and PyYAML are the ones Home Assistant uses:
docker run --rm -v "$PWD:/repo" ghcr.io/home-assistant/home-assistant:$(cat homeassistant/config/.HA_VERSION) \
    python3 /repo/tests/hot_water_decision_test.py
"""
import datetime as dt
import pathlib
import sys
from zoneinfo import ZoneInfo

import yaml
from jinja2 import Environment

PACKAGE = pathlib.Path(__file__).resolve().parent.parent / "homeassistant/config/integrations/sensors/hot_water.yaml"
LISBON = ZoneInfo("Europe/Lisbon")


def at(month, day, hour, minute=0):
    return dt.datetime(2026, month, day, hour, minute, tzinfo=LISBON)


def _binary_sensor():
    for block in yaml.safe_load(PACKAGE.read_text())["template"]:
        for sensor in block.get("binary_sensor", []):
            if sensor.get("unique_id") == "hot_water_resistance_wanted":
                return sensor
    raise AssertionError("binary sensor hot_water_resistance_wanted not found")


def wanted(*, now, override="Auto", temp=55.0, switch="off", schedule="off", next_event=None, net=200.0,
           winter=55.0, summer=50.0, surplus_max=60.0):
    states = {
        "input_select.hot_water_override": override,
        "sensor.hot_water_temperature": "unavailable" if temp is None else str(temp),
        "switch.resistencia_termoacumulador_switch_0": switch,
        "schedule.hotwater_schedule": schedule,
        "sensor.energy_consumption_mean_over_last_10_minutes": str(net),
        "input_number.desired_hot_water_temperature_winter": str(winter),
        "input_number.desired_hot_water_temperature_summer": str(summer),
        "input_number.hot_water_surplus_max_temp": str(surplus_max),
    }
    env = Environment()
    env.globals.update(
        now=lambda: now,
        states=lambda entity: states.get(entity, "unknown"),
        is_state=lambda entity, value: states.get(entity) == value,
        state_attr=lambda entity, attr: next_event if (entity, attr) == ("schedule.hotwater_schedule", "next_event") else None,
        as_timestamp=lambda value: value.timestamp(),
    )
    sensor = _binary_sensor()
    if env.from_string(sensor["availability"]).render().strip().lower() != "true":
        return None
    return env.from_string(sensor["state"]).render().strip().lower() == "true"


def test_summer_morning_start():
    monday_seven = at(7, 6, 7)
    assert wanted(now=at(7, 6, 5, 0), temp=47, next_event=monday_seven) is False
    assert wanted(now=at(7, 6, 5, 30), temp=47, next_event=monday_seven) is True


def test_winter_morning_start():
    monday_seven = at(11, 9, 7)
    assert wanted(now=at(11, 9, 4, 50), temp=50, next_event=monday_seven) is False
    assert wanted(now=at(11, 9, 5, 0), temp=50, next_event=monday_seven) is True


def test_no_start_when_warm_enough():
    assert wanted(now=at(11, 9, 6, 0), temp=57, next_event=at(11, 9, 7)) is False


def test_in_window_low_and_keep():
    window = dict(now=at(11, 9, 7, 30), schedule="on", next_event=at(11, 9, 9), net=2500)
    assert wanted(temp=53, switch="off", **window) is True
    assert wanted(temp=59.9, switch="on", **window) is True
    assert wanted(temp=60.0, switch="on", **window) is False


def test_override():
    assert wanted(now=at(11, 9, 12), override="Ligada", temp=70) is True
    assert wanted(now=at(11, 9, 7, 30), override="Desligada", temp=40, schedule="on", next_event=at(11, 9, 9)) is False


def test_surplus():
    base = dict(now=at(11, 9, 11), schedule="off", next_event=at(11, 9, 19, 30))
    assert wanted(temp=50, net=-2000, **base) is True
    assert wanted(temp=50, net=-1000, **base) is False
    assert wanted(temp=61, net=-2000, **base) is False
    assert wanted(temp=50, net=600, switch="on", **base) is False
    assert wanted(temp=55, net=400, switch="on", **base) is True


def test_season_boundaries():
    def low_in_window(month, day):
        return wanted(now=at(month, day, 7, 30), temp=52, schedule="on", next_event=at(month, day, 9))

    assert low_in_window(5, 31) is True
    assert low_in_window(6, 1) is False
    assert low_in_window(9, 30) is False
    assert low_in_window(10, 1) is True


def test_sunday_to_monday():
    assert wanted(now=at(11, 8, 22, 30), temp=44, next_event=at(11, 9, 7)) is False
    assert wanted(now=at(11, 9, 4, 30), temp=44, next_event=at(11, 9, 7)) is True
    assert wanted(now=at(11, 8, 8, 0), temp=44, next_event=at(11, 8, 19, 30)) is False


def test_unavailable_temperature():
    assert wanted(now=at(11, 9, 5), temp=None, next_event=at(11, 9, 7)) is None
    assert wanted(now=at(11, 9, 5), temp=None, override="Ligada", next_event=at(11, 9, 7)) is True
    assert wanted(now=at(11, 9, 5), temp=None, override="Desligada", next_event=at(11, 9, 7)) is False


def test_trajectory_single_cycle():
    switch, temp, step = "off", 50.0, dt.timedelta(minutes=5)
    now, end, seven = at(11, 9, 4), at(11, 9, 7), at(11, 9, 7)
    turned_on = turned_off = on_steps = 0
    while now <= end:
        schedule, next_event = ("on", at(11, 9, 9)) if now >= seven else ("off", seven)
        grid_import = 2200 if switch == "on" else 200
        decision = wanted(now=now, temp=round(temp, 2), switch=switch, schedule=schedule, next_event=next_event,
                          net=grid_import)
        if decision and switch == "off":
            switch, turned_on = "on", turned_on + 1
        elif not decision and switch == "on":
            switch, turned_off = "off", turned_off + 1
        on_steps += switch == "on"
        temp += 0.5 if switch == "on" else -0.05
        now += step
    assert (turned_on, turned_off) == (1, 1), (turned_on, turned_off)
    assert on_steps * 5 >= 45, on_steps
    assert temp >= 55, temp


if __name__ == "__main__":
    tests = [fn for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for fn in tests:
        fn()
    print(f"OK: {len(tests)} tests")
    sys.exit(0)
