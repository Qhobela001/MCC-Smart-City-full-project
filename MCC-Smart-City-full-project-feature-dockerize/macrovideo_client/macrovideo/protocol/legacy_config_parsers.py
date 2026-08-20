from __future__ import annotations

import struct
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TimeWindow:
    enabled: bool
    start_hour: int
    start_minute: int
    start_second: int
    end_hour: int
    end_minute: int
    end_second: int


@dataclass(frozen=True)
class NetworkConfig:
    mode: int
    ap_name: str
    ap_password: str
    wifi_name: str
    wifi_password: str
    device_version: int = 10


@dataclass(frozen=True)
class RecordConfig:
    record_status: int
    frame_size: int
    disk_size: int
    disk_remaining_size: int
    auto_record: bool
    alarm_record: bool
    full_record_operation: int
    enable_1080p: bool
    enable_720p: bool
    enable_d1: bool
    enable_vga: bool
    enable_cif: bool
    enable_qvga: bool
    enable_qcif: bool
    audio_enabled: bool
    sd_card_formatting: bool
    retrench_record_enabled: int
    retrench_time: int
    min_retrench_time: int
    max_retrench_time: int
    frame_rate: int
    min_frame_rate: int
    max_frame_rate: int


@dataclass(frozen=True)
class VersionConfig:
    app_version: str | None
    app_version_date: str | None
    kernel_version: str | None
    kernel_version_date: str | None
    hardware_version: str | None
    hardware_version_date: str | None
    new_version_flag: int
    device_new_version_name: str | None


@dataclass(frozen=True)
class IPConfig:
    disable_dhcp: bool
    ip_address: str | None
    subnet_mask: str | None
    gateway: str | None
    dns1: str | None
    dns2: str | None


@dataclass(frozen=True)
class DateTimeConfig:
    time_type: int
    timezone_enabled: bool
    timezone_index: int
    time_text: str | None
    time_offset: int
    time_format: int


@dataclass(frozen=True)
class PowerTimer:
    start_hour: int
    start_minute: int
    start_second: int
    end_hour: int
    end_minute: int
    end_second: int


@dataclass(frozen=True)
class DeviceXConfig:
    pir_sensitivity: int
    light_value: int
    light_time: int
    photo_sensitivity: int
    light_sensitivity: int
    speech_player_type: int
    reset_enabled: int
    rtsp_enabled: int
    smoke_sensitivity: int
    rtsp_video_type: int
    osd_enabled: int
    indicator_light_enabled: int
    led_enabled: int
    ptz_vertical_sensitivity: int
    ptz_horizontal_sensitivity: int
    video_standard: int
    power_source: int
    focal_enabled: int
    focal_time: int
    speaker_volume: int
    has_qr_info: int
    config_list: int
    selected: int
    model_id: str | None
    power_mode: int
    power_timer_enabled: int
    timers: tuple[PowerTimer, ...]
    power_mode_list: int | None
    log_upload: int | None
    hdr: int | None
    detection_list: int | None
    detection: int | None


@dataclass(frozen=True)
class PTZTimerCruise:
    timer_id: int
    start_hour: int
    start_minute: int
    start_second: int
    end_hour: int
    end_minute: int
    end_second: int


@dataclass(frozen=True)
class PTZCruisePoint:
    point_id: int
    stay_duration: int


@dataclass(frozen=True)
class PTZAutoCruise:
    start_hour: int
    start_minute: int
    start_second: int
    end_hour: int
    end_minute: int
    end_second: int
    points: tuple[PTZCruisePoint, ...]


@dataclass(frozen=True)
class PTZCruiseConfig:
    usable_count: int
    auto_max: int
    point_of_auto_max: int
    action_type: int
    timer_enabled: bool
    timer_count: int
    timer_cruises: tuple[PTZTimerCruise, ...]
    auto_enabled: bool
    auto_count: int
    auto_cruises: tuple[PTZAutoCruise, ...]
    auto_check_enabled: int | None
    auto_check_hour: int | None
    auto_check_minute: int | None
    auto_check_second: int | None


@dataclass(frozen=True)
class WhiteLightAction:
    action: int
    start_hour: int
    start_minute: int
    start_second: int
    end_hour: int
    end_minute: int
    end_second: int


