"""Runs the holiday mode YAML in a real Home Assistant core with fake covers, alarm and phones.

docker run --rm -v "$PWD:/repo" ghcr.io/home-assistant/home-assistant:$(cat homeassistant/config/.HA_VERSION) \
    python3 /repo/tests/holiday_mode_test.py
"""
import asyncio
import datetime as dt
import logging
import pathlib
import sys
import tempfile

from homeassistant import bootstrap, config_entries, loader
from homeassistant.core import Context, HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.util.yaml import load_yaml

CONFIG = pathlib.Path(__file__).resolve().parent.parent / "homeassistant/config"
STOPPED_BY_SCRIPT = {
    "cover.curtains_livingroom_right": 60,
    "cover.curtains_livingroom_left": 60,
    "cover.estores_escritorio": 60,
    "cover.estores_lavandaria": 60,
    "cover.curtains_kitchen": 60,
    "cover.curtains_hall": 35,
    "cover.curtains_wcsuite": 25,
}
SELF_STOPPING = ["cover.curtains_guestroom", "cover.curtains_suite"]
NO_REPORTS_WHILE_MOVING = "cover.estores_lavandaria"  # Shelly 2.5: only the start and the end, stops by itself
ALL_COVERS = [*STOPPED_BY_SCRIPT, *SELF_STOPPING]
STEP_SECONDS = 0.4


class House:
    """The hardware: covers that echo the target before moving and may ignore a stop, the alarm and the phones."""

    def __init__(self, hass):
        self.hass = hass
        self.calls = []
        self.motors = {}
        self.real_position = {}  # what a stop reports; during the echo it differs from the reported one
        self.echo_delay = {}
        self.stops_to_ignore = {}
        self.alarm_refuses = False

    def install_services(self):
        """Called after startup, otherwise the real cover, light and alarm integrations replace these."""
        hass = self.hass
        for service in ("open_cover", "close_cover", "set_cover_position", "stop_cover"):
            hass.services.async_register("cover", service, self.cover_service)
        for domain, service in (("light", "turn_on"), ("light", "turn_off"), ("switch", "turn_on"),
                                ("switch", "turn_off"), ("notify", "ha_mobile_apps")):
            hass.services.async_register(domain, service, self.record)
        hass.services.async_register("alarm_control_panel", "alarm_arm_away", self.arm)
        hass.services.async_register("alarm_control_panel", "alarm_disarm", self.record)

    async def record(self, call):
        self.calls.append((f"{call.domain}.{call.service}", dict(call.data)))

    async def arm(self, call):
        await self.record(call)
        if not self.alarm_refuses:
            self.hass.states.async_set("alarm_control_panel.casa", "armed_away")

    async def cover_service(self, call):
        await self.record(call)
        entities = call.data.get("entity_id") or []
        for entity in [entities] if isinstance(entities, str) else entities:
            if call.service == "set_cover_position":
                self.stop_motor(entity)
                self.motors[entity] = asyncio.create_task(self.move(entity, call.data["position"]))
            elif call.service == "stop_cover":
                if self.stops_to_ignore.get(entity, 0) > 0:
                    self.stops_to_ignore[entity] -= 1
                elif self.stop_motor(entity):
                    self.set_cover(entity, "open", self.real_position[entity])
            else:
                self.stop_motor(entity)
                opened = call.service == "open_cover"
                self.set_cover(entity, "open" if opened else "closed", 100 if opened else 0)

    async def move(self, entity, target):
        position = self.real_position[entity] = self.position(entity)
        if entity == NO_REPORTS_WHILE_MOVING:
            self.set_cover(entity, "opening", position)
            await asyncio.sleep(3)
            self.real_position[entity] = target
            self.set_cover(entity, "open", target)
            return
        await asyncio.sleep(self.echo_delay.get(entity, 0.2))
        self.set_cover(entity, "open", target)
        await asyncio.sleep(0.1)
        self.set_cover(entity, "opening", target)
        # Only the two self-stopping covers obey the target; the others run to the top unless stopped (worst case).
        limit = target if entity in SELF_STOPPING else 100
        while position < limit:
            await asyncio.sleep(STEP_SECONDS)
            position = self.real_position[entity] = min(position + 4, limit)
            self.set_cover(entity, "opening", position)
        self.set_cover(entity, "open", position)

    def stop_motor(self, entity):
        motor = self.motors.pop(entity, None)
        if motor is None or motor.done():
            return False
        motor.cancel()
        return True

    def position(self, entity):
        return self.hass.states.get(entity).attributes["current_position"]

    def set_cover(self, entity, state, position):
        self.hass.states.async_set(entity, state, {"current_position": position})

    def called(self, service):
        return [data for name, data in self.calls if name == service]

    def reset(self, *, covers_at=0):
        for entity in ALL_COVERS:
            self.stop_motor(entity)
            self.set_cover(entity, "closed" if covers_at == 0 else "open", covers_at)
        self.calls.clear()
        self.echo_delay.clear()
        self.stops_to_ignore.clear()
        self.alarm_refuses = False
        self.hass.states.async_set("alarm_control_panel.casa", "disarmed")


