# Hot Water Resistance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatic control of the solar water heater resistance with comfort floors, surplus use, a 45 min minimum cycle and a three-state override.

**Architecture:** One template `binary_sensor` holds the whole decision as a pure function of states (the switch state is its memory), so it can be unit-tested by rendering its template with stubbed states. A thin automation applies the decision with a cycle-time guard. Two small automations handle manual-toggle-as-override and the daily override reset.

**Tech Stack:** Home Assistant YAML packages (2026.11.1), Jinja templates, a Python script run in the HA Docker image for the template tests, `yamllint` and HA `check_config` as in CI.

**Spec:** `specs/2026-11-10-hot-water-resistance-design.md`

## Global Constraints

- Comfort floor M: `input_number.desired_hot_water_temperature_winter` = 55 (1 Oct to 31 May); `input_number.desired_hot_water_temperature_summer` = 50 (1 Jun to 30 Sep). Target A = M + 5.
- Windows (`schedule.hotwater_schedule`, key unchanged): Mon-Fri 07:00-09:00 and 19:30-21:30; Sat 09:00-13:00 and 19:30-21:30; Sun 19:30-21:30.
- Constants in a `variables:` style block inside the template: heating 6 C/h, loss 0.6 C/h, start margin 1.25, keep margin 1.5 + 0.5 h, surplus start when 10 min mean below -1800 W, surplus stop when above +500 W, `input_number.hot_water_surplus_max_temp` = 60.
- Minimum 45 min between automatic changes, timed with `input_datetime.hot_water_last_switched` (never the switch `last_changed`, Shelly `unavailable` blips reset it).
- Override `input_select.hot_water_override` options `Auto`, `Ligada`, `Desligada`, reset to `Auto` at 10:00 and 23:00.
- Repo conventions: one automation per file, `id` equals filename, `alias` present, `triggers:`/`conditions:`/`actions:` with `trigger:`/`action:`, `.yaml` only, new package files hold one top-level domain key, no new `!secret` keys, keep the `CONST_DESIRED_HOT_WATER_TEMPERATURE` secret name.
- Work on branch `feature/hot-water-resistance`, never on `main`. No `Co-Authored-By` or "Generated with" lines in commits or the PR. Push and open the PR only after Marco says yes.

## Review Focus

- `sensor.hot_water_temperature` unavailable with override `Auto`: the decision is unavailable and nothing is switched (Task 2 test).
- Shelly `unavailable` blips: no switching, no stamp, no manual-override detection (Task 3 conditions).
- Home Assistant restart mid-cycle: `last_switched` is restored, the decision is recomputed from the switch state without flapping (Task 2 trajectory test, Task 3 checklist).
- Sunday evening to Monday 07:00 and the missing Sunday morning window: lead time is computed across midnight (Task 2 tests).
- Override reset at 10:00 or 23:00 within 45 min of a manual change: the automation waits for the cycle guard instead of reverting at once (Task 3 checklist).

---

### Task 1: Helpers, schedule and legacy migration

**Files:**
- Create: `homeassistant/config/integrations/input_select.yaml`
- Modify: `homeassistant/config/integrations/input_number.yaml:36`, `integrations/input_datetime.yaml`, `integrations/schedule_hot_water.yaml`, `helpers/input_boolean.yaml`, `dashboards/tablet-views/home.yaml` (cards ~275 and ~293, badge line 181), `dashboards/tablet-views/home-office.yaml` (cards ~341 and ~359, badge line 236)
- Delete: `automations/temperature_and_humidity/control_hot_water_schedule.yaml`, `automations/others/clear_force_hot_water_helpers.yaml`

**Interfaces:**
- Produces: `input_select.hot_water_override` (options `Auto`, `Ligada`, `Desligada`, initial `Auto`), `input_number.desired_hot_water_temperature_winter` (initial from `!secret CONST_DESIRED_HOT_WATER_TEMPERATURE`), `input_number.desired_hot_water_temperature_summer` (50), `input_number.hot_water_surplus_max_temp` (60), `input_datetime.hot_water_last_switched` (date and time), `schedule.hotwater_schedule` with the new windows.