@dataclass(frozen=True)
class WhiteLightConfig:
    total: int
    default_action: int
    capability: int
    actions: tuple[WhiteLightAction, ...]
    main_switch: int
    motion_detection_switch: int
    human_detection_switch: int
    car_detection_switch: int
    pet_detection_switch: int
    alarm_warning_switch: int


@dataclass(frozen=True)
class PrivateModeConfig:
    enabled: bool
    timer_enabled: bool
    timer_count: int
    timers: tuple[TimeWindow, ...]


@dataclass(frozen=True)
class AIHumanDetectConfig:
    human_detect_enabled: int
    human_frame_enabled: int
    sensitivity: int
    sound_notice_enabled: int
    time_control_enabled: int
    time_setting_count: int
    alarm_times: tuple[TimeWindow, ...]
    area_rows: int
    area_columns: int
    alarm_area_indices: tuple[int, ...]
    ai_voice_type: int
    ai_light_detection: int


@dataclass(frozen=True)
class TimeBacktrackingEntry:
    entry_type: int
    name: str | None
    start: int
    start_real: int
    end_offset: int
    task_duration: int
    task_shot_interval: int
    next_task_interval: int


@dataclass(frozen=True)
class TimeBacktrackingConfig:
    count: int
    entries: tuple[TimeBacktrackingEntry, ...]


@dataclass(frozen=True)
class CPEConfig:
    enabled: int


@dataclass(frozen=True)
class RawConfig:
    config_type: int
    payload_hex: str


DecodedConfig = (
    NetworkConfig
    | RecordConfig
    | VersionConfig
    | IPConfig
    | DateTimeConfig
    | DeviceXConfig
    | PTZCruiseConfig
    | WhiteLightConfig
    | PrivateModeConfig
    | AIHumanDetectConfig
    | TimeBacktrackingConfig
    | CPEConfig
    | RawConfig
)


def decode_config_payload(
    config_type: int,
    payload: bytes,
) -> DecodedConfig:
    parsers = {
        1: parse_network_config,
        2: parse_record_config,
        4: parse_version_config,
        5: parse_ip_config,
        6: parse_datetime_config,
        7: parse_device_x_config,
        9: parse_ptz_cruise_config,
        10: parse_white_light_config,
        11: parse_private_mode_config,
        14: parse_ai_human_detect_config,
        15: parse_time_backtracking_config,
        16: parse_cpe_config,
    }

    parser = parsers.get(config_type)

    if parser is None:
        return RawConfig(
            config_type=config_type,
            payload_hex=payload.hex(),
        )

    return parser(payload)


def decoded_to_dict(
    decoded: DecodedConfig,
) -> dict[str, Any]:
    document = asdict(decoded)
    document["decoded_type"] = type(decoded).__name__
    return document


def parse_network_config(payload: bytes) -> NetworkConfig:
    _require_length(payload, 196, "network configuration")

    return NetworkConfig(
        mode=_i32(payload, 0),
        ap_name=_cstring(payload, 4, 64, "gbk") or "",
        ap_password=_cstring(payload, 68, 32, "gbk") or "",
        wifi_name=_cstring(payload, 100, 64, "utf-8") or "",
        wifi_password=_cstring(payload, 164, 32, "gbk") or "",
    )


def parse_record_config(payload: bytes) -> RecordConfig:
    _require_length(payload, 36, "record configuration")

    return RecordConfig(
        record_status=payload[0],
        frame_size=payload[1] + 1000,
        disk_size=_i32(payload, 2),
        disk_remaining_size=_i32(payload, 6),
        auto_record=_truth(payload[10]),
        alarm_record=_truth(payload[11]),
        full_record_operation=_i32(payload, 12),
        enable_1080p=_truth(payload[16]),
        enable_720p=_truth(payload[17]),
        enable_d1=_truth(payload[18]),
        enable_vga=_truth(payload[19]),
        enable_cif=_truth(payload[20]),
        enable_qvga=_truth(payload[21]),
        enable_qcif=_truth(payload[22]),
        audio_enabled=_truth(payload[24]),
        sd_card_formatting=_truth(payload[25]),
        retrench_record_enabled=payload[26],
        retrench_time=_u16(payload, 27),
        min_retrench_time=_u16(payload, 29),
        max_retrench_time=_u16(payload, 31),
        frame_rate=payload[33],
        min_frame_rate=payload[34],
        max_frame_rate=payload[35],
    )