def load(path):
    return load_yaml(str(CONFIG / path))


def build_config():
    automations = [load(path.relative_to(CONFIG)) for path in sorted((CONFIG / "automations/holiday").glob("*.yaml"))]
    arrival = next(a for a in automations if a["id"] == "holiday_exit_on_arrival")
    assert arrival["triggers"][0]["for"] == "00:05:00"
    arrival["triggers"][0]["for"] = {"seconds": 1}
    return {
        "homeassistant": {"time_zone": "Europe/Lisbon", "latitude": 38.5, "longitude": -8.9, "elevation": 0,
                          "unit_system": "metric", "country": "PT", "currency": "EUR"},
        "input_boolean": load("integrations/input_boolean.yaml")["input_boolean"],
        "input_datetime": load("integrations/input_datetime.yaml")["input_datetime"],
        "input_text": {"active_mode": {}},
        "template": load("integrations/sensors/presence.yaml")["template"],
        "script": {**load("scripts/mode_sleep.yaml"), **load("scripts/mode_holiday_morning.yaml"),
                   **load("scripts/open_cover_to_position.yaml")},
        "automation": automations,
    }


async def settle(hass, house, seconds=60):
    """Waits until no script, automation or motor is running."""
    quiet = 0
    for _ in range(int(seconds / 0.2)):
        await asyncio.sleep(0.2)
        busy = (any(s.state == "on" for s in hass.states.async_all("script"))
                or any(s.attributes.get("current", 0) for s in hass.states.async_all("automation"))
                or any(not motor.done() for motor in house.motors.values()))
        quiet = 0 if busy else quiet + 1
        if quiet >= 5:
            return
    running = [s.entity_id for s in hass.states.async_all(("script", "automation"))
               if s.attributes.get("current", 0)]
    moving = [entity for entity, motor in house.motors.items() if not motor.done()]
    raise AssertionError(f"the house never settled: running {running}, moving {moving}")


async def call(hass, domain, service, **data):
    await hass.services.async_call(domain, service, data, blocking=True, context=Context())


async def people(hass, house, *, home):
    state = "home" if home else "not_home"
    hass.states.async_set("person.marco_cunha", state)
    hass.states.async_set("person.darlene_parreira", "not_home")
    await asyncio.sleep(0.3)


async def holiday(hass, house, on):
    await call(hass, "input_boolean", "turn_on" if on else "turn_off", entity_id="input_boolean.holiday_mode")
    await asyncio.sleep(0.3)


async def fresh(hass, house, *, home, mode_on, covers_at=0):
    await holiday(hass, house, False)
    await people(hass, house, home=home)
    await settle(hass, house)
    if mode_on:
        await holiday(hass, house, True)
        await settle(hass, house)
    house.reset(covers_at=covers_at)


def assert_stopped_near_target(house):
    for entity, target in STOPPED_BY_SCRIPT.items():
        final = house.position(entity)
        # A premature stop (on the echo) would leave it near 0; no stop at all would leave it at 100.
        assert target - 3 <= final <= target + 8, (entity, target, final)
    for entity in SELF_STOPPING:
        assert house.position(entity) == 25, (entity, house.position(entity))


async def test_morning_stops_every_cover_near_its_target(hass, house):
    await fresh(hass, house, home=False, mode_on=False)
    # Echo latency seen on the real covers: 0.2 s to 1.9 s.
    house.echo_delay = {entity: delay for entity, delay in zip(STOPPED_BY_SCRIPT, [0.2, 0.7, 1.9, 0.2, 1.9, 0.5, 1.2])}
    await call(hass, "script", "turn_on", entity_id="script.mode_holiday_morning")
    await settle(hass, house)
    assert_stopped_near_target(house)
    assert hass.states.get("input_text.active_mode").state == "MORNING"
    assert not house.called("alarm_control_panel.alarm_disarm")
    assert not house.called("cover.open_cover")