- [ ] **Step 1: Create the branch and baseline.** `git switch -c feature/hot-water-resistance`; create the scratch venv and install yamllint: `python3 -m venv "$SCRATCH/venv" && "$SCRATCH/venv/bin/pip" install yamllint` (`SCRATCH` is the session scratchpad). Run `"$SCRATCH/venv/bin/yamllint" --strict homeassistant/config .github`. Expected: no output.
- [ ] **Step 2: Baseline `check_config`.** Copy `secrets.example.yaml` to `secrets.yaml` (gitignored; delete it at the end of the plan), then run the CI command: `docker run --rm -v "$PWD/homeassistant/config:/config" ghcr.io/home-assistant/home-assistant:$(cat homeassistant/config/.HA_VERSION) python -m homeassistant --script check_config --config /config`. Expected: ends without `Failed config`; `Unknown device` lines are fine (first run pulls the image).
- [ ] **Step 3: Edit the helper and schedule files.** Rename the key `desired_hot_water_temperature` to `desired_hot_water_temperature_winter` (same name text with "winter", same `!secret`), add the summer and surplus-max `input_number` entries (min 0, max 80, step 1, mode box), add the `input_datetime` entry (icon `mdi:water-boiler`), create `input_select.yaml` (package with one top-level `input_select:` key), rewrite the schedule windows from Global Constraints (all seven days listed), remove `force_hot_water_on` and `force_hot_water_off` from `helpers/input_boolean.yaml`, delete the two legacy automations.
- [ ] **Step 4: Migrate the dashboards.** In both views replace the two bubble-card buttons that use the removed booleans with two buttons that call `input_select.select_option` on `input_select.hot_water_override` (`option: Desligada` and `option: Ligada`), keep icon, layout and the Portuguese/English naming of the neighbours; point both `badge_icon` templates to `input_number.desired_hot_water_temperature_winter`.
- [ ] **Step 5: Verify.** `grep -rn "force_hot_water\|input_number.desired_hot_water_temperature\b" homeassistant/config` must print nothing outside `*_winter`/`*_summer`; rerun yamllint and `check_config` from Steps 1-2. Expected: both clean.
- [ ] **Step 6: Commit.** Stage only these files by name: `Add hot water helpers and migrate the force buttons`.

### Task 2: Decision sensors with tests (TDD)

**Files:**
- Create: `tests/hot_water_decision_test.py`, `homeassistant/config/integrations/sensors/hot_water.yaml`

**Interfaces:**
- Consumes: Task 1 helpers; `sensor.hot_water_temperature`, `switch.resistencia_termoacumulador_switch_0`, `schedule.hotwater_schedule` (state and `next_event` attribute), `sensor.energy_consumption_mean_over_last_10_minutes`.
- Produces: `binary_sensor.hot_water_resistance_wanted` (`on` = resistance should be on; unavailable when override is `Auto` and the temperature is not a number) and `sensor.hot_water_predicted_temperature` (C, temperature expected at the next window start: T - 0.6 * hours, equal to T while a window is active). Both use `default_entity_id` and `unique_id` like `integrations/sensors/presence.yaml`.