def parse_version_config(payload: bytes) -> VersionConfig:
    _require_length(payload, 159, "version configuration")

    return VersionConfig(
        app_version=_cstring(payload, 0, 32, "gbk"),
        app_version_date=_cstring(payload, 32, 10, "gbk"),
        kernel_version=_cstring(payload, 42, 32, "gbk"),
        kernel_version_date=_cstring(payload, 74, 10, "gbk"),
        hardware_version=_cstring(payload, 84, 32, "gbk"),
        hardware_version_date=_cstring(payload, 116, 10, "gbk"),
        new_version_flag=payload[126],
        device_new_version_name=_cstring(payload, 127, 32, "gbk"),
    )


def parse_ip_config(payload: bytes) -> IPConfig:
    _require_length(payload, 81, "IP configuration")

    return IPConfig(
        disable_dhcp=_truth(payload[0]),
        ip_address=_cstring(payload, 1, 16, "gbk"),
        subnet_mask=_cstring(payload, 17, 16, "gbk"),
        gateway=_cstring(payload, 33, 16, "gbk"),
        dns1=_cstring(payload, 49, 16, "gbk"),
        dns2=_cstring(payload, 65, 16, "gbk"),
    )


def parse_datetime_config(payload: bytes) -> DateTimeConfig:
    _require_length(payload, 38, "date/time configuration")

    return DateTimeConfig(
        time_type=payload[0],
        timezone_enabled=_truth(payload[1]),
        timezone_index=_u16(payload, 2),
        time_text=_cstring(payload, 4, 32, "gbk"),
        time_offset=_signed_byte(payload[36]),
        time_format=payload[37],
    )


def parse_device_x_config(payload: bytes) -> DeviceXConfig:
    _require_length(payload, 66, "device-X configuration")

    timer_count = payload[65]
    timers: list[PowerTimer] = []
    cursor = 66

    for _ in range(timer_count):
        if cursor + 6 > len(payload):
            break

        timers.append(
            PowerTimer(
                start_hour=payload[cursor],
                start_minute=payload[cursor + 1],
                start_second=payload[cursor + 2],
                end_hour=payload[cursor + 3],
                end_minute=payload[cursor + 4],
                end_second=payload[cursor + 5],
            )
        )
        cursor += 6

    trailing = payload[cursor:]
    power_mode_base = payload[63]
    power_mode_extension = trailing[2] if len(trailing) >= 3 else 0

    power_mode = (
        ((power_mode_extension & 0xE0) << 22)
        | ((power_mode_base & 0xE0) << 19)
        | (power_mode_base & 0x1F)
        | ((power_mode_extension & 0x1F) << 5)
    )

    power_mode_list = None
    if len(trailing) >= 4:
        first = trailing[0]
        fourth = trailing[3]
        power_mode_list = (
            ((first & 0xE0) << 19)
            | ((fourth & 0xE0) << 22)
            | (first & 0x1F)
            | ((fourth & 0x1F) << 5)
        )

    return DeviceXConfig(
        pir_sensitivity=payload[0],
        light_value=payload[1],
        light_time=_u16(payload, 2),
        photo_sensitivity=payload[4],
        light_sensitivity=payload[5],
        speech_player_type=payload[6],
        reset_enabled=payload[7],
        rtsp_enabled=payload[8],
        smoke_sensitivity=payload[9],
        rtsp_video_type=payload[10],
        osd_enabled=payload[11],
        indicator_light_enabled=payload[12],
        led_enabled=payload[13],
        ptz_vertical_sensitivity=payload[14],
        ptz_horizontal_sensitivity=payload[15],
        video_standard=payload[16],
        power_source=payload[17],
        focal_enabled=payload[18],
        focal_time=_u16(payload, 19),
        speaker_volume=payload[21],
        has_qr_info=payload[22],
        config_list=_i32(payload, 23),
        selected=_i32(payload, 27),
        model_id=_cstring(payload, 31, 32, "gbk"),
        power_mode=power_mode,
        power_timer_enabled=payload[64],
        timers=tuple(timers),
        power_mode_list=power_mode_list,
        log_upload=trailing[1] if len(trailing) >= 2 else None,
        hdr=trailing[4] if len(trailing) >= 5 else None,
        detection_list=trailing[5] if len(trailing) >= 6 else None,
        detection=trailing[6] if len(trailing) >= 7 else None,
    )


