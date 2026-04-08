# Visualising and adjusting the heating curve

This guide explains how to set up a Home Assistant dashboard view that displays
the custom heating curve as an interactive graph and lets you adjust each curve
point with sliders — all from the same card.

---

## Prerequisites

### 1. Enable the heating-curve entities

The heating-curve `number` entities are **disabled by default** to keep the
entity list clean for users who do not need fine-grained control.

You must enable each one before they appear in the dashboard:

1. Go to **Settings → Devices & Services → Qvantum Modbus → Entities**.
2. Search for `heating_curve`.
3. Click each entity below and toggle **Enable**.

| Entity ID | Description |
|---|---|
| `number.qvantum_heat_pump_heating_curve_minus30` | Supply temp at −30 °C outdoor |
| `number.qvantum_heat_pump_heating_curve_minus20` | Supply temp at −20 °C outdoor |
| `number.qvantum_heat_pump_heating_curve_minus10` | Supply temp at −10 °C outdoor |
| `number.qvantum_heat_pump_heating_curve_0` | Supply temp at 0 °C outdoor |
| `number.qvantum_heat_pump_heating_curve_10` | Supply temp at +10 °C outdoor |
| `number.qvantum_heat_pump_heating_curve_20` | Supply temp at +20 °C outdoor |
| `number.qvantum_heat_pump_heating_curve_30` | Supply temp at +30 °C outdoor |

You should also enable the min/max supply temperature entities used as reference
lines in the graph:

| Entity ID | Description |
|---|---|
| `number.qvantum_heat_pump_max_heating_supply_temp` | Maximum allowed supply temperature |
| `number.qvantum_heat_pump_min_heating_supply_temp` | Minimum allowed supply temperature |

### 2. Install the Plotly Graph Card

The graph is powered by the excellent
[Plotly Graph Card](https://github.com/dbuezas/lovelace-plotly-graph-card) by
[@dbuezas](https://github.com/dbuezas). Many thanks for building and maintaining
such a flexible and capable card!

Install it via HACS (recommended):

1. Open **HACS → Frontend**.
2. Search for **Plotly Graph Card** and click **Download**.
3. Reload your browser.

Or follow the
[manual installation instructions](https://github.com/dbuezas/lovelace-plotly-graph-card#manually)
in the card's repository.

---

## Installing the dashboard view

A ready-made dashboard YAML file is included in this repository:
[`qvantum_heat_curve.yaml`](qvantum_heat_curve.yaml)

### Option A — Import as a new dashboard (easiest)

1. In Home Assistant, go to **Settings → Dashboards → Add Dashboard**.
2. Give it a name (e.g. "Heat Curve") and confirm.
3. Open the new dashboard, click the three-dot menu → **Edit dashboard** →
   **Raw configuration editor**.
4. Paste the full contents of
   [`qvantum_heat_curve.yaml`](qvantum_heat_curve.yaml) and click **Save**.

### Option B — Add as a view to an existing dashboard

1. Open the dashboard you want to add the view to.
2. Click the three-dot menu → **Edit dashboard**.
3. Click **+ Add view** → **YAML** (or open the **Raw configuration editor**).
4. Copy the content of the `views[0]` block from
   [`qvantum_heat_curve.yaml`](qvantum_heat_curve.yaml) and paste it as a new
   entry under `views:` in your dashboard YAML.

---

## What the view contains

### Settings section

A card with the most relevant heat-pump settings in one place:

- Curve type
- Temperature compensation
- Parallel offset / curve offset
- Max and min supply temperatures
- Pump speeds
- Desired indoor temperature

### Custom heat curve section

| Card | Purpose |
|---|---|
| **Graph** | Plots the seven curve points (outdoor temp on X axis, supply temp on Y axis) with red reference lines for the min/max supply temperature limits. Updates live when you move the sliders. |
| **Adjust heat curve** | Seven sliders — one per outdoor temperature point — to change the supply temperature target at that point. Changes are written to the device immediately via Modbus. |

---

## How the graph works

The graph uses `raw_plotly_config: true` with static x-axis values
(`[30, 20, 10, 0, -10, -20, -30]`) and reads the y-axis values live from
`hass.states` using `$ex` expressions. Internal (hidden) traces for each entity
ensure the card re-renders automatically whenever a slider value changes.

The two red reference lines are drawn the same way — reading
`number.qvantum_heat_pump_max_heating_supply_temp` and
`number.qvantum_heat_pump_min_heating_supply_temp` at render time and
projecting them across the full x range.