- [ ] **Step 1: Write the test harness and the failing tests.** `tests/hot_water_decision_test.py` loads the `template:` YAML, renders the binary sensor `availability` and `state` strings with Jinja stubs `now()`, `states(entity)`, `is_state(entity, value)`, `state_attr(entity, attr)`, `as_timestamp(value)`, and exposes `wanted(**inputs) -> bool | None` (`None` when unavailable) with inputs `override, temp, switch, schedule, next_event, net, now, winter=55.0, summer=50.0, surplus_max=60.0`. Test functions, each with the assertions below (dates are Lisbon local, 2026):
  - `test_summer_morning_start`: Mon 5 Oct is winter, so use Mon 6 Jul: T=47, off, next_event 07:00; at 05:00 `False`, at 05:30 `True`.
  - `test_winter_morning_start`: Mon 9 Nov, T=50, off, next_event 07:00; at 04:50 `False`, at 05:00 `True`.
  - `test_no_start_when_warm_enough`: winter, T=57, h=1 -> `False`.
  - `test_in_window_low_and_keep`: schedule `on`, T=53, off -> `True`; switch `on`, T=59.9 -> `True`; T=60.0 -> `False`.
  - `test_override`: `Ligada` with T=70 -> `True`; `Desligada` with T=40 in a window -> `False`.
  - `test_surplus`: off, net=-2000, T=50, schedule off, next_event 9 h away -> `True`; net=-1000 -> `False`; net=-2000, T=61 -> `False`; on, net=+600 -> `False`; on, net=+400, T=55 -> `True`.
  - `test_season_boundaries`: floor 55 on 31 May and 1 Oct, 50 on 1 Jun and 30 Sep (assert through `wanted` at T=52 inside a window).
  - `test_sunday_to_monday`: Sun 22:30, T=44, next_event Mon 07:00 -> `False`; Mon 04:30 -> `True`; Sun 08:00 with next_event Sun 19:30 -> `False`.
  - `test_unavailable_temperature`: `temp=None` with `Auto` -> `None`; with `Ligada` -> `True`.
  - `test_trajectory_single_cycle`: winter Mon 04:00, T=50, net=+200; step 5 min with the switch following `wanted`, +0.5 C per step while on, -0.05 C per step while off; assert exactly one off->on and one on->off between 04:00 and 07:00, on-time at least 45 min and T at 07:00 at least 55.
  The script ends by printing `OK: <n> tests`.
- [ ] **Step 2: Run it and see it fail.** `docker run --rm -v "$PWD:/repo" ghcr.io/home-assistant/home-assistant:$(cat homeassistant/config/.HA_VERSION) python3 /repo/tests/hot_water_decision_test.py`. Expected: fails because `hot_water.yaml` does not exist.
- [ ] **Step 3: Implement `integrations/sensors/hot_water.yaml`.** Package with one `template:` key holding the two entities. Decision, with M and A from the season, `h` = hours to `next_event` (0 while the schedule is `on`, 999 if none), `on` = switch state, `net` = 10 min mean (W), `S` = surplus max:
  `grid_start = T - 0.6*h < M and h <= 1.25*(A-T)/6`; `grid_keep = on and T < A and h <= 1.5*(A-T)/6 + 0.5`; `surplus = T < S and ((not on and net < -1800) or (on and net <= 500))`; `wanted = grid_start or grid_keep or surplus`; override `Desligada` -> false, `Ligada` -> true before the above. `availability`: override is not `Auto` or the temperature is a number. Use `as_timestamp` for `h`.
- [ ] **Step 4: Run the tests until `OK`, then yamllint and `check_config`.** Expected: `OK: 10 tests`, both clean.
- [ ] **Step 5: Replay on real data (throwaway, scratchpad only).** Feed `wanted` the two hourly water-temperature series already analysed (`$SCRATCH/hotwater_analysis.py` holds the 10 autumn days; the 22-28 Jun week is not saved and must be re-fetched with `ha_get_history`, `source=statistics`, `period=hour`, `sensor.hot_water_temperature`, 2026-06-22 to 2026-06-29) with the heating and loss rates above and report switch changes per day and temperature at each window start. Expected: at most 4 changes per day and window-start temperatures at or above the floor on days without a cold-start shower dip. Nothing from this step is committed.
- [ ] **Step 6: Commit.** `Add the hot water decision sensors and their tests`.

### Task 3: Automations

**Files:**
- Create: `automations/temperature_and_humidity/control_hot_water.yaml`, `automations/temperature_and_humidity/hot_water_manual_switch_override.yaml`, `automations/temperature_and_humidity/reset_hot_water_override.yaml`

**Interfaces:**
- Consumes: Task 2 `binary_sensor.hot_water_resistance_wanted`, Task 1 helpers, the switch.
- Produces: `input_datetime.hot_water_last_switched` stamped on every switch change made by these automations or by a manual override.