def parse_ptz_cruise_config(payload: bytes) -> PTZCruiseConfig:
    _require_length(payload, 12, "PTZ cruise configuration")

    timer_count = payload[5]
    cursor = 6
    timer_cruises: list[PTZTimerCruise] = []

    for _ in range(timer_count):
        _require_available(payload, cursor, 7, "PTZ timer cruise")
        timer_cruises.append(
            PTZTimerCruise(
                timer_id=payload[cursor],
                start_hour=payload[cursor + 1],
                start_minute=payload[cursor + 2],
                start_second=payload[cursor + 3],
                end_hour=payload[cursor + 4],
                end_minute=payload[cursor + 5],
                end_second=payload[cursor + 6],
            )
        )
        cursor += 7

    _require_available(payload, cursor, 2, "PTZ auto-cruise header")
    auto_enabled = payload[cursor] == 1
    cursor += 1
    auto_count = payload[cursor]
    cursor += 1

    auto_cruises: list[PTZAutoCruise] = []

    for _ in range(auto_count):
        _require_available(payload, cursor, 7, "PTZ auto-cruise schedule")
        start_hour = payload[cursor]
        start_minute = payload[cursor + 1]
        start_second = payload[cursor + 2]
        end_hour = payload[cursor + 3]
        end_minute = payload[cursor + 4]
        end_second = payload[cursor + 5]
        cursor += 6

        point_count = payload[cursor]
        cursor += 1
        points: list[PTZCruisePoint] = []

        for _ in range(point_count):
            _require_available(payload, cursor, 5, "PTZ cruise point")
            points.append(
                PTZCruisePoint(
                    point_id=payload[cursor],
                    stay_duration=_i32(payload, cursor + 1),
                )
            )
            cursor += 5

        auto_cruises.append(
            PTZAutoCruise(
                start_hour=start_hour,
                start_minute=start_minute,
                start_second=start_second,
                end_hour=end_hour,
                end_minute=end_minute,
                end_second=end_second,
                points=tuple(points),
            )
        )

    auto_check_enabled = None
    auto_check_hour = None
    auto_check_minute = None
    auto_check_second = None

    if cursor + 4 <= len(payload):
        auto_check_enabled = payload[cursor]
        auto_check_hour = payload[cursor + 1]
        auto_check_minute = payload[cursor + 2]
        auto_check_second = payload[cursor + 3]

    usable_count = payload[0]
    if len(timer_cruises) < 6:
        usable_count = 5

    return PTZCruiseConfig(
        usable_count=usable_count,
        auto_max=payload[1],
        point_of_auto_max=payload[2],
        action_type=payload[3],
        timer_enabled=payload[4] == 1,
        timer_count=timer_count,
        timer_cruises=tuple(timer_cruises),
        auto_enabled=auto_enabled,
        auto_count=auto_count,
        auto_cruises=tuple(auto_cruises),
        auto_check_enabled=auto_check_enabled,
        auto_check_hour=auto_check_hour,
        auto_check_minute=auto_check_minute,
        auto_check_second=auto_check_second,
    )


def parse_white_light_config(payload: bytes) -> WhiteLightConfig:
    _require_length(payload, 12, "white-light configuration")

    total = payload[0]
    actions: list[WhiteLightAction] = []
    cursor = 6

    for _ in range(total):
        _require_available(payload, cursor, 7, "white-light action")
        actions.append(
            WhiteLightAction(
                action=payload[cursor],
                start_hour=payload[cursor + 1],
                start_minute=payload[cursor + 2],
                start_second=payload[cursor + 3],
                end_hour=payload[cursor + 4],
                end_minute=payload[cursor + 5],
                end_second=payload[cursor + 6],
            )
        )
        cursor += 7

    _require_available(payload, cursor, 6, "white-light switches")

    return WhiteLightConfig(
        total=total,
        default_action=payload[1],
        capability=_i32(payload, 2),
        actions=tuple(actions),
        main_switch=payload[cursor],
        motion_detection_switch=payload[cursor + 1],
        human_detection_switch=payload[cursor + 2],
        car_detection_switch=payload[cursor + 3],
        pet_detection_switch=payload[cursor + 4],
        alarm_warning_switch=payload[cursor + 5],
    )


