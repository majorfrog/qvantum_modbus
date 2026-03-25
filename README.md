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
| `sensor.qvantum_bt1` | Input 0 | INT16 (÷10) | °C | BT1 temperature |

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
| Read-only | Writing to holding registers is not yet supported |
| Fixed polling interval | The 5-second polling interval is not user-configurable |
| One unit per config entry | Each Modbus unit ID requires its own config entry |
| No automatic reconnect delay | After a connection failure the integration retries on the next poll cycle (5 s) |
| TCP only — no TLS | Modbus TCP has no encryption; see the security warning above |

---

## License

MIT — see [LICENSE](LICENSE).