async def test_ignored_stop_is_sent_again(hass, house):
    await fresh(hass, house, home=False, mode_on=False)
    house.stops_to_ignore = {entity: 1 for entity in STOPPED_BY_SCRIPT}
    await call(hass, "script", "turn_on", entity_id="script.mode_holiday_morning")
    await settle(hass, house)
    for entity, target in STOPPED_BY_SCRIPT.items():
        if entity == NO_REPORTS_WHILE_MOVING:
            assert house.position(entity) == target
            continue
        final = house.position(entity)
        assert target - 3 <= final <= target + 25, (entity, target, final)
        stops = [d for d in house.called("cover.stop_cover") if entity in str(d)]
        assert len(stops) == 2, (entity, len(stops))


async def test_cover_already_open_enough_is_left_alone(hass, house):
    await fresh(hass, house, home=False, mode_on=False, covers_at=80)
    await call(hass, "script", "turn_on", entity_id="script.mode_holiday_morning")
    await settle(hass, house)
    commanded = str(house.called("cover.set_cover_position") + house.called("cover.stop_cover"))
    for entity in STOPPED_BY_SCRIPT:
        assert entity not in commanded, entity


async def run_at_drawn_time(hass, house, helper):
    at = (dt_util.now() + dt.timedelta(seconds=2)).strftime("%H:%M:%S")
    await call(hass, "input_datetime", "set_datetime", entity_id=helper, time=at)
    await asyncio.sleep(3)
    await settle(hass, house)


async def test_open_time_runs_only_in_holiday_mode_even_with_someone_home(hass, house):
    await fresh(hass, house, home=True, mode_on=False)
    await run_at_drawn_time(hass, house, "input_datetime.holiday_open_time")
    assert not house.called("cover.set_cover_position")

    await fresh(hass, house, home=True, mode_on=True)
    await run_at_drawn_time(hass, house, "input_datetime.holiday_open_time")
    assert_stopped_near_target(house)


async def test_close_time_with_empty_house_arms(hass, house):
    await fresh(hass, house, home=False, mode_on=True)
    await run_at_drawn_time(hass, house, "input_datetime.holiday_close_time")
    assert house.called("cover.close_cover")
    assert house.called("alarm_control_panel.alarm_arm_away")


async def test_close_time_with_someone_home_does_not_arm_nor_complain(hass, house):
    await fresh(hass, house, home=True, mode_on=True)
    await run_at_drawn_time(hass, house, "input_datetime.holiday_close_time")
    assert house.called("cover.close_cover")
    assert not house.called("alarm_control_panel.alarm_arm_away")
    assert not house.called("notify.ha_mobile_apps")


async def test_sleep_button_still_arms_with_someone_home(hass, house):
    await fresh(hass, house, home=True, mode_on=False)
    await call(hass, "script", "turn_on", entity_id="script.mode_sleep")
    await settle(hass, house)
    assert house.called("alarm_control_panel.alarm_arm_away")


async def test_alarm_arms_on_activation_or_when_the_last_one_leaves(hass, house):
    await fresh(hass, house, home=False, mode_on=False)
    await holiday(hass, house, True)
    await settle(hass, house)
    assert len(house.called("alarm_control_panel.alarm_arm_away")) == 1

    await fresh(hass, house, home=True, mode_on=False)
    await holiday(hass, house, True)
    await settle(hass, house)
    assert not house.called("alarm_control_panel.alarm_arm_away")
    await people(hass, house, home=False)
    await settle(hass, house)
    assert len(house.called("alarm_control_panel.alarm_arm_away")) == 1

    await fresh(hass, house, home=True, mode_on=False)
    await people(hass, house, home=False)
    await settle(hass, house)
    assert not house.called("alarm_control_panel.alarm_arm_away")


async def test_activation_reports_an_alarm_that_does_not_arm(hass, house):
    await fresh(hass, house, home=False, mode_on=False)
    house.alarm_refuses = True
    await holiday(hass, house, True)
    await settle(hass, house)
    assert "armar o alarme" in str(house.called("notify.ha_mobile_apps"))


async def test_arrival_turns_the_mode_off_but_a_restart_blip_does_not(hass, house):
    await fresh(hass, house, home=False, mode_on=True)
    await people(hass, house, home=True)
    await asyncio.sleep(1.5)
    await settle(hass, house)
    assert hass.states.get("input_boolean.holiday_mode").state == "off"
    assert house.called("notify.ha_mobile_apps")

    await fresh(hass, house, home=False, mode_on=True)
    hass.states.async_set("binary_sensor.anyone_home", "unavailable")
    await asyncio.sleep(0.3)
    hass.states.async_set("binary_sensor.anyone_home", "on")
    await asyncio.sleep(1.5)
    await settle(hass, house)
    assert hass.states.get("input_boolean.holiday_mode").state == "on"


