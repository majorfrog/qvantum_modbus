# Qvantum Modbus — Home Assistant Custom Integration

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
- Works on any device that exposes standard Modbus input or holding registers
- Configurable via the **UI** (Settings → Integrations) or directly in **`configuration.yaml`**
- Polling interval: 5 seconds (local Modbus TCP minimum)
- Clean disconnect on integration unload/reload

### Sensors

| Entity ID | Register | Type | Unit | Description |
|---|---|---|---|---|
| `sensor.bt1_outdoor` | Input 0 | INT16 (÷10) | °C | BT1 temperature |

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

> **Note:** You can add multiple devices (one config entry per unit ID).

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

## Heating curve dashboard

The integration exposes seven `number` entities that represent the custom
heating curve — one supply temperature target per outdoor temperature point
(−30 °C to +30 °C). You can visualise and adjust the curve directly from a
Home Assistant dashboard.

See **[HEAT_CURVE.md](HEAT_CURVE.md)** for the full guide, including:

- Which entities to enable before use (disabled by default)
- How to install the [Plotly Graph Card](https://github.com/dbuezas/lovelace-plotly-graph-card)
- How to import the ready-made dashboard view ([`qvantum_heat_curve.yaml`](qvantum_heat_curve.yaml))

---

## Full control dashboard

A ready-made four-tab Lovelace dashboard is included at
[`dashboards/qvantum_heatpump.yaml`](dashboards/qvantum_heatpump.yaml).

### Tabs

| Tab | What it contains |
|---|---|
| **Overview** | Hot water boost buttons, heat pump status, key temperatures, active demands |
| **Sensors** | All sensor data grouped by category (temperatures, DHW, refrigerant, pumps, energy) |
| **Configuration** | Operation mode, manual mode permissions, DHW settings, sensor selection, alarms |
| **Heat Curve** | Same interactive curve graph and sliders as the standalone heat curve dashboard |

### How to add the dashboard

1. Copy `dashboards/qvantum_heatpump.yaml` to your HA `config/dashboards/` folder.
2. Add the following block under the `lovelace:` → `dashboards:` key in your `configuration.yaml`:

```yaml
lovelace:
  dashboards:
    lovelace-qvantum-heatpump:
      mode: yaml
      filename: dashboards/qvantum_heatpump.yaml
      title: Qvantum Heat Pump
      icon: mdi:heat-pump
      show_in_sidebar: true
```

3. Restart Home Assistant. The dashboard appears in the sidebar as **Qvantum Heat Pump**.

> **Note:** The Overview tab uses the
> `qvantum_modbus.start_extra_hot_water` and
> `qvantum_modbus.cancel_extra_hot_water` service actions described below.
> The Heat Curve tab requires the
> [Plotly Graph Card](https://github.com/dbuezas/lovelace-plotly-graph-card)
> custom frontend card (install via HACS).

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

## License

MIT — see [LICENSE](LICENSE).