- [ ] **Step 1: `control_hot_water.yaml`** (`id: control_hot_water`, `mode: single`). Triggers: state change of the wanted sensor to `on`/`off`, and `time_pattern` every 5 minutes. Conditions: wanted sensor and switch both `on`/`off` (not `unavailable`/`unknown`); wanted differs from the switch; and (override is not `Auto` or `now() - last_switched >= 45 minutes`, treating an unset helper as satisfied). Actions: `switch.turn_on`/`turn_off` per wanted, then `input_datetime.set_datetime` with `timestamp: "{{ now().timestamp() }}"`.
- [ ] **Step 2: `hot_water_manual_switch_override.yaml`.** Trigger on the switch changing between `on` and `off` only (`from`/`to` limited to those, so `unavailable` blips never trigger). Condition: `trigger.to_state.context.user_id` is set and `context.parent_id` is none. Actions: set `input_select.hot_water_override` to `Ligada` when the new state is `on`, else `Desligada`; stamp `last_switched`.
- [ ] **Step 3: `reset_hot_water_override.yaml`.** Time triggers `10:00:00` and `23:00:00`; action `input_select.select_option` with `option: Auto`.
- [ ] **Step 4: Verify.** yamllint and `check_config`; expected clean. Commit: `Add the hot water control, manual override and reset automations`.

### Task 4: Admin dashboard (generic, all overrides)

**Files:**
- Create: `homeassistant/config/dashboards/admin.yaml`
- Modify: `homeassistant/config/configuration.yaml` (add under `lovelace: dashboards:`)

- [ ] **Step 1: Register** `admin-dashboard` (`mode: yaml`, `filename: dashboards/admin.yaml`, title `Admin`, icon `mdi:tune`, `show_in_sidebar: true`), same shape as the two existing entries.
- [ ] **Step 2: Dashboard with core cards only** (no custom card resources): tiles for `sensor.hot_water_temperature`, `sensor.hot_water_predicted_temperature`, the switch and `binary_sensor.hot_water_resistance_wanted`; a tile for `input_select.hot_water_override` showing the current option; three `button` cards (Auto, Ligada, Desligada) calling `input_select.select_option`; tiles for `sensor.energy_consumption_mean_over_last_10_minutes` and `sensor.contador_producao_channel_1_power`; a `history-graph` of temperature and switch for 24 h.
- [ ] **Step 3: Verify and commit.** yamllint and `check_config` clean. Commit: `Add the admin dashboard with the hot water override`.

### Task 5: Docs and pull request

**Files:**
- Modify: `AGENTS.md` (untracked, not part of the commit), `specs/` files are committed as the first commit of the branch.

- [ ] **Step 1: Update `AGENTS.md`**: one short section on the hot water control (decision sensor, override select, cycle guard in `input_datetime`, helper rename, new dashboard registered in `configuration.yaml`).
- [ ] **Step 2: Cleanup.** Delete the local `secrets.yaml` created in Task 1; run `git status` and confirm only intended files changed.
- [ ] **Step 3: Ask Marco** before pushing. On "yes": push the branch and open the PR into `main` (body via the `mattpocock-skills:pr` style, no attribution line). State that merging does not deploy: Marco pulls on the VM and restarts HA (new dashboard registration needs a restart).

### Task 6: Live verification (after Marco deploys)

- [ ] **Step 1:** `ha_get_system_health` with `include=config_check,repairs`: valid, no new repairs. Confirm all new entities exist with `ha_get_state`.
- [ ] **Step 2:** The legacy automation entity `automation.control_hot_water_based_on_schedule` is gone; the new `automation.control_hot_water` is disabled or enabled as restored. Marco enables it in the UI.
- [ ] **Step 3:** With Marco's OK, call `switch.turn_on` via the MCP (a user context): the override select becomes `Ligada` and `last_switched` is stamped. Set it back to `Auto`.
- [ ] **Step 4:** After the first morning and evening windows, read `ha_get_automation_traces` for `automation.control_hot_water` and the switch history: temperature at window start at or above the floor, no change within 45 min of another automatic one.