async def test_leaving_stamps_the_time(hass, house):
    await fresh(hass, house, home=True, mode_on=False)
    await call(hass, "input_datetime", "set_datetime", entity_id="input_datetime.nobody_home_since",
               datetime="2026-01-01 00:00:00")
    await people(hass, house, home=False)
    await settle(hass, house)
    stamp = hass.states.get("input_datetime.nobody_home_since").attributes["timestamp"]
    assert abs(dt_util.utcnow().timestamp() - stamp) < 30, stamp


async def suggest(hass, house, *, hours_away, home, mode_on):
    await fresh(hass, house, home=home, mode_on=mode_on)
    since = dt_util.now() - dt.timedelta(hours=hours_away)
    await call(hass, "input_datetime", "set_datetime", entity_id="input_datetime.nobody_home_since",
               timestamp=since.timestamp())
    await call(hass, "automation", "trigger", entity_id="automation.holiday_suggest_holiday_mode",
               skip_condition=False)
    await settle(hass, house)
    return house.called("notify.ha_mobile_apps")


async def test_suggestion_only_after_a_day_away(hass, house):
    asked = await suggest(hass, house, hours_away=25, home=False, mode_on=False)
    assert [a["action"] for a in asked[0]["data"]["actions"]] == ["HOLIDAY_MODE_ON", "HOLIDAY_MODE_IGNORE"]
    assert not await suggest(hass, house, hours_away=23, home=False, mode_on=False)
    assert not await suggest(hass, house, hours_away=25, home=True, mode_on=False)
    assert not await suggest(hass, house, hours_away=25, home=False, mode_on=True)


async def test_notification_answers(hass, house):
    for action, expected in (("HOLIDAY_MODE_IGNORE", "off"), ("HOLIDAY_MODE_ON", "on"), ("TURN_OFF_x", "off")):
        await fresh(hass, house, home=False, mode_on=False)
        hass.bus.async_fire("mobile_app_notification_action", {"action": action})
        await asyncio.sleep(0.5)
        await settle(hass, house)
        assert hass.states.get("input_boolean.holiday_mode").state == expected, action
        cleared = [d for d in house.called("notify.ha_mobile_apps") if d["message"] == "clear_notification"]
        assert bool(cleared) == action.startswith("HOLIDAY"), action


async def test_drawn_times_stay_in_their_windows(hass, house):
    await fresh(hass, house, home=False, mode_on=False)
    sunsets = {
        "2026-12-21T17:18:00+00:00": ("18:00", "18:30"),  # winter, before the window
        "2026-06-21T20:05:00+00:00": ("19:30", "20:00"),  # summer (21:05 local), after the window
        "2026-09-10T18:50:00+00:00": ("19:30", "20:00"),  # 19:50 local
        "2026-04-01T18:00:00+00:00": ("18:45", "19:15"),  # 19:00 local, follows the sunset
    }
    for sunset, (first, last) in sunsets.items():
        hass.states.async_set("sun.sun", "above_horizon", {"next_setting": sunset})
        for _ in range(60):
            await call(hass, "automation", "trigger", entity_id="automation.holiday_pick_the_times_of_the_day")
            await asyncio.sleep(0.02)
            opening = hass.states.get("input_datetime.holiday_open_time").state[:5]
            closing = hass.states.get("input_datetime.holiday_close_time").state[:5]
            assert "08:00" <= opening <= "08:59", opening
            assert first <= closing <= last, (sunset, closing)


async def main():
    with tempfile.TemporaryDirectory() as directory:
        hass = HomeAssistant(directory)
        loader.async_setup(hass)
        hass.config_entries = config_entries.ConfigEntries(hass, {})
        await bootstrap.async_load_base_functionality(hass)
        house = House(hass)
        hass.states.async_set("sun.sun", "above_horizon", {"next_setting": "2026-12-21T17:18:00+00:00"})
        hass.states.async_set("person.marco_cunha", "home")
        hass.states.async_set("person.darlene_parreira", "home")
        house.reset()
        assert await bootstrap.async_from_config_dict(build_config(), hass)
        await hass.async_start()
        await hass.async_block_till_done()
        house.install_services()

        failed = 0
        tests = [fn for name, fn in globals().items() if name.startswith("test_")]
        for test in tests:
            try:
                await test(hass, house)
                print("PASS", test.__name__)
            except Exception as error:
                failed += 1
                print("FAIL", test.__name__, repr(error))
        await hass.async_stop(force=True)
        print(f"{len(tests) - failed}/{len(tests)} passed")
        return failed


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    sys.exit(1 if asyncio.run(main()) else 0)