def parse_private_mode_config(payload: bytes) -> PrivateModeConfig:
    _require_length(payload, 3, "private-mode configuration")

    timer_count = payload[2]
    cursor = 3
    timers: list[TimeWindow] = []

    for _ in range(timer_count):
        _require_available(payload, cursor, 6, "private-mode timer")
        timers.append(
            TimeWindow(
                enabled=True,
                start_hour=payload[cursor],
                start_minute=payload[cursor + 1],
                start_second=payload[cursor + 2],
                end_hour=payload[cursor + 3],
                end_minute=payload[cursor + 4],
                end_second=payload[cursor + 5],
            )
        )
        cursor += 6

    return PrivateModeConfig(
        enabled=payload[0] == 1,
        timer_enabled=payload[1] == 1,
        timer_count=timer_count,
        timers=tuple(timers),
    )


def parse_ai_human_detect_config(
    payload: bytes,
) -> AIHumanDetectConfig:
    _require_length(payload, 79, "AI human-detection configuration")

    alarm_times: list[TimeWindow] = []
    cursor = 6

    # JADX always parses three seven-byte time slots.
    for _ in range(3):
        alarm_times.append(
            TimeWindow(
                enabled=payload[cursor] == 1,
                start_hour=payload[cursor + 1],
                start_minute=payload[cursor + 2],
                start_second=payload[cursor + 3],
                end_hour=payload[cursor + 4],
                end_minute=payload[cursor + 5],
                end_second=payload[cursor + 6],
            )
        )
        cursor += 7

    rows = payload[27]
    columns = payload[28]
    area_count = rows * columns
    _require_available(payload, 29, area_count, "AI alarm-area map")

    return AIHumanDetectConfig(
        human_detect_enabled=payload[0],
        human_frame_enabled=payload[1],
        sensitivity=payload[2],
        sound_notice_enabled=payload[3],
        time_control_enabled=payload[4],
        time_setting_count=payload[5],
        alarm_times=tuple(alarm_times),
        area_rows=rows,
        area_columns=columns,
        alarm_area_indices=tuple(payload[29:29 + area_count]),
        ai_voice_type=payload[77],
        ai_light_detection=payload[78],
    )


def parse_time_backtracking_config(
    payload: bytes,
) -> TimeBacktrackingConfig:
    _require_length(payload, 1, "time-backtracking configuration")

    count = payload[0]
    cursor = 1
    entries: list[TimeBacktrackingEntry] = []

    for _ in range(count):
        _require_available(payload, cursor, 65, "time-backtracking entry")

        entries.append(
            TimeBacktrackingEntry(
                entry_type=payload[cursor],
                name=_cstring(payload, cursor + 1, 32, "utf-8"),
                start=_i32(payload, cursor + 33),
                start_real=_i32(payload, cursor + 41),
                end_offset=_i32(payload, cursor + 49),
                task_duration=_i32(payload, cursor + 53),
                task_shot_interval=_i32(payload, cursor + 57),
                next_task_interval=_i32(payload, cursor + 61),
            )
        )
        cursor += 65

    return TimeBacktrackingConfig(
        count=count,
        entries=tuple(entries),
    )


def parse_cpe_config(payload: bytes) -> CPEConfig:
    _require_length(payload, 1, "CPE configuration")
    return CPEConfig(enabled=payload[0])


def _truth(value: int) -> bool:
    return value != 0


def _signed_byte(value: int) -> int:
    return value - 256 if value >= 128 else value


def _i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _cstring(
    data: bytes,
    offset: int,
    size: int,
    encoding: str,
) -> str | None:
    field = data[offset:offset + size]
    value = field.split(b"\x00", 1)[0]

    if not value:
        return None

    try:
        return value.decode(encoding)
    except UnicodeDecodeError:
        return value.decode(encoding, errors="replace")


def _require_length(
    payload: bytes,
    minimum: int,
    label: str,
) -> None:
    if len(payload) < minimum:
        raise ValueError(
            f"{label.capitalize()} requires at least "
            f"{minimum} bytes; received {len(payload)}."
        )


def _require_available(
    payload: bytes,
    offset: int,
    size: int,
    label: str,
) -> None:
    if offset < 0 or offset + size > len(payload):
        raise ValueError(
            f"{label.capitalize()} exceeds the payload: "
            f"offset={offset}, size={size}, "
            f"payload={len(payload)}."
        )
