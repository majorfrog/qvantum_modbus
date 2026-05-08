# Qvantum Modbus — Home Assistant Custom Integration

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=majorfrog&repository=qvantum_modbus&category=integration)

A Home Assistant custom integration that polls a Modbus device over **TCP/IP** or **RTU (serial)** and exposes its registers as standard HA entities.

The integration is built on top of [pymodbus](https://github.com/pymodbus-dev/pymodbus) and uses the fully async client, so it never blocks the HA event loop.

---

> **Disclaimer:** This integration is an independent community project. It is **not** owned, developed, or endorsed by Qvantum Energy AB or any affiliated entity. Use it entirely at your own risk. The authors accept no responsibility for damage, data loss, or any other consequence arising from its use.

---

## ⚠️ Warning — Modbus external interface

> **By activating the Modbus external interface on your device, you accept full responsibility for any values written through it.** The manufacturer is not liable for issues caused by incorrect or out-of-range values written via Modbus. Such actions may void the warranty and/or negatively affect the lifecycle and performance of the product. Always verify that values are within the specified safe range before writing them.

---

## ⚠️ Security warning — Modbus TCP

> **Do not expose Modbus TCP to any network that is not under your exclusive control.**

The Modbus TCP protocol has **no authentication, no authorisation, and no encryption**. Any device that can reach the configured host and port can:

- Read every register on your device without restriction.
- Write to any writable (holding) register — potentially changing setpoints, modes, or other safety-critical settings.

Safe deployment guidelines:

- **Use Modbus TCP only on a fully isolated, private LAN** (e.g. a dedicated VLAN or a direct Ethernet cable between the gateway and the HA host).
- **Never forward the Modbus port (default: 502) through a firewall or router** to the internet or to any shared network segment.
- **Never use Modbus TCP over Wi-Fi** unless the wireless network is private, encrypted (WPA2/WPA3), and separated from guest or IoT networks.
- If you need remote access to Home Assistant, use HA's built-in encrypted remote-access features (Nabu Casa / secured reverse proxy) rather than exposing the Modbus port.
- Prefer **Modbus RTU over a physical serial cable** whenever the device is close enough — it is inherently local and not exposed to any network.

---

## Features

- Supports both **Modbus TCP** (over Ethernet/Wi-Fi) and **Modbus RTU** (over serial/RS-485)
- Designed specifically for **Qvantum heat pumps** using their documented Modbus register map
- Configurable via the **UI** (Settings → Integrations) or directly in **`configuration.yaml`**
- Polling interval: 5 seconds (local Modbus TCP minimum)
- Clean disconnect on integration unload/reload

### Entities

The integration exposes entities across six platforms.

**Summary by platform and category:**

| Platform | Category | Examples |
|---|---|---|
| `sensor` | Temperatures | Outdoor (BT1), indoor (BT2), DHW tank (BT30/BT31), calculated supply |
| `sensor` | Flow & pumps | DHW flow (BF1), pump RPM, pump speed (GP1/GP2), compressor speed |
| `sensor` | Operating status | Unit state, heatpump state, compressor state, degree minute, time to defrost |
| `sensor` | Runtime & maintenance | Compressor run time, start count, ventilation fan run time, filter time left |
| `sensor` | Power & energy | Compressor power (W); MWh/kWh counters per category (compressor, heating, DHW, cooling, backup) |
| `sensor` | Alarms | Active alarm count, alarm codes 1–5 |
| `sensor` | Smart grid | SG mode, smart DHW mode and control status, BBR locked |
| `sensor` | Device info | Serial number, IP address, firmware version |
| `binary_sensor` | Demands | Heating, DHW, backup heater (heating and DHW) |
| `binary_sensor` | Relays | 10 relay output states (L1–L3, GP10, QM10, QN8-1/2, GP3, Pump, HA12) |
| `binary_sensor` | Protection | Compressor blocked, freeze protection active |
| `binary_sensor` | Smart grid | SG Ready A/B inputs, smart price (heating/DHW), energy prices available |
| `binary_sensor` | Connectivity | Wi-Fi connected, cloud connected, vacation mode |
| `switch` | Power | Unit on/off |
| `select` | Climate | Operation mode, desired indoor temperature, DHW mode, heating curve offset, room compensation factor |
| `number` | Setpoints | Heating/cooling curve points, supply temp limits, DHW temperatures, pump speeds, room temp external |
| `button` | Maintenance | Reset alarms |

Entities that are **enabled by default** are those most commonly useful — temperatures, key demands, compressor status, and energy totals. More specialist entities (refrigerant sensors, individual energy counters, setpoint numbers) are disabled by default and can be enabled per-entity in **Settings → Devices & Services → Qvantum Modbus → Entities**.

---

## Requirements

| Requirement | Value |
|---|---|
| Home Assistant | 2024.1 or newer (Python 3.13+) |
| HACS or manual install | see below |
| Python dependency | `pymodbus>=3.11,<4` (auto-installed) |

---

## Installation

### HACS (recommended)

1. Open **HACS** → **Integrations** → three-dot menu → **Custom repositories**.
2. Add `https://github.com/majorfrog/qvantum_modbus` with category **Integration**.
3. Search for **Qvantum Modbus** and click **Download**.
4. Restart Home Assistant.

### Manual

1. Copy the `custom_components/qvantum_modbus` directory into your HA `config/custom_components/` folder.
2. Restart Home Assistant.

---

## Configuration

You can set up the integration either through the UI or via `configuration.yaml`. Both methods produce the same config entry.

### Option A — UI (recommended)

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Qvantum Modbus**.
3. Select the connection type:
   - **TCP/IP** → enter host, port, and unit ID.
   - **RTU (Serial)** → enter serial port path and serial parameters.
4. The integration tests the connection before saving. If the test fails, correct the settings and try again.

> **Note:** You can add multiple devices. Each config entry is unique by connection (TCP: host + port + unit ID; RTU: serial port + unit ID), so the same unit ID on different hosts counts as separate entries.

### Option B — `configuration.yaml`

Add the following to your `configuration.yaml`. If you have multiple devices, use a YAML list.

#### TCP (Ethernet / Wi-Fi gateway)

```yaml
qvantum_modbus:
  connection_type: tcp
  host: 192.168.1.100     # IP address or hostname of the Modbus gateway
  port: 502               # optional — default: 502
  unit_id: 1              # optional — default: 1
```

#### RTU (Serial / RS-485)

> **Note:** RTU support has not yet been tested on real hardware. The implementation follows the pymodbus API, but serial communication is awaiting physical device validation. Use at your own risk and please report any issues.

```yaml
qvantum_modbus:
  connection_type: rtu
  port: /dev/ttyUSB0      # serial device path (Linux) or COM3 (Windows)
  unit_id: 1              # optional — default: 1
  baudrate: 9600          # optional — default: 9600
  bytesize: 8             # optional — default: 8  (5/6/7/8)
  parity: "N"             # optional — default: N  (N=none, E=even, O=odd)
  stopbits: 1             # optional — default: 1  (1 or 2)
```

#### Multiple devices

```yaml
qvantum_modbus:
  - connection_type: tcp
    host: 192.168.1.100
    unit_id: 1
  - connection_type: rtu
    port: /dev/ttyUSB0
    unit_id: 2
    baudrate: 19200
```

> **Note:** When using `configuration.yaml`, Home Assistant creates a config entry automatically on startup. No connection test is performed at import time — the device may be temporarily offline without preventing startup. You can manage or remove the entry later under **Settings → Devices & Services**.

### Configuration parameters

#### Common parameters

| Parameter | Required | Default | Description |
|---|---|---|---|
| `connection_type` | **Yes** | — | `tcp` or `rtu` |
| `unit_id` | No | `1` | Modbus unit ID, 1–247 |

#### TCP parameters

| Parameter | Required | Default | Description |
|---|---|---|---|
| `host` | **Yes** | — | IP address or hostname of the Modbus TCP gateway |
| `port` | No | `502` | TCP port |

#### RTU parameters

| Parameter | Required | Default | Description |
|---|---|---|---|
| `port` | **Yes** | — | Serial device path, e.g. `/dev/ttyUSB0` or `COM3` |
| `baudrate` | No | `9600` | Communication speed in bps |
| `bytesize` | No | `8` | Number of data bits (5, 6, 7, or 8) |
| `parity` | No | `N` | Parity: `N` (none), `E` (even), `O` (odd) |
| `stopbits` | No | `1` | Number of stop bits (1 or 2) |

---

## Removal

1. Go to **Settings → Devices & Services**.
2. Find the **Qvantum Modbus** integration.
3. Click the three-dot menu and select **Delete**.
4. If you used `configuration.yaml`, remove the `qvantum_modbus:` block and restart Home Assistant.

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
|---|---|---|
| Integration shows as unavailable | Device offline or wrong IP/port | Check network connectivity and settings |
| Sensors show `Unknown` | Register returns an error response | Verify register address and unit ID |
| Cannot add via UI — "Failed to connect" | TCP: Wrong host/port; RTU: Wrong port path or serial parameters | Correct the settings and retry |
| RTU serial port not found | Wrong device path | Check `ls /dev/tty*`; ensure HA has permission to access the port |
| Values seem 10× too high or low | Wrong `scale` | Adjust `scale` in `models.py` |

---

## Known limitations

| Limitation | Notes |
|---|---|
| Fixed polling interval | The 5-second polling interval is not user-configurable |
| One unit per config entry | Each Modbus unit ID requires its own config entry |
| No automatic reconnect delay | After a connection failure the integration retries on the next poll cycle (5 s) |
| TCP only — no TLS | Modbus TCP has no encryption; see the security warning above |

### Known register limitations (Modbus API)

The Modbus interface of the Qvantum heat pump has a few known constraints. These are limitations of the device firmware, not of this integration. We can expect some of these to be resolved in future firmware updates, and/or modbus register map revisions. The integration will be updated accordingly when that happens.

| Sensor / entity | Issue |
|---|---|
| `sensor.electricity_price_region` | Always reports `null`. The register holds only 2 ASCII bytes, which is not enough for 3-character Swedish region codes such as `SE4`. The cloud API exposes the full string; Modbus does not. |
| `sensor.compressor_run_time`, `sensor.compressor_starts` | Report `0` on firmware 1.7.22 despite significant accumulated run time. These registers appear not to be populated by the current firmware. Values may become available on a future firmware release. |
| `sensor.ventilation_fan_run_time` | Always `0` on **air-to-water** models, which have no ventilation fan. The register is only meaningful on **extract-air** heat pump models. |
| `sensor.bt15_source_return` | Always `0.0 °C` on **air-to-water** models. BT15 measures the source-side return temperature, which I suspect only exists on **extract-air** models. Air-to-water units do not have this sensor installed and the firmware reports `0` with no sentinel value. |

---

## Dashboards

Three ready-made Lovelace dashboards are included. All follow the same installation method described below.

### Quick-start dashboard (defaults only)

[`dashboards/qvantum_heatpump_defaults.yaml`](dashboards/qvantum_heatpump_defaults.yaml)

A clean five-tab dashboard that uses **only the entities that are enabled by default**. This is the best starting point — no extra entities need to be enabled before it works.

| Tab | What it contains |
|---|---|
| **Overview** | Unit on/off, operation mode, key temperatures + 24-hour graph, system status, active demands, alerts |
| **Hot Water** | DHW temperatures, flow, control, smart DHW status, monthly energy stat |
| **Energy** | Compressor power gauge, monthly energy totals per category, lifetime compressor stats |
| **Smart Grid** | SG Ready A/B, SG mode, smart price (heating & DHW), energy prices availability |
| **Diagnostics** | Alarm codes, pump speeds, ventilation filter, relay states, device info & connectivity |

### Full control dashboard

[`dashboards/qvantum_heatpump.yaml`](dashboards/qvantum_heatpump.yaml)

A comprehensive four-tab dashboard that exposes the full range of entities, including those that are disabled by default. Enable the relevant entities before opening this dashboard.

| Tab | What it contains |
|---|---|
| **Overview** | Hot water boost buttons, heat pump status, key temperatures, active demands |
| **Sensors** | All sensor data grouped by category (temperatures, DHW, refrigerant, pumps, energy) |
| **Configuration** | Operation mode, manual mode permissions, DHW settings, sensor selection, alarms |
| **Heat Curve** | Same interactive curve graph and sliders as the standalone heat curve dashboard |

> **Note:** The Overview tab uses the `qvantum_modbus.start_extra_hot_water` and
> `qvantum_modbus.cancel_extra_hot_water` service actions described below.
> The Heat Curve tab requires the
> [Plotly Graph Card](https://github.com/dbuezas/lovelace-plotly-graph-card)
> custom frontend card (install via HACS).

### Heating curve dashboard

[`dashboards/qvantum_heat_curve.yaml`](dashboards/qvantum_heat_curve.yaml)

A focused dashboard for visualising and adjusting the custom heating curve. See **[HEAT_CURVE.md](HEAT_CURVE.md)** for the full guide, including which entities to enable before use and how to install the Plotly Graph Card.

### How to add a dashboard

1. Copy the dashboard YAML file to your HA `config/dashboards/` folder.
2. Add an entry under `lovelace:` → `dashboards:` in `configuration.yaml`. For example, for the defaults dashboard:

```yaml
lovelace:
  dashboards:
    lovelace-qvantum-defaults:
      mode: yaml
      filename: dashboards/qvantum_heatpump_defaults.yaml
      title: Qvantum Heat Pump
      icon: mdi:heat-pump
      show_in_sidebar: true
```

3. Restart Home Assistant. The dashboard appears in the sidebar.

---

## Service actions

The integration registers two service actions that are available from the UI
(**Developer Tools → Services**), from automations, and from scripts.

### `qvantum_modbus.start_extra_hot_water`

Activates the **Extra** DHW mode for a configurable number of hours and then
automatically restores the DHW mode that was active before the boost.

If the service is called while a boost is already running, the previous timer
is cancelled and a new one is started from the current point in time
(restart semantics).

| Field | Type | Default | Range | Description |
|---|---|---|---|---|
| `duration_hours` | float | `4` | 0.5 – 24 | How long to run the boost, in hours |

**Example — start a 2-hour boost:**

```yaml
action: qvantum_modbus.start_extra_hot_water
data:
  duration_hours: 2
```

**Example — start with the default 4-hour duration:**

```yaml
action: qvantum_modbus.start_extra_hot_water
```

---

### `qvantum_modbus.cancel_extra_hot_water`

Immediately stops the running hot water boost and restores the DHW mode
that was active when the boost was started.

```yaml
action: qvantum_modbus.cancel_extra_hot_water
```

---

### Automation examples

#### Boost every morning before people wake up

```yaml
automation:
  - alias: "Qvantum — Morning hot water boost"
    triggers:
      - trigger: time
        at: "06:00:00"
    actions:
      - action: qvantum_modbus.start_extra_hot_water
        data:
          duration_hours: 1.5
```

#### Boost when a button is pressed (e.g. a Zigbee remote)

```yaml
automation:
  - alias: "Qvantum — Button hot water boost"
    triggers:
      - trigger: state
        entity_id: sensor.my_button
        to: "single"
    actions:
      - action: qvantum_modbus.start_extra_hot_water
        data:
          duration_hours: 2
```

#### Cancel boost if tank temperature is already high enough

```yaml
automation:
  - alias: "Qvantum — Cancel boost when tank is warm"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.qvantum_heat_pump_bt30_dhw_tank
        above: 58
    conditions:
      - condition: state
        entity_id: select.qvantum_heat_pump_dhw_mode
        state: extra
    actions:
      - action: qvantum_modbus.cancel_extra_hot_water
```

---

## Using an existing room temperature sensor as input to the heat pump

The heat pump can use a measured indoor temperature to adjust the heating
curve output in real time (room compensation). If you already have a
temperature sensor in Home Assistant — such as a Zigbee thermometer, a
smart thermostat, or any other `sensor` entity — you can forward its value
to the heat pump via the `room_temp_external` register.

### Prerequisites

Two settings must be configured on the heat pump first:

1. **Enable the `room_temp_external` number entity.** It is disabled by default. Go to
   **Settings → Devices & Services → Qvantum Modbus → Entities**, find
   `Room temp external`, and enable it.
   (`Room compensation factor` is already enabled by default and does not need this step.)

2. **Set `use_operation_mode_sensor` to `external`.** This tells the heat
   pump to read the room temperature from the Modbus register rather than
   from one of its own built-in sensors. Go to your dashboard (or
   **Developer Tools → States**) and set the
   `select.qvantum_heat_pump_use_operation_mode_sensor` entity to
   **external**.

> **Note:** Without step 2 the value written to `room_temp_external` is
> accepted by the device but has no effect on the heating output.

### Automation to forward a room sensor

The example below triggers whenever your room sensor changes state and
writes its temperature to the heat pump's `room_temp_external` number
entity. Replace `sensor.living_room_temperature` with your actual sensor
entity ID.

```yaml
automation:
  - alias: "Qvantum — Forward room temperature to heat pump"
    triggers:
      - trigger: state
        entity_id: sensor.living_room_temperature
    conditions:
      - condition: template
        value_template: "{{ states('sensor.living_room_temperature') | is_number }}"
    actions:
      - action: number.set_value
        target:
          entity_id: number.qvantum_heat_pump_room_temp_external
        data:
          value: "{{ states('sensor.living_room_temperature') | float }}"
```

> **Tip:** Add a `numeric_state` condition if you want to guard against
> unrealistic values, for example:
> ```yaml
> conditions:
>   - condition: numeric_state
>     entity_id: sensor.living_room_temperature
>     above: 5
>     below: 35
> ```

---

## License

MIT — see [LICENSE](LICENSE).
