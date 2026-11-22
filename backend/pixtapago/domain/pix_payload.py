"""Leitura dos campos EMV usados no QR Code e no Pix Copia e Cola."""

from __future__ import annotations

import unicodedata


def emv_field(field_id: str, value: str) -> str:
    return f"{field_id}{len(value):02d}{value}"


def crc16_ccitt(payload: str) -> str:
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def create_static_pix_payload(pix_key: str, name: str) -> str:
    merchant = emv_field("00", "BR.GOV.BCB.PIX") + emv_field("01", pix_key)
    normalized_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().upper()[:25]
    payload = (
        emv_field("00", "01") + emv_field("01", "11") + emv_field("26", merchant)
        + emv_field("52", "0000") + emv_field("53", "986") + emv_field("58", "BR")
        + emv_field("59", normalized_name) + emv_field("60", "SAO PAULO")
        + emv_field("62", emv_field("05", "***")) + "6304"
    )
    return payload + crc16_ccitt(payload)


def parse_pix_payload(payload: str) -> dict:
    clean = payload.strip()
    if len(clean) < 20 or "6304" not in clean:
        raise ValueError("Informe um código Pix Copia e Cola válido.")

    crc_position = clean.rfind("6304")
    expected_crc = crc16_ccitt(clean[:crc_position + 4])
    received_crc = clean[crc_position + 4:crc_position + 8].upper()
    if expected_crc != received_crc:
        raise ValueError("O código Pix está com o verificador inválido.")

    fields = _parse_emv_fields(clean)
    merchant = _parse_emv_fields(fields.get("26", ""))
    pix_key = merchant.get("01")
    location = merchant.get("25")
    if not pix_key and not location:
        raise ValueError("Este código Pix não contém uma cobrança compatível.")

    amount = float(fields["54"]) if fields.get("54") else None
    return {
        "pixKey": pix_key,
        "location": location,
        "amount": amount,
        "payload": clean,
    }


def _parse_emv_fields(payload: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    cursor = 0
    while cursor + 4 <= len(payload):
        field_id = payload[cursor:cursor + 2]
        try:
            length = int(payload[cursor + 2:cursor + 4])
        except ValueError as error:
            raise ValueError("Código Pix inválido.") from error
        start = cursor + 4
        end = start + length
        if end > len(payload):
            raise ValueError("Código Pix incompleto.")
        fields[field_id] = payload[start:end]
        cursor = end
    return fields
